"""
Package scaffolding for the Blackboard pool export format.

This module builds everything that wraps the per-item `<item>` elements from
the per-type builder modules (`MC.py`/`MA.py`/`MATCH.py`/`FIB.py`/`NUM.py`/
`MULTI_FIB.py`, sharing `common_xml.py`) into a complete Blackboard Original
pool-export package:

- the `questestinterop` > `assessment` > `section` pool wrapper (`res00002.dat`),
- the `imsmanifest.xml` content-package manifest in Blackboard's `bb:` namespace,
- the small fixed-content sidecar `.dat` resources (`res00001`, `res00003`,
  `res00004`, `res00006`, `res00007`),
- the `res00005.dat` CSResourceLinks sidecar plus the per-image LOM sidecars
  that wire embedded csfiles images to the pool (see the csfiles image
  embedding section),
- the plain-text `.bb-package-info` and `.bb-log-info` property/log files.

It deliberately writes NO `.bb-package-sig`: that signature is computed
server-side at export and cannot be regenerated from package contents (see
`docs/active_plans/audits/blackboard_export_zip_forgeability.md`). A
present-but-non-server sig is more likely to be rejected on import than an
absent one, so the engine omits it.

Why this module does NOT reuse `qti_package_maker.common.qti_manifest`:
that shared helper emits the IMS-standard content package manifest
(`imscp_v1p1` default namespace, `imsqti_xmlv1p2` resource types) used by the
open QTI engines. Blackboard's pool export uses a different manifest schema --
the `bb:` namespace (`http://www.blackboard.com/content-packaging/`) with
`bb:file` / `bb:title` / `xml:base` attributes and `course/x-bb-*` and
`assessment/x-bb-qti-pool` resource types. The two schemas share no elements,
so this engine builds its own BB-local manifest here rather than bending the
IMS-standard builder.

The minimal required file set and the per-type schema are pinned from
byte-level study of the real sample pools under `BB_Export_ZIP/`; see the
forgeability audit (docs/active_plans/audits/blackboard_export_zip_forgeability.md).
"""

# Standard Library
import os
import time

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.blackboard_export_zip import common_xml

#============================================
# Namespace and manifest constants
#============================================
# Blackboard's content-packaging namespace, declared as the `bb:` prefix in the
# manifest. The IMS-standard manifest uses a different (imscp_v1p1) namespace,
# which is why common/qti_manifest does not fit here (see module docstring).
BB_NAMESPACE = "http://www.blackboard.com/content-packaging/"
# The W3C XML namespace, needed for the `xml:base` attribute on resources.
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"

# The pool XML always lands in res00002.dat; the manifest identifies it by the
# resource `type=` attribute, not the filename.
POOL_DAT_FILENAME = "res00002.dat"
POOL_RESOURCE_TYPE = "assessment/x-bb-qti-pool"

# The CSResourceLinks sidecar (res00005.dat) carries one <cms_resource_link>
# per embedded csfiles image; the reader cross-checks every body xid token
# against these entries (see build_csresourcelinks_dat and the csfiles image
# embedding section).
CSRESOURCELINKS_DAT_FILENAME = "res00005.dat"

#============================================
# Manifest resource table
#============================================
# Each tuple pins one manifest <resource> entry, in res0000N order, matching the
# real sample manifests: (identifier, dat filename, bb:title, type). res00002
# (the pool) is inserted separately so its title can carry the package name.
_SIDECAR_RESOURCES = (
	("res00001", "res00001.dat", "CourseSettings", "course/x-bb-coursesetting"),
	("res00003", "res00003.dat", "Assessment Creation Settings",
		"course/x-bb-courseassessmentcreationsettings"),
	("res00004", "res00004.dat", "LearnRubrics", "course/x-bb-rubrics"),
	("res00005", "res00005.dat", "CSResourceLinks", "course/x-bb-csresourcelinks"),
	("res00006", "res00006.dat", "Standard Alignments", "course/x-bb-stdsalignments"),
	("res00007", "res00007.dat", "CourseRubricAssociation",
		"course/x-bb-crsrubricassocation"),
)

