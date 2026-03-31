
# Import modules from the standard library
import re
import html
import json

# Pip3 Library
import lxml.etree
import lxml.html

# Import modules from external Pypi libraries

# Import modules from local libraries
#from qti_package_maker.common import string_functions

#============================================
def format_question_text(crc16_text: str, question_text: str):
	# Replace adjacent paragraph tags with a line break for cleaner formatting
	question_text = re.sub(r'</p>\s*<p>', '<br/>', question_text, flags=re.MULTILINE)
	# Add the question text inside another uniquely identified div
	html_content = f"<div id=\"statement_text_{crc16_text}\">{question_text}</div>\n"
	return html_content

#============================================
def escape_non_iso_8859_1(html_text: str) -> str:
	"""
	Replace non-ISO-8859-1 characters with numeric HTML entities.
	"""
	if html_text is None:
		return ""
	return html_text.encode("iso-8859-1", "xmlcharrefreplace").decode("iso-8859-1")

#============================================
def add_result_div(crc16_text: str):
	# Add a div to display the result message, styled with inline CSS
	style = (
		'style="display: block; '
		'margin: 0; '
		'padding: 0; '
		'font-size: large; '
		'font-weight: bold; '
		'font-family: monospace;"'
		)
	html_content = f"<div id=\"result_{crc16_text}\" {style}>&nbsp;</div>\n"
	return html_content

