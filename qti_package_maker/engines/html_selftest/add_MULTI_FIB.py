# Standard Library
import json
import re

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions

#==============
def _make_input(blank_name: str, answers: list) -> str:
	json_answers = json.dumps(answers)
	return (
		f'<input type="text" name="{blank_name}" id="{blank_name}" '
		f'data-answers=\'{json_answers}\' class="fib-blank" '
		f'placeholder="{blank_name}"/>'
	)

#==============
def _inject_blanks(question_text: str, answer_map: dict) -> str:
	"""
	Replace [blank] markers in a MULTI_FIB stem with input elements.
	"""
	pattern = re.compile(r"\[([^\]]+)\]")
	def repl(match):
		key = match.group(1)
		if key in answer_map:
			return _make_input(key, answer_map[key])
		return match.group(0)
	return pattern.sub(repl, question_text)

#==============
def generate_core_html(crc16_text: str, question_text: str, answer_map: dict):
	stem_with_inputs = _inject_blanks(question_text, answer_map)
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	html_content += html_functions.format_question_text(crc16_text, stem_with_inputs)
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	html_content += "</div>"
	return html_content

#==============
def generate_javascript(crc16_text: str) -> str:
	js = "<script>\n"
	js += "function normalizeAnswer(val) {\n"
	js += "  if (val === undefined || val === null) return '';\n"
	js += "  let v = String(val).trim().toLowerCase();\n"
	js += "  v = v.replace(/,/g, '');\n"
	js += "  v = v.replace(/\\s+/g, '');\n"
	js += "  v = v.replace(/(?:cm|mapunits)$/i, '');\n"
	js += "  return v;\n"
	js += "}\n"

	js += f"function checkAnswer_{crc16_text}() {{\n"
	js += "  const inputs = document.querySelectorAll('.fib-blank');\n"
	js += "  let correctCount = 0;\n"
	js += "  inputs.forEach(input => {\n"
	js += "    const userRaw = input.value;\n"
	js += "    const userNorm = normalizeAnswer(userRaw);\n"
	js += "    const allowed = JSON.parse(input.dataset.answers || '[]');\n"
	js += "    const allowedNorm = allowed.map(normalizeAnswer);\n"
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
	# Locate Check button to disable on full-correct
	js += "  const checkBtn = document.querySelector(\"[onclick='checkAnswer_"+crc16_text+"()']\");\n"
	js += "  if (correctCount === inputs.length) {\n"
	# All blanks correct: engage success pill and disable Check
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	js += "    resultDiv.textContent = 'CORRECT';\n"
	js += "    if (checkBtn) { checkBtn.disabled = true; }\n"
	js += "  } else {\n"
	# Partial: engage error pill
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "    resultDiv.textContent = `Correct: ${correctCount} of ${inputs.length}`;\n"
	js += "  }\n"
	js += "}\n"

	js += "document.addEventListener('DOMContentLoaded', function() {\n"
	js += "  document.querySelectorAll('.fib-blank').forEach(input => {\n"
	js += "    input.addEventListener('keydown', function(e) {\n"
	js += "      if (e.key === 'Enter') { e.preventDefault(); }\n"
	js += "    });\n"
	js += "  });\n"
	js += "});\n"
	js += "</script>\n"
	return js

#==============
def generate_html(item_number: int, crc16_text: str, question_text: str, answer_map: dict):
	raw_html = generate_core_html(crc16_text, question_text, answer_map)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_javascript(crc16_text)
	return full_html
