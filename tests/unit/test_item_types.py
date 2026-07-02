# Standard Library
import re

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items import item_types


CRC16_PATTERN = re.compile(r"\b([0-9a-f]{4})(?:_[0-9a-f]{4})*\b")


@pytest.mark.parametrize(
	"item_cls",
	[
		item_types.MC("Q1?", ["A", "B", "C"], "A"),
		item_types.MA("Q2?", ["A", "B", "C"], ["A", "B"]),
		item_types.MATCH("Q3?", ["A", "B"], ["1", "2"]),
		item_types.NUM("Q4?", 3.14, 0.01, True),
		item_types.FIB("Q5?", ["answer"]),
		item_types.MULTI_FIB("Q6 [a] [b]?", {"a": ["x"], "b": ["y"]}),
		item_types.ORDER("Q7?", ["one", "two", "three"]),
	],
)
def test_item_crc_and_type(item_cls: item_types.BaseItem) -> None:
	assert CRC16_PATTERN.fullmatch(item_cls.item_crc16)
	assert item_cls.item_type == item_cls.__class__.__name__


def test_mc_answer_index() -> None:
	item = item_types.MC("Q1?", ["A", "B", "C"], "B")
	assert item.answer_index == 1


def test_ma_answer_index_list() -> None:
	item = item_types.MA("Q2?", ["A", "B", "C"], ["A", "C"])
	assert item.answer_index_list == [0, 2]


def test_copy_is_deep() -> None:
	item = item_types.MC("Q3?", ["A", "B"], "A")
	item_copy = item.copy()
	item_copy.question_text = "Changed"
	assert item.question_text != item_copy.question_text


def test_get_tuple_rejects_empty_supporting_field() -> None:
	item = item_types.MC("Q4?", ["A", "B"], "A")
	item.answer_text = ""
	with pytest.raises(ValueError):
		item.get_tuple()