#============================================
# Sidecar .dat fixed contents
#============================================
# These small resources carry no in-scope semantics (rubrics, standards, CS
# links are a documented non-goal). The engine emits minimal valid root
# elements rather than copying the private course/server ids the real samples
# contain. Each value is the inner XML body; build_sidecar_dat wraps it with the
# XML declaration. res00001 (course settings) ships a neutral ULTRASTATUS stub.
# res00005.dat (CSResourceLinks) is NOT listed here: it carries per-image
# content built by build_csresourcelinks_dat, not a fixed body.
_SIDECAR_DAT_BODIES = {
	"res00001.dat": '<COURSE><ULTRASTATUS value="C"/></COURSE>',
	"res00003.dat": "<ASSESSMENTCREATIONSETTINGS/>",
	"res00004.dat": "<LEARNRUBRICS/>",
	"res00006.dat": "<STDS_ALIGNMENTS/>",
	"res00007.dat": "<COURSERUBRICASSOCIATIONS/>",
}

# The XML declaration the engine prepends to every emitted .dat body. The real
# samples use this exact double-quoted UTF-8 form.
_XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'

#============================================
# Pool wrapper builders (res00002.dat)
#============================================
#============================================
def _build_pool_metadata(tag: str, question_type: str, absolutescore_max: float) -> lxml.etree.Element:
	"""
	Build an `assessmentmetadata` / `sectionmetadata` block for the pool wrapper.

	The `assessment` and `section` levels both carry a near-identical `bbmd_*` /
	`qmd_*` metadata block in the real samples. This builds either one; the
	`question_type` placeholder mirrors the sample (the first item's type) and is
	not load-bearing for import, since per-item metadata lives on each `<item>`.

	Args:
		tag: The wrapping element tag ("assessmentmetadata" or "sectionmetadata").
		question_type: The `bbmd_questiontype` placeholder value.
		absolutescore_max: The summed maximum score across all items.

	Returns:
		The metadata element.
	"""
	metadata = lxml.etree.Element(tag)
	_add_text_child(metadata, "bbmd_asitype",
		"Assessment" if tag == "assessmentmetadata" else "Section")
	_add_text_child(metadata, "bbmd_assessmenttype", "Pool")
	_add_text_child(metadata, "bbmd_sectiontype", "Subsection")
	_add_text_child(metadata, "bbmd_questiontype", question_type)
	_add_text_child(metadata, "bbmd_is_from_cartridge", "false")
	_add_text_child(metadata, "bbmd_is_disabled", "false")
	_add_text_child(metadata, "bbmd_negative_points_ind", "N")
	_add_text_child(metadata, "bbmd_canvas_fullcrdt_ind", "false")
	_add_text_child(metadata, "bbmd_all_fullcredit_ind", "false")
	_add_text_child(metadata, "bbmd_numbertype", "none")
	# Empty elements present in the samples; kept for structural fidelity.
	lxml.etree.SubElement(metadata, "bbmd_partialcredit")
	_add_text_child(metadata, "bbmd_orientationtype", "vertical")
	_add_text_child(metadata, "bbmd_is_extracredit", "false")
	lxml.etree.SubElement(metadata, "bbmd_is_metadataenabled")
	_add_text_child(metadata, "bbmd_ai_state", "No")
	# Samples store the score as a fixed 15-decimal-place float string.
	_add_text_child(metadata, "qmd_absolutescore_max", f"{absolutescore_max:.15f}")
	_add_text_child(metadata, "qmd_weighting", "0")
	lxml.etree.SubElement(metadata, "qmd_instructornotes")
	return metadata

#============================================
def _add_text_child(parent: lxml.etree.Element, tag: str, text: str) -> lxml.etree.Element:
	"""
	Append a child element with the given tag and text to a parent.

	Args:
		parent: The parent element.
		tag: The child element tag name.
		text: The text content for the child.

	Returns:
		The newly created child element.
	"""
	child = lxml.etree.SubElement(parent, tag)
	child.text = text
	return child

#============================================
def _build_empty_formatted_material() -> lxml.etree.Element:
	"""
	Build the empty `flow_mat`/`material` block the rubric and presentation_material carry.

	The samples carry an empty `<mat_formattedtext type="HTML"/>` here as a
	structural placeholder; nothing in scope reads it.

	Returns:
		The `<flow_mat class="Block">` element.
	"""
	flow_mat = lxml.etree.Element("flow_mat")
	flow_mat.set("class", "Block")
	material = lxml.etree.SubElement(flow_mat, "material")
	mat_extension = lxml.etree.SubElement(material, "mat_extension")
	mat_formattedtext = lxml.etree.SubElement(mat_extension, "mat_formattedtext")
	mat_formattedtext.set("type", "HTML")
	return flow_mat

