"""
Cross-reference integrity check for generated assessment packages.

Structure tests assert that elements are present; roundtrip tests read a
package back through our own reader, which resolves answers positionally and
therefore hides dangling identifiers. Neither catches a package that is
schema-plausible but internally inconsistent: a correctResponse that names a
choice id no choice declares, a manifest dependency that points at nothing, or
a Blackboard export whose resource-link parentId names an item the pool never
emitted. Two live Blackboard Learn import failures were exactly this class of
bug.

This module runs a referential-integrity check over a finished package (a ZIP
path or an already-extracted directory tree) and returns a list of
human-readable violation strings. An empty list means the package is clean.

The check dispatches on what it finds inside the package (the manifest
namespace, resource types, and .dat files) rather than on an engine name, so
it works on ANY package flavor -- including real Blackboard exports under
SAMPLES/ -- without being told which engine produced it.

Checks applied per flavor:

IMS content-packaging manifest flavors (canvas_qti_v1_2,
blackboard_qti_v2_1):
  - manifest integrity: every <resource href>, every <file href>, and every
	<dependency identifierref> resolves within the package.
  - item answer linkage: every correctResponse value (QTI 2.1) or scored
	<varequal> value into a choice response (QTI 1.2) literally matches an
	interaction choice identifier declared in the SAME item. This is a
	self-consistency check; the padding scheme is irrelevant, both sides must
	simply agree.
  - rewritten media src: every <img src> that is not external or a data URI
	resolves to a packaged file, resolved relative to the item file's folder.

Blackboard export flavor (blackboard_export_zip):
  - every manifest bb:file resolves to a package entry.
  - every body bbcswebdav/xid-<n> token resolves to a csfiles binary AND to a
	res00005 CSResourceLinks resourceId.
  - every CSResourceLinks parentId resolves to a bbmd_asi_object_id present in
	the pool.
  - every csfiles binary has its LOM sidecar.

Applied to every flavor, regardless of manifest shape:
  - every packaged raster image (.png, .jpg/.jpeg, .gif) is larger than a
	single invisible pixel. A 1x1-pixel probe image once imported into
	Blackboard successfully but rendered invisible on the page, costing a
	full day of false "image not imported" verdicts before the pixel
	dimension was noticed; see MIN_IMAGE_DIMENSION_PX below.
  - every identifier-bearing attribute this checker already reads (manifest
	identifier, resource identifier, dependency identifierref, item/
	assessment identifiers in item XML) is an id-safe token. A manifest
	identifier containing a literal space (identifier="main manifest")
	shipped in our own output; see IDENTIFIER_SAFE_RE below.
  - every QTI 2.1 assessmentItem (any manifest flavor) declares an
	<outcomeDeclaration identifier="SCORE">, the outcome
	blackboard_qti_v2_1's item_xml_helpers.create_outcome_declarations()
	always emits and Blackboard Ultra's scoring engine requires on import.
"""

# Standard Library
import os
import re
import html
import struct
import zipfile
import posixpath

# Pip3 Library
import lxml.etree

# Namespace of the IMS content-packaging manifest shared by the QTI flavors.
IMSCP_NS = "http://www.imsglobal.org/xsd/imscp_v1p1"
# Namespace Blackboard stamps on its export manifest resource attributes.
BB_CP_NS = "http://www.blackboard.com/content-packaging/"

# A packaged raster image whose smaller side is at or below this many pixels
# is flagged as effectively invisible. A 1x1-pixel probe image imported into
# Blackboard cleanly but was never visible on the rendered page, costing a
# full day of false "image not imported" verdicts before anyone noticed the
# probe itself was a single pixel.
MIN_IMAGE_DIMENSION_PX = 5

# Extensions eligible for the packaged-image dimension check; matches the
# first-class raster set in qti_package_maker/common/media_assets.py
# (SUPPORTED_IMAGE_EXTENSIONS). SVG is a vector format with no fixed pixel
# grid and is intentionally excluded.
RASTER_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif")

