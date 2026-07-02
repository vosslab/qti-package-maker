"""
Shared image-asset layer for every reader and writer (frozen API).

File-reference-first design. Item content keeps the author's plain
`<img src="images/foo.jpg" alt="...">`; there is NO `asset:` scheme in item
content. A MediaAsset is a DERIVED resolution result (not durable state)
produced by scanning an item's HTML and resolving each `src` against a base
directory. Every engine consumes this one module so scanning, classification,
collision-safe naming, output rewriting, and policy warnings live in exactly
one place.

Frozen public API (downstream work packages are briefed from this):

	Policy value constants (the four media_policy outcomes):
		POLICY_PACKAGE, POLICY_REFERENCE_WARN, POLICY_PLACEHOLDER_WARN, POLICY_FAIL
		VALID_MEDIA_POLICIES -- tuple of the four values above

	Asset kind constants:
		KIND_LOCAL, KIND_EXTERNAL, KIND_DATA_URI

	MediaAsset (dataclass) -- portable record keyed by the in-content `src`:
		src            in-content src string; this is the identity
		kind           one of KIND_LOCAL / KIND_EXTERNAL / KIND_DATA_URI
		mime_type      e.g. "image/png"; None for external
		file_path      resolved absolute path (local assets only)
		data_bytes     in-memory / extracted payload (data-uri or added bytes)
		output_name    collision-safe output filename a writer will use
		content_hash   optional sha256 for dedup / collision / verification
		read_bytes()   returns the payload from data_bytes or file_path

	MediaWarning (dataclass) -- itemized warning: engine_name, item_crc, src, reason.
	MediaPolicyDecision (dataclass) -- policy, warnings list, placeholders map.
	MediaPolicyError (Exception) -- raised by the `fail` policy and read_bytes gaps.

	classify_src(src) -> str
	guess_mime_type(name) -> str                    (raises on unsupported mime)
	scan_html_for_assets(html_str) -> list[str]     (lxml.html, lenient fragment parse)
	resolve_local_path(base_dir, src) -> str        (raises: traversal escape)
	resolve_asset(src, base_dir=None) -> MediaAsset (raises: missing/traversal/mime)
	compute_content_hash(asset) -> str
	assign_output_names(assets) -> list[MediaAsset] (deterministic, path-identity)
	rewrite_html_srcs(html_str, src_map_fn) -> str  (WRITER OUTPUT ONLY)
	placeholder_text(asset) -> str
	apply_media_policy(policy, assets, engine_name, item_crc) -> MediaPolicyDecision

MIME support: PNG / JPEG / GIF are first-class; SVG is packaged but warned;
every other extension (e.g. `.webp`) raises. External URLs and data URIs are
never bundled by file-packaging engines; `apply_media_policy` is the single
channel that emits the external / data-uri / SVG warnings so every engine
surfaces them identically.

Additive helpers (extracted from byte-identical per-engine copies; not part of
the original freeze, but stable and shared going forward, same behavior):

	IMG_TAG_PATTERN, SRC_ATTR_PATTERN -- compiled `<img>` / `src=` regexes.
		SRC_ATTR_PATTERN excludes hyphenated pseudo-attrs (`data-src`, `lazy-src`)
		via a negative lookbehind, so only a real `src=` attribute matches.
	rewrite_field_value(value, src_map_fn) -> object
		Recursively rewrites `<img src>` in a string / list / dict field, same shape.
	rewrite_item_media(item_cls, src_map_fn) -> item_types.BaseItem
		Deep-copies an item and rewrites every HTML field's `<img src>` (writer
		output only; the bank's stored item is never mutated).
	raise_on_data_uri_assets(item_assets, engine_name, item_crc16) -> None
		Raises MediaPolicyError when a file-packaging engine is handed a data URI.
	make_src_map_fn(src_map) -> collections.abc.Callable[[str], str]
		Builds the src->writer-output callable that packaging engines hand to
		rewrite_item_media (unmapped srcs pass through unchanged).
"""

# Standard Library
import os
import re
import base64
import hashlib
import dataclasses
import urllib.parse
import collections.abc

# Pip3 Library
import lxml.html

# QTI Package Maker
from qti_package_maker.assessment_items import item_types