#============================================
def build_pool_wrapper(
	item_elements: list[lxml.etree.Element],
	pool_title: str,
	question_type: str,
	total_score: float,
) -> lxml.etree.Element:
	"""
	Build the `questestinterop` > `assessment` > `section` pool wrapper.

	This is the root of `res00002.dat`. It wraps the already-built per-item
	`<item>` elements (from the per-type `build_<type>` modules) inside the pool
	envelope the real samples use: an `<assessment>` carrying `assessmentmetadata`,
	an empty `rubric` and `presentation_material`, and a `<section>` carrying its
	own `sectionmetadata` followed by every `<item>`.

	This module builds only the wrapper; the per-type dispatch that produces the
	`<item>` elements lives in the write path, which passes built items in here.

	Args:
		item_elements: Already-built `<item>` lxml Elements, in output order.
		pool_title: The pool title (typically the humanized package name).
		question_type: The `bbmd_questiontype` placeholder for the assessment and
			section metadata (typically the first item's type marker).
		total_score: The summed maximum score across all items, used for the
			`qmd_absolutescore_max` placeholder.

	Returns:
		The `<questestinterop>` root element.
	"""
	questestinterop = lxml.etree.Element("questestinterop")
	assessment = lxml.etree.SubElement(questestinterop, "assessment", title=pool_title)
	assessment.append(_build_pool_metadata("assessmentmetadata", question_type, total_score))

	# Empty rubric + presentation_material placeholders, matching the samples.
	rubric = lxml.etree.SubElement(assessment, "rubric", view="All")
	rubric.append(_build_empty_formatted_material())
	presentation_material = lxml.etree.SubElement(assessment, "presentation_material")
	presentation_material.append(_build_empty_formatted_material())

	# The section holds its own metadata, then every item.
	section = lxml.etree.SubElement(assessment, "section")
	section.append(_build_pool_metadata("sectionmetadata", question_type, total_score))
	for item_element in item_elements:
		section.append(item_element)
	return questestinterop

#============================================
# imsmanifest.xml builder
#============================================
#============================================
def build_manifest(pool_title: str) -> lxml.etree.Element:
	"""
	Build the `imsmanifest.xml` root element in Blackboard's `bb:` namespace.

	The manifest lists one `<resource>` per `res0000N.dat`, with the Blackboard
	attributes `bb:file`, `bb:title`, `identifier`, `type`, and `xml:base`. The
	`res00001` course-settings resource additionally carries an empty
	`<file href=.../>` child, matching the samples. The pool resource (`res00002`,
	type `assessment/x-bb-qti-pool`) carries the pool title.

	Args:
		pool_title: The title used for the `res00002` pool resource (`bb:title`).

	Returns:
		The `<manifest>` root element.
	"""
	# Declare the bb: prefix and the xml: prefix used by xml:base attributes.
	nsmap = {"bb": BB_NAMESPACE}
	manifest = lxml.etree.Element("manifest", nsmap=nsmap, attrib={"identifier": "main_manifest"})
	# Organizations are empty for a pool export.
	lxml.etree.SubElement(manifest, "organizations")
	resources = lxml.etree.SubElement(manifest, "resources")

	# res00001 first, then the pool (res00002), then res00003..res00007, so the
	# emitted order matches the real sample manifests.
	res00001 = _SIDECAR_RESOURCES[0]
	pool_resource = ("res00002", POOL_DAT_FILENAME, pool_title, POOL_RESOURCE_TYPE)
	ordered_resources = [res00001, pool_resource] + list(_SIDECAR_RESOURCES[1:])

	for identifier, dat_filename, bb_title, resource_type in ordered_resources:
		resource = lxml.etree.SubElement(resources, "resource")
		# bb:file and bb:title are namespaced; identifier/type/xml:base follow.
		resource.set(f"{{{BB_NAMESPACE}}}file", dat_filename)
		resource.set(f"{{{BB_NAMESPACE}}}title", bb_title)
		resource.set("identifier", identifier)
		resource.set("type", resource_type)
		resource.set(f"{{{XML_NAMESPACE}}}base", identifier)
		# The course-settings resource carries an empty <file href=.../> child.
		if identifier == "res00001":
			lxml.etree.SubElement(resource, "file", href=f"/{identifier}")
	return manifest