# PNG file signature (the fixed 8-byte magic number every PNG starts with).
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# GIF file signatures for the two still-current spec versions.
GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
# JPEG files start with a Start Of Image marker.
JPEG_SOI = b"\xff\xd8"

# JPEG Start-Of-Frame marker bytes that carry frame dimensions. 0xC0-0xCF is
# shared with DHT (0xC4), JPG extension (0xC8), and DAC (0xCC), which are NOT
# SOF markers and are excluded here.
JPEG_SOF_MARKERS = frozenset({
	0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
	0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
})

# An id-safe token: starts with a letter or underscore, then only letters,
# digits, dot, underscore, or hyphen. No spaces, no leading digit. A manifest
# identifier of "main manifest" (a literal space) shipped in our own output
# and is exactly the malformed shape this check exists to catch.
IDENTIFIER_SAFE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")

# QTI 2.1 element local-names that declare a selectable answer identifier.
# A correctResponse value must match one of these identifiers inside the item.
QTI21_CHOICE_TAGS = frozenset({
	"simpleChoice",
	"simpleAssociableChoice",
	"gap",
	"gapText",
	"gapImg",
	"inlineChoice",
	"hottext",
	"associableHotspot",
	"hotspotChoice",
})


#============================================
def _local_name(tag: object) -> str:
	"""Return the namespace-stripped local name of an lxml tag."""
	# comments and processing instructions have non-string tags; ignore them
	if not isinstance(tag, str):
		return ""
	# strip a leading "{namespace}" prefix if present
	return tag.rpartition("}")[2]


#============================================
def _child_text(element: lxml.etree._Element, child_local_name: str) -> str | None:
	"""Return the stripped text of the first child with the given local name."""
	for child in element:
		if _local_name(child.tag) == child_local_name:
			if child.text is None:
				return None
			return child.text.strip()
	return None


#============================================
def _load_entries(package_path: str) -> dict:
	"""
	Read a package into a mapping of POSIX entry name to raw bytes.

	Accepts either a ZIP file path or an already-extracted directory tree so
	the check works on freshly written packages and on real extracted exports
	alike. Directory entries (zip names ending in "/") are skipped.
	"""
	entries = {}
	if os.path.isdir(package_path):
		# walk the extracted tree, keying by path relative to the tree root
		for dirpath, _dirnames, filenames in os.walk(package_path):
			for filename in filenames:
				full_path = os.path.join(dirpath, filename)
				rel_path = os.path.relpath(full_path, package_path)
				# normalize to POSIX separators so keys match zip names
				posix_name = rel_path.replace(os.sep, "/")
				with open(full_path, "rb") as file_pointer:
					entries[posix_name] = file_pointer.read()
		return entries
	# otherwise treat the path as a ZIP archive
	with zipfile.ZipFile(package_path, "r") as zip_file:
		for info in zip_file.infolist():
			# skip directory members, which have no file bytes
			if info.filename.endswith("/"):
				continue
			entries[info.filename] = zip_file.read(info.filename)
	return entries


#============================================
def check_package(package_path: str) -> list:
	"""
	Run the cross-reference integrity check on a finished package.

	Args:
		package_path: a ZIP file path or an extracted package directory.

	Returns:
		A list of human-readable violation strings. Empty means the package
		passed every applicable integrity check.
	"""
	entries = _load_entries(package_path)
	violations = check_entries(entries)
	return violations


