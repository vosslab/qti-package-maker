# Standard Library
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.engines.okla_chrst_bqgen import read_package


def test_okla_read_items_from_file(tmp_path: pathlib.Path) -> None:
	content = """1. What is 2+2?
*a) 4
b) 3

2. Select primes.
*a) 2
*b) 3
c) 4

blank 3. The sky is __
*a. blue
b. azure

match 4. Match capitals
*a) France/Paris
b) USA/Washington
"""
	infile = tmp_path / "okla-sample.txt"
	infile.write_text(content, encoding="utf-8")
	bank = read_package.read_items_from_file(str(infile), allow_mixed=True)
	assert len(bank) == 4
	item_types = {item.item_type for item in bank.items_dict.values()}
	assert item_types == {"MC", "MA", "FIB", "MATCH"}

	match_item = next(item for item in bank.items_dict.values() if item.item_type == "MATCH")
	assert match_item.prompts_list == ["France", "USA"]
	assert match_item.choices_list == ["Paris", "Washington"]

	fib_item = next(item for item in bank.items_dict.values() if item.item_type == "FIB")
	assert fib_item.answers_list == ["blue", "azure"]