#============================================
# Serialization helpers
#============================================
#============================================
def serialize_xml(element: lxml.etree.Element) -> bytes:
	"""
	Serialize an lxml element to pretty-printed UTF-8 XML bytes with a declaration.

	Blackboard's own serialization is inconsistent (some pools minified, some
	pretty-printed); the engine emits one clean, valid pretty-printed form for
	every file, since byte-faithfulness is not required (the sig is omitted).

	Args:
		element: The lxml root element to serialize.

	Returns:
		The XML document as UTF-8 bytes, including the XML declaration.
	"""
	xml_bytes = lxml.etree.tostring(
		element,
		pretty_print=True,
		xml_declaration=True,
		encoding="UTF-8",
	)
	return xml_bytes

#============================================
def build_sidecar_dat(dat_filename: str) -> bytes:
	"""
	Build the bytes for a fixed-content sidecar `.dat` file.

	Looks up the minimal valid XML body for the named resource and prepends the
	XML declaration. These bodies are intentionally empty/minimal placeholders:
	reproducing the rubric/standards/CS-link semantics is a documented non-goal,
	and the real samples' bodies carry private course/server ids the engine must
	not copy.

	Args:
		dat_filename: One of res00001.dat or res00003.dat..res00007.dat.

	Returns:
		The sidecar file contents as UTF-8 bytes.
	"""
	body = _SIDECAR_DAT_BODIES[dat_filename]
	text = _XML_DECLARATION + body + "\n"
	return text.encode("utf-8")

#============================================
def sidecar_dat_filenames() -> list[str]:
	"""
	Return the fixed-content sidecar `.dat` filenames the package must include.

	This is res00001, res00003, res00004, res00006, res00007 -- every fixed-body
	`.dat`. It excludes the pool (res00002.dat, built from the items via
	build_pool_wrapper) and the CSResourceLinks sidecar (res00005.dat, built
	per-image by build_csresourcelinks_dat).

	Returns:
		The sidecar filenames in res0000N order.
	"""
	return list(_SIDECAR_DAT_BODIES.keys())

#============================================
# csfiles image embedding
#============================================
# Blackboard's Original pool export carries item images through a proprietary,
# manifest-untracked "csfiles" mechanism (confirmed from the real export under
# SAMPLES/blackboard_learn_classic-bb_export and mirrored in the committed slice
# tests/fixtures/bb_export_slice.zip). For each image the export:
#   1. writes the binary to csfiles/home_dir/__xid-<n>_1.<ext>,
#   2. embeds an <img src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1">
#      token in the item HTML (the item body, not the manifest),
#   3. writes a LOM sidecar csfiles/home_dir/__xid-<n>_1.<ext>.xml whose
#      <identifier> recovers the original course-relative filename,
#   4. records one <cms_resource_link> in res00005.dat (CSResourceLinks) whose
#      resourceId is the xid and whose parentId is the owning item's asi id.
# The csfiles binaries and sidecars are deliberately NOT declared in
# imsmanifest.xml (implicit bundling), exactly as the real export leaves them.
# The reader (read_package.py) is the inverse of this wiring.
#
# Hotspot images use a different, manifest-tracked path: the QTI <matapplication
# uri> element points at a file under the pool resource's own directory, declared
# as a bb-namespace <file href> child of the res00002 manifest resource. The
# write side does NOT emit hotspot images: no item_types class models a hotspot
# response area, so no bank item can ever carry a <matapplication>. The reader
# still handles the hotspot mechanism on import; this asymmetry is intentional.

# csfiles binaries and their LOM sidecars live under this package subdirectory.
CSFILES_HOME_SUBDIR = os.path.join("csfiles", "home_dir")
# The LOM sidecar namespaces, matching the real __xid-<n>_1.jpg.xml sidecars.
LOM_NAMESPACE = "http://www.imsglobal.org/xsd/imsmd_rootv1p2p1"
XSI_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"
LOM_SCHEMA_LOCATION = f"{LOM_NAMESPACE} imsmd_rootv1p2p1.xsd"
# Every Blackboard content-collection xid carries a version suffix; exports use
# "_1" for a first-version file, so minted tokens mirror that ("xid-<n>_1").
_XID_VERSION_SUFFIX = "_1"
# Neutral course context embedded in the LOM <identifier> path. The reader takes
# only the basename after the '#', so this value is cosmetic on round-trip; it is
# a generator marker, never a real Learn course id.
_LOM_COURSE_CONTEXT = "qti_package_maker"
# Neutral placeholder ids for CSResourceLinks entries. The real export carries
# private Learn courseId / link-id PkIds here; the engine emits neutral markers
# instead (the reader keys only on resourceId, never these).
_CSRESOURCE_COURSE_ID = "_1_1"

