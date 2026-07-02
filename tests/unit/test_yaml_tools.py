# Standard Library
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.common import yaml_tools


def test_unique_key_loader_rejects_duplicates(tmp_path: pathlib.Path) -> None:
	yaml_path = tmp_path / "dup.yaml"
	yaml_path.write_text("a: 1\na: 2\n", encoding="utf-8")
	with pytest.raises(AssertionError):
		yaml_tools.read_yaml_file(str(yaml_path), msg=False)


def test_apply_replacement_rules_to_text() -> None:
	text = " true false "
	out = yaml_tools.applyReplacementRulesToText(text)
	assert "<strong>" in out


def test_apply_replacement_rules_to_list() -> None:
	out_list = yaml_tools.applyReplacementRulesToList([" True ", " False "])
	assert all("<strong>" in item for item in out_list)


def test_append_clear_font_space_helpers() -> None:
	text = "Hello"
	assert "letter-spacing" in yaml_tools.append_clear_font_space_to_text(text)
	out_list = yaml_tools.append_clear_font_space_to_list(["A", "B"])
	assert len(out_list) == 2
	assert all("letter-spacing" in item for item in out_list)


def test_read_yaml_file_missing() -> None:
	with pytest.raises(FileNotFoundError):
		yaml_tools.read_yaml_file("nope.yaml", msg=False)


def test_apply_replacement_rules_to_text_type_error() -> None:
	with pytest.raises(TypeError):
		yaml_tools.applyReplacementRulesToText(123)
