# Standard Library
import re
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
import qti_package_maker.assessment_items.item_bank
import qti_package_maker.assessment_items.item_types
import qti_package_maker.engines.bbq_text_upload.engine_class
import qti_package_maker.engines.bbq_text_upload.read_package
import qti_package_maker.engines.text2qti.engine_class
import qti_package_maker.engines.text2qti.read_package
import qti_package_maker.engines.okla_chrst_bqgen.engine_class
import qti_package_maker.engines.okla_chrst_bqgen.read_package


def _build_bank(
	items: list,
) -> qti_package_maker.assessment_items.item_bank.ItemBank:
	bank = qti_package_maker.assessment_items.item_bank.ItemBank(allow_mixed=True)
	for item in items:
		bank.add_item_cls(item)
	return bank


def _norm_float(value: float) -> float:
	return round(float(value), 6)


def _strip_bbq_num_note(text: str) -> str:
	pattern = (
		r"<p><i>Note: answers need to be within .*? "
		r"of the correct number to be correct\.</i></p>"
	)
	cleaned = re.sub(pattern, "", text)
	return cleaned.strip()


def _normalize_item(item: qti_package_maker.assessment_items.item_types.BaseItem) -> tuple:
	item_type = item.item_type
	if item_type == "MC":
		return (item_type, item.question_text, tuple(item.choices_list), item.answer_text)
	if item_type == "MA":
		return (item_type, item.question_text, tuple(item.choices_list), tuple(item.answers_list))
	if item_type == "MATCH":
		return (item_type, item.question_text, tuple(item.prompts_list), tuple(item.choices_list))
	if item_type == "NUM":
		return (
			item_type,
			_strip_bbq_num_note(item.question_text),
			_norm_float(item.answer_float),
			_norm_float(item.tolerance_float),
		)
	if item_type == "FIB":
		return (item_type, item.question_text, tuple(item.answers_list))
	if item_type == "MULTI_FIB":
		answer_map = tuple((key, tuple(values)) for key, values in sorted(item.answer_map.items()))
		return (item_type, item.question_text, answer_map)
	if item_type == "ORDER":
		return (item_type, item.question_text, tuple(item.ordered_answers_list))
	raise ValueError(f"Unsupported item type for normalization: {item_type}")


def _normalize_bank(bank: qti_package_maker.assessment_items.item_bank.ItemBank) -> list:
	normalized = [_normalize_item(item) for item in bank.items_dict.values()]
	return sorted(normalized)


def _write_bbq(
	bank: qti_package_maker.assessment_items.item_bank.ItemBank,
	tmp_path: pathlib.Path,
	filename: str,
) -> str:
	engine = qti_package_maker.engines.bbq_text_upload.engine_class.EngineClass("pkg", verbose=False)
	outfile = tmp_path / filename
	return engine.save_package(bank, outfile=str(outfile))


def _read_bbq(path: str) -> qti_package_maker.assessment_items.item_bank.ItemBank:
	return qti_package_maker.engines.bbq_text_upload.read_package.read_items_from_file(str(path), allow_mixed=True)


def _write_text2qti(
	bank: qti_package_maker.assessment_items.item_bank.ItemBank,
	tmp_path: pathlib.Path,
	filename: str,
) -> str:
	engine = qti_package_maker.engines.text2qti.engine_class.EngineClass("pkg", verbose=False)
	outfile = tmp_path / filename
	return engine.save_package(bank, outfile=str(outfile))


def _read_text2qti(path: str) -> qti_package_maker.assessment_items.item_bank.ItemBank:
	return qti_package_maker.engines.text2qti.read_package.read_items_from_file(str(path), allow_mixed=True)


def _write_okla(
	bank: qti_package_maker.assessment_items.item_bank.ItemBank,
	tmp_path: pathlib.Path,
	filename: str,
) -> str:
	engine = qti_package_maker.engines.okla_chrst_bqgen.engine_class.EngineClass("pkg", verbose=False)
	outfile = tmp_path / filename
	return engine.save_package(bank, outfile=str(outfile))


def _read_okla(path: str) -> qti_package_maker.assessment_items.item_bank.ItemBank:
	return qti_package_maker.engines.okla_chrst_bqgen.read_package.read_items_from_file(str(path), allow_mixed=True)