# Frozen media_policy values. Every engine declares one; every image routes
# through exactly one of these four outcomes.
POLICY_PACKAGE = "package"
POLICY_REFERENCE_WARN = "reference_warn"
POLICY_PLACEHOLDER_WARN = "placeholder_warn"
POLICY_FAIL = "fail"
VALID_MEDIA_POLICIES = (
	POLICY_PACKAGE,
	POLICY_REFERENCE_WARN,
	POLICY_PLACEHOLDER_WARN,
	POLICY_FAIL,
)

# Asset kind classification of an in-content src.
KIND_LOCAL = "local"
KIND_EXTERNAL = "external"
KIND_DATA_URI = "data-uri"

# First-class raster image types: extension -> MIME.
SUPPORTED_IMAGE_EXTENSIONS = {
	".png": "image/png",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".gif": "image/gif",
}

# Packaged but flagged as LMS-uncertain: extension -> MIME.
WARN_IMAGE_EXTENSIONS = {
	".svg": "image/svg+xml",
}

# MIME for SVG, used to route the uncertain-support warning.
SVG_MIME_TYPE = "image/svg+xml"

#========================================================
class MediaPolicyError(Exception):
	"""Raised when a media policy forbids an image (fail) or a payload is missing."""

#========================================================
@dataclasses.dataclass
class MediaAsset:
	"""
	Portable, derived image record keyed by the in-content src.

	The record repackages from either a resolved file path (file-authored input)
	or in-memory bytes (data URI, extracted ZIP payload, or add_image). The src
	is the identity; content_hash is an optional aid for dedup / collision /
	verification and is never the identity.
	"""
	src: str
	kind: str
	mime_type: str | None = None
	file_path: str | None = None
	data_bytes: bytes | None = None
	output_name: str | None = None
	content_hash: str | None = None

	#----------------------------------------------------
	def read_bytes(self) -> bytes:
		"""
		Return the asset payload from in-memory bytes or the resolved file path.

		Raises:
			MediaPolicyError: the asset has no resolvable payload (e.g. external).
		"""
		# in-memory payload wins (data URI, extracted ZIP bytes, added bytes)
		if self.data_bytes is not None:
			return self.data_bytes
		# otherwise read lazily from the resolved local file
		if self.file_path is not None:
			with open(self.file_path, "rb") as file_pointer:
				file_data = file_pointer.read()
			return file_data
		raise MediaPolicyError(
			f"MediaAsset '{self.src}' (kind={self.kind}) has no resolvable payload to read"
		)

#========================================================
@dataclasses.dataclass
class MediaWarning:
	"""Itemized media warning; one per (engine, item, src, reason)."""
	engine_name: str
	item_crc: str
	src: str
	reason: str

	#----------------------------------------------------
	def __str__(self) -> str:
		# single readable line an engine can print directly
		warning_line = f"[{self.engine_name}] item {self.item_crc}: {self.src} -- {self.reason}"
		return warning_line

#========================================================
@dataclasses.dataclass
class MediaPolicyDecision:
	"""
	Result of apply_media_policy for one item.

	policy is the engine's declared value; warnings are the itemized warnings to
	surface; placeholders maps src -> readable placeholder text (populated only
	for the placeholder_warn policy).
	"""
	policy: str
	warnings: list
	placeholders: dict

#========================================================
def classify_src(src: str) -> str:
	"""
	Classify an in-content src as local, external, or a data URI.

	Args:
		src: the raw `src` attribute value from an `<img>` tag.

	Returns:
		One of KIND_LOCAL, KIND_EXTERNAL, KIND_DATA_URI.
	"""
	stripped = src.strip()
	lowered = stripped.lower()
	# inline data URIs carry their own payload
	if lowered.startswith("data:"):
		return KIND_DATA_URI
	# absolute web references are never bundled
	if lowered.startswith("http://") or lowered.startswith("https://"):
		return KIND_EXTERNAL
	# protocol-relative URLs are also external
	if lowered.startswith("//"):
		return KIND_EXTERNAL
	# everything else is a local file reference relative to the base dir
	return KIND_LOCAL

#========================================================
def guess_mime_type(name: str) -> str:
	"""
	Map a filename or src to a supported image MIME type.

	PNG / JPEG / GIF are first-class; SVG is allowed (warned later); every other
	extension raises so unsupported media fails loudly.

	Args:
		name: a filename, src, or output name carrying an extension.

	Returns:
		The MIME type string.

	Raises:
		ValueError: the extension is not a supported image type.
	"""
	# lowercase extension drives the lookup
	extension = os.path.splitext(name)[1].lower()
	if extension in SUPPORTED_IMAGE_EXTENSIONS:
		return SUPPORTED_IMAGE_EXTENSIONS[extension]
	if extension in WARN_IMAGE_EXTENSIONS:
		return WARN_IMAGE_EXTENSIONS[extension]
	raise ValueError(
		f"unsupported image type '{extension}' for '{name}'; "
		f"supported: png, jpg, jpeg, gif (svg packaged with a warning)"
	)

