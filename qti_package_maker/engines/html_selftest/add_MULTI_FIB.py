# Standard Library
import html
import json
import re

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions

#==============
def _make_input(
		crc16_text: str, blank_name: str, answers: list, occurrence_index: int) -> str:
	"""Build one attribute-safe MULTI_FIB input with a document-unique ID."""
	# Encode both values for the double-quoted attributes that carry them.
	escaped_blank_name = html.escape(blank_name, quote=True)
	escaped_json_answers = html.escape(json.dumps(answers), quote=True)
	# The occurrence suffix keeps repeated blank names unique within one item.
	input_id = f"fib_blank_{crc16_text}_{occurrence_index}"
	input_html = (
		f'<input type="text" name="{escaped_blank_name}" id="{input_id}" '
		f'data-answers="{escaped_json_answers}" class="fib-blank" '
		f'placeholder="{escaped_blank_name}"/>'
	)
	return input_html

#==============
def _inject_blanks(crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""
	Replace [blank] markers in a MULTI_FIB stem with input elements.
	"""
	pattern = re.compile(r"\[([^\]]+)\]")
	occurrence_index = 0
	def repl(match: re.Match) -> str:
		nonlocal occurrence_index
		key = match.group(1)
		if key in answer_map:
			occurrence_index += 1
			return _make_input(crc16_text, key, answer_map[key], occurrence_index)
		return match.group(0)
	stem_with_inputs = pattern.sub(repl, question_text)
	return stem_with_inputs

#==============
def generate_core_html(crc16_text: str, question_text: str, answer_map: dict) -> str:
	stem_with_inputs = _inject_blanks(crc16_text, question_text, answer_map)
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	html_content += html_functions.format_question_text(crc16_text, stem_with_inputs)
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	html_content += "</div>"
	return html_content

#==============
def generate_javascript(crc16_text: str) -> str:
	js = "<script>\n"
	js += f"function normalizeAnswer_{crc16_text}(val) {{\n"
	js += "  if (val === undefined || val === null) return '';\n"
	js += "  let v = String(val).trim().toLowerCase();\n"
	js += "  v = v.replace(/,/g, '');\n"
	js += "  v = v.replace(/\\s+/g, '');\n"
	js += "  v = v.replace(/(?:cm|mapunits)$/i, '');\n"
	js += "  return v;\n"
	js += "}\n"

	js += f"function checkAnswer_{crc16_text}() {{\n"
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  if (!container) { return; }\n"
	js += "  const inputs = container.querySelectorAll('.fib-blank');\n"
	js += "  let correctCount = 0;\n"
	js += "  inputs.forEach(input => {\n"
	js += "    const userRaw = input.value;\n"
	js += f"    const userNorm = normalizeAnswer_{crc16_text}(userRaw);\n"
	js += "    const allowed = JSON.parse(input.dataset.answers || '[]');\n"
	js += f"    const allowedNorm = allowed.map(normalizeAnswer_{crc16_text});\n"
	js += "    const isCorrect = allowedNorm.includes(userNorm) && userNorm !== '';\n"
	js += "    if (isCorrect) {\n"
	js += "      input.classList.add('correct');\n"
	js += "      input.classList.remove('incorrect');\n"
	js += "      correctCount++;\n"
	js += "    } else {\n"
	js += "      input.classList.add('incorrect');\n"
	js += "      input.classList.remove('correct');\n"
	js += "    }\n"
	js += "  });\n"
	js += "  const resultDiv = document.getElementById('result_"+crc16_text+"');\n"
	js += "  if (correctCount === inputs.length) {\n"
	# All blanks correct: engage success pill.
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	js += "    resultDiv.textContent = 'CORRECT';\n"
	js += "  } else {\n"
	# Partial: engage error pill
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "    resultDiv.textContent = `Correct: ${correctCount} of ${inputs.length}`;\n"
	js += "  }\n"
	js += "}\n"

	js += f"function initMultiFib_{crc16_text}() {{\n"
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  if (!container) { return; }\n"
	js += "  container.querySelectorAll('.fib-blank').forEach(input => {\n"
	js += "    input.addEventListener('keydown', function(e) {\n"
	js += "      if (e.key === 'Enter') { e.preventDefault(); }\n"
	js += "    });\n"
	js += "  });\n"
	js += "}\n"
	js += f"initMultiFib_{crc16_text}();\n"
	js += "</script>\n"
	return js

#==============
def generate_html(item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	raw_html = generate_core_html(crc16_text, question_text, answer_map)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_javascript(crc16_text)
	return full_html