def _make_item(item_type: str) -> qti_package_maker.assessment_items.item_types.BaseItem:
	if item_type == "MC":
		return qti_package_maker.assessment_items.item_types.MC("MC question?", ["A", "B", "C"], "B")
	if item_type == "MA":
		return qti_package_maker.assessment_items.item_types.MA("MA question?", ["A", "B", "C", "D"], ["A", "D"])
	if item_type == "MATCH":
		return qti_package_maker.assessment_items.item_types.MATCH("MATCH question?", ["P1", "P2"], ["C1", "C2"])
	if item_type == "NUM":
		return qti_package_maker.assessment_items.item_types.NUM("NUM question?", 3.14, 0.01, False)
	if item_type == "FIB":
		return qti_package_maker.assessment_items.item_types.FIB("FIB question?", ["alpha", "beta"])
	if item_type == "MULTI_FIB":
		return qti_package_maker.assessment_items.item_types.MULTI_FIB("MULTI_FIB [x] [y]?", {"x": ["one"], "y": ["two"]})
	if item_type == "ORDER":
		return qti_package_maker.assessment_items.item_types.ORDER("ORDER question?", ["first", "second", "third"])
	raise ValueError(f"Unsupported item type: {item_type}")


def test_roundtrip_okla_bbq_okla_multi_item(tmp_path: pathlib.Path) -> None:
	items = [
		_make_item("MC"),
		_make_item("MA"),
		_make_item("FIB"),
		_make_item("MATCH"),
	]
	bank = _build_bank(items)
	okla_path = _write_okla(bank, tmp_path, "okla.txt")
	okla_bank = _read_okla(okla_path)

	bbq_path = _write_bbq(okla_bank, tmp_path, "bbq.txt")
	bbq_bank = _read_bbq(bbq_path)

	okla_path_2 = _write_okla(bbq_bank, tmp_path, "okla-2.txt")
	okla_bank_2 = _read_okla(okla_path_2)
	assert _normalize_bank(okla_bank_2) == _normalize_bank(okla_bank)


@pytest.mark.parametrize("item_type", ["MC", "MA", "NUM", "FIB"])
def test_roundtrip_text2qti_bbq_text2qti_single_item(tmp_path: pathlib.Path, item_type: str) -> None:
	item = _make_item(item_type)
	bank = _build_bank([item])
	text_path = _write_text2qti(bank, tmp_path, "text2qti.txt")
	text_bank = _read_text2qti(text_path)

	bbq_path = _write_bbq(text_bank, tmp_path, "bbq.txt")
	bbq_bank = _read_bbq(bbq_path)

	text_path_2 = _write_text2qti(bbq_bank, tmp_path, "text2qti-2.txt")
	text_bank_2 = _read_text2qti(text_path_2)

	assert _normalize_bank(text_bank_2) == _normalize_bank(text_bank)


@pytest.mark.parametrize("item_type", ["MC", "MA", "FIB"])
def test_roundtrip_okla_text2qti_okla_single_item(tmp_path: pathlib.Path, item_type: str) -> None:
	item = _make_item(item_type)
	bank = _build_bank([item])
	okla_path = _write_okla(bank, tmp_path, "okla.txt")
	okla_bank = _read_okla(okla_path)

	text_path = _write_text2qti(okla_bank, tmp_path, "text2qti.txt")
	text_bank = _read_text2qti(text_path)

	okla_path_2 = _write_okla(text_bank, tmp_path, "okla-2.txt")
	okla_bank_2 = _read_okla(okla_path_2)

	assert _normalize_bank(okla_bank_2) == _normalize_bank(okla_bank)


@pytest.mark.parametrize("item_type", ["MC", "MA", "FIB"])
def test_roundtrip_all_three_engines_chain_single_item(tmp_path: pathlib.Path, item_type: str) -> None:
	item = _make_item(item_type)
	bank = _build_bank([item])
	okla_path = _write_okla(bank, tmp_path, "okla.txt")
	okla_bank = _read_okla(okla_path)

	bbq_path = _write_bbq(okla_bank, tmp_path, "bbq.txt")
	bbq_bank = _read_bbq(bbq_path)

	text_path = _write_text2qti(bbq_bank, tmp_path, "text2qti.txt")
	text_bank = _read_text2qti(text_path)

	bbq_path_2 = _write_bbq(text_bank, tmp_path, "bbq-2.txt")
	bbq_bank_2 = _read_bbq(bbq_path_2)

	okla_path_2 = _write_okla(bbq_bank_2, tmp_path, "okla-2.txt")
	okla_bank_2 = _read_okla(okla_path_2)

	assert _normalize_bank(okla_bank_2) == _normalize_bank(okla_bank)