#========================================================
def scan_html_for_assets(html_str: str) -> list[str]:
	"""
	Find every `<img src>` in an arbitrary HTML field via lxml.

	Shares validator.validate_html's intent of tolerating arbitrary real-world
	item HTML, but not its mechanism: this scanner uses the lenient
	lxml.html.fragment_fromstring parser, while the validator runs a stricter
	lxml.etree.fromstring pipeline over cleaned XML. Returns src strings in
	document order and may contain duplicates; the caller resolves and dedups
	them.

	Args:
		html_str: an HTML-bearing item field (question text, a choice, etc.).

	Returns:
		List of `src` strings from `<img>` tags, in document order.
	"""
	# fast exit avoids parsing fields that carry no image
	if not html_str or "<img" not in html_str.lower():
		return []
	# wrap the fragment so mixed text/element content parses cleanly
	fragment = lxml.html.fragment_fromstring(html_str, create_parent="div")
	src_list = []
	# walk every <img> descendant in document order
	for img_element in fragment.iter("img"):
		src_value = img_element.get("src")
		if src_value is None:
			continue
		src_value = src_value.strip()
		if src_value:
			src_list.append(src_value)
	return src_list

#========================================================
def _parse_data_uri(src: str) -> tuple:
	"""
	Split a data URI into its MIME type and decoded payload bytes.

	Args:
		src: a `data:[<mime>][;base64],<payload>` string.

	Returns:
		Tuple of (mime_type, payload_bytes).
	"""
	# separate the metadata header from the payload at the first comma
	header, _, payload = src.partition(",")
	# strip the leading "data:" scheme marker
	meta = header[len("data:"):]
	# detect and remove the base64 marker
	is_base64 = meta.endswith(";base64")
	if is_base64:
		meta = meta[:-len(";base64")]
	# the MIME type is the first token; default when omitted
	mime_type = meta.split(";")[0]
	if not mime_type:
		mime_type = "application/octet-stream"
	# decode the payload according to its transfer encoding
	if is_base64:
		payload_bytes = base64.b64decode(payload)
	else:
		payload_bytes = urllib.parse.unquote_to_bytes(payload)
	return mime_type, payload_bytes

#========================================================
def resolve_local_path(base_dir: str, src: str) -> str:
	"""
	Resolve a local src against a base directory, rejecting path traversal.

	Shared traversal guard: resolve_asset() and ItemBank.add_image() both need
	the identical abspath+normpath+startswith check before touching the
	filesystem, so it lives here once rather than duplicated at each call site.

	Args:
		base_dir: directory the resolved path must stay within.
		src: the relative path to resolve (an in-content src or caller path).

	Returns:
		The resolved absolute path.

	Raises:
		ValueError: the resolved path escapes base_dir.
	"""
	# resolve to an absolute path and reject traversal that escapes base_dir
	base_abs = os.path.abspath(base_dir)
	resolved_path = os.path.normpath(os.path.join(base_abs, src))
	if resolved_path != base_abs and not resolved_path.startswith(base_abs + os.sep):
		raise ValueError(f"path '{src}' escapes the base directory '{base_dir}'")
	return resolved_path

#========================================================
def resolve_asset(src: str, base_dir: str | None = None) -> MediaAsset:
	"""
	Resolve an in-content src into a MediaAsset record.

	Local files are resolved against base_dir; external URLs and data URIs are
	recorded without touching the filesystem. The output_name defaults to the
	src basename for local assets and is refined by assign_output_names when a
	whole set is known.

	Args:
		src: the raw `<img src>` value.
		base_dir: directory that local srcs resolve against (required for local).

	Returns:
		A MediaAsset record.

	Raises:
		ValueError: local src without base_dir, traversal escape, or bad mime.
		FileNotFoundError: a local file that does not exist.
	"""
	kind = classify_src(src)
	# external references carry no payload and are never bundled
	if kind == KIND_EXTERNAL:
		return MediaAsset(src=src, kind=kind)
	# data URIs carry their own decoded payload and MIME
	if kind == KIND_DATA_URI:
		mime_type, payload_bytes = _parse_data_uri(src)
		return MediaAsset(src=src, kind=kind, mime_type=mime_type, data_bytes=payload_bytes)
	# local file: base_dir is mandatory
	if base_dir is None:
		raise ValueError(f"cannot resolve local image '{src}' without a base directory")
	resolved_path = resolve_local_path(base_dir, src)
	# supported-mime check fires before existence so `.webp` reports its own error
	mime_type = guess_mime_type(src)
	# the local file must exist; name it in the error for the author
	if not os.path.isfile(resolved_path):
		raise FileNotFoundError(f"image file not found for src '{src}': {resolved_path}")
	# provisional output name is the basename; assign_output_names refines it
	output_name = os.path.basename(src)
	resolved_asset = MediaAsset(
		src=src,
		kind=kind,
		mime_type=mime_type,
		file_path=resolved_path,
		output_name=output_name,
	)
	return resolved_asset

