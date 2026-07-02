"""
Automated structure checks for the LMS probe kits.

Unzips each buildable probe package (devel/build_canvas_media_probe.py,
devel/build_ultra_media_probe.py, devel/build_bb_original_probe.py) and
asserts its layout/manifest matches the corresponding SAMPLES/ reference
shape BEFORE any human sandbox import, so package correctness is proven by
fixtures and only real-LMS rendering waits on a human. The gate B (BB Learn
CLASSIC) kit's bbexport variant csfiles image-embedding shape is checked
against tests/fixtures/bb_export_slice.zip, the trimmed real-export reference
(the write path that variant exercises); its qti21 variant is checked
against the same webcontent/dependency shape the gate D qti21 variant uses,
since both are driven by the real blackboard_qti_v2_1 engine.
"""

# Standard Library
import re
import pathlib
import zipfile

# Pip3 Library
import lxml.etree
import pytest

# QTI Package Maker
import devel.build_canvas_media_probe as canvas_probe
import devel.build_ultra_media_probe as ultra_probe
import devel.build_bb_original_probe as bb_learn_probe
from qti_package_maker.engines.blackboard_export_zip import assessment_meta as bb_assessment_meta


#============================================
def _find_by_local_name(root: lxml.etree._Element, name: str, attrib: dict | None = None) -> list:
	"""
	Find every descendant whose local tag name matches, ignoring the default
	XML namespace both the Canvas/BB QTI manifests and the Ultra manifest
	declare (an unqualified findall would otherwise match nothing).
	"""
	matches = []
	for node in root.iter():
		if not node.tag.endswith(f"}}{name}") and node.tag != name:
			continue
		if attrib and any(node.get(key) != value for key, value in attrib.items()):
			continue
		matches.append(node)
	return matches


