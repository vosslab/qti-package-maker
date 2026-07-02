# Standard Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types


def test_base_item_repr_contains_type_and_crc() -> None:
	item = item_types.MC("Q1?", ["A", "B"], "A")
	text = repr(item)
	assert "MC" in text
	assert item.item_crc16 in text
