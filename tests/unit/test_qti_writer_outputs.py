# Standard Library
import pathlib
import zipfile

# Pip3 Library
import pytest
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as qti12_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as qti21_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import write_item as qti21_write_item


def _build_bank_qti12() -> ItemBank:
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("FIB", ("Q2?", ["alpha", "beta"]))
	return bank


def _build_bank_qti21() -> ItemBank:
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MC", ("Q1?", ["A", "B"], "B"))
	bank.add_item("NUM", ("Q2?", 3.14, 0.01))
	return bank


def _parse_xml_bytes(xml_bytes: bytes) -> lxml.etree._Element:
	return lxml.etree.fromstring(xml_bytes)


def _find_first_by_local_name(root: lxml.etree._Element, name: str) -> lxml.etree._Element | None:
	for node in root.iter():
		if node.tag.endswith(name):
			return node
	return None


def _assert_manifest_refs_present(manifest_bytes: bytes, zip_names: set) -> None:
	root = _parse_xml_bytes(manifest_bytes)
	file_hrefs = [node.get("href") for node in root.findall(".//file")]
	resource_hrefs = [node.get("href") for node in root.findall(".//resource")]
	for href in file_hrefs + resource_hrefs:
		if href:
			assert href in zip_names


def _correct_response_values(item_root: lxml.etree._Element) -> list[str]:
	# collect the <value> text under every <correctResponse>
	values: list[str] = []
	for node in item_root.iter():
		if node.tag.endswith("correctResponse"):
			for value_node in node:
				if value_node.tag.endswith("value"):
					values.append(value_node.text)
	return values


def _simple_choice_identifiers(item_root: lxml.etree._Element) -> set[str]:
	# collect the identifier of every <simpleChoice>
	identifiers: set[str] = set()
	for node in item_root.iter():
		if node.tag.endswith("simpleChoice"):
			identifiers.add(node.get("identifier"))
	return identifiers


def test_qti21_mc_correct_response_matches_a_choice() -> None:
	# Learn rejects an MC item (mc.no_valid_answer_match) unless the correctResponse
	# value is one of the declared simpleChoice identifiers. The real Learn export
	# links them with unpadded ids like answer_2 (SAMPLES/.../assessmentItem00001.xml).
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MC", ("Q1?", ["Red", "Blue", "Green"], "Blue"))
	item = list(bank)[0]
	item_root = qti21_write_item.MC(item)
	correct_values = _correct_response_values(item_root)
	choice_ids = _simple_choice_identifiers(item_root)
	assert set(correct_values).issubset(choice_ids)


def test_qti21_ma_correct_responses_match_choices() -> None:
	# Every correctResponse value in a multiple-answer item must resolve to a
	# declared simpleChoice identifier; the real MA export uses answer_1/answer_2
	# (SAMPLES/.../assessmentItem00002.xml).
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MA", ("Q2?", ["Red", "Blue", "Green", "Yellow"], ["Blue", "Yellow"]))
	item = list(bank)[0]
	item_root = qti21_write_item.MA(item)
	correct_values = _correct_response_values(item_root)
	choice_ids = _simple_choice_identifiers(item_root)
	assert set(correct_values).issubset(choice_ids)


def test_qti21_ma_correct_response_order_is_numeric() -> None:
	# With 11+ choices, unpadded ids (answer_1 .. answer_11) sort lexically as
	# answer_1, answer_10, answer_11, answer_2, ... A plain string sort would
	# put answer_10 before answer_2; the writer must sort by the integer suffix
	# instead so correctResponse values line up with declared choice order.
	choices = [f"Choice{n}" for n in range(1, 12)]
	correct_choices = [choices[1], choices[9]]
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MA", ("Pick correct:", choices, correct_choices))
	item = list(bank)[0]
	item_root = qti21_write_item.MA(item)

	# Map each declared simpleChoice identifier to its position in the item body.
	choice_order = [
		node.get("identifier") for node in item_root.iter()
		if node.tag.endswith("simpleChoice")
	]
	correct_values = _correct_response_values(item_root)
	# correctResponse values must appear in the same order as their declared choices.
	correct_positions = [choice_order.index(value) for value in correct_values]
	assert correct_positions == sorted(correct_positions)
	assert correct_values == ["answer_2", "answer_10"]


def test_qti12_zip_layout_and_manifest(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	engine = qti12_engine.EngineClass("sample", verbose=False)
	outfile = tmp_path / "qti12.zip"
	engine.save_package(_build_bank_qti12(), outfile=str(outfile))
	assert outfile.exists()

	with zipfile.ZipFile(outfile, "r") as zipf:
		zip_names = set(zipf.namelist())
		assert "imsmanifest.xml" in zip_names
		assert "canvas_qti12_questions/assessment_meta.xml" in zip_names
		assert "canvas_qti12_questions/canvas_qti12_questions.xml" in zip_names

		manifest_bytes = zipf.read("imsmanifest.xml")
		_assert_manifest_refs_present(manifest_bytes, zip_names)

		items_bytes = zipf.read("canvas_qti12_questions/canvas_qti12_questions.xml")
		items_text = items_bytes.decode("utf-8")
		assert "</item>\n\n      <item" in items_text
		assert "</itemmetadata>\n\n        <presentation>" in items_text
		root = _parse_xml_bytes(items_bytes)
		assert root.tag.endswith("questestinterop")


def test_qti21_zip_layout_and_manifest(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	engine = qti21_engine.EngineClass("sample", verbose=False)
	outfile = tmp_path / "qti21.zip"
	engine.save_package(_build_bank_qti21(), outfile=str(outfile))
	assert outfile.exists()

	with zipfile.ZipFile(outfile, "r") as zipf:
		zip_names = set(zipf.namelist())
		assert "imsmanifest.xml" in zip_names
		assert "qti21_items/assessment_meta.xml" in zip_names
		assert "qti21_items/item_00001.xml" in zip_names
		assert "qti21_items/item_00002.xml" in zip_names

		manifest_bytes = zipf.read("imsmanifest.xml")
		_assert_manifest_refs_present(manifest_bytes, zip_names)

		item_bytes = zipf.read("qti21_items/item_00001.xml")
		item_text = item_bytes.decode("utf-8")
		assert "</responseDeclaration>\n\n  <outcomeDeclaration" in item_text
		assert "/>\n\n  <itemBody>" in item_text
		item_root = _parse_xml_bytes(item_bytes)
		assert item_root.tag.endswith("assessmentItem")
		assert _find_first_by_local_name(item_root, "responseDeclaration") is not None
		assert _find_first_by_local_name(item_root, "itemBody") is not None
		assert _find_first_by_local_name(item_root, "responseProcessing") is not None
