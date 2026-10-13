# Standard Library

# Pip3 Library
import pytest
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import validator


def test_clean_html_for_xml_basic() -> None:
	assert validator.clean_html_for_xml("simple&copy;") == "simple"
	assert validator.clean_html_for_xml("&amp;&gt;&lt;") == ""
	assert validator.clean_html_for_xml("<script>let i=0;</script>") == "<script></script>"
	assert validator.clean_html_for_xml("<th colspan=2>Header</th>") == "<th colspan=\"2\">Header</th>"
	assert validator.clean_html_for_xml("<td rowspan=3>Data</td>") == "<td rowspan=\"3\">Data</td>"
	assert validator.clean_html_for_xml("<a href=\"https://x.com/page?q=123\">Link</a>") == "<a href=\"https://x.com/page\">Link</a>"
	assert validator.clean_html_for_xml("smiles=\"C[C@H](N)C(=O)O\"") == "smiles=\"\""


def test_is_valid_crc16_code_string() -> None:
	assert validator.is_valid_crc16_code_string("a1b2") is True
	assert validator.is_valid_crc16_code_string("a1b2_c3d4") is True
	assert validator.is_valid_crc16_code_string("zzzz") is False
	assert validator.is_valid_crc16_code_string("123") is False


def test_validate_html_accepts_clean_inputs() -> None:
	assert validator.validate_html("simple string") is True
	assert validator.validate_html("<p>simple html paragraph</p>") is True
	assert validator.validate_html("<p>&copy; simple html paragraph &amp; escaped characters</p>") is True


@pytest.mark.parametrize('style', [
	'color: ff0303', 'color: #gg0303', 'color: #12345',
	'color: rgb(banana)', 'color: hsl(banana)', 'color: notacolor',
	'font-size: 12potatoes', 'height: 25', 'padding: -2px',
	'text-align: sideways', 'vert-align: middle', 'spacing: 20px',
	'border: 1px solid rgb(banana)', 'background: ff0303',
	'color: ff0303; color: red', 'color: ff0303 !important; color: red',
	'color red', 'color: red; broken',
])
def test_inline_css_rejects_confirmed_errors(style: str) -> None:
	with pytest.raises(ValueError, match='inline CSS'):
		validator.validate_string_text(f'<span style="{style}">Text</span>', 'question_text')


@pytest.mark.parametrize('style', [
	'color: #abc', 'color: #abcd', 'color: #aAbBcC', 'color: #12345678',
	'color: rebeccapurple', 'color: rgb(255, 3, 3)', 'color: rgb(100% 0% 0% / .5)',
	'color: hsl(120deg 50% 50%)', 'color: oklch(50% .2 120)',
	'color: currentColor', 'color: CanvasText', 'color: transparent',
	'border: 1px solid #abcd', 'background: #12345678',
	'width: 50%; height: 0; margin-left: -2px; line-height: 1.5',
	'display: flex; text-align: start; font-weight: 450; width: 20cqw',
	'container-type: inline-size; aspect-ratio: 2 / 1',
	'color: var(--ink); --ink: #123; width: calc(100% - 2em)',
	'color: rgb(from red r g b); color: color-mix(in srgb, red, blue)',
	'future-property: future-value; color: future-color(1)',
	'color: red /* comment */ !important; COLOR: blue',
	'color: &#35;ff0303', 'accent-color: auto',
	'background: center / cover red; text-decoration: underline solid red',
	'font-style: oblique 20deg; display: inline flow-root',
	'color: color(--my-profile 0 0 0)',
])
def test_inline_css_preserves_valid_and_unclassified_content(style: str) -> None:
	html = f'<span style="{style}">Text</span>'
	assert validator.validate_html(html) is True


def test_inline_css_reports_answer_and_legacy_attribute_context() -> None:
	with pytest.raises(ValueError, match='text-shadow'):
		validator.validate_html('<span style="text-shadow: 1px 1px rgb(banana)">Text</span>')
	with pytest.raises(ValueError, match='choices_list.*span.*color.*ff0303'):
		validator.validate_MC('Choose one.', ['<span style="color: ff0303">Red</span>', 'Blue'], 'Blue')
	with pytest.raises(ValueError, match='td.*bgcolor.*4d4d4d'):
		validator.validate_html('<table><tr><td bgcolor="4d4d4d">Cell</td></tr></table>')
	assert validator.validate_html('<font color="#4d4d4d">Text</font>') is True
	with pytest.raises(ValueError, match='td.*color.*ff0303'):
		validator.validate_html('<tr><td style="color: ff0303">Cell</td></tr>')


def test_validate_string_text_accepts_valid() -> None:
	assert validator.validate_string_text("What is 2 + 2?", "question_text") is True
	assert validator.validate_string_text("2", "answer_text", 1) is True


def test_validate_string_text_rejects_empty() -> None:
	with pytest.raises(ValueError):
		validator.validate_string_text("", "question_text")


def test_validate_string_text_rejects_short() -> None:
	with pytest.raises(ValueError):
		validator.validate_string_text("ab", "question_text", min_length=3)


def test_validate_string_text_rejects_bad_html() -> None:
	with pytest.raises(lxml.etree.XMLSyntaxError):
		validator.validate_string_text("<p><b>", "question_text")


def test_validate_list_of_strings_accepts_valid() -> None:
	assert validator.validate_list_of_strings(["4", "3"], "choices_list") is True


def test_validate_list_of_strings_rejects_duplicates() -> None:
	with pytest.raises(ValueError):
		validator.validate_list_of_strings(["A", "A"], "choices_list")


def test_validate_mc_accepts_valid() -> None:
	assert validator.validate_MC("What is 2 + 2?", ["4", "3"], "4") is True


def test_validate_ma_accepts_valid() -> None:
	assert validator.validate_MA("Select all fruits", ["apple", "banana", "carrot"], ["apple", "banana"]) is True


def test_validate_fib_accepts_valid() -> None:
	assert validator.validate_FIB("What color are bananas at the store?", ["green", "yellow"]) is True


def test_validate_multi_fib_accepts_valid() -> None:
	answer_map = {"colors": ["red", "blue"], "cities": ["Chicago", "New York"]}
	assert validator.validate_MULTI_FIB("What [colors] is which [cities]?", answer_map) is True


def test_validate_multi_fib_requires_placeholders() -> None:
	with pytest.raises(ValueError):
		validator.validate_MULTI_FIB("Fill in [animal].", {"color": ["red"]})


def test_validate_num_accepts_valid() -> None:
	assert validator.validate_NUM("What year was this written?", 2025, 0.5) is True


def test_validate_num_rejects_negative_tolerance() -> None:
	with pytest.raises(ValueError):
		validator.validate_NUM("Q?", 3.14, -0.01)


@pytest.mark.parametrize("answer_float,tolerance_float", [
	(True, 0.0),
	(1.0, False),
	(float("nan"), 0.0),
	(float("inf"), 0.0),
	(float("-inf"), 0.0),
	(1.0, float("nan")),
	(1.0, float("inf")),
])
def test_validate_num_rejects_non_finite_and_boolean_values(
	answer_float: float | bool, tolerance_float: float | bool
) -> None:
	with pytest.raises(ValueError):
		validator.validate_NUM("Q?", answer_float, tolerance_float)


def test_validate_match_accepts_valid() -> None:
	assert validator.validate_MATCH("Match the fruit to their color?", ["orange", "strawberry"], ["orange", "red"]) is True


def test_validate_order_accepts_valid() -> None:
	assert validator.validate_ORDER("In what order do the numbers go?", ["1", "2", "3"]) is True
