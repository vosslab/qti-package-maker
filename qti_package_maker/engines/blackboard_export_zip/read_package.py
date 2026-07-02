"""
Read a Blackboard Original pool-export package back into an ItemBank.

This module is the inverse of the write path (the per-type `<item>` builder
modules `MC.py`/`MA.py`/`MATCH.py`/`FIB.py`/`NUM.py`/`MULTI_FIB.py` plus their
shared `common_xml.py`, wrapped by `assessment_meta.py`). It accepts either a
Blackboard pool-export ZIP
(`Pool_ExportFile_*.zip`) or an already-unzipped pool directory, locates the
`assessment/x-bb-qti-pool` resource through `imsmanifest.xml`, and parses each
`<item>` in the pool `.dat` into an internal `item_types.*` instance.

The pool dialect is the QTI-1.2-derived envelope with Blackboard extensions
that the per-type builder modules write (and that the real sample pools under
`BB_Export_ZIP/` carry). The reader keys each item on its `<bbmd_questiontype>`
ELEMENT value (not an attribute), recovers question/choice HTML by reading the
`mat_formattedtext` element text (lxml un-escapes it once, reversing the
single-escape the write path applies), and recovers correct answers from the
`resprocessing` `varequal` conditions.

Type dispatch (from the forgeability audit and the real samples):

- `Multiple Choice` -> MC when the choice `response_lid` is `rcardinality="Single"`,
  MA when it is `rcardinality="Multiple"`.
- `Multiple Answer` -> MA.
- `Fill in the Blank` -> FIB (one `response_str` + per-answer `varequal`).
- `Numeric` -> NUM (answer from `varequal`, tolerance from the vargte/varlte window).
- `Fill in the Blank Plus` -> MULTI_FIB (per-blank `respident` keys, `<and>` of `<or>`).
- `Matching` -> MATCH (prompt->choice pairing recovered via each prompt
  `response_lid` ident's `varequal` answer ident, mapped back to its position
  and the `RIGHT_MATCH_BLOCK` text).
- `True/False` -> MC (the internal model has no T/F type).

Edge cases are surfaced, never silently swallowed: a missing or empty manifest
pool entry raises; multiple pool resources are read into one combined ItemBank;
an unparseable item is skipped with a warning naming its source; an unknown
`bbmd_questiontype` is skipped with a warning naming the type and source item;
duplicate `item_crc16` collisions are handled by `ItemBank` dedup (logged there).

Image capture: a pool carries images through two independent
mechanisms, both resolved before any item is parsed so extraction does not
depend on which item types the dispatch table supports. The csfiles
mechanism embeds `<img src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/
xid-<n>_1">` tokens directly in item HTML; each token is cross-checked
against a `res00005.dat`-shaped CSResourceLinks resource, resolved to the
binary at `csfiles/home_dir/__xid-<n>_1.<ext>`, and named from the LOM
sidecar `csfiles/home_dir/__xid-<n>_1.<ext>.xml`. The hotspot mechanism wires
a `<matapplication uri="<hash>/<file>">` element (manifest-tracked) to a file
under the pool resource's own directory (its manifest `xml:base`). Every
resolved binary is copied into one fresh, persistent extraction directory
under its recovered plain filename (collision-safe); `ItemBank.media_base_dir`
is pointed at that directory (via `set_media_base_dir(media_dir, owned=True)`,
so the bank owns and will remove it) and each parsed item's HTML is rewritten
from the `@X@...` token to the plain recovered filename, so an imported
package takes on the same shape as file-authored input and flows through the
identical derived resolver in `ItemBank.collect_assets()`.

When a pool carries images, the returned bank owns its extraction directory;
call `bank.cleanup()` once done with an image-bearing imported bank to remove
that directory. Pools with no images (the common case) return a bank with no
directory to clean up, so calling `cleanup()` unconditionally is always safe.
"""

# Standard Library
import os
import re
import shutil
import zipfile
import tempfile
import collections.abc

# PIP3 modules
import lxml.html
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types
from qti_package_maker.common import media_assets
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
# Manifest / namespace constants
#============================================
# Blackboard's content-packaging namespace; the manifest declares it as `bb:`.
BB_NAMESPACE = "http://www.blackboard.com/content-packaging/"
# The W3C XML namespace that carries the `xml:base` attribute on a resource.
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
# The manifest resource that carries the question pool.
POOL_RESOURCE_TYPE = "assessment/x-bb-qti-pool"
# The manifest resource that carries the csfiles xid -> item CSResourceLinks.
CSRESOURCELINKS_RESOURCE_TYPE = "course/x-bb-csresourcelinks"
# The manifest filename inside every pool package.
MANIFEST_FILENAME = "imsmanifest.xml"

#============================================
# Image capture constants
#============================================
# Matches a whole csfiles token (the part after common_xml.CSFILES_SRC_PREFIX)
# anywhere in raw pool text, capturing just the "xid-<n>_1" identifier.
CSFILES_TOKEN_PATTERN = re.compile(
	re.escape(common_xml.CSFILES_SRC_PREFIX) + r"(xid-\d+_\d+)")
# csfiles binaries and their LOM sidecars live under this subdirectory of the
# pool package root.
CSFILES_HOME_SUBDIR = os.path.join("csfiles", "home_dir")
# The LOM namespace on the `.jpg.xml` sidecar's <identifier> element.
LOM_NAMESPACE = "http://www.imsglobal.org/xsd/imsmd_rootv1p2p1"