#============================================
def check_entries(entries: dict) -> list:
	"""
	Run the integrity check over an in-memory mapping of entry name to bytes.

	Dispatches by package shape: a Blackboard content-packaging manifest routes
	to the export-zip checks, an IMS content-packaging manifest routes to the
	QTI manifest, item-answer, and media-src checks. The packaged-image
	dimension check, the identifier-safety check, and the QTI 2.1 SCORE
	outcome check apply to every flavor, since a raster image, a malformed
	identifier, or an assessmentItem missing SCORE can appear in any of them.
	"""
	violations = []
	# every supported flavor carries a top-level imsmanifest.xml
	if "imsmanifest.xml" not in entries:
		violations.append("imsmanifest.xml: missing from package")
		return violations
	manifest_root = lxml.etree.fromstring(entries["imsmanifest.xml"])
	if _is_bb_export_manifest(manifest_root):
		violations += _check_bb_export(entries, manifest_root)
	else:
		violations += _check_imscp_manifest(entries, manifest_root)
		violations += _check_item_answer_linkage(entries)
		violations += _check_media_src(entries)
	# flavor-independent: every packaged raster image must be visibly sized
	violations += _check_image_dimensions(entries)
	# flavor-independent: every identifier-bearing attribute must be id-safe
	violations += _check_manifest_identifier_safety("imsmanifest.xml", manifest_root)
	violations += _check_item_identifier_safety(entries)
	# flavor-independent: every QTI 2.1 assessmentItem must declare SCORE
	violations += _check_qti21_score_outcome_declaration(entries)
	return violations


#============================================
def _is_bb_export_manifest(manifest_root: lxml.etree._Element) -> bool:
	"""Return True when the manifest carries Blackboard content-packaging attrs."""
	# Blackboard stamps bb:file / bb:title attributes on its resource elements;
	# the IMS content-packaging manifests never do
	bb_attr_prefix = "{" + BB_CP_NS + "}"
	for element in manifest_root.iter():
		for attr_key in element.attrib:
			if attr_key.startswith(bb_attr_prefix):
				return True
	return False


#============================================
def _check_imscp_manifest(entries: dict, manifest_root: lxml.etree._Element) -> list:
	"""
	Check IMS content-packaging manifest cross-references resolve.

	Every <resource href> and <file href> must name a package entry, and every
	<dependency identifierref> must name a declared <resource identifier>.
	"""
	violations = []
	# first pass: collect every declared resource identifier
	resource_identifiers = set()
	for element in manifest_root.iter():
		if _local_name(element.tag) == "resource":
			identifier = element.get("identifier")
			if identifier:
				resource_identifiers.add(identifier)
	# second pass: validate hrefs and dependency references
	for element in manifest_root.iter():
		local_name = _local_name(element.tag)
		if local_name == "resource":
			href = element.get("href")
			# webcontent and item resources carry an href that must exist
			if href and href not in entries:
				violations.append(
					f"imsmanifest.xml: resource href '{href}' missing from package")
		elif local_name == "file":
			href = element.get("href")
			if href and href not in entries:
				violations.append(
					f"imsmanifest.xml: <file href='{href}'> missing from package")
		elif local_name == "dependency":
			ref = element.get("identifierref")
			if ref and ref not in resource_identifiers:
				violations.append(
					f"imsmanifest.xml: dependency identifierref '{ref}' "
					f"resolves to no declared resource identifier")
	return violations


#============================================
def _check_item_answer_linkage(entries: dict) -> list:
	"""
	Check that scored answer identifiers match declared choices in each item.

	Parses every XML entry and dispatches QTI 1.2 (questestinterop) items and
	QTI 2.1 (assessmentItem) items to their respective self-consistency checks.
	"""
	violations = []
	for name, data in entries.items():
		if not name.endswith(".xml"):
			continue
		root = lxml.etree.fromstring(data)
		root_local = _local_name(root.tag)
		if root_local == "questestinterop":
			violations += _check_qti12_items(name, root)
		elif root_local == "assessmentItem":
			violations += _check_qti21_item(name, root)
	return violations


