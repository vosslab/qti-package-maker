# Standard Library

# QTI Package Maker
import qti_package_maker.assessment_items.item_types
import qti_package_maker.engines.html_selftest.html_functions
import qti_package_maker.engines.html_selftest.write_item


#============================================
def test_escape_non_ascii_latin1_block():
	"""Latin-1 characters (U+0080-U+00FF) must become numeric entities."""
	# U+00A0 non-breaking space, U+00B1 plus-minus, U+00B7 middle dot
	input_text = " ±·"
	result = qti_package_maker.engines.html_selftest.html_functions.escape_non_ascii(input_text)
	# Output must be pure ASCII
	assert result.isascii()
	# Each character must become its numeric character reference
	assert "&#160;" in result
	assert "&#177;" in result
	assert "&#183;" in result


#============================================
def test_escape_non_ascii_plain_ascii_unchanged():
	"""Plain ASCII text must pass through the escape function unchanged."""
	input_text = "Hello, world! <b>test</b> &alpha; &#945;"
	result = qti_package_maker.engines.html_selftest.html_functions.escape_non_ascii(input_text)
	assert result == input_text


#============================================
def test_escape_non_ascii_none_returns_empty():
	"""None input must return an empty string without raising."""
	result = qti_package_maker.engines.html_selftest.html_functions.escape_non_ascii(None)
	assert result == ""


#============================================
def test_add_result_div_uses_numeric_nbsp(sample_items):
	"""add_result_div must use &#160; not the named entity &nbsp;."""
	html_text = qti_package_maker.engines.html_selftest.html_functions.add_result_div("abcd")
	assert "&#160;" in html_text
	assert "&nbsp;" not in html_text


#============================================
def test_mc_output_is_pure_ascii(sample_items):
	"""Full MC output must contain no byte above 0x7F.

	Item inputs must be ASCII (the constructor enforces this).  Named HTML
	entities (&plusmn;, &middot;) are a valid way to inject non-ASCII glyphs;
	the escape step must leave them intact (they are already ASCII).
	"""
	# Build the MC item using the fixture's tuple; item text is already ASCII
	item_cls = qti_package_maker.assessment_items.item_types.MC(*sample_items["MC"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MC(item_cls)
	assert html_text.isascii()
