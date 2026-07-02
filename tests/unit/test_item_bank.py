# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items.item_bank import ItemBank


def test_item_bank_rejects_mixed_types_by_default() -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	with pytest.raises(ValueError):
		bank.add_item("MA", ("Q2?", ["A", "B", "C"], ["A", "B"]))


def test_item_bank_allows_mixed_types() -> None:
	bank = ItemBank(allow_mixed=True)
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MA", ("Q2?", ["A", "B", "C"], ["A", "B"]))
	assert len(bank) == 2


def test_item_bank_skips_duplicate_crc(capsys: pytest.CaptureFixture) -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	out = capsys.readouterr().out
	assert "Duplicate item" in out
	assert len(bank) == 1


def test_item_bank_merge_and_operators() -> None:
	bank1 = ItemBank()
	bank1.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank2 = ItemBank()
	bank2.add_item("MC", ("Q2?", ["A", "B"], "B"))

	merged = bank1.merge(bank2)
	assert len(merged) == 2
	assert merged == bank1 + bank2
	assert merged == bank1 | bank2
	assert bank2.merge(bank1) == merged


def test_item_bank_merge_preserves_first_item_type() -> None:
	bank1 = ItemBank()
	bank1.add_item("MC", ("Q1?", ["A", "B"], "A"))
	empty = ItemBank()
	merged = bank1.merge(empty)
	assert merged.first_item_type == "MC"
	with pytest.raises(ValueError):
		merged.add_item("MA", ("Q2?", ["A", "B", "C"], ["A"]))


def test_item_bank_merge_same_type_sets_first_item_type() -> None:
	bank1 = ItemBank()
	bank1.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank2 = ItemBank()
	bank2.add_item("MC", ("Q2?", ["A", "B"], "B"))
	merged = bank1.merge(bank2)
	assert merged.first_item_type == "MC"


def test_item_bank_getitem_slice_and_index() -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q2?", ["A", "B"], "B"))
	bank.add_item("MC", ("Q3?", ["A", "B"], "A"))

	sub_bank = bank[:2]
	assert isinstance(sub_bank, ItemBank)
	assert len(sub_bank) == 2
	assert bank[0].question_text == "Q1?"


def test_item_bank_setitem_reorders() -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q2?", ["A", "B"], "B"))
	bank.add_item("MC", ("Q3?", ["A", "B"], "A"))

	first_item = bank[0]
	last_item = bank[2]
	bank[0] = last_item
	bank[2] = first_item
	assert bank[0] == last_item


def test_item_bank_histogram_empty(capsys: pytest.CaptureFixture) -> None:
	bank = ItemBank()
	bank.print_histogram()
	out = capsys.readouterr().out
	assert out == ""


def test_item_bank_histogram_mc_output(capsys: pytest.CaptureFixture) -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q2?", ["A", "B"], "B"))
	bank.print_histogram()
	out = capsys.readouterr().out
	assert "Histogram" in out


def test_item_bank_renumber_items() -> None:
	bank = ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q2?", ["A", "B"], "B"))
	for idx, item in enumerate(bank, start=1):
		assert item.item_number == idx
	bank.items_dict_key_list = list(reversed(bank.items_dict_key_list))
	bank.renumber_items()
	item_numbers = [item.item_number for item in bank]
	assert sorted(item_numbers) == [1, 2]
