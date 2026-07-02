# Standard Library
import json

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions

#==============
def generate_core_html(crc16_text: str, question_text: str, answers_list: list) -> str:
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	html_content += html_functions.format_question_text(crc16_text, question_text)
	html_content += "<form>\n"
	html_content += f"<input type=\"text\" class=\"qti-input\" id=\"fib_input_{crc16_text}\" "
	html_content += "placeholder=\"Enter your answer\" autocomplete=\"off\"/>\n"
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	html_content += "</form><br/>\n"
	html_content += "</div>"
	return html_content

#==============
def generate_javascript(crc16_text: str, answers_list: list) -> str:
	normalized_answers = [ans.lower().strip() for ans in answers_list]
	js = "<script>\n"
	# json.dumps produces a valid JS/JSON array literal (double-quoted strings, proper escaping)
	js += f"const fibAnswers_{crc16_text} = {json.dumps(normalized_answers)};\n"
	js += f"function checkAnswer_{crc16_text}() {{\n"
	js += f"  const inputEl = document.getElementById('fib_input_{crc16_text}');\n"
	js += "  if (!inputEl) { return; }\n"
	js += "  const userAns = inputEl.value.trim().toLowerCase();\n"
	js += f"  const resultDiv = document.getElementById('result_{crc16_text}');\n"
	# Locate the Check Answer button to disable it on correct
	js += f"  const checkBtn = document.querySelector(\"[onclick='checkAnswer_{crc16_text}()']\");\n"
	js += f"  const isCorrect = fibAnswers_{crc16_text}.includes(userAns);\n"
	js += "  if (isCorrect) {\n"
	# Engage success pill and disable Check button
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	js += "    resultDiv.textContent = 'CORRECT';\n"
	js += "    if (checkBtn) { checkBtn.disabled = true; }\n"
	js += "  } else {\n"
	# Engage error pill
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "    resultDiv.textContent = 'incorrect';\n"
	js += "  }\n"
	js += "}\n"
	js += "</script>\n"
	return js

#==============
def generate_html(item_number: int, crc16_text: str, question_text: str, answers_list: list) -> str:
	raw_html = generate_core_html(crc16_text, question_text, answers_list)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_javascript(crc16_text, answers_list)
	return full_html