#============================================
def _collect_qti12_choice_map(item_element: lxml.etree._Element) -> dict:
	"""
	Map each choice response ident to the set of its choice label idents.

	Only responses that render a fixed choice list (render_choice) are mapped;
	fill-in responses (render_fib) carry literal answers, not identifiers, and
	are intentionally excluded so their literal <varequal> values are not
	mistaken for dangling references.
	"""
	choice_map = {}
	response_tags = ("response_lid", "response_str", "response_grp")
	for element in item_element.iter():
		if _local_name(element.tag) not in response_tags:
			continue
		response_ident = element.get("ident")
		if not response_ident:
			continue
		# collect label idents that live under a render_choice in this response
		label_idents = set()
		has_render_choice = False
		for descendant in element.iter():
			descendant_local = _local_name(descendant.tag)
			if descendant_local == "render_choice":
				has_render_choice = True
			elif descendant_local == "response_label":
				label_ident = descendant.get("ident")
				if label_ident:
					label_idents.add(label_ident)
		# only choice-rendered responses take part in the linkage check
		if has_render_choice:
			choice_map[response_ident] = label_idents
	return choice_map


#============================================
def _check_qti12_items(name: str, root: lxml.etree._Element) -> list:
	"""
	Check QTI 1.2 scored <varequal> values against declared choice labels.

	For every <varequal respident="R">V</varequal> whose R names a choice
	response, V must match a declared <response_label ident> inside that same
	response. Values into fill-in responses are literal answers and skipped.
	"""
	violations = []
	for item_element in root.iter():
		if _local_name(item_element.tag) != "item":
			continue
		item_ident = item_element.get("ident", "<no-ident>")
		choice_map = _collect_qti12_choice_map(item_element)
		for descendant in item_element.iter():
			if _local_name(descendant.tag) != "varequal":
				continue
			respident = descendant.get("respident")
			# only choice-rendered responses are answer-linkage candidates
			if respident not in choice_map:
				continue
			value = (descendant.text or "").strip()
			if value not in choice_map[respident]:
				declared = ", ".join(sorted(choice_map[respident]))
				violations.append(
					f"{name}: item '{item_ident}' scored varequal value "
					f"'{value}' (respident '{respident}') matches no declared "
					f"choice identifier; declared: [{declared}]")
	return violations


#============================================
def _collect_qti21_interaction_map(item_root: lxml.etree._Element) -> dict:
	"""
	Map each interaction responseIdentifier to its declared choice identifiers.

	Any element whose local name ends with "Interaction" and carries a
	responseIdentifier contributes the identifiers of its choice descendants.
	Interactions with no choice descendants (textEntry, extendedText) map to an
	empty set, marking them as literal-answer responses.
	"""
	interaction_map = {}
	for element in item_root.iter():
		local_name = _local_name(element.tag)
		if not local_name.endswith("Interaction"):
			continue
		response_identifier = element.get("responseIdentifier")
		if not response_identifier:
			continue
		choice_identifiers = set()
		for descendant in element.iter():
			if _local_name(descendant.tag) in QTI21_CHOICE_TAGS:
				identifier = descendant.get("identifier")
				if identifier:
					choice_identifiers.add(identifier)
		interaction_map[response_identifier] = choice_identifiers
	return interaction_map


#============================================
def _check_qti21_item(name: str, root: lxml.etree._Element) -> list:
	"""
	Check QTI 2.1 correctResponse values against declared choice identifiers.

	For each responseDeclaration bound to a choice-bearing interaction, every
	whitespace token of every correctResponse <value> (a single identifier for
	choiceInteraction, a "source target" pair for matchInteraction) must match
	a declared choice identifier in that interaction. Declarations bound to a
	literal-answer interaction (textEntry) are skipped.
	"""
	violations = []
	item_ident = root.get("identifier", "<no-ident>")
	interaction_map = _collect_qti21_interaction_map(root)
	for element in root.iter():
		if _local_name(element.tag) != "responseDeclaration":
			continue
		response_identifier = element.get("identifier")
		# skip declarations with no choice-bearing interaction (literal answers)
		if not interaction_map.get(response_identifier):
			continue
		choice_identifiers = interaction_map[response_identifier]
		# gather this declaration's correctResponse values
		for descendant in element.iter():
			if _local_name(descendant.tag) != "value":
				continue
			value_text = (descendant.text or "").strip()
			if not value_text:
				continue
			# a directedPair value is two whitespace-separated identifiers
			for token in value_text.split():
				if token not in choice_identifiers:
					declared = ", ".join(sorted(choice_identifiers))
					violations.append(
						f"{name}: item '{item_ident}' correctResponse token "
						f"'{token}' (response '{response_identifier}') matches "
						f"no declared choice identifier; declared: [{declared}]")
	return violations


