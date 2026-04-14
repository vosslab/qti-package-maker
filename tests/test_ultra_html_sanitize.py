"""Unit tests for bb_ultra_qti_v2_1.html_sanitize module."""

# Pip3 Library
import pytest
import lxml.html

# QTI Package Maker
from qti_package_maker.engines.bb_ultra_qti_v2_1 import html_sanitize


#============================================
def _tags(html_str: str) -> set:
	"""Return the set of tag names present in a sanitized fragment."""
	wrapper = lxml.html.fromstring(f'<div>{html_str}</div>')
	return {elem.tag for elem in wrapper.iter()}


def _attrs_on(html_str: str, tag_name: str) -> dict:
	"""Return the attribute dict of the first element matching tag_name."""
	wrapper = lxml.html.fromstring(f'<div>{html_str}</div>')
	for elem in wrapper.iter():
		if elem.tag == tag_name:
			return dict(elem.attrib)
	return {}


#============================================
def test_colgroup_self_closing_repair():
	# The Michaelis-Menten bug: self-closing non-void <colgroup/> must be
	# re-serialized as paired tags so Ultra's HTML5 parser does not collapse
	# the table on first import.
	input_html = '<table><colgroup width="160"/><tr><td>data</td></tr></table>'
	output = html_sanitize.sanitize_fragment(input_html)
	assert '<colgroup></colgroup>' in output or '<colgroup>' in output
	assert 'width' not in output


#============================================
TAG_REWRITE_CASES = [
	('<b>x</b>', 'strong', 'b'),
	('<i>x</i>', 'em', 'i'),
	('<u>x</u>', 'span', 'u'),
	('<h1>x</h1>', 'h4', 'h1'),
	('<h2>x</h2>', 'h4', 'h2'),
	('<h3>x</h3>', 'h4', 'h3'),
	('<pre>x</pre>', 'p', 'pre'),
]


def test_h4_demoted_to_h5_when_h1_present():
	# h4->h5 only fires when higher headings are present, otherwise the
	# sanitizer's idempotence guard leaves standalone h4 alone.
	output = html_sanitize.sanitize_fragment('<h1>a</h1><h4>b</h4>')
	tags = _tags(output)
	assert 'h5' in tags
	assert 'h1' not in tags


@pytest.mark.parametrize('input_html,expected_tag,removed_tag', TAG_REWRITE_CASES)
def test_tag_rewrites(input_html, expected_tag, removed_tag):
	output = html_sanitize.sanitize_fragment(input_html)
	tags = _tags(output)
	assert expected_tag in tags
	assert removed_tag not in tags
	assert 'x' in output


#============================================
STRIP_ATTR_CASES = [
	('<p style="color:red">x</p>', 'p', 'style'),
	('<p class="intro">x</p>', 'p', 'class'),
	('<p id="main">x</p>', 'p', 'id'),
	('<table cellpadding="4"><tr><td>x</td></tr></table>', 'table', 'cellpadding'),
	('<table width="800"><tr><td>x</td></tr></table>', 'table', 'width'),
	('<p onclick="bad()">x</p>', 'p', 'onclick'),
	('<p xml:lang="en">x</p>', 'p', 'xml:lang'),
]


@pytest.mark.parametrize('input_html,tag,banned_attr', STRIP_ATTR_CASES)
def test_attribute_stripping(input_html, tag, banned_attr):
	output = html_sanitize.sanitize_fragment(input_html)
	attrs = _attrs_on(output, tag)
	assert banned_attr not in attrs


#============================================
DROP_TAG_CASES = [
	('<p>keep</p><script>alert("bad")</script>', 'script', 'alert'),
	('<p>keep</p><style>body{color:red}</style>', 'style', 'color: red'),
	('<p>keep</p><img src="test.png"/>', 'img', 'test.png'),
]


@pytest.mark.parametrize('input_html,dropped_tag,dropped_content', DROP_TAG_CASES)
def test_tag_drops(input_html, dropped_tag, dropped_content):
	output = html_sanitize.sanitize_fragment(input_html)
	assert dropped_tag not in _tags(output)
	assert dropped_content not in output
	assert 'keep' in output


#============================================
UNWRAP_CASES = [
	('<blockquote>quoted text</blockquote>', 'blockquote', 'quoted text'),
	('<p>Press <kbd>Ctrl+C</kbd> to copy.</p>', 'kbd', 'Ctrl+C'),
]


@pytest.mark.parametrize('input_html,unwrapped_tag,preserved_text', UNWRAP_CASES)
def test_tag_unwrapping(input_html, unwrapped_tag, preserved_text):
	output = html_sanitize.sanitize_fragment(input_html)
	assert unwrapped_tag not in _tags(output)
	assert preserved_text in output


#============================================
def test_a_href_is_preserved():
	# <a> links are the one allowed-tag-with-attribute case.
	input_html = '<a href="http://example.com" class="external">link</a>'
	output = html_sanitize.sanitize_fragment(input_html)
	attrs = _attrs_on(output, 'a')
	assert attrs.get('href') == 'http://example.com'
	assert 'class' not in attrs


