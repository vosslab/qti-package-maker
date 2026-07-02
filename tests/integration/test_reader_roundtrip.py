# Standard Library
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker import package_interface
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.bbq_text_upload import read_package as bbq_read_package
from qti_package_maker.engines.okla_chrst_bqgen import read_package as okla_read_package
from qti_package_maker.engines.text2qti import read_package as text2qti_read_package


def _items_by_type(bank: item_bank.ItemBank) -> dict:
	items = {}
	for item in bank.items_dict.values():
		items.setdefault(item.item_type, []).append(item)
	return items


def test_bbq_text_upload_roundtrip_all_types(tmp_cwd: pathlib.Path) -> None:
	qti_packer = package_interface.QTIPackageInterface("bbq-roundtrip", verbose=False, allow_mixed=True)
	qti_packer.add_item("MC", ("Pick a color.", ["red", "blue", "green"], "blue"))
	qti_packer.add_item("MA", ("Select fruits.", ["apple", "carrot", "banana"], ["apple", "banana"]))
	qti_packer.add_item("MATCH", ("Match sounds.", ["cat", "dog"], ["meow", "bark"]))
	qti_packer.add_item("NUM", ("Approx pi.", 3.14, 0.01, True))
	qti_packer.add_item("FIB", ("Capital of France?", ["Paris", "PARIS"]))
	qti_packer.add_item(
		"MULTI_FIB",
		("A [animal] says [sound].", {"animal": ["cat"], "sound": ["meow"]}),
	)
	qti_packer.add_item("ORDER", ("Order numbers.", ["one", "two", "three"]))

	outfile = qti_packer.save_package("bbq_text_upload")
	bank = bbq_read_package.read_items_from_file(outfile, allow_mixed=True)
	assert len(bank) == 7

	items = _items_by_type(bank)
	assert set(items.keys()) == {"MC", "MA", "MATCH", "NUM", "FIB", "MULTI_FIB", "ORDER"}

	mc_item = items["MC"][0]
	assert mc_item.question_text == "Pick a color."
	assert mc_item.choices_list == ["red", "blue", "green"]
	assert mc_item.answer_text == "blue"

	ma_item = items["MA"][0]
	assert ma_item.answers_list == ["apple", "banana"]

	num_item = items["NUM"][0]
	assert num_item.answer_float == pytest.approx(3.14)
	assert num_item.tolerance_float == pytest.approx(0.01)

	fib_item = items["FIB"][0]
	assert set(fib_item.answers_list) == {"Paris", "PARIS"}

	multi_item = items["MULTI_FIB"][0]
	assert multi_item.answer_map == {"animal": ["cat"], "sound": ["meow"]}

	order_item = items["ORDER"][0]
	assert order_item.ordered_answers_list == ["one", "two", "three"]


@pytest.mark.parametrize(
	"item_type,item_tuple,expected",
	[
		("MC", ("What is 2+2?", ["3", "4"], "4"), (["3", "4"], "4")),
		(
			"MA",
			("Pick primes.", ["2", "3", "4"], ["2", "3"]),
			(["2", "3", "4"], ["2", "3"], 1, True),
		),
		("NUM", ("Approx pi.", 3.14, 0.01, True), (3.14, 0.01, True)),
		("FIB", ("Capital of France?", ["Paris"]), (["Paris"],)),
	],
)
def test_text2qti_roundtrip_single_item(
		tmp_cwd: pathlib.Path, item_type: str, item_tuple: tuple, expected: tuple
		) -> None:
	qti_packer = package_interface.QTIPackageInterface("text2qti-rt", verbose=False)
	qti_packer.add_item(item_type, item_tuple)
	outfile = qti_packer.save_package("text2qti")
	bank = text2qti_read_package.read_items_from_file(outfile, allow_mixed=True)
	assert len(bank) == 1
	item = next(iter(bank.items_dict.values()))
	assert item.item_type == item_type
	if item_type == "NUM":
		assert item.answer_float == pytest.approx(expected[0])
		assert item.tolerance_float == pytest.approx(expected[1])
		assert item.tolerance_message == expected[2]
	else:
		assert item.get_tuple() == expected


def test_okla_chrst_bqgen_roundtrip(tmp_cwd: pathlib.Path) -> None:
	qti_packer = package_interface.QTIPackageInterface("okla-rt", verbose=False, allow_mixed=True)
	qti_packer.add_item("MC", ("What is 2+2?", ["3", "4"], "4"))
	qti_packer.add_item("MA", ("Pick primes.", ["2", "3", "4"], ["2", "3"]))
	qti_packer.add_item("FIB", ("Sky color?", ["blue", "azure"]))
	qti_packer.add_item("MATCH", ("Match capitals.", ["France", "USA"], ["Paris", "Washington"]))

	outfile = qti_packer.save_package("okla_chrst_bqgen")
	bank = okla_read_package.read_items_from_file(outfile, allow_mixed=True)
	assert len(bank) == 4

	items = _items_by_type(bank)
	assert set(items.keys()) == {"MC", "MA", "FIB", "MATCH"}
	match_item = items["MATCH"][0]
	assert match_item.prompts_list == ["France", "USA"]
	assert match_item.choices_list == ["Paris", "Washington"]