#============================================
# Public entry point
#============================================
#============================================
def read_items_from_file(infile: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	"""
	Read a Blackboard pool-export package (ZIP or directory) into an ItemBank.

	Args:
		infile: Path to a Blackboard pool-export ZIP or an unzipped pool directory.
		allow_mixed: When True, the returned ItemBank accepts mixed item types
			(pool exports are frequently mixed, e.g. MC + MATCH in one pool).

	Returns:
		An ItemBank holding every parsed item from every pool resource in the
		package. When the pool carries images, the bank owns its media
		extraction directory (see the module docstring); call
		`item_bank.cleanup()` once done with the returned bank.
	"""
	# A ZIP needs extracting first; a directory is read in place.
	if zipfile.is_zipfile(infile):
		new_item_bank = _read_from_zip(infile, allow_mixed)
	elif os.path.isdir(infile):
		new_item_bank = _read_from_directory(infile, allow_mixed)
	else:
		raise ValueError(
			f"Input is neither a ZIP file nor a directory: '{infile}'"
		)
	return new_item_bank

#============================================
def _read_from_zip(zip_path: str, allow_mixed: bool) -> item_bank.ItemBank:
	"""
	Extract a pool-export ZIP to a temp directory and read it.

	Args:
		zip_path: Path to the pool-export ZIP.
		allow_mixed: Passed through to the ItemBank.

	Returns:
		The parsed ItemBank.
	"""
	# Extract into a self-cleaning temp directory, then read it as a directory.
	# Any recovered media is copied out to its own persistent directory before
	# this temp directory is cleaned up (see _extract_pool_media).
	with tempfile.TemporaryDirectory() as temp_dir:
		with zipfile.ZipFile(zip_path, "r") as zip_file:
			_safe_extract_zip(zip_file, temp_dir)
		# Some exports nest the package one folder deep inside the ZIP; resolve
		# to whichever directory actually holds the manifest.
		pool_root = _find_manifest_root(temp_dir)
		new_item_bank = _read_from_directory(pool_root, allow_mixed)
	return new_item_bank

#============================================
def _safe_extract_zip(zip_file: zipfile.ZipFile, dest_dir: str) -> None:
	"""
	Extract every entry of zip_file into dest_dir, rejecting path traversal.

	Every member's resolved destination path is validated to stay within
	dest_dir BEFORE anything is written, so a malicious "../" entry name
	(zip-slip) raises instead of writing outside the extraction directory.

	Args:
		zip_file: An open ZipFile to extract.
		dest_dir: The directory every entry must resolve inside of.

	Raises:
		ValueError: a member's path would escape dest_dir.
	"""
	dest_abs = os.path.abspath(dest_dir)
	for member in zip_file.infolist():
		member_path = os.path.normpath(os.path.join(dest_abs, member.filename))
		if member_path != dest_abs and not member_path.startswith(dest_abs + os.sep):
			raise ValueError(
				f"zip entry '{member.filename}' escapes the extraction directory"
			)
	zip_file.extractall(dest_abs)

#============================================
def _find_manifest_root(start_dir: str) -> str:
	"""
	Find the directory that holds `imsmanifest.xml` within an extracted tree.

	Args:
		start_dir: The directory to search from.

	Returns:
		The directory path containing the manifest.
	"""
	# Fast path: the manifest sits directly in start_dir.
	if os.path.isfile(os.path.join(start_dir, MANIFEST_FILENAME)):
		return start_dir
	# Otherwise walk until the manifest is found (handles single-folder nesting).
	for current_dir, _subdirs, filenames in os.walk(start_dir):
		if MANIFEST_FILENAME in filenames:
			return current_dir
	raise ValueError(
		f"No {MANIFEST_FILENAME} found in extracted package under '{start_dir}'"
	)

#============================================
def _read_from_directory(pool_dir: str, allow_mixed: bool) -> item_bank.ItemBank:
	"""
	Read an unzipped pool directory into an ItemBank.

	Args:
		pool_dir: A directory containing `imsmanifest.xml` and the pool `.dat`.
		allow_mixed: Passed through to the ItemBank.

	Returns:
		The parsed ItemBank.
	"""
	manifest_path = os.path.join(pool_dir, MANIFEST_FILENAME)
	if not os.path.isfile(manifest_path):
		raise ValueError(
			f"Missing {MANIFEST_FILENAME} in pool directory '{pool_dir}'"
		)
	# Resolve every pool resource the manifest declares (usually one).
	pool_dat_names = _find_pool_dat_filenames(manifest_path)
	if not pool_dat_names:
		raise ValueError(
			f"Manifest '{manifest_path}' declares no '{POOL_RESOURCE_TYPE}' resource"
		)
	new_item_bank = item_bank.ItemBank(allow_mixed)
	# Extract every referenced image into a fresh persistent directory BEFORE
	# parsing items, so extraction covers the whole pool regardless of which
	# item types the dispatch table supports (see module docstring).
	media_dir, src_map_fn = _extract_pool_media(pool_dir, manifest_path, pool_dat_names)
	if media_dir is not None:
		# This bank created media_dir (see _extract_pool_media); mark it owned
		# so cleanup() removes it once the caller is done with the bank,
		# instead of leaking one tempfile.mkdtemp() directory per read.
		new_item_bank.set_media_base_dir(media_dir, owned=True)
	# Read every pool resource into one combined bank.
	for pool_dat_name in pool_dat_names:
		pool_dat_path = os.path.join(pool_dir, pool_dat_name)
		if not os.path.isfile(pool_dat_path):
			raise ValueError(
				f"Manifest points to missing pool file '{pool_dat_name}' in '{pool_dir}'"
			)
		_parse_pool_into_bank(pool_dat_path, new_item_bank, src_map_fn)
	return new_item_bank

#============================================
def _find_pool_dat_filenames(manifest_path: str) -> list[str]:
	"""
	Read the manifest and return every pool resource's `.dat` filename.

	The pool resource is identified by `type="assessment/x-bb-qti-pool"`; its
	`.dat` filename is the namespaced `bb:file` attribute, not the resource id.

	Args:
		manifest_path: Path to `imsmanifest.xml`.

	Returns:
		The pool `.dat` filenames, in manifest order.
	"""
	tree = lxml.etree.parse(manifest_path)
	root = tree.getroot()
	bb_file_attr = f"{{{BB_NAMESPACE}}}file"
	pool_dat_names = []
	# Scan every <resource>; keep those typed as the BB pool.
	for resource in root.iter("resource"):
		if resource.get("type") != POOL_RESOURCE_TYPE:
			continue
		dat_filename = resource.get(bb_file_attr)
		# A pool resource with no bb:file is malformed; surface it rather than
		# silently dropping the only pool the package carries.
		if not dat_filename:
			raise ValueError(
				f"Pool resource in '{manifest_path}' has no bb:file attribute"
			)
		pool_dat_names.append(dat_filename)
	return pool_dat_names

#============================================
# Image capture
#============================================
#============================================
def _extract_pool_media(
	pool_dir: str,
	manifest_path: str,
	pool_dat_names: list[str],
) -> tuple[str | None, collections.abc.Callable[[str], str]]:
	"""
	Extract every csfiles and hotspot image referenced by the pool(s).

	Scans the raw pool text for csfiles tokens and the parsed pool tree for
	`<matapplication>` elements, independent of whether the enclosing item's
	`bbmd_questiontype` is dispatchable, so extraction covers the whole
	package. When at least one image is found, every resolved binary is
	copied into one fresh persistent directory under a collision-safe
	recovered filename.

	Args:
		pool_dir: The pool package root (contains imsmanifest.xml).
		manifest_path: Path to imsmanifest.xml.
		pool_dat_names: The pool `.dat` filenames declared by the manifest.

	Returns:
		A tuple of (media_dir, src_map_fn). media_dir is None and src_map_fn
		is the identity function when the pool carries no images at all
		(existing no-image behavior stays untouched).
	"""
	# desired_name_by_key maps a stable identity (csfiles token or
	# matapplication uri) to its recovered/label basename, before collision
	# disambiguation; source_path_by_key maps the same identity to the
	# on-disk file to copy.
	desired_name_by_key: dict[str, str] = {}
	source_path_by_key: dict[str, str] = {}
	csfiles_tokens: set[str] = set()

	for pool_dat_name in pool_dat_names:
		pool_dat_path = os.path.join(pool_dir, pool_dat_name)
		csfiles_tokens.update(_scan_csfiles_tokens(pool_dat_path))
		pool_base_dir = _find_pool_resource_base_dir(manifest_path, pool_dat_name)
		for uri, label in _scan_matapplication_refs(pool_dat_path):
			if uri in source_path_by_key:
				continue
			source_path_by_key[uri] = _resolve_package_relative_path(
				pool_dir, os.path.join(pool_base_dir, uri)
			)
			desired_name_by_key[uri] = label

	if csfiles_tokens:
		# Only require the CSResourceLinks resource to exist when a csfiles
		# token was actually found; packages with no csfiles images (e.g. the
		# minimal test manifests) need not declare or ship res00005.dat.
		resource_id_set = _load_csresourcelinks_ids(manifest_path, pool_dir)
		for token in csfiles_tokens:
			resource_id = token[len("xid-"):]
			if resource_id not in resource_id_set:
				raise ValueError(
					f"csfiles token '{token}' has no matching resourceId in the "
					f"CSResourceLinks manifest resource"
				)
			binary_path, sidecar_path = _find_csfiles_files(pool_dir, token)
			source_path_by_key[token] = binary_path
			desired_name_by_key[token] = _recover_original_filename(sidecar_path)

	if not desired_name_by_key:
		return None, _identity_src_map

	output_name_by_key = _assign_collision_safe_names(desired_name_by_key)
	media_dir = tempfile.mkdtemp(prefix="qti_bbexport_media_")
	for key, source_path in source_path_by_key.items():
		dest_path = os.path.join(media_dir, output_name_by_key[key])
		shutil.copyfile(source_path, dest_path)

	token_to_output_name = {
		token: output_name_by_key[token] for token in csfiles_tokens
	}
	src_map_fn = _make_csfiles_src_mapper(token_to_output_name)
	return media_dir, src_map_fn

#============================================
def _scan_csfiles_tokens(pool_dat_path: str) -> set[str]:
	"""
	Find every distinct csfiles xid token referenced anywhere in a pool `.dat`.

	Scans the raw file text rather than the parsed tree: the token text
	itself carries no characters that need XML unescaping, so a plain regex
	scan finds every reference regardless of which item encloses it (an item
	whose `bbmd_questiontype` is not dispatchable is scanned all the same).

	Args:
		pool_dat_path: Path to a pool `.dat`.

	Returns:
		The distinct "xid-<n>_1" tokens found, e.g. {"xid-23446236_1"}.
	"""
	with open(pool_dat_path, "r", encoding="utf-8") as pool_file:
		pool_text = pool_file.read()
	return set(CSFILES_TOKEN_PATTERN.findall(pool_text))

#============================================
def _scan_matapplication_refs(pool_dat_path: str) -> list[tuple[str, str]]:
	"""
	Find every hotspot `<matapplication uri>` element in a pool `.dat`.

	Args:
		pool_dat_path: Path to a pool `.dat`.

	Returns:
		A list of (uri, label) pairs, in document order. label falls back to
		the uri's basename when the element carries no `label` attribute.
	"""
	tree = lxml.etree.parse(pool_dat_path)
	refs = []
	for matapplication_el in tree.getroot().iter("matapplication"):
		uri = matapplication_el.get("uri")
		if not uri:
			continue
		label = matapplication_el.get("label") or os.path.basename(uri)
		refs.append((uri, label))
	return refs

#============================================
def _find_pool_resource_base_dir(manifest_path: str, pool_dat_name: str) -> str:
	"""
	Return the pool resource's `xml:base` directory (where its files live).

	Real Blackboard exports declare `xml:base="res00002"` on the pool
	resource; hotspot `<matapplication uri>` paths resolve relative to this
	directory, not the package root. Falls back to the `.dat` filename's own
	stem when no `xml:base` is declared (e.g. minimal test manifests).

	Args:
		manifest_path: Path to imsmanifest.xml.
		pool_dat_name: The pool `.dat` filename (its resource is looked up by
			`bb:file`).

	Returns:
		The base directory name the pool resource's own files resolve under.
	"""
	tree = lxml.etree.parse(manifest_path)
	bb_file_attr = f"{{{BB_NAMESPACE}}}file"
	xml_base_attr = f"{{{XML_NAMESPACE}}}base"
	for resource in tree.getroot().iter("resource"):
		if resource.get(bb_file_attr) != pool_dat_name:
			continue
		xml_base = resource.get(xml_base_attr)
		if xml_base:
			return xml_base
		break
	return os.path.splitext(pool_dat_name)[0]

#============================================
def _load_csresourcelinks_ids(manifest_path: str, pool_dir: str) -> set[str]:
	"""
	Read every `resourceId` declared by the manifest's CSResourceLinks resource.

	Args:
		manifest_path: Path to imsmanifest.xml.
		pool_dir: The pool package root the CSResourceLinks `.dat` lives under.

	Returns:
		The set of resourceId strings (e.g. {"23446236_1", ...}); empty when
		the manifest declares no CSResourceLinks resource.

	Raises:
		ValueError: the manifest declares a CSResourceLinks resource whose
			`.dat` file is missing.
	"""
	tree = lxml.etree.parse(manifest_path)
	bb_file_attr = f"{{{BB_NAMESPACE}}}file"
	resource_ids: set[str] = set()
	for resource in tree.getroot().iter("resource"):
		if resource.get("type") != CSRESOURCELINKS_RESOURCE_TYPE:
			continue
		dat_filename = resource.get(bb_file_attr)
		if not dat_filename:
			continue
		dat_path = os.path.join(pool_dir, dat_filename)
		if not os.path.isfile(dat_path):
			raise ValueError(
				f"Manifest points to missing CSResourceLinks file '{dat_filename}' "
				f"in '{pool_dir}'"
			)
		links_tree = lxml.etree.parse(dat_path)
		for link_el in links_tree.getroot().iter("cms_resource_link"):
			resource_id_el = link_el.find("resourceId")
			if resource_id_el is not None and resource_id_el.text:
				resource_ids.add(resource_id_el.text.strip())
	return resource_ids

#============================================
def _find_csfiles_files(pool_dir: str, token: str) -> tuple[str, str]:
	"""
	Locate a csfiles binary and its LOM sidecar for one xid token.

	Args:
		pool_dir: The pool package root.
		token: A "xid-<n>_1" token (as found by _scan_csfiles_tokens).

	Returns:
		A tuple of (binary_path, sidecar_path).

	Raises:
		FileNotFoundError: the csfiles home dir, the binary, or the sidecar
			is missing.
	"""
	home_dir = os.path.join(pool_dir, CSFILES_HOME_SUBDIR)
	if not os.path.isdir(home_dir):
		raise FileNotFoundError(
			f"csfiles token '{token}' referenced but '{home_dir}' does not exist"
		)
	binary_prefix = f"__{token}."
	binary_path = None
	# deterministic scan order so ties (should not occur) resolve predictably
	for filename in sorted(os.listdir(home_dir)):
		if filename.startswith(binary_prefix) and not filename.endswith(".xml"):
			binary_path = os.path.join(home_dir, filename)
			break
	if binary_path is None:
		raise FileNotFoundError(
			f"csfiles binary not found for token '{token}' under '{home_dir}'"
		)
	sidecar_path = binary_path + ".xml"
	if not os.path.isfile(sidecar_path):
		raise FileNotFoundError(
			f"LOM sidecar not found for token '{token}': '{sidecar_path}'"
		)
	return binary_path, sidecar_path

#============================================
def _recover_original_filename(sidecar_path: str) -> str:
	"""
	Recover the original course-relative filename from a LOM sidecar.

	The sidecar's `<identifier>` element carries
	`"<xid>#/courses/<course>/<original-name>"`; the recovered name is the
	basename of the path portion after the `#`.

	Args:
		sidecar_path: Path to a `.jpg.xml` LOM sidecar.

	Returns:
		The recovered original filename, e.g. "image-1.jpg".

	Raises:
		ValueError: the sidecar has no identifier, or it names no file.
	"""
	tree = lxml.etree.parse(sidecar_path)
	identifier_el = tree.getroot().find(f".//{{{LOM_NAMESPACE}}}identifier")
	if identifier_el is None or not identifier_el.text:
		raise ValueError(f"LOM sidecar '{sidecar_path}' has no identifier element")
	identifier_text = identifier_el.text.strip()
	_, _, path_part = identifier_text.partition("#")
	source_path = path_part if path_part else identifier_text
	original_name = os.path.basename(source_path)
	if not original_name:
		raise ValueError(
			f"LOM sidecar '{sidecar_path}' identifier names no file: '{identifier_text}'"
		)
	return original_name

#============================================
def _resolve_package_relative_path(pool_dir: str, relative_path: str) -> str:
	"""
	Resolve a package-relative path, rejecting traversal outside pool_dir.

	Mirrors the traversal check in `media_assets.resolve_asset` /
	`ItemBank.add_image`: the resolved path must stay within pool_dir.

	Args:
		pool_dir: The pool package root.
		relative_path: A path relative to pool_dir (e.g. a matapplication
			uri under the pool resource's `xml:base` directory).

	Returns:
		The resolved absolute path.

	Raises:
		ValueError: the path escapes pool_dir.
		FileNotFoundError: the resolved file does not exist.
	"""
	base_abs = os.path.abspath(pool_dir)
	resolved_path = os.path.normpath(os.path.join(base_abs, relative_path))
	if resolved_path != base_abs and not resolved_path.startswith(base_abs + os.sep):
		raise ValueError(f"path '{relative_path}' escapes the package root '{pool_dir}'")
	if not os.path.isfile(resolved_path):
		raise FileNotFoundError(f"referenced file not found: {resolved_path}")
	return resolved_path

#============================================
def _assign_collision_safe_names(desired_name_by_key: dict[str, str]) -> dict[str, str]:
	"""
	Assign deterministic, collision-safe output names for a set of keys.

	Same disambiguation pattern as `media_assets.assign_output_names`: keys
	are processed in sorted order, and a colliding basename gets a
	deterministic `name(1).ext`, `name(2).ext`, ... suffix.

	Args:
		desired_name_by_key: mapping of a stable identity key to its desired
			(possibly colliding) basename.

	Returns:
		A mapping of the same keys to disambiguated output names.
	"""
	used_names: set[str] = set()
	output_name_by_key = {}
	for key in sorted(desired_name_by_key):
		base_name = desired_name_by_key[key]
		candidate_name = base_name
		collision_counter = 1
		while candidate_name in used_names:
			root, extension = os.path.splitext(base_name)
			candidate_name = f"{root}({collision_counter}){extension}"
			collision_counter += 1
		used_names.add(candidate_name)
		output_name_by_key[key] = candidate_name
	return output_name_by_key

#============================================
def _make_csfiles_src_mapper(
	token_to_output_name: dict[str, str],
) -> collections.abc.Callable[[str], str]:
	"""
	Build the `<img src>` rewrite function for one pool's csfiles tokens.

	Args:
		token_to_output_name: mapping of "xid-<n>_1" token to its recovered,
			collision-safe filename in the extraction directory.

	Returns:
		A callable mapping an in-content src to its rewritten src; any src
		that is not a recognized csfiles token passes through unchanged.
	"""
	#----------------------------------------------------
	def _map_src(old_src: str) -> str:
		if not old_src.startswith(common_xml.CSFILES_SRC_PREFIX):
			return old_src
		token = old_src[len(common_xml.CSFILES_SRC_PREFIX):]
		return token_to_output_name.get(token, old_src)
	return _map_src

#============================================
def _identity_src_map(src: str) -> str:
	"""Return src unchanged; used when a pool carries no images."""
	return src

#============================================
def _parse_pool_into_bank(
	pool_dat_path: str,
	new_item_bank: item_bank.ItemBank,
	src_map_fn: collections.abc.Callable[[str], str],
) -> None:
	"""
	Parse every `<item>` in one pool `.dat` and add the items to the bank.

	Args:
		pool_dat_path: Path to a pool `.dat` (the `assessment/x-bb-qti-pool` XML).
		new_item_bank: The ItemBank to add parsed items to.
		src_map_fn: Rewrites `<img src>` values while extracting item HTML (the
			identity function when the pool carries no images).
	"""
	tree = lxml.etree.parse(pool_dat_path)
	root = tree.getroot()
	dat_filename = os.path.basename(pool_dat_path)
	# Each question is one <item>; iterate them in document order.
	for item_index, item_el in enumerate(root.iter("item")):
		item_cls = _parse_one_item(item_el, dat_filename, item_index, src_map_fn)
		# A None result means the item was skipped (unknown type or malformed);
		# the per-item helper already warned with the source name.
		if item_cls is not None:
			new_item_bank.add_item_cls(item_cls)

#============================================
def _parse_one_item(
	item_el: lxml.etree.Element,
	dat_filename: str,
	item_index: int,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.BaseItem | None:
	"""
	Parse a single `<item>` element into an internal item, or skip it.

	Args:
		item_el: The `<item>` lxml element.
		dat_filename: The pool `.dat` filename, used in warning messages.
		item_index: The item's positional index, used in warning messages.
		src_map_fn: Rewrites `<img src>` values while extracting item HTML.

	Returns:
		The parsed item instance, or None when the item is skipped (unknown
		question type or malformed content).
	"""
	source = f"{dat_filename} item #{item_index + 1}"
	question_type = item_el.findtext("itemmetadata/bbmd_questiontype")
	# A missing type marker means we cannot dispatch; skip with a clear warning.
	if question_type is None:
		print(f"Warning: skipping {source}: no bbmd_questiontype element")
		return None
	question_type = question_type.strip()
	read_function = _QUESTION_TYPE_DISPATCH.get(question_type)
	if read_function is None:
		print(
			f"Warning: skipping {source}: unknown bbmd_questiontype "
			f"'{question_type}'"
		)
		return None
	# A malformed item body raises during parsing; catch it narrowly so one bad
	# item does not abort the whole pool, and name the source in the warning.
	try:
		item_cls = read_function(item_el, src_map_fn)
	except (ValueError, IndexError, KeyError, AttributeError) as exc:
		print(f"Warning: skipping malformed {source}: {exc}")
		return None
	return item_cls

#============================================
# Shared element-text extraction helpers
#============================================
#============================================
def _smart_text(
	material_owner: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read the HTML payload from the first SMART_TEXT material under an element.

	The write path stores HTML as the `.text` of a
	`mat_formattedtext type="SMART_TEXT"`; lxml escaped it once on write and
	un-escapes it once here, recovering the original HTML verbatim.

	Args:
		material_owner: An element whose subtree contains a
			`mat_formattedtext` element (a flow, response_label, etc.).
		src_map_fn: Rewrites any `<img src>` found in the recovered HTML (the
			identity function when the pool carries no images).

	Returns:
		The un-escaped HTML string (empty string when the carrier is empty),
		with `<img src>` values rewritten by src_map_fn.
	"""
	# The first SMART_TEXT carrier anywhere beneath this element holds the HTML.
	mat = material_owner.find(".//mat_formattedtext")
	if mat is None:
		raise ValueError("no mat_formattedtext element found")
	# lxml returns the un-escaped text; None text (empty element) reads as "".
	html_text = mat.text if mat.text is not None else ""
	# Real Blackboard exports carry unclosed void elements (<br>, <img ...>),
	# which item construction rejects (every HTML field is validated as XML);
	# self-close them before any src rewriting.
	html_text = _repair_html_void_elements(html_text)
	# Cheap no-op when html_text carries no <img> tag; rewrites csfiles tokens
	# to their recovered plain filenames otherwise.
	return media_assets.rewrite_html_srcs(html_text, src_map_fn)

#============================================
def _repair_html_void_elements(html_str: str) -> str:
	"""
	Self-close unclosed void HTML elements so html_str parses as valid XML.

	Real Blackboard-exported HTML writes void elements like `<br>` and
	`<img src="...">` without a self-closing slash; `item_types` construction
	validates every HTML field as XML (`validator.validate_html`), which
	rejects them. Re-serializing through lxml.html repairs this, but the
	lxml.html/libxml2 parser also normalizes markup while it does so: every
	element and attribute name is lowercased (`<STRONG>` becomes `<strong>`,
	`SRC=` becomes `src=`), and any decoded entity is re-escaped as an ASCII
	numeric character reference (see the `&nbsp;` handling below). Attribute
	VALUES, attribute order, and visible text content are preserved.

	Args:
		html_str: an HTML-bearing field (already src-rewritten).

	Returns:
		The same content with every void element self-closed and element/
		attribute names lowercased; a payload with no `<` is returned
		unchanged.
	"""
	# fast exit: plain text carries nothing to repair
	if "<" not in html_str:
		return html_str
	# wrap so lxml.html parses a fragment, not a full document
	wrapped = f"<div>{html_str}</div>"
	root = lxml.html.fromstring(wrapped)
	parts = []
	# text before the first child sits on the wrapper's own .text; a named
	# entity like &nbsp; decodes to a literal non-ASCII char during parsing
	# (item construction requires ASCII), so re-escape it as a numeric ref.
	if root.text:
		parts.append(root.text.encode("ascii", "xmlcharrefreplace").decode("ascii"))
	for child in root:
		# encoding="ascii" both self-closes void elements (method="xml") and
		# re-escapes any decoded entity (e.g. &nbsp;) as an ASCII-safe numeric
		# character reference instead of a literal non-ASCII byte.
		child_bytes = lxml.html.tostring(child, encoding="ascii", method="xml")
		parts.append(child_bytes.decode("ascii"))
	return "".join(parts)

#============================================
def _question_html(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read the question HTML from an item's `QUESTION_BLOCK`.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the recovered HTML.

	Returns:
		The un-escaped question HTML.
	"""
	# The question text lives in the single flow class="QUESTION_BLOCK".
	question_block = _find_flow_by_class(item_el, "QUESTION_BLOCK")
	if question_block is None:
		raise ValueError("no QUESTION_BLOCK flow found")
	return _smart_text(question_block, src_map_fn)

#============================================
def _find_flow_by_class(parent: lxml.etree.Element, class_value: str) -> lxml.etree.Element | None:
	"""
	Find the first descendant `<flow>` with the given `class` attribute.

	Args:
		parent: The element to search beneath.
		class_value: The `class` attribute value to match.

	Returns:
		The matching `<flow>` element, or None when none is found.
	"""
	for flow in parent.iter("flow"):
		if flow.get("class") == class_value:
			return flow
	return None

#============================================
def _resprocessing(item_el: lxml.etree.Element) -> lxml.etree.Element:
	"""
	Return the item's `<resprocessing>` element.

	Args:
		item_el: The `<item>` element.

	Returns:
		The `<resprocessing>` element.
	"""
	resprocessing = item_el.find("resprocessing")
	if resprocessing is None:
		raise ValueError("no resprocessing element found")
	return resprocessing

#============================================
# Choice-based readers (MC / MA)
#============================================
#============================================
def _choice_response_lid(item_el: lxml.etree.Element) -> lxml.etree.Element:
	"""
	Return the single choice `<response_lid>` for an MC/MA item.

	The choice response_lid is the one whose `render_choice` holds
	`response_label` choices directly (MATCH uses one response_lid per prompt and
	is handled separately).

	Args:
		item_el: The `<item>` element.

	Returns:
		The choice `<response_lid>` element.
	"""
	presentation = item_el.find("presentation")
	if presentation is None:
		raise ValueError("no presentation element found")
	# An MC/MA item has exactly one response_lid; take the first.
	response_lid = presentation.find(".//response_lid")
	if response_lid is None:
		raise ValueError("no response_lid element found for choice question")
	return response_lid

#============================================
def _read_choice_labels(
	response_lid: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> tuple[list[str], list[str]]:
	"""
	Read the choice idents and choice HTML texts from a choice `response_lid`.

	Args:
		response_lid: The choice `<response_lid>` element.
		src_map_fn: Rewrites any `<img src>` found in each choice's HTML.

	Returns:
		A tuple of (label idents, choice HTML strings), index-aligned.
	"""
	label_idents = []
	choice_texts = []
	# Each response_label is one choice; its ident keys scoring, its text is shown.
	for response_label in response_lid.iter("response_label"):
		label_idents.append(response_label.get("ident"))
		choice_texts.append(_smart_text(response_label, src_map_fn))
	if not choice_texts:
		raise ValueError("choice question has no response_label choices")
	return label_idents, choice_texts

#============================================
def _is_descendant_of_not(
	varequal_el: lxml.etree.Element,
	stop_el: lxml.etree.Element,
) -> bool:
	"""
	Return True if varequal_el has a `<not>` ancestor between itself and stop_el.

	Real Blackboard MA wraps incorrect choices in `<not><varequal .../></not>`
	inside the `<and>` of the `title="correct"` branch. Walking the parent chain
	from the varequal up to (but not including) the respcondition detects these
	negated choices so the reader can skip them.

	Args:
		varequal_el: The varequal element to test.
		stop_el: The respcondition element that is the boundary; the walk stops
			before reaching it.

	Returns:
		True when varequal_el is nested inside a `<not>` on the path to stop_el.
	"""
	parent = varequal_el.getparent()
	while parent is not None and parent is not stop_el:
		if parent.tag == "not":
			return True
		parent = parent.getparent()
	return False

#============================================
def _correct_choice_idents(item_el: lxml.etree.Element) -> list[str]:
	"""
	Read the correct label idents from the `title="correct"` resprocessing branch.

	For real Blackboard MA the `title="correct"` branch holds an `<and>` whose
	children list every choice: correct choices as bare `<varequal
	respident="response" case="No">IDENT</varequal>`, incorrect choices wrapped in
	`<not><varequal .../></not>`. Only the non-negated varequals name correct
	answers. For legacy engine-emitted MA (bare varequals in `<conditionvar>`
	without any `<and>` or `<not>`) the same predicate keeps all varequals because
	none has a `<not>` ancestor.

	Args:
		item_el: The `<item>` element.

	Returns:
		The correct label idents, in branch order.
	"""
	resprocessing = _resprocessing(item_el)
	correct_idents = []
	# The correct branch is titled "correct"; only non-negated varequal texts name answers.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") != "correct":
			continue
		for varequal in respcondition.iter("varequal"):
			# Skip varequals nested inside a <not>: those are incorrect choices in real BB MA.
			if _is_descendant_of_not(varequal, respcondition):
				continue
			if varequal.text:
				correct_idents.append(varequal.text.strip())
	if not correct_idents:
		raise ValueError("no correct varequal idents found in resprocessing")
	return correct_idents

#============================================
def _is_multiple_cardinality(response_lid: lxml.etree.Element) -> bool:
	"""
	Report whether a choice `response_lid` allows multiple selections (MA).

	Args:
		response_lid: The choice `<response_lid>` element.

	Returns:
		True when `rcardinality="Multiple"` (Multiple Answer), else False.
	"""
	return response_lid.get("rcardinality") == "Multiple"

#============================================
def _read_choice_item(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.BaseItem:
	"""
	Read an MC or MA item, choosing the type from the response cardinality.

	`rcardinality="Multiple"` is MA; otherwise MC. This refines the
	`bbmd_questiontype` marker, which Blackboard sometimes labels "Multiple
	Choice" even for multi-select questions.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the item's HTML.

	Returns:
		An MC or MA item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	response_lid = _choice_response_lid(item_el)
	label_idents, choice_texts = _read_choice_labels(response_lid, src_map_fn)
	correct_idents = _correct_choice_idents(item_el)
	# Map correct idents back to their choice texts via positional alignment.
	ident_to_text = dict(zip(label_idents, choice_texts))
	correct_texts = [
		ident_to_text[correct_ident]
		for correct_ident in correct_idents
		if correct_ident in ident_to_text
	]
	if not correct_texts:
		raise ValueError("correct idents did not match any choice label")
	# Multiple-cardinality or more than one correct answer means MA.
	if _is_multiple_cardinality(response_lid) or len(correct_texts) > 1:
		return item_types.MA(question_html, choice_texts, correct_texts)
	return item_types.MC(question_html, choice_texts, correct_texts[0])

#============================================
# Fill-in-the-blank readers (FIB / MULTI_FIB)
#============================================
#============================================
def _read_FIB(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.FIB:
	"""
	Read a Fill in the Blank item.

	Each accepted answer is the text of a `<varequal respident="response">` in
	its own (UUID-titled) respcondition; the `incorrect` branch is excluded.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A FIB item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	answers_list = []
	# Every non-incorrect branch carries one accepted answer for the response field.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		for varequal in respcondition.iter("varequal"):
			if varequal.get("respident") == "response" and varequal.text:
				answers_list.append(varequal.text)
	if not answers_list:
		raise ValueError("FIB item has no accepted answers")
	return item_types.FIB(question_html, answers_list)

#============================================
def _read_MULTI_FIB(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.MULTI_FIB:
	"""
	Read a Fill in the Blank Plus item.

	The `title="correct"` branch holds an `<and>` of one `<or>` per blank; each
	`<or>` carries one `<varequal respident="KEY">` per accepted answer for that
	blank. The answer_map keys are the per-blank `respident` values.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A MULTI_FIB item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	# Find the correct branch holding the <and> of <or> blank groups.
	correct_branch = None
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "correct":
			correct_branch = respcondition
			break
	if correct_branch is None:
		raise ValueError("MULTI_FIB item has no title='correct' branch")
	answer_map: dict[str, list[str]] = {}
	# Each <or> group is one blank; its varequal respident is the blank key.
	for or_group in correct_branch.iter("or"):
		for varequal in or_group.iter("varequal"):
			blank_key = varequal.get("respident")
			if blank_key is None or varequal.text is None:
				continue
			# Preserve insertion order; collect every accepted spelling per blank.
			answer_map.setdefault(blank_key, []).append(varequal.text)
	if not answer_map:
		raise ValueError("MULTI_FIB item recovered no blank answer groups")
	return item_types.MULTI_FIB(question_html, answer_map)

#============================================
# Numeric reader (NUM)
#============================================
#============================================
def _read_NUM(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.NUM:
	"""
	Read a Numeric item.

	The correct branch is any `<respcondition>` that is NOT titled "incorrect"
	and carries `<vargte>` or `<varequal>`. Real samples use a UUID title on the
	correct branch, not `title="correct"`. Once found, the branch carries
	`<vargte>` (answer - tolerance), `<varlte>` (answer + tolerance), and
	`<varequal>` (the exact answer). The answer is the varequal value; the
	tolerance is half the (varlte - vargte) window.

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the question HTML.

	Returns:
		A NUM item instance.
	"""
	question_html = _question_html(item_el, src_map_fn)
	resprocessing = _resprocessing(item_el)
	# The numeric correct branch is the one that is not titled "incorrect".
	correct_branch = None
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		# The numeric branch is identified by carrying the bound conditions.
		if respcondition.find(".//vargte") is not None or respcondition.find(".//varequal") is not None:
			correct_branch = respcondition
			break
	if correct_branch is None:
		raise ValueError("NUM item has no correct respcondition")
	varequal = correct_branch.find(".//varequal")
	if varequal is None or varequal.text is None:
		raise ValueError("NUM item correct branch has no varequal answer")
	answer_float = float(varequal.text)
	# Recover the tolerance from the bound window when both bounds are present.
	vargte = correct_branch.find(".//vargte")
	varlte = correct_branch.find(".//varlte")
	if vargte is not None and vargte.text and varlte is not None and varlte.text:
		lower_bound = float(vargte.text)
		upper_bound = float(varlte.text)
		tolerance_float = (upper_bound - lower_bound) / 2.0
	else:
		# No bound window means an exact-match numeric; zero tolerance.
		tolerance_float = 0.0
	return item_types.NUM(question_html, answer_float, tolerance_float)

#============================================
# Matching reader (MATCH)
#============================================
#============================================
def _read_MATCH(
	item_el: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> item_types.MATCH:
	"""
	Read a Matching item, recovering the prompt->choice pairing.

	Each prompt is a `<flow class="Block">` holding a `response_lid` (whose
	`render_choice` lists one `response_label` per right-side choice) followed by
	the prompt's own FORMATTED_TEXT_BLOCK. A sibling
	`<flow class="RIGHT_MATCH_BLOCK">` lists the choice texts in order.

	Pairing recovery: each prompt's `response_lid` ident appears as the
	`respident` of a `<varequal>` in `resprocessing`; that varequal's TEXT is the
	correct label ident. The label ident's position within the prompt's
	`response_label` list indexes the `RIGHT_MATCH_BLOCK` choice texts, recovering
	the prompt's matching choice. The returned MATCH stores prompts and choices in
	prompt order, so prompts_list[i] pairs with choices_list[i].

	Args:
		item_el: The `<item>` element.
		src_map_fn: Rewrites any `<img src>` found in the item's HTML.

	Returns:
		A MATCH item instance with prompts and choices in paired order.
	"""
	question_html = _question_html(item_el, src_map_fn)
	# RIGHT_MATCH_BLOCK is a sibling of RESPONSE_BLOCK in the real samples but a
	# child of it in the engine's own output; search the whole item so both
	# placements resolve. There is exactly one RIGHT_MATCH_BLOCK per item.
	presentation = item_el.find("presentation")
	if presentation is None:
		raise ValueError("MATCH item has no presentation")
	right_match_block = _find_flow_by_class(presentation, "RIGHT_MATCH_BLOCK")
	if right_match_block is None:
		raise ValueError("MATCH item has no RIGHT_MATCH_BLOCK")
	# The right-side choice texts, indexed positionally as written.
	choice_texts = _read_right_match_texts(right_match_block, src_map_fn)

	# Map each prompt's response_lid ident -> its correct label ident.
	correct_ident_by_prompt = _match_correct_idents(item_el)

	prompts_list = []
	choices_list = []
	# Each prompt block holds one response_lid and the prompt's display text.
	for prompt_block in _match_prompt_blocks(presentation):
		prompt_response_lid = prompt_block.find(".//response_lid")
		if prompt_response_lid is None:
			raise ValueError("MATCH prompt block has no response_lid")
		prompt_lid_ident = prompt_response_lid.get("ident")
		# The prompt's display text is its FORMATTED_TEXT_BLOCK (after the lid).
		prompt_text = _match_prompt_text(prompt_block, src_map_fn)
		# The label idents in this prompt, positionally aligned to the choices.
		label_idents = [
			label.get("ident")
			for label in prompt_response_lid.iter("response_label")
		]
		correct_label_ident = correct_ident_by_prompt.get(prompt_lid_ident)
		if correct_label_ident is None:
			raise ValueError(
				f"MATCH prompt '{prompt_lid_ident}' has no scoring varequal"
			)
		if correct_label_ident not in label_idents:
			raise ValueError(
				f"MATCH prompt '{prompt_lid_ident}' correct ident not in its labels"
			)
		# The label's position indexes the RIGHT_MATCH_BLOCK choice list.
		choice_index = label_idents.index(correct_label_ident)
		if choice_index >= len(choice_texts):
			raise ValueError("MATCH correct choice index out of range")
		prompts_list.append(prompt_text)
		choices_list.append(choice_texts[choice_index])
	if not prompts_list:
		raise ValueError("MATCH item recovered no prompts")
	return item_types.MATCH(question_html, prompts_list, choices_list)

#============================================
def _read_right_match_texts(
	right_match_block: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> list[str]:
	"""
	Read the right-side choice texts from a `RIGHT_MATCH_BLOCK`, in order.

	Args:
		right_match_block: The `<flow class="RIGHT_MATCH_BLOCK">` element.
		src_map_fn: Rewrites any `<img src>` found in each choice's HTML.

	Returns:
		The choice HTML strings, in document order.
	"""
	choice_texts = []
	# Each direct child flow class="Block" is one choice's formatted text.
	for choice_flow in right_match_block.findall("flow"):
		choice_texts.append(_smart_text(choice_flow, src_map_fn))
	if not choice_texts:
		raise ValueError("RIGHT_MATCH_BLOCK has no choice texts")
	return choice_texts

#============================================
def _match_prompt_blocks(presentation: lxml.etree.Element) -> list[lxml.etree.Element]:
	"""
	Return the per-prompt `<flow class="Block">` blocks of a MATCH item.

	A MATCH item has one `flow class="Block"` per prompt, each holding a direct
	`response_lid` child, alongside a `RIGHT_MATCH_BLOCK` whose own inner Block
	flows carry no response_lid. A prompt block is a Block flow with a
	response_lid as a direct child; this selects the prompt blocks regardless of
	whether RIGHT_MATCH_BLOCK is a sibling (real samples) or a child (engine
	output) of RESPONSE_BLOCK.

	Args:
		presentation: The `<presentation>` element.

	Returns:
		The per-prompt block elements, in document order.
	"""
	prompt_blocks = []
	# A prompt block is a Block flow whose direct child is a response_lid.
	for block in presentation.iter("flow"):
		if block.get("class") != "Block":
			continue
		if block.find("response_lid") is not None:
			prompt_blocks.append(block)
	return prompt_blocks

#============================================
def _match_prompt_text(
	prompt_block: lxml.etree.Element,
	src_map_fn: collections.abc.Callable[[str], str],
) -> str:
	"""
	Read a MATCH prompt's display text from its FORMATTED_TEXT_BLOCK.

	The prompt block holds the response_lid first, then a sibling
	`flow class="FORMATTED_TEXT_BLOCK"` carrying the prompt's own SMART_TEXT.

	Args:
		prompt_block: The per-prompt `<flow class="Block">` element.
		src_map_fn: Rewrites any `<img src>` found in the prompt's HTML.

	Returns:
		The un-escaped prompt HTML.
	"""
	# The prompt's display text is the FORMATTED_TEXT_BLOCK that is a direct
	# child of the prompt block (not the one nested inside the response_lid).
	for flow in prompt_block.findall("flow"):
		if flow.get("class") == "FORMATTED_TEXT_BLOCK":
			return _smart_text(flow, src_map_fn)
	raise ValueError("MATCH prompt block has no FORMATTED_TEXT_BLOCK display text")

#============================================
def _match_correct_idents(item_el: lxml.etree.Element) -> dict[str, str]:
	"""
	Map each MATCH prompt's response_lid ident to its correct label ident.

	The samples score MATCH via one untitled `respcondition` per prompt, each
	holding a `<varequal respident="PROMPT_LID">CORRECT_LABEL_IDENT</varequal>`.
	The `incorrect` branch is skipped.

	Args:
		item_el: The `<item>` element.

	Returns:
		A dict of {prompt response_lid ident: correct label ident}.
	"""
	resprocessing = _resprocessing(item_el)
	correct_by_prompt = {}
	# Each prompt scoring branch keys prompt-lid ident -> correct label ident.
	for respcondition in resprocessing.iter("respcondition"):
		if respcondition.get("title") == "incorrect":
			continue
		for varequal in respcondition.iter("varequal"):
			prompt_ident = varequal.get("respident")
			if prompt_ident is not None and varequal.text:
				correct_by_prompt[prompt_ident] = varequal.text.strip()
	return correct_by_prompt

#============================================
# Question-type dispatch table
#============================================
# Maps the `<bbmd_questiontype>` element value to its reader. MC/MA share one
# reader that refines the type by response cardinality; True/False maps to MC.
_QUESTION_TYPE_DISPATCH = {
	"Multiple Choice": _read_choice_item,
	"Multiple Answer": _read_choice_item,
	"Fill in the Blank": _read_FIB,
	"Fill in the Blank Plus": _read_MULTI_FIB,
	"Numeric": _read_NUM,
	"Matching": _read_MATCH,
	"True/False": _read_choice_item,
}
