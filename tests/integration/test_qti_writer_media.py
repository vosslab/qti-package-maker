# Standard Library
import base64
import pathlib
import zipfile

# Pip3 Library
import pytest
import lxml.etree

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as qti12_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as qti21_engine


# Inline byte constants (same reusable pattern as tests/unit/test_media_assets.py).

# 1x1 transparent PNG, 68 bytes.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# A second, distinct 1x1 PNG (opaque red) for the same-basename collision case.
PNG_BYTES_ALT = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


#============================================
def _find_by_local_name(root: lxml.etree._Element, name: str, attrib: dict | None = None) -> list:
	"""
	Find every descendant whose local tag name matches, ignoring the manifest's
	default XML namespace (the manifest declares xmlns=imscp_v1p1, so an
	unqualified findall("resource") would otherwise match nothing).
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
def _build_bank_with_image(tmp_path: pathlib.Path) -> ItemBank:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bank = ItemBank(media_base_dir=str(tmp_path))
	bank.add_item("MC", (
		'What does <img src="images/figure.png" alt="fig"/> show?',
		["A", "B"],
		"A",
	))
	return bank


#============================================
def test_canvas_qti12_packages_image_and_rewrites_relative_src(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = _build_bank_with_image(tmp_path)
	engine = qti12_engine.EngineClass("media-sample", verbose=False)
	outfile = tmp_path / "qti12.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		assert "media/figure.png" in names
		assert zip_file.read("media/figure.png") == PNG_BYTES

		items_text = zip_file.read("canvas_qti12_questions/canvas_qti12_questions.xml").decode("utf-8")
		assert 'src="../media/figure.png"' in items_text

		manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
		webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
		assert len(webcontent_resources) == 1
		assert webcontent_resources[0].get("href") == "media/figure.png"


#============================================
def test_canvas_qti12_filebase_variant_rewrites_src_token(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = _build_bank_with_image(tmp_path)
	engine = qti12_engine.EngineClass(
		"media-filebase", verbose=False, canvas_src_variant=qti12_engine.CANVAS_SRC_VARIANT_FILEBASE)
	outfile = tmp_path / "qti12_filebase.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		items_text = zip_file.read("canvas_qti12_questions/canvas_qti12_questions.xml").decode("utf-8")
		assert 'src="$IMS-CC-FILEBASE$/media/figure.png"' in items_text


#============================================
def test_blackboard_qti21_packages_image_at_root_and_rewrites_src(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = _build_bank_with_image(tmp_path)
	engine = qti21_engine.EngineClass("media-sample21", verbose=False)
	outfile = tmp_path / "qti21.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		# BB QTI 2.1 places images at the package ROOT, matching
		# SAMPLES/blackboard_learn_classic-qti21_export (root image-N.jpg files).
		assert "figure.png" in names
		assert zip_file.read("figure.png") == PNG_BYTES

		item_text = zip_file.read("qti21_items/item_00001.xml").decode("utf-8")
		assert 'src="../figure.png"' in item_text

		manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
		webcontent_resource = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})[0]
		assert webcontent_resource.get("href") == "figure.png"
		assert webcontent_resource.get("identifier") == "ccres00001"
		item_resource = _find_by_local_name(manifest_root, "resource", {"identifier": "item_00001"})[0]
		dependency_refs = [dep.get("identifierref") for dep in _find_by_local_name(item_resource, "dependency")]
		assert "ccres00001" in dependency_refs


#============================================
def test_blackboard_qti21_shared_image_gets_one_resource_many_dependencies(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bank = ItemBank(allow_mixed=True, media_base_dir=str(tmp_path))
	bank.add_item("MC", ('Q1 <img src="images/figure.png"/>?', ["A", "B"], "A"))
	bank.add_item("MC", ('Q2 <img src="images/figure.png"/>?', ["C", "D"], "C"))
	engine = qti21_engine.EngineClass("media-shared", verbose=False)
	outfile = tmp_path / "qti21_shared.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		# the same bytes are packaged exactly once
		assert zip_file.namelist().count("figure.png") == 1
		manifest_root = lxml.etree.fromstring(zip_file.read("imsmanifest.xml"))
		webcontent_resources = _find_by_local_name(manifest_root, "resource", {"type": "webcontent"})
		assert len(webcontent_resources) == 1
		shared_identifier = webcontent_resources[0].get("identifier")
		for item_identifier in ("item_00001", "item_00002"):
			item_resource = _find_by_local_name(manifest_root, "resource", {"identifier": item_identifier})[0]
			dependency_refs = [dep.get("identifierref") for dep in _find_by_local_name(item_resource, "dependency")]
			assert shared_identifier in dependency_refs


#============================================
def test_collision_renames_deterministic_across_bank(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	images_dir = tmp_path / "images"
	figures_dir = tmp_path / "figures"
	images_dir.mkdir()
	figures_dir.mkdir()
	(images_dir / "figure.png").write_bytes(PNG_BYTES)
	(figures_dir / "figure.png").write_bytes(PNG_BYTES_ALT)
	bank = ItemBank(allow_mixed=True, media_base_dir=str(tmp_path))
	bank.add_item("MC", ('Q1 <img src="images/figure.png"/>?', ["A", "B"], "A"))
	bank.add_item("MC", ('Q2 <img src="figures/figure.png"/>?', ["C", "D"], "C"))
	engine = qti21_engine.EngineClass("media-collision", verbose=False)
	outfile = tmp_path / "qti21_collision.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = set(zip_file.namelist())
		assert "figure.png" in names
		assert "figure(1).png" in names
		assert zip_file.read("figure.png") != zip_file.read("figure(1).png")


#============================================
def test_data_uri_image_raises_for_packaging_engine(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	encoded = base64.b64encode(b"not a real gif").decode("ascii")
	bank = ItemBank(media_base_dir=str(tmp_path))
	bank.add_item("MC", (
		f'What does <img src="data:image/gif;base64,{encoded}" alt="fig"/> show?',
		["A", "B"],
		"A",
	))
	engine = qti12_engine.EngineClass("media-datauri", verbose=False)
	with pytest.raises(media_assets.MediaPolicyError, match="data URI"):
		engine.save_package(bank, outfile=str(tmp_path / "qti12_datauri.zip"))


#============================================
def test_external_image_kept_verbatim_and_not_bundled(
			tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = ItemBank(media_base_dir=str(tmp_path))
	bank.add_item("MC", (
		'What does <img src="https://example.com/figure.png" alt="fig"/> show?',
		["A", "B"],
		"A",
	))
	engine = qti12_engine.EngineClass("media-external", verbose=False)
	outfile = tmp_path / "qti12_external.zip"
	engine.save_package(bank, outfile=str(outfile))

	with zipfile.ZipFile(outfile, "r") as zip_file:
		names = zip_file.namelist()
		assert not any(name.startswith("media/") for name in names)
		items_text = zip_file.read("canvas_qti12_questions/canvas_qti12_questions.xml").decode("utf-8")
		assert 'src="https://example.com/figure.png"' in items_text