#========================================================
def compute_content_hash(asset: MediaAsset) -> str:
	"""
	Compute the sha256 hex digest of an asset payload.

	The hash is an optional aid for dedup, collision detection, and byte
	verification. It is never the asset identity (the src is).

	Args:
		asset: a MediaAsset with a resolvable payload.

	Returns:
		The hex sha256 digest string.
	"""
	# read the payload once and hash it
	payload_bytes = asset.read_bytes()
	digest = hashlib.sha256(payload_bytes).hexdigest()
	return digest

#========================================================
def assign_output_names(assets: list) -> list:
	"""
	Assign deterministic, collision-safe output names to file-backed assets.

	Identity is the src: assets sharing a src share one output name (natural
	dedup). Distinct srcs that share a basename get a deterministic disambiguating
	suffix (e.g. `foo.png` and `foo(1).png`), so `images/foo.png` and
	`figures/foo.png` never collide while path identity is preserved. External
	and data-uri assets are left with output_name unchanged (they produce no
	bundled file in the file-packaging engines).

	Args:
		assets: MediaAsset records to name (may repeat srcs across items/fields).

	Returns:
		The same list, with output_name populated on file-backed assets.
	"""
	# collapse to one representative asset per src, first occurrence wins
	first_asset_by_src = {}
	for asset in assets:
		if asset.src not in first_asset_by_src:
			first_asset_by_src[asset.src] = asset
	# name only file-backed assets; deterministic order by src
	name_by_src = {}
	used_names = set()
	for src in sorted(first_asset_by_src):
		asset = first_asset_by_src[src]
		# skip assets that never become a bundled file
		if asset.file_path is None:
			continue
		# start from the natural basename and disambiguate on collision
		base_name = os.path.basename(src)
		candidate_name = base_name
		collision_counter = 1
		while candidate_name in used_names:
			root, extension = os.path.splitext(base_name)
			candidate_name = f"{root}({collision_counter}){extension}"
			collision_counter += 1
		used_names.add(candidate_name)
		name_by_src[src] = candidate_name
	# propagate the resolved name back to every instance sharing that src
	for asset in assets:
		if asset.src in name_by_src:
			asset.output_name = name_by_src[asset.src]
	return assets

#========================================================
# match a whole <img ...> tag; rewriting is scoped inside each tag only
IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
# match a quoted src="..." (or src='...') attribute inside an <img> tag; the
# negative lookbehind requires "src" to not be preceded by a word char or a
# hyphen, so "data-src=" / "lazy-src=" pseudo-attrs are never matched (a plain
# \b boundary would match there too, since "-" is a non-word character).
SRC_ATTR_PATTERN = re.compile(
	r"""((?<![\w-])src\s*=\s*)(["'])(.*?)\2""", re.IGNORECASE | re.DOTALL
)