#============================================
def add_selftest_theme_css():
	"""
	Inject scoped theme CSS for html_selftest output if not already present.
	"""
	css = """
.qti-selftest {
  color: var(--md-default-fg-color, #111111);
  background-color: var(--md-default-bg-color, transparent);
  --qti-choice-1-bg: #fff3dc; --qti-choice-1-fg: #8a5300;
  --qti-choice-2-bg: #e8f1ff; --qti-choice-2-fg: #004080;
  --qti-choice-3-bg: #e6fff3; --qti-choice-3-fg: #008066;
  --qti-choice-4-bg: #f5e6cc; --qti-choice-4-fg: #803300;
  --qti-choice-5-bg: #ffd6ff; --qti-choice-5-fg: #660033;
  --qti-dropzone-bg: #f8f8f8;
  --qti-dropzone-hover-bg: #e6e6e6;
  --qti-border: #999999;
  --qti-dropzone-border: #bbbbbb;
  --qti-dropzone-border-filled: #888888;
  --qti-success-bg: #ccffcc;
  --qti-error-bg: #ffcccc;
  --qti-success-fg: #008000;
  --qti-error-fg: #9b1b1b;
  --qti-warning-fg: #b37100;
  --qti-btn-bg: #e6eeff;
  --qti-btn-reset-bg: #fbe9eb;
  --qti-btn-fg: inherit;
  --qti-input-bg: #ffffff;
  --qti-input-fg: inherit;
  --qti-input-border: #999999;
}
.qti-choice-1 { background-color: var(--qti-choice-1-bg); color: var(--qti-choice-1-fg); }
.qti-choice-2 { background-color: var(--qti-choice-2-bg); color: var(--qti-choice-2-fg); }
.qti-choice-3 { background-color: var(--qti-choice-3-bg); color: var(--qti-choice-3-fg); }
.qti-choice-4 { background-color: var(--qti-choice-4-bg); color: var(--qti-choice-4-fg); }
.qti-choice-5 { background-color: var(--qti-choice-5-bg); color: var(--qti-choice-5-fg); }
.qti-selftest ul[id^="choices_"] {
  list-style: none;
  padding-left: 0;
  margin: 0 0 12px 0;
}
.qti-selftest ul[id^="choices_"] > li {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
}
.qti-selftest ul[id^="choices_"].qti-auto-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 6px 12px;
}
.qti-selftest ul[id^="choices_"].qti-auto-grid-compact {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 6px 12px;
}
.qti-selftest ul[id^="choices_"] > li > label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}
.qti-selftest ul[id^="choices_"] > li > input[type="radio"],
.qti-selftest ul[id^="choices_"] > li > input[type="checkbox"] {
  margin: 0;
}
.qti-dropzone {
  background-color: var(--qti-dropzone-bg, #f8f8f8);
}
.qti-dropzone-hover {
  background-color: var(--qti-dropzone-hover-bg, #e6e6e6);
}
.qti-btn {
  background-color: var(--qti-btn-bg, #e6eeff);
  color: var(--qti-btn-fg, inherit);
}
.qti-btn-reset {
  background-color: var(--qti-btn-reset-bg, #fbe9eb);
  color: var(--qti-btn-fg, inherit);
}
.qti-input {
  background-color: var(--qti-input-bg, #ffffff);
  color: var(--qti-input-fg, inherit);
  border: 1px solid var(--qti-input-border, #999999);
  font-size: 1.1em;
  line-height: 1.2;
  padding: 4px 6px;
}
.qti-feedback-success {
  background-color: var(--qti-success-bg, #ccffcc);
  color: var(--qti-success-fg, #008000);
}
.qti-feedback-error {
  background-color: var(--qti-error-bg, #ffcccc);
  color: var(--qti-error-fg, #9b1b1b);
}
@media (prefers-color-scheme: dark) {
  .qti-selftest {
    color: var(--md-default-fg-color, #e0e0e0);
    background-color: var(--md-default-bg-color, transparent);
    --qti-choice-1-bg: #5a3600; --qti-choice-1-fg: #ffd9a3;
    --qti-choice-2-bg: #0f2a55; --qti-choice-2-fg: #b7d4ff;
    --qti-choice-3-bg: #10493c; --qti-choice-3-fg: #b6f2e1;
    --qti-choice-4-bg: #4a2300; --qti-choice-4-fg: #f1c7a0;
    --qti-choice-5-bg: #4b0030; --qti-choice-5-fg: #f7b2df;
    --qti-dropzone-bg: #2b2b2b;
    --qti-dropzone-hover-bg: #3a3a3a;
    --qti-border: #777777;
    --qti-dropzone-border: #666666;
    --qti-dropzone-border-filled: #888888;
    --qti-success-bg: #1f4d2a;
    --qti-error-bg: #5a1f1f;
    --qti-success-fg: #a8e6b0;
    --qti-error-fg: #ffc1c1;
    --qti-warning-fg: #ffd9a3;
    --qti-btn-bg: #2a3550;
    --qti-btn-reset-bg: #4b2a2a;
    --qti-btn-fg: #e0e0e0;
    --qti-input-bg: #1f1f1f;
    --qti-input-fg: #e0e0e0;
    --qti-input-border: #666666;
  }
}
body[data-md-color-scheme="default"] .qti-selftest {
  color: var(--md-default-fg-color, #111111);
  background-color: var(--md-default-bg-color, transparent);
  --qti-choice-1-bg: #fff3dc; --qti-choice-1-fg: #8a5300;
  --qti-choice-2-bg: #e8f1ff; --qti-choice-2-fg: #004080;
  --qti-choice-3-bg: #e6fff3; --qti-choice-3-fg: #008066;
  --qti-choice-4-bg: #f5e6cc; --qti-choice-4-fg: #803300;
  --qti-choice-5-bg: #ffd6ff; --qti-choice-5-fg: #660033;
  --qti-dropzone-bg: #f8f8f8;
  --qti-dropzone-hover-bg: #e6e6e6;
  --qti-border: #999999;
  --qti-dropzone-border: #bbbbbb;
  --qti-dropzone-border-filled: #888888;
  --qti-success-bg: #ccffcc;
  --qti-error-bg: #ffcccc;
  --qti-success-fg: #008000;
  --qti-error-fg: #9b1b1b;
  --qti-warning-fg: #b37100;
  --qti-btn-bg: #e6eeff;
  --qti-btn-reset-bg: #fbe9eb;
  --qti-btn-fg: inherit;
  --qti-input-bg: #ffffff;
  --qti-input-fg: inherit;
  --qti-input-border: #999999;
}
body[data-md-color-scheme="slate"] .qti-selftest {
  color: var(--md-default-fg-color, #e0e0e0);
  background-color: var(--md-default-bg-color, transparent);
  --qti-choice-1-bg: #5a3600; --qti-choice-1-fg: #ffd9a3;
  --qti-choice-2-bg: #0f2a55; --qti-choice-2-fg: #b7d4ff;
  --qti-choice-3-bg: #10493c; --qti-choice-3-fg: #b6f2e1;
  --qti-choice-4-bg: #4a2300; --qti-choice-4-fg: #f1c7a0;
  --qti-choice-5-bg: #4b0030; --qti-choice-5-fg: #f7b2df;
  --qti-dropzone-bg: #2b2b2b;
  --qti-dropzone-hover-bg: #3a3a3a;
  --qti-border: #777777;
  --qti-dropzone-border: #666666;
  --qti-dropzone-border-filled: #888888;
  --qti-success-bg: #1f4d2a;
  --qti-error-bg: #5a1f1f;
  --qti-success-fg: #a8e6b0;
  --qti-error-fg: #ffc1c1;
  --qti-warning-fg: #ffd9a3;
  --qti-btn-bg: #2a3550;
  --qti-btn-reset-bg: #4b2a2a;
  --qti-btn-fg: #e0e0e0;
  --qti-input-bg: #1f1f1f;
  --qti-input-fg: #e0e0e0;
  --qti-input-border: #666666;
}
"""
	style_text = json.dumps(css.strip())
	script = "<script>(function() {"
	script += "if (document.getElementById('qti-selftest-theme')) return;"
	script += "var style = document.createElement('style');"
	script += "style.id = 'qti-selftest-theme';"
	script += f"style.textContent = {style_text};"
	script += "(document.head || document.documentElement).appendChild(style);"
	script += "})();</script>\n"
	return script

