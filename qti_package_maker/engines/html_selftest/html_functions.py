
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
def format_question_text(crc16_text: str, question_text: str) -> str:
	# Replace adjacent paragraph tags with a line break for cleaner formatting
	question_text = re.sub(r'</p>\s*<p>', '<br/>', question_text, flags=re.MULTILINE)
	# Add the question text inside another uniquely identified div
	html_content = f"<div id='statement_text_{crc16_text}'>{question_text}</div>\n"
	return html_content

#============================================
def escape_non_ascii(html_text: str) -> str:
	"""
	Replace all non-ASCII characters (codepoint > U+007F) with numeric HTML entities.

	Uses ascii/xmlcharrefreplace so that Latin-1 characters such as non-breaking
	space (U+00A0), plus-minus (U+00B1), and middle dot (U+00B7) are emitted as
	&#160;, &#177;, &#183; instead of raw multi-byte UTF-8 sequences that cause
	mojibake when the fragment is served without an explicit UTF-8 declaration.

	Plain ASCII is passed through unchanged. Already-numeric entities such as
	&#945; or named entities such as &alpha; are not double-escaped because the
	function operates on the raw text value, not on parsed HTML.
	"""
	if html_text is None:
		return ""
	# encode to ascii, replacing every codepoint > 0x7F with &#NNN;
	return html_text.encode("ascii", "xmlcharrefreplace").decode("ascii")

#============================================
def add_result_div(crc16_text: str) -> str:
	# Add a div to display the result message as a styled pill/badge.
	# The qti-feedback-result class provides base pill styling (neutral state).
	# JS toggles qti-feedback-success / qti-feedback-error after answer check.
	# Inline style dropped in favor of CSS classes for theme-awareness.
	# Use numeric entity &#160; instead of &nbsp; so output is pure ASCII
	html_content = f"<div id='result_{crc16_text}' class='qti-feedback-result'>&#160;</div>\n"
	return html_content

