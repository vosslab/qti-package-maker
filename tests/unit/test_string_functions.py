# Standard Library

# Pip3 Library
import pytest
import re

# QTI Package Maker
from qti_package_maker.common import string_functions


def test_strip_crc_prefix():
	assert string_functions.strip_crc_prefix("34. b5b6 banana") == "banana"
	assert string_functions.strip_crc_prefix("11. <p>b5b6</p> banana") == "banana"
	assert string_functions.strip_crc_prefix("<p>b5b6</p> banana") == "banana"
	assert string_functions.strip_crc_prefix("<p>6902_b5b6</p> <p><strong>banana</strong></p>") == "<p><strong>banana</strong></p>"
	assert string_functions.strip_crc_prefix("b5b6 banana") == "banana"
	assert string_functions.strip_crc_prefix("b5b6_6902 banana") == "banana"


def test_strip_prefix_from_string():
	assert string_functions.strip_prefix_from_string("A. Glucose") == "Glucose"
	assert string_functions.strip_prefix_from_string("B. Fructose") == "Fructose"
	assert string_functions.strip_prefix_from_string("2) Fructose") == "Fructose"
	assert string_functions.strip_prefix_from_string("b: Option B") == "Option B"
	assert string_functions.strip_prefix_from_string("1. Option 1") == "Option 1"
	assert string_functions.strip_prefix_from_string("7.5 mL stock solution") == "7.5 mL stock solution"
	assert string_functions.strip_prefix_from_string("3.14") == "3.14"
	assert string_functions.strip_prefix_from_string("1.2 mM glucose") == "1.2 mM glucose"
	assert string_functions.strip_prefix_from_string("<p>A. Glucose</p>") == "<p>Glucose</p>"
	assert string_functions.strip_prefix_from_string("<span style=\"color:red\">A. Glucose</span>") == "<span style=\"color:red\">Glucose</span>"
	assert string_functions.strip_prefix_from_string("Glucose") == "Glucose"
	assert string_functions.strip_prefix_from_string("<span>Glucose</span>") == "<span>Glucose</span>"


def test_remove_prefix_from_list():
	choices = ["A. One", "B. Two", "C. Three"]
	assert string_functions.remove_prefix_from_list(choices) == ["One", "Two", "Three"]


def test_number_helpers_basic():
	assert string_functions.number_to_letter(3) == "C"
	assert string_functions.number_to_lowercase(3) == "c"
	assert string_functions.number_to_ordinal(3) == "third"
	assert string_functions.number_to_cardinal(3) == "three"
	assert string_functions.number_to_roman(3) == "III"
	assert string_functions.number_to_roman(9) == "IX"
	assert string_functions.number_to_roman(44) == "XLIV"
	assert string_functions.number_to_roman(1999) == "MCMXCIX"


def test_number_helpers_bounds():
	with pytest.raises(ValueError):
		string_functions.number_to_letter(0)
	with pytest.raises(ValueError):
		string_functions.number_to_lowercase(0)


def test_generate_gene_letters():
	assert string_functions.generate_gene_letters(5, 3) == "defgh"
	assert string_functions.generate_gene_letters(5, 3, clear=True) == "defhj"
	random_letters = string_functions.generate_gene_letters(5)
	assert len(random_letters) == 5
	assert len(set(random_letters)) == 5


def test_crc16_helpers():
	code = string_functions.get_crc16_from_string("hello")
	assert re.fullmatch(r"[0-9a-f]{4}", code)
	rand_code = string_functions.get_random_crc16()
	assert re.fullmatch(r"[0-9a-f]{4}", rand_code)


def test_check_ascii_accepts_ascii():
	assert string_functions.check_ascii("abc 123") is True


def test_check_ascii_rejects_unicode():
	with pytest.raises(ValueError):
		string_functions.check_ascii("caf\u00e9")


def test_make_question_pretty_strips_html():
	assert string_functions.make_question_pretty("<p>Test</p>") == "Test"