#============================================
def test_canvas_probe_kit_matches_expected_layout(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	"""
	Gate A kit: both Canvas src-token variants package the image under
	media/ and rewrite <img src> to the variant-specific token (the writer's
	evidenced contract; no real Canvas sample exists yet, so this checks
	the QTI-1.2-spec-derived shape the engine already produces).
	"""
	monkeypatch.chdir(tmp_path)
	kit_paths = canvas_probe.build_probe_kit(str(tmp_path / "canvas"))
	assert set(kit_paths) == {"relative", "filebase"}

	expected_src_token = {
		"relative": "../media/probe-figure.jpg",
		"filebase": "$IMS-CC-FILEBASE$/media/probe-figure.jpg",
	}
	for variant_name, zip_path in kit_paths.items():
		with zipfile.ZipFile(zip_path) as zip_file:
			names = set(zip_file.namelist())
			assert "media/probe-figure.jpg" in names
			assert zip_file.read("media/probe-figure.jpg") == canvas_probe.PROBE_JPEG_BYTES

			items_text = zip_file.read(
				"canvas_qti12_questions/canvas_qti12_questions.xml").decode("utf-8")
			assert f'src="{expected_src_token[variant_name]}"' in items_text

			manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
			webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
			assert len(webcontent_resources) == 1
			assert webcontent_resources[0].get("href") == "media/probe-figure.jpg"


#============================================
def test_ultra_qti21_probe_kit_matches_expected_layout(tmp_path: pathlib.Path) -> None:
	"""
	Gate D kit (qti21 variant): the generated ZIP is built through the real
	blackboard_qti_v2_1 engine, which stages the probe image at the package
	root and rewrites the item's `<img src>` with a single `../`, matching
	SAMPLES/blackboard_learn_classic-qti21_export -- manifest identifier
	main_manifest, a webcontent manifest resource for the image, and the
	item resource wired to it via <dependency>. Targets Ultra's "Import
	from QTI 2.1 package" menu entry. See
	test_ultra_bbexport_probe_kit_matches_expected_layout for the other
	gate D variant, which targets Ultra's separate "Import from file"
	conversion importer.
	"""
	zip_path = ultra_probe.build_qti21_variant_zip(str(tmp_path))
	assert pathlib.Path(zip_path).name == ultra_probe.QTI21_OUTFILE_NAME

	with zipfile.ZipFile(zip_path) as zip_file:
		names = set(zip_file.namelist())
		assert ultra_probe.PROBE_IMAGE_FILENAME in names
		assert zip_file.read(ultra_probe.PROBE_IMAGE_FILENAME) == ultra_probe.PROBE_JPEG_BYTES

		manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
		assert manifest_root.get("identifier") == "main_manifest"

		webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
		assert len(webcontent_resources) == 1
		assert webcontent_resources[0].get("href") == ultra_probe.PROBE_IMAGE_FILENAME
		webcontent_identifier = webcontent_resources[0].get("identifier")

		item_resources = _find_by_local_name(
			manifest_root, "resource", {"type": "imsqti_item_xmlv2p1"})
		assert len(item_resources) == 1
		dependency_refs = [
			dep.get("identifierref") for dep in _find_by_local_name(item_resources[0], "dependency")
		]
		assert webcontent_identifier in dependency_refs

		# The visible title is set directly from package_name (no humanization),
		# distinct from the bbexport variant's title.
		meta_root = lxml.etree.fromstring(zip_file.read("qti21_items/assessment_meta.xml"))
		assert meta_root.get("title") == ultra_probe.QTI21_PACKAGE_NAME

		item_text = zip_file.read("qti21_items/item_00001.xml").decode("utf-8")
		assert f'<img src="../{ultra_probe.PROBE_IMAGE_FILENAME}"' in item_text


#============================================
def test_ultra_probe_shape_matches_real_samples_export() -> None:
	"""
	Document the real Ultra export image-embedding contract, read directly
	from SAMPLES/blackboard_ultra-qti21_export: every embedded-image
	webcontent resource's href sits under
	READ_ONLY/question/_<digits>_1/embedded/, and every item resource
	declares at least one <dependency> pointing at one of those image
	resources. This is independent of the probe kit above (which now
	targets the same webcontent/dependency shape blackboard_qti_v2_1
	already produces, staged at the package root, since gate D confirmed a
	synthesized-id `<img>` pool imports and renders); it stays useful
	reference for any future engine work reading this SAMPLES export
	directly. (The sample also carries one non-image webcontent resource, a
	qti21/web_content00001.log manifest artifact, excluded here since it is
	not an embedded-image reference.)
	"""
	repo_root = pathlib.Path(__file__).resolve().parents[2]
	sample_manifest_path = repo_root / "SAMPLES" / "blackboard_ultra-qti21_export" / "imsmanifest.xml"
	manifest_root = lxml.etree.fromstring(sample_manifest_path.read_bytes())

	embedded_folder_pattern = re.compile(r"^READ_ONLY/question/(_\d+_1)/embedded/[^/]+$")
	webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
	assert webcontent_resources
	image_webcontent_resources = [
		resource for resource in webcontent_resources
		if embedded_folder_pattern.match(resource.get("href"))
	]
	assert image_webcontent_resources
	webcontent_identifiers = {resource.get("identifier") for resource in image_webcontent_resources}
	# map each image webcontent identifier to its embedded folder id, so an
	# item's <dependency> can be resolved back to the folder id it points at.
	folder_id_by_webcontent_identifier = {
		resource.get("identifier"): embedded_folder_pattern.match(resource.get("href")).group(1)
		for resource in image_webcontent_resources
	}

	item_resources = _find_by_local_name(manifest_root, "resource", {"type": "imsqti_item_xmlv2p1"})
	assert item_resources
	for item_resource in item_resources:
		dependency_refs = {
			dep.get("identifierref") for dep in _find_by_local_name(item_resource, "dependency")
		}
		image_deps = dependency_refs & webcontent_identifiers
		assert image_deps

		# Every real Ultra item's own @identifier is "QUE_" + the embedded
		# folder id verbatim (the folder id already starts with "_", so this
		# yields a double underscore, e.g. "QUE__23221289_1" for folder
		# "_23221289_1"). Confirm that contract holds for the item XML file
		# this manifest resource points at.
		item_file_path = repo_root / "SAMPLES" / "blackboard_ultra-qti21_export" / item_resource.get("href")
		item_root = lxml.etree.fromstring(item_file_path.read_bytes())
		item_identifier = item_root.get("identifier")
		expected_identifiers = {
			f"QUE_{folder_id_by_webcontent_identifier[webcontent_identifier]}"
			for webcontent_identifier in image_deps
		}
		assert item_identifier in expected_identifiers


#============================================
def test_ultra_bbexport_probe_kit_matches_expected_layout(tmp_path: pathlib.Path) -> None:
	"""
	Gate D kit (bbexport variant): the third Ultra probe ZIP targets Ultra's
	"Import from file" conversion importer rather than "Import from QTI 2.1
	package", so it is built through the same blackboard_export_zip csfiles
	write path as the gate B kit -- a csfiles/home_dir/ binary plus its LOM
	sidecar, a matching res00005.dat CSResourceLinks resourceId, and an
	@X@...bbcswebdav/xid-<n>_1 body token in the pool .dat -- and carries its
	own distinct visible pool title.
	"""
	zip_path = ultra_probe.build_bbexport_variant_zip(str(tmp_path))
	assert pathlib.Path(zip_path).name == ultra_probe.BBEXPORT_OUTFILE_NAME

	with zipfile.ZipFile(zip_path) as zip_file:
		names = set(zip_file.namelist())

		# csfiles binary + LOM sidecar are both present, one xid pair for the
		# single probe image (the engine mints xids starting at 1).
		binary_name = "csfiles/home_dir/__xid-1_1.jpg"
		sidecar_name = f"{binary_name}.xml"
		assert binary_name in names
		assert sidecar_name in names
		assert zip_file.read(binary_name) == ultra_probe.PROBE_JPEG_BYTES

		# The pool .dat body carries the @X@...bbcswebdav/xid-1_1 src token.
		pool_text = zip_file.read(bb_assessment_meta.POOL_DAT_FILENAME).decode("utf-8")
		assert bb_assessment_meta.csfiles_src_value(1) in pool_text

		# The pool title is the humanized bbexport package name, distinct from
		# the two QTI 2.1 variant titles.
		pool_root = lxml.etree.fromstring(zip_file.read(bb_assessment_meta.POOL_DAT_FILENAME))
		assessment_node = pool_root.find("assessment")
		assert assessment_node.get("title") == "Ultra Media Probe IMG BBEXPORT"

		# res00005.dat CSResourceLinks records the matching resourceId.
		resource_links_root = lxml.etree.fromstring(
			zip_file.read(bb_assessment_meta.CSRESOURCELINKS_DAT_FILENAME))
		resource_ids = [
			node.text for node in _find_by_local_name(resource_links_root, "resourceId")
		]
		assert bb_assessment_meta.make_resource_id(1) in resource_ids

		# Every CSResourceLinks parentId must resolve to an item bbmd_asi_object_id
		# in the pool, or a live Blackboard import drops the embedded image with
		# "the parent ... cannot be located in the package".
		item_asi_ids = {
			node.text for node in _find_by_local_name(pool_root, "bbmd_asi_object_id")
		}
		parent_ids = [
			node.text for node in _find_by_local_name(resource_links_root, "parentId")
		]
		assert parent_ids
		assert all(parent_id in item_asi_ids for parent_id in parent_ids)

		# csfiles binaries/sidecars stay manifest-untracked (implicit bundling).
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert "csfiles" not in manifest_text


#============================================
def test_bb_learn_bbexport_probe_kit_matches_expected_layout(tmp_path: pathlib.Path) -> None:
	"""
	Gate B (optional) bbexport variant: the generated ZIP embeds the probe
	image through the csfiles mechanism confirmed by
	tests/fixtures/bb_export_slice.zip (the trimmed real-export reference) -- a
	csfiles/home_dir/ binary plus its LOM sidecar, a matching res00005.dat
	CSResourceLinks resourceId, and an @X@...bbcswebdav/xid-<n>_1 body token
	in the pool .dat, with the csfiles files left undeclared in
	imsmanifest.xml (implicit bundling). Targets classic Blackboard Learn's
	"Import Package" menu entry.
	"""
	zip_path = bb_learn_probe.build_bbexport_variant_zip(str(tmp_path))
	assert pathlib.Path(zip_path).name == bb_learn_probe.BBEXPORT_OUTFILE_NAME

	with zipfile.ZipFile(zip_path) as zip_file:
		names = set(zip_file.namelist())

		# csfiles binary + LOM sidecar are both present, one xid pair for the
		# single probe image (the engine mints xids starting at 1).
		binary_name = "csfiles/home_dir/__xid-1_1.jpg"
		sidecar_name = f"{binary_name}.xml"
		assert binary_name in names
		assert sidecar_name in names
		assert zip_file.read(binary_name) == bb_learn_probe.PROBE_JPEG_BYTES

		# The pool .dat body carries the @X@...bbcswebdav/xid-1_1 src token.
		pool_text = zip_file.read(
			bb_assessment_meta.POOL_DAT_FILENAME).decode("utf-8")
		assert bb_assessment_meta.csfiles_src_value(1) in pool_text

		# The pool title is the humanized bbexport package name, distinct from
		# the qti21 variant's title.
		pool_root = lxml.etree.fromstring(zip_file.read(bb_assessment_meta.POOL_DAT_FILENAME))
		assessment_node = pool_root.find("assessment")
		assert assessment_node.get("title") == "BB Learn Probe IMG BBEXPORT"

		# res00005.dat CSResourceLinks records the matching resourceId.
		resource_links_root = lxml.etree.fromstring(
			zip_file.read(bb_assessment_meta.CSRESOURCELINKS_DAT_FILENAME))
		resource_ids = [
			node.text for node in _find_by_local_name(resource_links_root, "resourceId")
		]
		assert bb_assessment_meta.make_resource_id(1) in resource_ids

		# Every CSResourceLinks parentId must resolve to an item bbmd_asi_object_id
		# in the pool, or a live Blackboard import drops the embedded image with
		# "the parent ... cannot be located in the package".
		item_asi_ids = {
			node.text for node in _find_by_local_name(pool_root, "bbmd_asi_object_id")
		}
		parent_ids = [
			node.text for node in _find_by_local_name(resource_links_root, "parentId")
		]
		assert parent_ids
		assert all(parent_id in item_asi_ids for parent_id in parent_ids)

		# csfiles binaries/sidecars stay manifest-untracked (implicit bundling).
		manifest_text = zip_file.read("imsmanifest.xml").decode("utf-8")
		assert "csfiles" not in manifest_text


#============================================
def test_bb_learn_qti21_probe_kit_matches_expected_layout(tmp_path: pathlib.Path) -> None:
	"""
	Gate B (optional) qti21 variant: the generated ZIP stages the probe image
	at the package root and rewrites the item's `<img src>` with a single
	`../`, matching SAMPLES/blackboard_learn_classic-qti21_export -- a
	webcontent manifest resource for the image, and the item resource wired
	to it via <dependency>. Targets classic Blackboard Learn's separate
	"Pools > Import" QTI 2.1 menu entry.
	"""
	zip_path = bb_learn_probe.build_qti21_variant_zip(str(tmp_path))
	assert pathlib.Path(zip_path).name == bb_learn_probe.QTI21_OUTFILE_NAME

	with zipfile.ZipFile(zip_path) as zip_file:
		names = set(zip_file.namelist())
		assert bb_learn_probe.PROBE_MEDIA_FILENAME in names
		assert zip_file.read(bb_learn_probe.PROBE_MEDIA_FILENAME) == bb_learn_probe.PROBE_JPEG_BYTES

		manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
		webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
		assert len(webcontent_resources) == 1
		assert webcontent_resources[0].get("href") == bb_learn_probe.PROBE_MEDIA_FILENAME
		webcontent_identifier = webcontent_resources[0].get("identifier")

		item_resources = _find_by_local_name(
			manifest_root, "resource", {"type": "imsqti_item_xmlv2p1"})
		assert len(item_resources) == 1
		dependency_refs = [
			dep.get("identifierref") for dep in _find_by_local_name(item_resources[0], "dependency")
		]
		assert webcontent_identifier in dependency_refs

		# The visible title is set directly from package_name (no humanization),
		# distinct from the bbexport variant's title.
		meta_root = lxml.etree.fromstring(zip_file.read("qti21_items/assessment_meta.xml"))
		assert meta_root.get("title") == "BB Learn Probe IMG QTI21"

		item_text = zip_file.read("qti21_items/item_00001.xml").decode("utf-8")
		assert f'<img src="../{bb_learn_probe.PROBE_MEDIA_FILENAME}"' in item_text