#============================================
def _iter_img_srcs(xml_text: str) -> list:
	"""
	Return every <img src="..."> value found in item XML or embedded HTML.

	Item stems store images either as real <img> elements (QTI 2.1) or as
	HTML-escaped markup inside a text node (QTI 1.2 mattext). Unescaping first
	makes a single regex find both forms.
	"""
	unescaped = html.unescape(xml_text)
	# capture the src of any <img> tag, escaped or not
	srcs = re.findall(r"<img[^>]*\ssrc=\"([^\"]+)\"", unescaped)
	return srcs


#============================================
def _check_media_src(entries: dict) -> list:
	"""
	Check that rewritten <img src> references resolve to packaged files.

	External (scheme) and data-URI sources are skipped. The Canvas file-base
	token is resolved relative to the package root; every other source is
	resolved relative to the item file's own folder, so a "../figure.png" from
	qti21_items/ correctly targets the package root.
	"""
	violations = []
	filebase_prefix = "$IMS-CC-FILEBASE$/"
	for name, data in entries.items():
		if not name.endswith(".xml"):
			continue
		xml_text = data.decode("utf-8", "replace")
		for src in _iter_img_srcs(xml_text):
			# skip external references and inline data URIs
			if "://" in src or src.startswith("data:") or src.startswith("mailto:"):
				continue
			if src.startswith(filebase_prefix):
				# Canvas file-base token points at a package-root-relative path
				target = src[len(filebase_prefix):]
			elif src.startswith("$"):
				# other Canvas placeholder tokens are not resolvable to a file
				continue
			else:
				# resolve relative to the item file's folder within the package
				item_dir = posixpath.dirname(name)
				target = posixpath.normpath(posixpath.join(item_dir, src))
			if target not in entries:
				violations.append(
					f"{name}: <img src='{src}'> resolves to '{target}', "
					f"which is missing from package")
	return violations


#============================================
def _parse_png_dimensions(data: bytes) -> tuple | None:
	"""
	Return (width, height) parsed from a PNG's IHDR chunk, or None if unreadable.

	The IHDR chunk always immediately follows the 8-byte PNG signature and the
	4-byte chunk-length plus 4-byte "IHDR" type fields, so width and height are
	fixed at bytes 16-19 and 20-23, big-endian, in any valid PNG.
	"""
	if not data.startswith(PNG_SIGNATURE):
		return None
	if len(data) < 24:
		return None
	width, height = struct.unpack(">II", data[16:24])
	return (width, height)


#============================================
def _parse_gif_dimensions(data: bytes) -> tuple | None:
	"""
	Return (width, height) parsed from a GIF's logical screen descriptor.

	The descriptor immediately follows the 6-byte "GIF87a"/"GIF89a" signature:
	logical screen width and height are 2 bytes each, little-endian.
	"""
	if data[:6] not in GIF_SIGNATURES:
		return None
	if len(data) < 10:
		return None
	width, height = struct.unpack("<HH", data[6:10])
	return (width, height)


