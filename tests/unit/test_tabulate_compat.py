# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import tabulate_compat


def test_plain_tabulate_basic() -> None:
	rows = [[1, "A"], [2, "B"]]
	headers = ["num", "letter"]
	text = tabulate_compat._plain_tabulate(rows, headers=headers)
	assert "num" in text
	assert "letter" in text
	assert "1" in text
	assert "A" in text
	assert "2" in text
	assert "B" in text


def test_plain_tabulate_empty() -> None:
	assert tabulate_compat._plain_tabulate([], headers=()) == ""