def rewrite_html_srcs(html_str: str, src_map_fn: collections.abc.Callable[[str], str]) -> str:
	"""
	Rewrite every `<img src>` in WRITER OUTPUT via a mapping function.

	This is used ONLY on writer output (never on stored item content): it maps
	each in-content src to the writer's platform path. The rewrite is surgical
	(regex-scoped to `<img>` tags), so all surrounding HTML is preserved exactly.

	Args:
		html_str: the writer's HTML string containing `<img>` tags.
		src_map_fn: callable mapping an old src to its new src.

	Returns:
		The HTML string with `<img src>` values remapped.
	"""
	#----------------------------------------------------
	def _rewrite_src_attribute(src_match: re.Match) -> str:
		# rebuild the src attribute with the mapped value, preserving the quote
		attr_prefix = src_match.group(1)
		quote_char = src_match.group(2)
		old_src = src_match.group(3)
		new_src = src_map_fn(old_src)
		rewritten_attr = f"{attr_prefix}{quote_char}{new_src}{quote_char}"
		return rewritten_attr

	#----------------------------------------------------
	def _rewrite_img_tag(tag_match: re.Match) -> str:
		# only touch the src attribute within this single <img> tag
		img_tag = tag_match.group(0)
		rewritten_tag = SRC_ATTR_PATTERN.sub(_rewrite_src_attribute, img_tag)
		return rewritten_tag

	rewritten_html = IMG_TAG_PATTERN.sub(_rewrite_img_tag, html_str)
	return rewritten_html

#========================================================
def rewrite_field_value(
			value: object,
			src_map_fn: collections.abc.Callable[[str], str]) -> object:
	"""
	Recursively rewrite `<img src>` values inside an item field, preserving shape.

	Item fields hold plain strings, lists of strings (choices/answers), or dicts
	whose values are strings (answer maps); non-string scalars carry no HTML.

	Args:
		value: a supporting-field value from an item.
		src_map_fn: maps an in-content src to its writer-output src.

	Returns:
		The value with every string leaf's `<img src>` rewritten, same shape.
	"""
	if isinstance(value, str):
		return rewrite_html_srcs(value, src_map_fn)
	if isinstance(value, list):
		return [rewrite_field_value(element, src_map_fn) for element in value]
	if isinstance(value, dict):
		return {key: rewrite_field_value(element, src_map_fn) for key, element in value.items()}
	return value

#========================================================
def rewrite_item_media(
			item_cls: item_types.BaseItem,
			src_map_fn: collections.abc.Callable[[str], str]) -> item_types.BaseItem:
	"""
	Return a deep-copied item with every HTML field's `<img src>` rewritten.

	Writer-output rewriting only: the bank's stored item is never mutated, and
	item identity (item_crc16 and its CRC components) is preserved from the
	copy, so the src rewrite changes only the emitted output, not item identity.

	Args:
		item_cls: the stored item to render.
		src_map_fn: maps an in-content src to its writer-output src.

	Returns:
		A rewritten copy safe to hand to the per-type write function.
	"""
	rewritten_item = item_cls.copy()
	rewritten_item.question_text = rewrite_html_srcs(item_cls.question_text, src_map_fn)
	for field_name in item_cls.get_supporting_field_names():
		original_value = getattr(item_cls, field_name)
		setattr(rewritten_item, field_name, rewrite_field_value(original_value, src_map_fn))
	return rewritten_item

#========================================================
def make_src_map_fn(src_map: dict) -> collections.abc.Callable[[str], str]:
	"""
	Return a src-mapping callable backed by src_map for rewrite_item_media.

	Packaging engines build a per-item `{in_content_src: writer_output_src}`
	map, then hand this callable to rewrite_item_media. An src absent from the
	map passes through unchanged (that pass-through is the intended default,
	not a hidden fallback), so external and unresolved references are left as-is.

	Args:
		src_map: maps an in-content src to its writer-output src.

	Returns:
		A callable taking one src string and returning the mapped src.
	"""
	#--------------
	def src_map_fn(old_src: str) -> str:
		return src_map.get(old_src, old_src)
	return src_map_fn

#========================================================
def raise_on_data_uri_assets(item_assets: list, engine_name: str, item_crc16: str) -> None:
	"""
	Raise if any referenced asset is a data URI; a packaging engine needs a file.

	Args:
		item_assets: resolved MediaAsset records referenced by the item.
		engine_name: the engine name, used in the error message.
		item_crc16: the item CRC, used in the error message.

	Raises:
		MediaPolicyError: one or more assets is a data URI.
	"""
	data_uri_srcs = [asset.src for asset in item_assets if asset.kind == KIND_DATA_URI]
	if data_uri_srcs:
		offending = ", ".join(data_uri_srcs)
		raise MediaPolicyError(
			f"engine '{engine_name}' cannot package a data URI image; item {item_crc16} "
			f"references: {offending}. Supply a file-backed <img src> instead."
		)