#============================================
def _parse_jpeg_dimensions(data: bytes) -> tuple | None:
	"""
	Return (width, height) parsed by scanning JPEG markers for a SOF segment.

	Walks the marker stream after the Start Of Image marker, skipping any
	0xFF fill bytes and non-dimension-bearing segments by their declared
	length, until a Start-Of-Frame marker (baseline, progressive, or another
	SOF variant) is found. The SOF segment layout is fixed:
	length(2) precision(1) height(2) width(2), big-endian.
	"""
	if not data.startswith(JPEG_SOI):
		return None
	offset = 2
	while offset < len(data):
		if data[offset] != 0xFF:
			# not aligned on a marker; the header is corrupt
			return None
		# skip 0xFF fill bytes that may pad the marker prefix
		while offset < len(data) and data[offset] == 0xFF:
			offset += 1
		if offset >= len(data):
			return None
		marker = data[offset]
		offset += 1
		# markers with no following length/segment: TEM and the restart markers
		if marker == 0x01 or 0xD0 <= marker <= 0xD7:
			continue
		# End Of Image with no SOF found means the header never declared a size
		if marker == 0xD9:
			return None
		if offset + 2 > len(data):
			return None
		segment_length = struct.unpack(">H", data[offset:offset + 2])[0]
		if marker in JPEG_SOF_MARKERS:
			if offset + 7 > len(data):
				return None
			height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
			return (width, height)
		offset += segment_length
	return None


#============================================
def _detect_raster_dimensions(name: str, data: bytes) -> tuple | None:
	"""
	Detect a packaged raster image's pixel dimensions from its magic bytes.

	Dispatches by the entry's magic-byte signature rather than trusting its
	extension, so a mislabeled extension does not let an unread image slip
	past the check. When the magic bytes match no known raster signature, the
	entry's extension is used as a fallback cross-check to still attempt the
	matching parser.

	Returns:
		(width, height) when the header was readable, or None when no known
		format's parser could read it.
	"""
	if data.startswith(PNG_SIGNATURE):
		return _parse_png_dimensions(data)
	if data[:6] in GIF_SIGNATURES:
		return _parse_gif_dimensions(data)
	if data.startswith(JPEG_SOI):
		return _parse_jpeg_dimensions(data)
	# magic bytes unrecognized; fall back to the entry's extension
	lowered_name = name.lower()
	if lowered_name.endswith(".png"):
		return _parse_png_dimensions(data)
	if lowered_name.endswith(".gif"):
		return _parse_gif_dimensions(data)
	if lowered_name.endswith((".jpg", ".jpeg")):
		return _parse_jpeg_dimensions(data)
	return None


#============================================
def _check_image_dimensions(entries: dict) -> list:
	"""
	Check every packaged raster image is larger than a single invisible pixel.

	Any entry whose extension names a supported raster format is a candidate;
	its actual dimensions are read from its file header, and an entry is
	flagged when min(width, height) <= MIN_IMAGE_DIMENSION_PX or when the
	header could not be parsed at all (unreadable dimensions is itself a
	packaging defect, not something to silently skip).
	"""
	violations = []
	for name, data in entries.items():
		if not name.lower().endswith(RASTER_IMAGE_EXTENSIONS):
			continue
		dimensions = _detect_raster_dimensions(name, data)
		if dimensions is None:
			violations.append(f"{name}: could not read image dimensions from header")
			continue
		width, height = dimensions
		if min(width, height) <= MIN_IMAGE_DIMENSION_PX:
			violations.append(
				f"{name}: image dimensions {width}x{height} are at or below the "
				f"minimum visible size of {MIN_IMAGE_DIMENSION_PX}px")
	return violations


#============================================
def _check_identifier_value(
			violations: list, name: str, attribute: str, value: str | None) -> None:
	"""Append a violation to violations when value is present but not id-safe."""
	if value is None:
		return
	if not IDENTIFIER_SAFE_RE.match(value):
		violations.append(
			f"{name}: {attribute}='{value}' is not an id-safe token "
			f"(must match {IDENTIFIER_SAFE_RE.pattern})")