#============================================
def add_selftest_theme_css() -> str:
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
  --qti-btn-bg: #3a5acd;
  --qti-btn-fg: #ffffff;
  --qti-btn-disabled-bg: #aaaaaa;
  --qti-btn-disabled-fg: #eeeeee;
  --qti-btn-reset-bg: transparent;
  --qti-btn-reset-fg: #555555;
  --qti-btn-reset-border: #999999;
  --qti-input-bg: #ffffff;
  --qti-input-fg: #111111;
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
/* Each choice row: min 40px height for comfortable tap targets */
.qti-selftest ul[id^="choices_"] > li {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 0;
  padding: 6px 4px;
  min-height: 40px;
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
  gap: 10px;
  margin: 0;
  cursor: pointer;
}
/* Enlarged radio/checkbox inputs: ~1.4em via width/height, transform-origin top-left keeps layout aligned */
.qti-selftest ul[id^="choices_"] > li > input[type="radio"],
.qti-selftest ul[id^="choices_"] > li > input[type="checkbox"] {
  margin: 0;
  flex-shrink: 0;
  width: 1.4em;
  height: 1.4em;
  cursor: pointer;
  accent-color: var(--qti-btn-bg, #3a5acd);
}
.qti-dropzone {
  background-color: var(--qti-dropzone-bg, #f8f8f8);
}
.qti-dropzone-hover {
  background-color: var(--qti-dropzone-hover-bg, #e6e6e6);
}
/* Primary filled button (Check Answer) */
.qti-btn {
  background-color: var(--qti-btn-bg, #3a5acd);
  color: var(--qti-btn-fg, #ffffff);
  border: none;
  border-radius: 4px;
  padding: 8px 20px;
  font-weight: 600;
  cursor: pointer;
}
.qti-btn:hover {
  filter: brightness(1.1);
}
/* Disabled state: muted appearance after a correct answer (disabled attribute set by JS) */
.qti-btn:disabled,
.qti-btn[disabled] {
  background-color: var(--qti-btn-disabled-bg, #aaaaaa);
  color: var(--qti-btn-disabled-fg, #eeeeee);
  opacity: 0.55;
  cursor: not-allowed;
  filter: none;
}
/* Secondary ghost button (Clear / Reset) */
.qti-btn-reset {
  background-color: var(--qti-btn-reset-bg, transparent);
  color: var(--qti-btn-reset-fg, #555555);
  border: 1px solid var(--qti-btn-reset-border, #999999);
  border-radius: 4px;
  padding: 7px 20px;
  cursor: pointer;
}
.qti-btn-reset:hover {
  background-color: var(--qti-dropzone-hover-bg, #e6e6e6);
}
/* Text input styling */
.qti-input {
  background-color: var(--qti-input-bg, #ffffff);
  color: var(--qti-input-fg, #111111);
  border: 1px solid var(--qti-input-border, #999999);
  border-radius: 4px;
  font-size: 1.1em;
  line-height: 1.2;
  padding: 4px 6px;
}
/* Responsive images: prevent RDKit/structure canvases from overflowing on mobile */
.qti-selftest canvas,
.qti-selftest img {
  max-width: 100%;
  height: auto;
}
/* Feedback pill: neutral base state (empty placeholder, invisible until JS sets content) */
.qti-feedback-result {
  display: inline-block;
  min-height: 1.5em;
  margin: 8px 0 8px 0;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 1em;
  font-weight: 600;
  font-family: inherit;
  line-height: 1.5;
  vertical-align: middle;
}
/* Success pill */
.qti-feedback-success {
  display: inline-block;
  background-color: var(--qti-success-bg, #ccffcc);
  color: var(--qti-success-fg, #008000);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 1em;
  font-weight: 600;
  font-family: inherit;
  line-height: 1.5;
  margin: 8px 0 8px 0;
  vertical-align: middle;
}
/* Error pill */
.qti-feedback-error {
  display: inline-block;
  background-color: var(--qti-error-bg, #ffcccc);
  color: var(--qti-error-fg, #9b1b1b);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 1em;
  font-weight: 600;
  font-family: inherit;
  line-height: 1.5;
  margin: 8px 0 8px 0;
  vertical-align: middle;
}
/* Non-color accessibility markers (ASCII, no impact on textContent) */
.qti-feedback-success::before { content: "[+] "; }
.qti-feedback-error::before { content: "[x] "; }
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
    --qti-btn-bg: #4a6ee0;
    --qti-btn-fg: #ffffff;
    --qti-btn-disabled-bg: #555555;
    --qti-btn-disabled-fg: #aaaaaa;
    --qti-btn-reset-bg: transparent;
    --qti-btn-reset-fg: #c0c0c0;
    --qti-btn-reset-border: #777777;
    --qti-input-bg: #2a2a2a;
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
  --qti-btn-bg: #3a5acd;
  --qti-btn-fg: #ffffff;
  --qti-btn-disabled-bg: #aaaaaa;
  --qti-btn-disabled-fg: #eeeeee;
  --qti-btn-reset-bg: transparent;
  --qti-btn-reset-fg: #555555;
  --qti-btn-reset-border: #999999;
  --qti-input-bg: #ffffff;
  --qti-input-fg: #111111;
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
  --qti-btn-bg: #4a6ee0;
  --qti-btn-fg: #ffffff;
  --qti-btn-disabled-bg: #555555;
  --qti-btn-disabled-fg: #aaaaaa;
  --qti-btn-reset-bg: transparent;
  --qti-btn-reset-fg: #c0c0c0;
  --qti-btn-reset-border: #777777;
  --qti-input-bg: #2a2a2a;
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
def make_button(button_text: str, js_function: str, button_class: str = None) -> str:
	# Add a custom button
	button_content = ""
	# Set the button type to "button" to prevent form submission
	button_content += "<button type='button' "
	# Set the class of the button to match the material design theme of the website
	button_class = button_class or "md-button md-button--secondary custom-button qti-btn"
	button_content += f'class="{button_class}" '
	# Add an onclick event to call the answer-checking function for this question
	button_content += f"onclick='{js_function}()'>"
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
	# "Clear Selection" ghost button (qti-btn-reset = secondary/ghost style)
	js_function = f"clearSelection_{crc16_text}"
	return make_button(button_text, js_function, "md-button md-button--secondary custom-button qti-btn-reset")

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
