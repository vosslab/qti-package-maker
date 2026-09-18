# Standard Library
import os
import types
import pathlib
import importlib.util

# Pip3 Library
import pytest

# local repo modules
import file_utils


def _load_bbq_converter() -> types.ModuleType:
	path = os.path.join(file_utils.get_repo_root(), "tools", "bbq_converter.py")
	spec = importlib.util.spec_from_file_location("bbq_converter_script", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


bbq_converter = _load_bbq_converter()


def test_extract_core_name_success(tmp_path: pathlib.Path) -> None:
	assert bbq_converter.extract_core_name("bbq-biology-questions.txt") == "biology"
	bbq_path = tmp_path / "bbq-chem-questions.txt"
	assert bbq_converter.extract_core_name(str(bbq_path)) == "chem"


def test_extract_core_name_rejects_bad_names() -> None:
	with pytest.raises(ValueError):
		bbq_converter.extract_core_name("biology-questions.txt")
