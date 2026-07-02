# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.bbq_text_upload import write_item


def test_bbq_write_mc_basic() -> None:
	item = item_types.MC("Q1?", ["A", "B"], "B")
	text = write_item.MC(item)
	assert text.startswith("MC\t")
	assert item.item_crc16 in text
	assert text.count("Correct") == 1
	assert text.count("Incorrect") == 1
	assert text.count("\n") <= 1
	assert text.rstrip("\n").count("\n") == 0


def test_bbq_write_ma_basic() -> None:
	item = item_types.MA("Q2?", ["A", "B", "C"], ["A", "C"])
	text = write_item.MA(item)
	assert text.startswith("MA\t")
	assert item.item_crc16 in text
	assert text.count("Correct") == 2
	assert text.count("Incorrect") == 1


def test_bbq_write_num_includes_tolerance_note() -> None:
	item = item_types.NUM("Q3?", 10.0, 1.0, True)
	text = write_item.NUM(item)
	assert text.startswith("NUM\t")
	assert "Note: answers need to be within" in text


def test_bbq_write_num_zero_answer_does_not_raise() -> None:
	item = item_types.NUM("Q4?", 0.0, 1.0, True)
	text = write_item.NUM(item)
	assert text.startswith("NUM\t")
	assert "Note: answers need to be within" in text


def test_bbq_write_multi_fib_basic() -> None:
	item = item_types.MULTI_FIB("Q4 [x] [y]?", {"x": ["one"], "y": ["two"]})
	text = write_item.MULTI_FIB(item)
	assert text.startswith("FIB_PLUS\t")
	assert "x" in text
	assert "one" in text
	assert "y" in text
	assert "two" in text