def test_html_helpers():
	assert "monospace" in string_functions.html_monospace("A B", use_nbsp=False)
	assert "color" in string_functions.html_color_text("Hi", "ff0000")


def test_html_table_to_text():
	html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
	table_text = string_functions._html_table_to_text(html)
	assert "[TABLE]" not in table_text
	assert "A" in table_text
	assert "B" in table_text
	assert "1" in table_text
	assert "2" in table_text


def test_format_html_lxml_basic():
	raw_html = "<div><p>Text</p><ul><li>A</li><li>B</li></ul></div>"
	formatted = string_functions.format_html_lxml(raw_html)
	assert "<div" in formatted
	assert "<li" in formatted


def test_format_html_lxml_skips_script(capsys):
	raw_html = "<script>var x = 1;</script><div>ok</div>"
	formatted = string_functions.format_html_lxml(raw_html)
	out = capsys.readouterr().out
	assert "skipping" in out
	assert formatted == raw_html


def test_html_table_to_text_cell_borders():
	# Cell-level visible borders should produce fancy_grid (box-drawing grid lines)
	html = (
		'<table>'
		'<tr><td style="border: 1px solid black">A</td>'
		'<td style="border: 1px solid black">B</td></tr>'
		'<tr><td style="border: 1px solid black">1</td>'
		'<td style="border: 1px solid black">2</td></tr>'
		'</table>'
	)
	result = string_functions._html_table_to_text(html)
	assert "[TABLE]" not in result
	assert "A" in result
	# fancy_grid uses double-line top border character
	assert "\u2554" in result or "\u2555" in result or "\u2550" in result


def test_html_table_to_text_cell_border_zero():
	# Cell-level border: 0 should NOT trigger fancy_grid
	# This is the metabolic pathway table pattern
	html = (
		"<table border='0' style='border-collapse: collapse; border: 0;'>"
		"<tr><td style='border: 0; text-align: center;'>A</td>"
		"<td style='border: 0; text-align: center;'>B</td></tr>"
		"<tr><td style='border: 0; text-align: center;'>1</td>"
		"<td style='border: 0; text-align: center;'>2</td></tr>"
		"</table>"
	)
	result = string_functions._html_table_to_text(html)
	assert "[TABLE]" not in result
	assert "A" in result
	# Should be plain format - no box-drawing characters
	for ch in ("\u2550", "\u2554", "\u2502", "\u2551", "\u256a"):
		assert ch not in result


def test_html_table_to_text_border_zero():
	# border="0" should produce plain format (no box-drawing characters)
	html = (
		'<table border="0">'
		'<tr><th>X</th><th>Y</th></tr>'
		'<tr><td>3</td><td>4</td></tr>'
		'</table>'
	)
	result = string_functions._html_table_to_text(html)
	assert "[TABLE]" not in result
	assert "X" in result
	assert "3" in result
	# plain format should not have box-drawing characters
	for ch in ("\u2550", "\u2554", "\u2502", "\u2551", "\u256a"):
		assert ch not in result


def test_html_table_to_text_border_collapse():
	# Table-level border + collapse should produce fancy_outline
	html = (
		'<table style="border: 1px solid black; border-collapse: collapse;">'
		'<tr><th>H1</th><th>H2</th></tr>'
		'<tr><td>a</td><td>b</td></tr>'
		'<tr><td>c</td><td>d</td></tr>'
		'</table>'
	)
	result = string_functions._html_table_to_text(html)
	assert "[TABLE]" not in result
	assert "H1" in result
	assert "a" in result
	# fancy_outline has outer border and a header separator, but no inter-row lines
	assert "\u2550" in result  # double line present in outline border
	# fancy_outline only has 1 separator (header/body), not between data rows
	# fancy_grid would have separators between every row
	lines_with_separator = [l for l in result.split("\n") if "\u256a" in l]
	assert len(lines_with_separator) <= 1  # at most header separator
