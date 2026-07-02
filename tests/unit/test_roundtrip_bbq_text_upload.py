# Standard Library
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.bbq_text_upload import write_item
from qti_package_maker.engines.bbq_text_upload import read_package


def _build_items() -> list:
	return [
		item_types.MC("MC question?", ["A", "B", "C"], "B"),
		item_types.MA("MA question?", ["A", "B", "C", "D"], ["A", "D"]),
		item_types.MATCH("MATCH question?", ["P1", "P2"], ["C1", "C2"]),
		item_types.NUM("NUM question?", 10.0, 1.0, True),
		item_types.FIB("FIB question?", ["alpha", "beta"]),
		item_types.MULTI_FIB("MULTI_FIB [x] [y]?", {"x": ["one"], "y": ["two"]}),
		item_types.ORDER("ORDER question?", ["first", "second", "third"]),
	]


def _write_item_text(item_cls: item_types.BaseItem) -> str:
	writer = getattr(write_item, item_cls.item_type)
	return writer(item_cls)


def test_bbq_roundtrip_all_supported_types(tmp_path: pathlib.Path) -> None:
	items = _build_items()
	content = "".join(_write_item_text(item) for item in items)
	infile = tmp_path / "bbq-roundtrip.txt"
	infile.write_text(content, encoding="utf-8")

	bank = read_package.read_items_from_file(str(infile), allow_mixed=True)
	assert len(bank) == len(items)

	by_type = {item.item_type: item for item in bank.items_dict.values()}
	assert by_type["MC"].question_text == "MC question?"
	assert by_type["MC"].answer_text == "B"

	assert by_type["MA"].question_text == "MA question?"
	assert set(by_type["MA"].answers_list) == {"A", "D"}

	assert by_type["MATCH"].prompts_list == ["P1", "P2"]
	assert by_type["MATCH"].choices_list == ["C1", "C2"]

	assert by_type["NUM"].answer_float == 10.0
	assert by_type["NUM"].tolerance_float == 1.0

	assert by_type["FIB"].answers_list == ["alpha", "beta"]
	assert by_type["MULTI_FIB"].answer_map["x"] == ["one"]
	assert by_type["MULTI_FIB"].answer_map["y"] == ["two"]
	assert by_type["ORDER"].ordered_answers_list == ["first", "second", "third"]
