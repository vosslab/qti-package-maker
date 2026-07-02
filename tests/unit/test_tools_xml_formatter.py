# Standard Library
import types
import importlib.util
from pathlib import Path

# Pip3 Library


def _load_module() -> types.ModuleType:
	path = Path(__file__).resolve().parents[2] / "tools" / "xml_formatter.py"
	spec = importlib.util.spec_from_file_location("xml_formatter", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_format_xml_with_lxml(tmp_path: Path) -> None:
	mod = _load_module()
	xml_path = tmp_path / "input.xml"
	xml_path.write_text("<root><child>value</child></root>", encoding="utf-8")
	formatted = mod.format_xml_with_lxml(str(xml_path))
	assert formatted.startswith("<?xml")
	assert "<root>" in formatted
	assert "\n" in formatted


def test_save_formatted_xml(tmp_path: Path) -> None:
	mod = _load_module()
	output_path = tmp_path / "output.xml"
	mod.save_formatted_xml("<root/>", str(output_path))
	assert output_path.exists()
	assert output_path.read_text(encoding="utf-8") == "<root/>"
