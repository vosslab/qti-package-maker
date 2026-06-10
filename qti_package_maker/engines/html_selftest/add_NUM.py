# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions

#==============
def generate_core_html(crc16_text: str, question_text: str, answer_float: float, tolerance_float: float=None):
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	html_content += html_functions.format_question_text(crc16_text, question_text)
	html_content += "<div>\n"
	html_content += f"<input type=\"text\" class=\"qti-input\" id=\"num_input_{crc16_text}\" inputmode=\"decimal\" pattern=\"[0-9]*[.,]?[0-9]*\" "
	html_content += "placeholder=\"Enter a number\" />\n"
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	html_content += "</div><br/>\n"
	html_content += "</div>"
	return html_content

#==============
def generate_javascript(crc16_text: str, answer_float: float, tolerance_float: float=None) -> str:
	"""
	Build JavaScript that checks a numeric answer.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	js = "<script>\n"
	tol = tolerance_float if tolerance_float is not None else 0.0
	js += f"const numAnswer_{crc16_text} = {answer_float};\n"
	js += f"const numTolerance_{crc16_text} = {tol};\n"
	js += f"function checkAnswer_{crc16_text}() {{\n"
	js += f"  const inputEl = document.getElementById('num_input_{crc16_text}');\n"
	js += "  if (!inputEl) { return; }\n"
	js += "  const valStr = inputEl.value.trim();\n"
	js += f"  const resultDiv = document.getElementById('result_{crc16_text}');\n"
	# Locate the Check button to disable it on correct
	js += f"  const checkBtn = document.querySelector(\"[onclick='checkAnswer_{crc16_text}()']\");\n"
	js += "  if (valStr === '') {\n"
	# Neutral pill for empty input
	js += "    resultDiv.className = 'qti-feedback-result';\n"
	js += "    resultDiv.textContent = 'Please enter a value.';\n"
	js += "    return;\n"
	js += "  }\n"
	js += "  const userVal = Number(valStr);\n"
	js += "  if (Number.isNaN(userVal)) {\n"
	# Neutral pill for invalid input
	js += "    resultDiv.className = 'qti-feedback-result';\n"
	js += "    resultDiv.textContent = 'Please enter a valid number.';\n"
	js += "    return;\n"
	js += "  }\n"
	js += f"  const lower = numAnswer_{crc16_text} - numTolerance_{crc16_text};\n"
	js += f"  const upper = numAnswer_{crc16_text} + numTolerance_{crc16_text};\n"
	js += "  const isCorrect = (userVal >= lower && userVal <= upper);\n"
	js += "  if (isCorrect) {\n"
	# Engage success pill and disable Check on correct
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	js += "    resultDiv.textContent = 'CORRECT';\n"
	js += "    if (checkBtn) { checkBtn.disabled = true; }\n"
	js += "  } else {\n"
	# Engage error pill for wrong answer
	js += "    if (userVal > upper) {\n"
	js += "      resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "      resultDiv.textContent = 'Too high. Try again.';\n"
	js += "    } else if (userVal < lower) {\n"
	js += "      resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "      resultDiv.textContent = 'Too low. Try again.';\n"
	js += "    } else {\n"
	js += "      resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "      resultDiv.textContent = 'Incorrect. Try again.';\n"
	js += "    }\n"
	js += "  }\n"
	js += "}\n"
	js += "document.addEventListener('DOMContentLoaded', function() {\n"
	js += f"  const inputEl = document.getElementById('num_input_{crc16_text}');\n"
	js += "  if (!inputEl) return;\n"
	js += "  inputEl.addEventListener('keydown', function(e) {\n"
	js += f"    if (e.key === 'Enter') {{ e.preventDefault(); checkAnswer_{crc16_text}(); }}\n"
	js += "  });\n"
	js += "});\n"
	js += "</script>\n"
	return js

#==============
def generate_html(item_number: int, crc16_text: str, question_text: str, answer_float: float, tolerance_float: float, tolerance_message=True):
	raw_html = generate_core_html(crc16_text, question_text, answer_float, tolerance_float)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_javascript(crc16_text, answer_float, tolerance_float)
	return full_html