#============================================
def _check_manifest_identifier_safety(
			name: str, manifest_root: lxml.etree._Element) -> list:
	"""
	Check every identifier-bearing manifest attribute is an id-safe token.

	Covers the top-level <manifest identifier>, every <resource identifier>,
	and every <dependency identifierref> -- the same attributes the manifest
	cross-reference check (_check_imscp_manifest) already reads.
	"""
	violations = []
	if _local_name(manifest_root.tag) == "manifest":
		_check_identifier_value(
			violations, name, "manifest identifier", manifest_root.get("identifier"))
	for element in manifest_root.iter():
		local_name = _local_name(element.tag)
		if local_name == "resource":
			_check_identifier_value(
				violations, name, "resource identifier", element.get("identifier"))
		elif local_name == "dependency":
			_check_identifier_value(
				violations, name, "dependency identifierref", element.get("identifierref"))
	return violations


#============================================
def _check_item_identifier_safety(entries: dict) -> list:
	"""
	Check every item/assessment identifier declared in item XML is id-safe.

	Covers QTI 1.2 <item ident> and QTI 2.1 <assessmentItem identifier> --
	the same attributes _check_item_answer_linkage already reads.
	"""
	violations = []
	for name, data in entries.items():
		if not name.endswith(".xml"):
			continue
		root = lxml.etree.fromstring(data)
		root_local = _local_name(root.tag)
		if root_local == "questestinterop":
			for element in root.iter():
				if _local_name(element.tag) == "item":
					_check_identifier_value(
						violations, name, "item ident", element.get("ident"))
		elif root_local == "assessmentItem":
			_check_identifier_value(
				violations, name, "assessmentItem identifier", root.get("identifier"))
	return violations


#============================================
def _check_qti21_score_outcome_declaration(entries: dict) -> list:
	"""
	Check every QTI 2.1 assessmentItem declares an outcomeDeclaration for SCORE.

	blackboard_qti_v2_1's item_xml_helpers.create_outcome_declarations() (see
	engines/blackboard_qti_v2_1/item_xml_helpers.py) always emits
	<outcomeDeclaration baseType="float" cardinality="single"
	identifier="SCORE">; Blackboard Ultra's import scoring engine requires
	this declaration to grade the item. This scans by the assessmentItem root
	tag rather than by manifest flavor, so it applies to any QTI 2.1 item
	regardless of which manifest packaged it.
	"""
	violations = []
	for name, data in entries.items():
		if not name.endswith(".xml"):
			continue
		root = lxml.etree.fromstring(data)
		if _local_name(root.tag) != "assessmentItem":
			continue
		item_ident = root.get("identifier", "<no-ident>")
		has_score_outcome = False
		for element in root.iter():
			if _local_name(element.tag) != "outcomeDeclaration":
				continue
			if element.get("identifier") == "SCORE":
				has_score_outcome = True
				break
		if not has_score_outcome:
			violations.append(
				f"{name}: assessmentItem '{item_ident}' has no "
				f"outcomeDeclaration identifier=\"SCORE\"")
	return violations


#============================================
def _check_bb_export(entries: dict, manifest_root: lxml.etree._Element) -> list:
	"""
	Check Blackboard export-zip cross-references resolve.

	Covers manifest bb:file resolution, embedded xid image tokens, resource
	link parentId to pool object id, and csfiles binary to LOM sidecar pairing.
	"""
	violations = []
	violations += _check_bb_manifest_files(entries, manifest_root)
	# collect the identifiers scattered across the .dat resource files
	asi_object_ids, resource_ids, parent_ids, dat_text = _collect_bb_dat_refs(entries)
	violations += _check_bb_xid_tokens(entries, dat_text, resource_ids)
	violations += _check_bb_parent_ids(parent_ids, asi_object_ids)
	violations += _check_bb_sidecars(entries)
	return violations