#============================================
def make_xid_token(xid_number: int) -> str:
	"""
	Return the body src token identifier for a minted xid (e.g. "xid-7_1").

	Args:
		xid_number: The unique integer minted for one image.

	Returns:
		The "xid-<n>_1" token that appears after the CSFILES_SRC_PREFIX in the
		item body HTML.
	"""
	return f"xid-{xid_number}{_XID_VERSION_SUFFIX}"

#============================================
def make_resource_id(xid_number: int) -> str:
	"""
	Return the CSResourceLinks resourceId for a minted xid (e.g. "7_1").

	Args:
		xid_number: The unique integer minted for one image.

	Returns:
		The "<n>_1" resourceId string cross-checked by the reader.
	"""
	return f"{xid_number}{_XID_VERSION_SUFFIX}"

#============================================
def csfiles_src_value(xid_number: int) -> str:
	"""
	Return the full `<img src>` token value the item body carries for an xid.

	Args:
		xid_number: The unique integer minted for one image.

	Returns:
		The complete src string
		"@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1".
	"""
	return common_xml.CSFILES_SRC_PREFIX + make_xid_token(xid_number)

#============================================
def csfiles_binary_name(xid_number: int, extension: str) -> str:
	"""
	Return the csfiles binary filename for a minted xid (e.g. "__xid-7_1.jpg").

	Args:
		xid_number: The unique integer minted for one image.
		extension: The image file extension including the leading dot (".jpg").

	Returns:
		The "__xid-<n>_1<ext>" filename the reader locates by its "__<token>."
		prefix.
	"""
	return f"__{make_xid_token(xid_number)}{extension}"

#============================================
def build_lom_sidecar(resource_id: str, original_name: str) -> bytes:
	"""
	Build a LOM `.xml` sidecar mapping a csfiles resourceId to its original name.

	Mirrors the real `__xid-<n>_1.jpg.xml` sidecars: a `<lom>` carrying a
	`relation/resource/identifier` whose text is
	`"<resourceId>#/courses/<course>/<original_name>"`. The reader recovers the
	original filename as the basename of the path portion after the `#`, so the
	basename must be the plain filename the round-tripped `<img src>` should read.

	Args:
		resource_id: The CSResourceLinks resourceId (e.g. "7_1").
		original_name: The plain image filename to recover (e.g. "cell.png").

	Returns:
		The LOM sidecar as UTF-8 XML bytes.
	"""
	nsmap = {None: LOM_NAMESPACE, "xsi": XSI_NAMESPACE}
	lom = lxml.etree.Element(f"{{{LOM_NAMESPACE}}}lom", nsmap=nsmap)
	lom.set(f"{{{XSI_NAMESPACE}}}schemaLocation", LOM_SCHEMA_LOCATION)
	relation = lxml.etree.SubElement(lom, f"{{{LOM_NAMESPACE}}}relation")
	resource = lxml.etree.SubElement(relation, f"{{{LOM_NAMESPACE}}}resource")
	identifier = lxml.etree.SubElement(resource, f"{{{LOM_NAMESPACE}}}identifier")
	# The reader partitions on '#' and takes the basename of the path part.
	identifier.text = f"{resource_id}#/courses/{_LOM_COURSE_CONTEXT}/{original_name}"
	return serialize_xml(lom)

