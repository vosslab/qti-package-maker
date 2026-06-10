# Standard Library
import random

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions
from qti_package_maker.engines.html_selftest import javascript_functions

#==============
def _choice_token(crc16_text: str, idx: int) -> str:
	return f"{crc16_text}_{idx:03d}"

#==============
def generate_drag_and_drop_js(crc16_text: str):
	js = "<script>\n"
	js += f"function initDragAndDrop_{crc16_text}() {{\n"
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  if (!container) {\n"
	js += "    return;\n"
	js += "  }\n"
	js += "  let draggedItem = null;\n"

	js += '  container.querySelectorAll(".draggable").forEach(item => {\n'
	js += '    item.addEventListener("dragstart", function() {\n'
	js += "      draggedItem = this;\n"
	js += '      setTimeout(() => this.style.opacity = "0.5", 0);\n'
	js += "    });\n"
	js += '    item.addEventListener("dragend", function() {\n'
	js += '      this.style.opacity = "1";\n'
	js += "    });\n"
	js += "  });\n"

	js += '  container.querySelectorAll(".dropzone").forEach(zone => {\n'
	js += '  zone.addEventListener("dragover", e => { e.preventDefault(); zone.style.backgroundColor = "var(--qti-dropzone-hover-bg, #e6e6e6)"; });\n'
	js += '  zone.addEventListener("dragleave", () => {\n'
	js += '    if (!zone.dataset.value) { zone.style.backgroundColor = "var(--qti-dropzone-bg, #f8f8f8)"; }\n'
	js += '    else { zone.style.backgroundColor = zone.dataset.originalBgColor || "var(--qti-dropzone-bg, #f8f8f8)"; }\n'
	js += "  });\n"
	js += "  zone.addEventListener(\"drop\", () => {\n"
	js += "    if (!draggedItem) return;\n"
	js += "    zone.dataset.originalBgColor = draggedItem.style.backgroundColor;\n"
	js += "    zone.style.backgroundColor = zone.dataset.originalBgColor;\n"
	js += '    zone.style.border = "2px solid var(--qti-dropzone-border-filled, #888888)";\n'
	js += "    const span = draggedItem.querySelector('span');\n"
	js += "    if (span) { zone.style.color = span.style.color; zone.style.fontWeight = 'bold'; }\n"
	js += "    let choiceText = draggedItem.innerText.trim();\n"
	js += '    zone.innerHTML = choiceText.length > 30 ? choiceText.substring(0, 27) + "..." : choiceText;\n'
	js += "    zone.title = draggedItem.getAttribute('title');\n"
	js += "    zone.dataset.value = draggedItem.dataset.value;\n"
	js += "  });\n"
	js += "  });\n"

	js += "}\n"
	js += f"initDragAndDrop_{crc16_text}();\n"

	js += "</script>\n"
	return js

#==============
def generate_check_answers_js(crc16_text: str):
	"""
	Build JavaScript that scores ordering answers and updates feedback.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	js = "<script>\n"
	js += f"function checkAnswer_{crc16_text}() {{\n"
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  if (!container) {\n"
	js += "    return;\n"
	js += "  }\n"
	js += "  let correct = 0;\n"
	js += "  let total = 0;\n"
	js += '  const dropzones = container.querySelectorAll(".dropzone");\n'
	js += "  const feedbackCells = container.querySelectorAll('.feedback');\n"
	js += "  dropzones.forEach((zone, index) => {\n"
	js += "    const expected = zone.dataset.correct;\n"
	js += "    const actual = zone.dataset.value;\n"
	js += "    const feedbackCell = feedbackCells[index];\n"
	js += "    total++;\n"
	js += "    if (actual && actual === expected) {\n"
	js += "      correct++;\n"
	js += "      feedbackCell.innerHTML = \"<strong><span style='color:var(--qti-success-fg, #008000); font-size:large;'>&#9989;</span></strong>\";\n"
	js += "      feedbackCell.style.backgroundColor = 'var(--qti-success-bg, #ccffcc)';\n"
	js += "    } else {\n"
	js += "      feedbackCell.innerHTML = \"&#10060;\";\n"
	js += "      feedbackCell.style.backgroundColor = 'var(--qti-error-bg, #ffcccc)';\n"
	js += "    }\n"
	js += "  });\n"
	js += f"  const resultDiv = document.getElementById('result_{crc16_text}');\n"
	# Locate Check button to disable on full-correct
	js += f"  const checkBtn = document.querySelector(\"[onclick='checkAnswer_{crc16_text}()']\");\n"
	js += "  resultDiv.textContent = `Correct positions: ${correct} of ${total}`;\n"
	# Engage success pill on full-correct, error pill otherwise; disable Check on full-correct
	js += "  if (correct === total) {\n"
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	js += "    if (checkBtn) { checkBtn.disabled = true; }\n"
	js += "  } else {\n"
	js += "    resultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	js += "  }\n"
	js += "}\n"
	js += "</script>\n"
	return js

#==============
def generate_dropzones_table(crc16_text: str, ordered_answers_list: list):
	table = "<table style=\"border: 1px solid var(--qti-border, #999999); border-collapse: collapse; width: 100%;\">\n"
	table += "<thead><tr>"
	table += "<th style=\"width: 30px;\"></th>"
	table += "<th style=\"padding: 8px; width: 200px; text-align: center;\">Position</th>"
	table += "<th style=\"padding: 8px;\">Your choice</th>"
	table += "</tr></thead>\n<tbody>\n"
	for idx, _ in enumerate(ordered_answers_list, start=1):
		correct_token = _choice_token(crc16_text, idx)
		table += "<tr>\n"
		table += "<td class=\"feedback\" style=\"border: 1px solid var(--qti-border, #999999); text-align: center; padding: 3px;\"></td>\n"
		table += f"<td style=\"border: 1px solid var(--qti-border, #999999); padding: 8px; text-align: center; font-weight:bold;\">{idx}</td>\n"
		table += f"<td class=\"dropzone qti-dropzone\" data-correct=\"{correct_token}\" title=\"Drop Your Choice Here\" "
		table += "style=\"border: 2px dashed var(--qti-dropzone-border, #bbbbbb); padding: 8px; text-align: center; "
		table += "font-size: 12px; min-width: 200px; max-width: 400px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;\">"
		table += "<span style=\"font-style: italic;\">Drop Your Choice Here</span></td>\n"
		table += "</tr>\n"
	table += "</tbody></table>\n"
	return table

#==============
def generate_choices_list(crc16_text: str, ordered_answers_list: list):
	html = '<p style="font-style: italic; font-size: 14px; margin-top: 10px;">Drag each answer into the correct position:</p>\n'
	html += '<ul style="list-style: none; padding: 0;">\n'
	colors = [
		("var(--qti-choice-1-fg)", "var(--qti-choice-1-bg)"),
		("var(--qti-choice-2-fg)", "var(--qti-choice-2-bg)"),
		("var(--qti-choice-3-fg)", "var(--qti-choice-3-bg)"),
		("var(--qti-choice-4-fg)", "var(--qti-choice-4-bg)"),
		("var(--qti-choice-5-fg)", "var(--qti-choice-5-bg)")
	]
	choices = [(i, txt) for i, txt in enumerate(ordered_answers_list, start=1)]
	random.shuffle(choices)
	for display_idx, (orig_idx, choice_text) in enumerate(choices, start=1):
		token = _choice_token(crc16_text, orig_idx)
		color_index = display_idx % len(colors)
		text_color, bg_color = colors[color_index]
		palette_index = color_index + 1
		clean_title = string_functions.make_question_pretty(choice_text)
		html += f'<li class="draggable qti-choice-{palette_index}" draggable="true" data-value="{token}" title="{clean_title}" '
		html += 'style="border: 1px solid var(--qti-border, #999999); padding: 8px; margin: 5px; cursor: grab; display: inline-block; '
		html += f'background-color: {bg_color};">'
		html += f"<span style=\"color: {text_color};\"><strong>{display_idx}.</strong> {choice_text}</span>"
		html += "</li>\n"
	html += "</ul>\n"
	return html

#==============
def generate_core_html(crc16_text: str, question_text: str, ordered_answers_list: list):
	html = f"<div id=\"question_html_{crc16_text}\">\n"
	html += html_functions.format_question_text(crc16_text, question_text)
	html += generate_dropzones_table(crc16_text, ordered_answers_list)
	html += generate_choices_list(crc16_text, ordered_answers_list)
	html += html_functions.add_check_answer_button(crc16_text)
	html += html_functions.add_reset_game_button(crc16_text)
	html += html_functions.add_result_div(crc16_text)
	html += "</div>"
	return html

#==============
def generate_html(item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	raw_html = generate_core_html(crc16_text, question_text, ordered_answers_list)
	formatted_html = string_functions.format_html_lxml(raw_html)
	full_html = formatted_html
	full_html += generate_drag_and_drop_js(crc16_text)
	full_html += generate_check_answers_js(crc16_text)
	full_html += javascript_functions.add_reset_game_javascript(crc16_text)
	return full_html
