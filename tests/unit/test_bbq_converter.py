# Standard Library
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from tools import bbq_converter


def test_extract_core_name_success(tmp_path: pathlib.Path) -> None:
	assert bbq_converter.extract_core_name("bbq-biology-questions.txt") == "biology"
	bbq_path = tmp_path / "bbq-chem-questions.txt"
	assert bbq_converter.extract_core_name(str(bbq_path)) == "chem"


def test_extract_core_name_rejects_bad_names() -> None:
	with pytest.raises(ValueError):
		bbq_converter.extract_core_name("biology-questions.txt")
