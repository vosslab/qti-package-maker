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


def test_validate_match_accepts_valid() -> None:
	assert validator.validate_MATCH("Match the fruit to their color?", ["orange", "strawberry"], ["orange", "red"]) is True


def test_validate_order_accepts_valid() -> None:
	assert validator.validate_ORDER("In what order do the numbers go?", ["1", "2", "3"]) is True