#============================================
def test_numeric_nbsp_entity_survives():
	# Ultra preserves nbsp runs; this is the only reliable layout primitive.
	input_html = '<p>text&#xa0;with&#xa0;nbsp</p>'
	output = html_sanitize.sanitize_fragment(input_html)
	wrapper = lxml.html.fromstring(f'<div>{output}</div>')
	assert '\xa0' in wrapper.text_content()


#============================================
def test_complex_mixed_case_and_idempotence():
	# One realistic fragment exercises every transformation and confirms
	# sanitize(sanitize(x)) == sanitize(x).
	input_html = (
		'<div style="color:red">'
		'<h1>Title</h1>'
		'<b>bold</b> and <i>italic</i> and <u>underline</u>'
		'<table cellpadding="4" width="100%">'
		'<tr><td onclick="bad()">cell</td></tr>'
		'</table>'
		'<blockquote class="quote">quoted</blockquote>'
		'<script>alert("xss")</script>'
		'</div>'
	)
	first_pass = html_sanitize.sanitize_fragment(input_html)
	second_pass = html_sanitize.sanitize_fragment(first_pass)
	assert first_pass == second_pass
	tags = _tags(first_pass)
	# Legacy tags rewritten away
	assert {'b', 'i', 'u', 'h1', 'blockquote', 'script'}.isdisjoint(tags)
	# Target tags present
	assert {'strong', 'em', 'h4'}.issubset(tags)
	# Banned attributes gone everywhere
	wrapper = lxml.html.fromstring(f'<div>{first_pass}</div>')
	for elem in wrapper.iter():
		assert {'style', 'class', 'onclick', 'cellpadding', 'width'}.isdisjoint(elem.attrib)
	# Unwrapped content preserved
	assert 'quoted' in first_pass


#============================================

def test_drop_anti_cheat_hidden_span():
	"""Anti-cheat hidden-term spans are dropped with their content."""
	input_html = (
		"real word "
		"<span style='font-size: 1px; color: white;'>caused</span>"
		" another word"
	)
	output = html_sanitize.sanitize_fragment(input_html)
	assert "caused" not in output
	assert "real word" in output and "another word" in output


def test_drop_hidden_style_variants():
	"""Any element marked hidden by common CSS signatures is dropped."""
	variants = [
		"<span style='display: none'>secret</span>",
		"<span style='visibility: hidden'>secret</span>",
		"<span style='opacity: 0'>secret</span>",
		"<span style='color: #fff'>secret</span>",
		"<span style='font-size: 0'>secret</span>",
	]
	for variant in variants:
		output = html_sanitize.sanitize_fragment(f"visible {variant} text")
		assert "secret" not in output, f"leaked from: {variant}"


def test_hidden_span_preserves_word_boundary():
	"""
	Anti-cheat helpers emit hidden spans as replacements for inter-word
	spaces, so dropping the span must leave a space in its place or
	adjacent words collapse.
	"""
	input_html = (
		"The<span style='font-size: 1px; color: white;'>cheat</span>following"
		" question refers to"
		"<span style='font-size: 1px; color: white;'>noise</span>the table"
	)
	output = html_sanitize.sanitize_fragment(input_html)
	assert "cheat" not in output and "noise" not in output
	assert "The following" in output
	assert "to the table" in output


def test_table_cells_survive_background_color_white():
	"""
	Regression: the hidden-element signature was matching `color:white`
	as a substring of `background-color:white`, which dropped every
	table cell with a white background. Cell values must survive.
	"""
	input_html = (
		"<table><tr>"
		"<td style='background-color: white'>0.001</td>"
		"<td style='background-color:#ffffff'>26.7</td>"
		"<td style='border-color: white'>57.2</td>"
		"</tr></table>"
	)
	output = html_sanitize.sanitize_fragment(input_html)
	assert "0.001" in output
	assert "26.7" in output
	assert "57.2" in output


def test_table_cell_values_preserved():
	"""Plain table cell values pass through sanitization unchanged."""
	input_html = (
		"<table><tbody>"
		"<tr><th>[S]</th><th>V0</th></tr>"
		"<tr><td>0.001</td><td>26.7</td></tr>"
		"<tr><td>0.005</td><td>57.2</td></tr>"
		"</tbody></table>"
	)
	output = html_sanitize.sanitize_fragment(input_html)
	for value in ("[S]", "V0", "0.001", "26.7", "0.005", "57.2"):
		assert value in output, f"lost cell value: {value}"


def test_hidden_span_idempotent():
	"""Sanitizing twice produces the same result for hidden-span inputs."""
	input_html = (
		"<p>foo <span style='font-size: 1px; color: white;'>hidden</span> bar</p>"
	)
	first = html_sanitize.sanitize_fragment(input_html)
	second = html_sanitize.sanitize_fragment(first)
	assert first == second