#============================================
def build_csresourcelinks_dat(link_entries: list[tuple[str, str]]) -> bytes:
	"""
	Build the res00005.dat CSResourceLinks body from per-image link entries.

	Emits one `<cms_resource_link>` per entry, shaped like the real export
	(courseId / parentId / resourceId / storageType / aiState / id), using
	neutral placeholder ids for every field except resourceId and parentId. An
	empty entry list yields the minimal `<cms_resource_link_list/>` the engine
	writes when a package carries no images.

	Args:
		link_entries: (parent_id, resource_id) pairs, one per embedded image; the
			parent_id is the owning item's asi id, the resource_id is the xid.

	Returns:
		The res00005.dat contents as UTF-8 XML bytes.
	"""
	root = lxml.etree.Element("cms_resource_link_list")
	for index, (parent_id, resource_id) in enumerate(link_entries):
		link = lxml.etree.SubElement(root, "cms_resource_link")
		# courseId carries a private Learn PkId in real exports; neutral here.
		course = _add_text_child(link, "courseId", _CSRESOURCE_COURSE_ID)
		course.set("data-type", "blackboard.data.course.Course")
		# parentId ties the image to its owning item: a live Blackboard import
		# matches it against that item's <bbmd_asi_object_id> (emitted by
		# common_xml.build_itemmetadata from the same make_item_asi_object_id
		# helper) to locate the image's parent. A parentId with no matching
		# asi_object_id makes Learn drop the resource link and the embedded image.
		# The round-trip reader keys on resourceId, not parentId.
		parent = _add_text_child(link, "parentId", parent_id)
		parent.set("parent_data_type", "asiobject")
		# resourceId is the xid the reader cross-checks against the body token.
		_add_text_child(link, "resourceId", resource_id)
		_add_text_child(link, "storageType", "PUBLIC")
		_add_text_child(link, "aiState", "No")
		# id is a private link PkId in real exports; a neutral deterministic
		# marker keeps the shape without copying server data.
		link_id = _add_text_child(link, "id", f"_{index + 1}_1")
		link_id.set("data-type", "blackboard.platform.contentsystem.data.CSResourceLink")
	return serialize_xml(root)

#============================================
# .bb-* plain-text sidecar builders
#============================================
#============================================
def build_bb_package_info(package_name: str) -> bytes:
	"""
	Build a minimal valid `.bb-package-info` Java-property file.

	The real file carries Learn server metadata (install id, site id, server
	paths, JDBC/JVM details) stamped at export. The engine emits an
	engine-generated equivalent with NO private server ids: just the property
	header, an export timestamp, an EXPORT operation marker, and the package
	name. This keeps the file shape valid without copying server-private data.

	Args:
		package_name: The package name, recorded as the package identifier.

	Returns:
		The `.bb-package-info` contents as UTF-8 bytes.
	"""
	# Java .properties files lead with a "#"-comment header and timestamp line.
	timestamp = time.strftime("%a %b %d %H:%M:%S %Z %Y")
	lines = []
	lines.append("#Bb PackageInfo Property File")
	lines.append(f"#{timestamp}")
	# A neutral release marker identifying the generator, not a Learn server.
	lines.append("app.release.number=qti-package-maker")
	lines.append("cx.config.operation=EXPORT")
	lines.append(f"cx.config.package.name={package_name}")
	lines.append("cx.package.info.version=6.0")
	text = "\n".join(lines) + "\n"
	return text.encode("utf-8")

#============================================
def build_bb_log_info(package_name: str) -> bytes:
	"""
	Build a minimal valid `.bb-log-info` plain-text export log.

	The real file is a short free-text export log referencing internal Learn
	PkIds. The engine emits a neutral two-line log naming the package, carrying
	no server-private identifiers.

	Args:
		package_name: The package name, named in the log lines.

	Returns:
		The `.bb-log-info` contents as UTF-8 bytes.
	"""
	lines = []
	lines.append(f"Information: Pool '{package_name}' is being exported")
	lines.append("Information: Export complete")
	text = "\n".join(lines) + "\n"
	return text.encode("utf-8")

#============================================
# Package title helper
#============================================
#============================================
def humanize_package_name(package_name: str) -> str:
	"""
	Turn a snake_case package name into a human-readable pool title.

	Underscores become spaces; hyphens are preserved (they often carry meaning,
	like a trailing subject tag). Mirrors the Ultra engine's title helper so
	titles read the same across engines.

	Args:
		package_name: The raw package name.

	Returns:
		The humanized title.
	"""
	return package_name.replace("_", " ")

#============================================
def first_question_type(item_elements: list[lxml.etree.Element]) -> str:
	"""
	Read the `bbmd_questiontype` of the first item for the wrapper metadata.

	The pool/section metadata in the real samples carries the first item's
	question-type marker as a placeholder. This recovers it from the first
	already-built `<item>` element so the wrapper need not be told the type
	separately. An empty pool falls back to "Multiple Choice", matching the
	most common sample marker.

	Args:
		item_elements: The already-built `<item>` elements.

	Returns:
		The first item's `bbmd_questiontype` text, or "Multiple Choice" when
		there are no items.
	"""
	if not item_elements:
		return "Multiple Choice"
	# The marker lives at item > itemmetadata > bbmd_questiontype.
	marker = item_elements[0].findtext("itemmetadata/bbmd_questiontype")
	if marker is None:
		return "Multiple Choice"
	return marker