#========================================================
def _readable_name(asset: MediaAsset) -> str:
	"""
	Return a short human-readable name for placeholders and warnings.

	Args:
		asset: the MediaAsset to name.

	Returns:
		The output name, src basename, or a generic label for embedded data.
	"""
	# a resolved output name is the clearest label
	if asset.output_name:
		return asset.output_name
	# embedded data URIs have no filename; give a generic label
	if asset.kind == KIND_DATA_URI:
		return "embedded image"
	# derive a basename from a local path or external URL, ignoring queries
	src_path = asset.src.split("?")[0].rstrip("/")
	base_name = os.path.basename(src_path)
	if base_name:
		return base_name
	return asset.src

#========================================================
def placeholder_text(asset: MediaAsset) -> str:
	"""
	Return the readable placeholder string for a markup-free format.

	Args:
		asset: the MediaAsset being replaced.

	Returns:
		A `[image: name.ext]` placeholder string.
	"""
	readable = _readable_name(asset)
	placeholder = f"[image: {readable}]"
	return placeholder

#========================================================
def _package_warning_reason(asset: MediaAsset, engine_name: str) -> str | None:
	"""
	Return the itemized package-policy warning reason for an asset, or None.

	First-class raster images bundle cleanly and need no warning; external URLs,
	data URIs, and SVGs each get their standard caution.

	Args:
		asset: the MediaAsset under a package-policy engine.
		engine_name: the engine emitting the warning.

	Returns:
		A reason string, or None when the asset packages without caution.
	"""
	# external references are kept verbatim, never copied into the package
	if asset.kind == KIND_EXTERNAL:
		return "external image URL kept verbatim; not bundled into the package"
	# data URIs cannot be written as a file resource by file-packaging engines
	if asset.kind == KIND_DATA_URI:
		return f"data URI image cannot be bundled as a file by {engine_name}"
	# SVG is packaged but its LMS import support is not guaranteed
	if asset.mime_type == SVG_MIME_TYPE:
		return "SVG image bundled, but LMS support is not guaranteed"
	# first-class raster images bundle cleanly, no warning
	return None

#========================================================
def apply_media_policy(
			policy: str,
			assets: list,
			engine_name: str,
			item_crc: str) -> MediaPolicyDecision:
	"""
	Route one item's images through exactly one of the four media policies.

	This is the single channel for external-URL, data-URI, and SVG warnings, so
	every engine surfaces them identically. The `fail` policy raises when any
	image is present (Ultra strict). `reference_warn` keeps references verbatim
	with an itemized warning; `placeholder_warn` supplies readable placeholder
	text with an itemized warning; `package` warns only on external / data-uri /
	SVG edge cases (first-class raster images bundle silently).

	Args:
		policy: one of VALID_MEDIA_POLICIES.
		assets: resolved MediaAsset records referenced by the item.
		engine_name: the engine name for itemized warnings.
		item_crc: the item CRC for itemized warnings.

	Returns:
		A MediaPolicyDecision carrying the policy, warnings, and placeholders.

	Raises:
		ValueError: an unknown policy value.
		MediaPolicyError: the `fail` policy with one or more images present.
	"""
	# an unknown policy is a programming error, not an author error
	if policy not in VALID_MEDIA_POLICIES:
		raise ValueError(f"unknown media policy '{policy}'; valid: {VALID_MEDIA_POLICIES}")
	# fail policy: any image at all is fatal (Ultra strict)
	if policy == POLICY_FAIL:
		if assets:
			offending_srcs = ", ".join(asset.src for asset in assets)
			raise MediaPolicyError(
				f"engine '{engine_name}' forbids images; item {item_crc} references: {offending_srcs}"
			)
		return MediaPolicyDecision(policy=policy, warnings=[], placeholders={})
	# build itemized warnings (and placeholders) per asset
	warnings = []
	placeholders = {}
	for asset in assets:
		reason = None
		if policy == POLICY_REFERENCE_WARN:
			# reference kept verbatim; files are not transported by this engine
			reason = f"image reference kept verbatim; {engine_name} does not transport image files"
		elif policy == POLICY_PLACEHOLDER_WARN:
			# markup-free format: substitute a readable placeholder
			reason = f"image replaced with a text placeholder; {engine_name} format carries no image markup"
			placeholders[asset.src] = placeholder_text(asset)
		elif policy == POLICY_PACKAGE:
			# only edge content (external / data-uri / svg) warns under package
			reason = _package_warning_reason(asset, engine_name)
		if reason is not None:
			warnings.append(MediaWarning(engine_name, item_crc, asset.src, reason))
	decision = MediaPolicyDecision(policy=policy, warnings=warnings, placeholders=placeholders)
	return decision