#============================================
def validate_selftest_html(html_str: str) -> bool:
	"""
	Validate html_selftest output with a JS-tolerant HTML parser.
	"""
	if html_str.count("<script") != html_str.count("</script>"):
		raise ValueError("Unbalanced <script> tags in html_selftest output.")
	cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", html_str, flags=re.DOTALL | re.IGNORECASE)
	parser = lxml.html.HTMLParser(remove_blank_text=True)
	try:
		lxml.html.fromstring(cleaned, parser=parser)
	except (lxml.etree.ParserError, lxml.etree.XMLSyntaxError) as exc:
		raise ValueError(f"Invalid html_selftest output: {exc}") from exc
	errors = [e for e in parser.error_log if e.level_name in ("ERROR", "FATAL")]
	if errors:
		raise ValueError(f"Invalid html_selftest output: {errors[0]}")
	return True

#============================================
def make_button(button_text: str, js_function: str, button_class: str = None):
	# Add a custom button
	button_content = ""
	# Set the button type to "button" to prevent form submission
	button_content += "<button type=\"button\" "
	# Set the class of the button to match the material design theme of the website
	button_class = button_class or "md-button md-button--secondary custom-button qti-btn"
	button_content += f'class="{button_class}" '
	# Add an onclick event to call the answer-checking function for this question
	button_content += f"onclick=\"{js_function}()\">"
	# Set the button's visible text
	button_content += button_text
	# Close the button element
	button_content += "</button>\n"
	return button_content

#============================================
def add_check_answer_button(crc16_text: str, button_text: str="Check Answer"):
	# Add a button for submitting the answer
	js_function = f"checkAnswer_{crc16_text}"
	return make_button(button_text, js_function)

#============================================
def add_clear_selection_button(crc16_text: str, button_text: str="Clear Selection"):
	# "Clear Selection" button
	js_function = f"clearSelection_{crc16_text}"
	return make_button(button_text, js_function)

#============================================
def add_reset_game_button(crc16_text: str, button_text: str="Reset Game"):
	# "Reset Game" button
	js_function = f"resetGame_{crc16_text}"
	return make_button(button_text, js_function, "md-button md-button--secondary custom-button qti-btn qti-btn-reset")

#============================================
def _visible_text_length(html_text: str) -> int:
	"""
	Return the visible character count of an HTML string.

	Strips HTML tags and unescapes entities so that markup like
	K<sub>M</sub> counts as 2 chars and &alpha; counts as 1 char.
	"""
	# Strip HTML tags
	stripped = re.sub(r'<[^>]+>', '', html_text)
	# Unescape HTML entities (e.g. &alpha; -> single char)
	unescaped = html.unescape(stripped)
	return len(unescaped)

#============================================
def determine_choice_layout_class(choices_list: list) -> str:
	"""
	Determine the CSS grid class for MC/MA choice layout based on choice count
	and visible text length.

	Uses CSS Grid auto-fit to let the browser automatically arrange choices
	based on their actual rendered width. No measurement needed in Python.

	Returns one of:
	- "" (empty string): default vertical layout (2-3 choices or any long choice)
	- "qti-auto-grid-compact": responsive grid with min 150px columns (4-5 short choices)
	- "qti-auto-grid": responsive grid with min 200px columns (6+ short choices)
	"""
	num_choices = len(choices_list)

	# For 2-3 choices, keep vertical layout (clearest to read)
	if num_choices <= 3:
		return ""

	# If any choice has long visible text, force vertical layout to avoid wrapping
	max_visible_len = max(_visible_text_length(c) for c in choices_list)
	if max_visible_len > 50:
		return ""

	# For 4-5 short choices, use compact grid (min 150px per choice)
	# Will fit 2-3 columns on typical screens, adapts to actual width
	if num_choices <= 5:
		return "qti-auto-grid-compact"

	# For 6+ short choices, use standard grid (min 200px per choice)
	# Will fit 2-4 columns depending on choice content width
	return "qti-auto-grid"
