# Standard Library
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.okla_chrst_bqgen import write_item
from qti_package_maker.engines.okla_chrst_bqgen import read_package


def test_okla_roundtrip_supported_types(tmp_path: pathlib.Path) -> None:
	items = [
		item_types.MC("MC question?", ["A", "B", "C"], "B"),
		item_types.MA("MA question?", ["A", "B", "C"], ["A", "C"]),
		item_types.FIB("FIB question?", ["alpha", "beta"]),
		item_types.MATCH("MATCH question?", ["P1", "P2"], ["C1", "C2"]),
	]
	for idx, item in enumerate(items, start=1):
		item.item_number = idx

	content = ""
	content += write_item.MC(items[0])
	content += write_item.MA(items[1])
	content += write_item.FIB(items[2])
	content += write_item.MATCH(items[3])

	infile = tmp_path / "okla-roundtrip.txt"
	infile.write_text(content, encoding="utf-8")
	bank = read_package.read_items_from_file(str(infile), allow_mixed=True)
	assert len(bank) == 4

	by_type = {item.item_type: item for item in bank.items_dict.values()}
	assert by_type["MC"].answer_text == "B"
	assert set(by_type["MA"].answers_list) == {"A", "C"}
	assert by_type["FIB"].answers_list == ["alpha", "beta"]
	assert by_type["MATCH"].prompts_list == ["P1", "P2"]
	assert by_type["MATCH"].choices_list == ["C1", "C2"]
