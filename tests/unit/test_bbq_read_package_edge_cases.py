# Standard Library
import pathlib

# QTI Package Maker
from qti_package_maker.engines.bbq_text_upload import read_package


def test_multi_fib_multiple_groups() -> None:
	line = "FIB_PLUS\tFill in: [animal] and [sound].\tanimal\tcat\t\tsound\tmeow\tchatter"
	item = read_package.make_item_cls_from_line(line)
	assert item.answer_map == {"animal": ["cat"], "sound": ["meow", "chatter"]}


def test_num_missing_tolerance_defaults() -> None:
	line = "NUM\tApprox pi?\t3.14"
	item = read_package.make_item_cls_from_line(line)
	assert item.answer_float == 3.14
	assert item.tolerance_float == 0.0


def test_read_items_defaults_num_missing_tolerance(tmp_path: pathlib.Path) -> None:
	bbq_file = tmp_path / "bbq-missing-tolerance.txt"
	bbq_file.write_text(
		"NUM\tApprox pi?\t3.14\nMC\t2+2?\t3\tincorrect\t4\tcorrect\n",
		encoding="utf-8",
	)
	bank = read_package.read_items_from_file(str(bbq_file), allow_mixed=True)
	assert len(bank) == 2
	num_item = next(item for item in bank if item.item_type == "NUM")
	assert num_item.tolerance_float == 0.0
