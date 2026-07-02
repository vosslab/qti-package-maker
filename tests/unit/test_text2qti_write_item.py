# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.text2qti import write_item


def test_text2qti_mc_output() -> None:
	item = item_types.MC("Q1?", ["A", "B"], "B")
	item.item_number = 1
	output = write_item.MC(item)
	assert output.startswith("1. Q1?")
	assert "A) A" in output
	assert "*B) B" in output


def test_text2qti_ma_output() -> None:
	item = item_types.MA("Q2?", ["A", "B", "C"], ["A", "C"])
	item.item_number = 2
	output = write_item.MA(item)
	assert output.startswith("2. Q2?")
	assert "[*] A" in output
	assert "[ ] B" in output
	assert "[*] C" in output


def test_text2qti_num_output() -> None:
	item = item_types.NUM("Q3?", 3.14, 0.01)
	item.item_number = 3
	output = write_item.NUM(item)
	assert output.startswith("3. Q3?")
	assert "= 3.14 +- 0.01" in output


def test_text2qti_fib_output() -> None:
	item = item_types.FIB("Q4?", ["A", "B"])
	item.item_number = 4
	output = write_item.FIB(item)
	assert output.startswith("4. Q4?")
	assert "* A" in output
	assert "* B" in output