#============================================
def _check_bb_manifest_files(entries: dict, manifest_root: lxml.etree._Element) -> list:
	"""Check every manifest bb:file attribute names a package entry."""
	violations = []
	bb_file_attr = "{" + BB_CP_NS + "}file"
	for element in manifest_root.iter():
		bb_file = element.get(bb_file_attr)
		if bb_file and bb_file not in entries:
			violations.append(
				f"imsmanifest.xml: bb:file '{bb_file}' missing from package")
	return violations


#============================================
def _collect_bb_dat_refs(entries: dict) -> tuple:
	"""
	Gather cross-reference identifiers from every .dat resource file.

	Returns the set of pool object ids (bbmd_asi_object_id), the set of
	resource-link resourceIds, the list of resource-link parentIds, and the
	concatenated .dat text used for xid-token scanning.
	"""
	asi_object_ids = set()
	resource_ids = set()
	parent_ids = []
	dat_text_parts = []
	for name, data in entries.items():
		if not name.endswith(".dat"):
			continue
		dat_text_parts.append(data.decode("utf-8", "replace"))
		root = lxml.etree.fromstring(data)
		for element in root.iter():
			local_name = _local_name(element.tag)
			if local_name == "bbmd_asi_object_id":
				if element.text:
					asi_object_ids.add(element.text.strip())
			elif local_name == "cms_resource_link":
				resource_id = _child_text(element, "resourceId")
				parent_id = _child_text(element, "parentId")
				if resource_id:
					resource_ids.add(resource_id)
				if parent_id:
					parent_ids.append(parent_id)
	dat_text = "".join(dat_text_parts)
	return asi_object_ids, resource_ids, parent_ids, dat_text


#============================================
def _check_bb_xid_tokens(entries: dict, dat_text: str, resource_ids: set) -> list:
	"""
	Check every embedded xid image token resolves to a binary and a link.

	Each bbcswebdav/xid-<n> token in the pool body must have a csfiles binary
	(csfiles/home_dir/__xid-<n>.<ext>) and a matching res00005 resourceId.
	"""
	violations = []
	# collect the csfiles binary basenames present in the package
	binary_names = set()
	for name in entries:
		basename = posixpath.basename(name)
		if basename.startswith("__xid-") and not name.endswith(".xml"):
			binary_names.add(basename)
	# scan every xid token referenced by the pool body text
	xid_tokens = set(re.findall(r"bbcswebdav/xid-([0-9A-Za-z_]+)", dat_text))
	for xid in sorted(xid_tokens):
		# a binary basename is "__xid-<xid>.<ext>"; match by that prefix
		binary_prefix = f"__xid-{xid}."
		has_binary = any(basename.startswith(binary_prefix) for basename in binary_names)
		if not has_binary:
			violations.append(
				f"xid token 'xid-{xid}' has no csfiles binary "
				f"(expected csfiles/home_dir/__xid-{xid}.*)")
		if xid not in resource_ids:
			violations.append(
				f"xid token 'xid-{xid}' has no matching CSResourceLinks "
				f"resourceId in res00005")
	return violations


#============================================
def _check_bb_parent_ids(parent_ids: list, asi_object_ids: set) -> list:
	"""Check every CSResourceLinks parentId names a pool bbmd_asi_object_id."""
	violations = []
	for parent_id in parent_ids:
		if parent_id not in asi_object_ids:
			violations.append(
				f"CSResourceLinks parentId '{parent_id}' resolves to no "
				f"bbmd_asi_object_id in the pool")
	return violations


#============================================
def _check_bb_sidecars(entries: dict) -> list:
	"""Check every csfiles binary carries its LOM sidecar XML."""
	violations = []
	for name in entries:
		basename = posixpath.basename(name)
		# a csfiles binary is an __xid- file that is not itself a sidecar
		if not basename.startswith("__xid-"):
			continue
		if name.endswith(".xml"):
			continue
		sidecar_name = f"{name}.xml"
		if sidecar_name not in entries:
			violations.append(
				f"csfiles binary '{name}' is missing its LOM sidecar "
				f"'{sidecar_name}'")
	return violations
