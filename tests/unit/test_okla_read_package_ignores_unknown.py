# Standard Library
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.engines.okla_chrst_bqgen import read_package


def test_okla_ignores_unknown_blocks(tmp_path: pathlib.Path) -> None:
	content = """essay 1. Write about space.
This is not supported.

1. What is 2+2?
*a) 4
b) 3
"""
	infile = tmp_path / "okla-unknown.txt"
	infile.write_text(content, encoding="utf-8")
	bank = read_package.read_items_from_file(str(infile))
	assert len(bank) == 1
	item = next(iter(bank.items_dict.values()))
	assert item.item_type == "MC"
