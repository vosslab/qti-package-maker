# Standard Library
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.text2qti import write_item
from qti_package_maker.engines.text2qti import read_package


def _roundtrip_one(
	item_cls: item_types.BaseItem, tmp_path: pathlib.Path, filename: str
) -> item_types.BaseItem:
	item_cls.item_number = 1
	writer = getattr(write_item, item_cls.item_type)
	content = writer(item_cls)
	infile = tmp_path / filename
	infile.write_text(content, encoding="utf-8")
	bank = read_package.read_items_from_file(str(infile), allow_mixed=True)
	assert len(bank) == 1
	return next(iter(bank.items_dict.values()))


def test_text2qti_roundtrip_mc(tmp_path: pathlib.Path) -> None:
	item = item_types.MC("MC question?", ["A", "B"], "B")
	roundtripped = _roundtrip_one(item, tmp_path, "mc.txt")
	assert roundtripped.item_type == "MC"
	assert roundtripped.question_text == "MC question?"
	assert roundtripped.answer_text == "B"


def test_text2qti_roundtrip_ma(tmp_path: pathlib.Path) -> None:
	item = item_types.MA("MA question?", ["A", "B", "C"], ["A", "C"])
	roundtripped = _roundtrip_one(item, tmp_path, "ma.txt")
	assert roundtripped.item_type == "MA"
	assert set(roundtripped.answers_list) == {"A", "C"}


def test_text2qti_roundtrip_num(tmp_path: pathlib.Path) -> None:
	item = item_types.NUM("NUM question?", 3.14, 0.01)
	roundtripped = _roundtrip_one(item, tmp_path, "num.txt")
	assert roundtripped.item_type == "NUM"
	assert roundtripped.answer_float == 3.14
	assert roundtripped.tolerance_float == 0.01


def test_text2qti_roundtrip_fib(tmp_path: pathlib.Path) -> None:
	item = item_types.FIB("FIB question?", ["alpha", "beta"])
	roundtripped = _roundtrip_one(item, tmp_path, "fib.txt")
	assert roundtripped.item_type == "FIB"
	assert roundtripped.answers_list == ["alpha", "beta"]
