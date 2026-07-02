# Standard Library
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.engines.bbq_text_upload import read_package as bbq_reader
from qti_package_maker.engines.text2qti import read_package as text2qti_reader
from qti_package_maker.engines.okla_chrst_bqgen import read_package as okla_reader


def test_bbq_reader_rejects_unknown_type() -> None:
	with pytest.raises(ValueError):
		bbq_reader.make_item_cls_from_line("NOPE\tQuestion\tA")


def test_bbq_reader_skips_empty_line() -> None:
	assert bbq_reader.make_item_cls_from_line("") is None


def test_bbq_reader_rejects_bad_num_format() -> None:
	with pytest.raises(ValueError):
		bbq_reader.make_item_cls_from_line("NUM\tQ?\tnope\t0.1")


def test_bbq_reader_rejects_missing_correct_flag() -> None:
	with pytest.raises(ValueError):
		bbq_reader.make_item_cls_from_line("MC\tQ?\tA\tincorrect\tB\tincorrect")


def test_text2qti_reader_rejects_missing_num_answer() -> None:
	block = "1. Numeric question\n... feedback"
	with pytest.raises(ValueError):
		text2qti_reader.read_NUM(block, 1)


def test_text2qti_reader_rejects_unknown_block() -> None:
	assert text2qti_reader.make_item_cls_from_block("No number header") is None


def test_okla_reader_ignores_empty_blocks(tmp_path: pathlib.Path) -> None:
	content = " \n\n1. Q1?\n*a) A\nb) B\n"
	infile = tmp_path / "okla.txt"
	infile.write_text(content, encoding="utf-8")
	bank = okla_reader.read_items_from_file(str(infile), allow_mixed=True)
	assert len(bank) == 1
