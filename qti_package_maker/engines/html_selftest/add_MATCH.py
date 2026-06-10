# Import modules from the standard library
import random

# Import modules from external pypi libraries

# Import modules from local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions
from qti_package_maker.engines.html_selftest import javascript_functions
#============================================
def generate_drag_and_drop_js(crc16_text: str):
	"""
	Build drag-and-drop JavaScript for MATCH items.
	"""
	js_content = ""
	# Open script tag
	js_content += "<script>\n"
	# Function definition with unique identifier
	js_content += f"\tfunction initDragAndDrop_{crc16_text}() {{\n"
	js_content += f"\t\tconst container = document.getElementById('question_html_{crc16_text}');\n"
	js_content += "\t\tif (!container) {\n"
	js_content += "\t\t\treturn;\n"
	js_content += "\t\t}\n"
	js_content += "\t\tlet draggedItem = null;\n\n"

	# Enable drag functionality for each choice
	js_content += '\t\tcontainer.querySelectorAll(".draggable").forEach(item => {\n'
	js_content += '\t\t\titem.addEventListener("dragstart", function() {\n'
	js_content += "\t\t\t\tdraggedItem = this;\n"
	js_content += '\t\t\t\tsetTimeout(() => this.style.opacity = "0.5", 0);\n'
	js_content += "\t\t\t});\n\n"

	js_content += '\t\t\titem.addEventListener("dragend", function() {\n'
	js_content += '\t\t\t\tthis.style.opacity = "1";\n'
	js_content += "\t\t\t});\n"
	js_content += "\t\t});\n\n"

	# Enable drop functionality for each drop zone
	js_content += '\t\tcontainer.querySelectorAll(".dropzone").forEach(zone => {\n'

	# Store the original background color when an item is dropped
	js_content += '\t\t\tzone.addEventListener("drop", function() {\n'
	js_content += "\t\t\t\tif (!draggedItem) {\n"
	js_content += "\t\t\t\t\treturn;\n"
	js_content += "\t\t\t\t}\n"
	js_content += "\t\t\t\tthis.dataset.originalBgColor = draggedItem.style.backgroundColor;\n"
	js_content += "\t\t\t\tthis.style.backgroundColor = this.dataset.originalBgColor;\n"
	js_content += '\t\t\t\tthis.style.border = "2px solid var(--qti-dropzone-border-filled, #888888)";\n'
	js_content += "\t\t\t\tthis.style.color = draggedItem.querySelector(\"span\").style.color;\n"
	js_content += '\t\t\t\tthis.style.fontWeight = "bold";\n\n'

	# Handle text truncation for drop zones
	js_content += "\t\t\t\tlet choiceText = draggedItem.innerText.trim();\n"
	js_content += '\t\t\t\tthis.innerHTML = choiceText.length > 30 ? choiceText.substring(0, 27) + "..." : choiceText;\n'
	js_content += "\t\t\t\tthis.dataset.value = draggedItem.dataset.value;\n"
	js_content += '\t\t\t\tthis.title = draggedItem.getAttribute("title");\n'
	js_content += "\t\t\t});\n\n"

	# Restore the stored background color on drag leave
	js_content += '\t\t\tzone.addEventListener("dragleave", function() {\n'
	js_content += '\t\t\t\tif (!this.dataset.value) {\n'
	js_content += '\t\t\t\t\tthis.style.backgroundColor = "var(--qti-dropzone-bg, #f8f8f8)";\n'
	js_content += '\t\t\t\t} else {\n'
	js_content += '\t\t\t\t\tthis.style.backgroundColor = this.dataset.originalBgColor;\n'
	js_content += '\t\t\t\t}\n'
	js_content += "\t\t\t});\n\n"

	# Prevents accidental clearing when dragging over a filled drop zone
	js_content += '\t\t\tzone.addEventListener("dragover", function(e) {\n'
	js_content += "\t\t\t\te.preventDefault();\n"
	js_content += '\t\t\t\tthis.style.backgroundColor = "var(--qti-dropzone-hover-bg, #e6e6e6)";\n'
	js_content += "\t\t\t});\n"

	js_content += "\t\t});\n"
	js_content += "\t}\n"
	js_content += f"\tinitDragAndDrop_{crc16_text}();\n"
	# Close script tag
	js_content += "</script>\n"
	return js_content

def generate_check_answers_js(crc16_text: str):
	"""
	Build JavaScript that scores matching answers and updates feedback.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	js_content = ""

	# Open script tag
	js_content += "<script>\n"

	# Function definition with unique identifier
	js_content += f"\tfunction checkAnswer_{crc16_text}() {{\n"

	# Initialize score tracking
	js_content += f"\t\tconst container = document.getElementById('question_html_{crc16_text}');\n"
	js_content += "\t\tif (!container) {\n"
	js_content += "\t\t\treturn;\n"
	js_content += "\t\t}\n"
	js_content += "\t\tlet score = 0;\n"
	js_content += "\t\tlet possible = 0;\n"
	js_content += "\t\tlet feedbackText = \"\";\n\n"

	# Loop through each dropzone to check answers
	js_content += "\t\tconst dropzones = container.querySelectorAll(\".dropzone\");\n"
	js_content += "\t\tconst feedbackCells = container.querySelectorAll(\".feedback\");\n"
	js_content += "\t\tdropzones.forEach((zone, index) => {\n"
	js_content += "\t\t\tlet selectedValue = zone.dataset.value;\n"
	js_content += "\t\t\tlet correctValue = zone.dataset.correct;\n"
	js_content += "\t\t\tlet feedbackCell = feedbackCells[index];\n\n"

	# Check if the answer is correct
	js_content += "\t\t\tif (selectedValue === correctValue) {\n"
	js_content += "\t\t\t\tscore++;\n"
	js_content += "\t\t\t\tpossible++;\n"
	js_content += "\t\t\t\tfeedbackCell.innerHTML = \"<strong>"
	js_content += "<span style='color:var(--qti-success-fg, #008000); font-size:large;'>&#9989;</span></strong>\";\n"
	js_content += "\t\t\t\tfeedbackCell.style.backgroundColor = \"var(--qti-success-bg, #ccffcc)\";\n"
	js_content += "\t\t\t} else {\n"
	js_content += "\t\t\t\tpossible++;\n"
	js_content += "\t\t\t\tfeedbackCell.innerHTML = \"&#10060;\";\n"
	js_content += "\t\t\t\tfeedbackCell.style.backgroundColor = \"var(--qti-error-bg, #ffcccc)\";\n"
	js_content += "\t\t\t}\n"
	js_content += "\t\t});\n\n"

	# Update feedback text
	js_content += "\t\tfeedbackText = `Total Score: ${score} out of ${possible}`;\n";
	js_content += "\t\tconst resultDiv = document.getElementById('result_"+crc16_text+"');\n";
	# Locate Check button to disable on full-correct
	js_content += "\t\tconst checkBtn = document.querySelector(\"[onclick='checkAnswer_"+crc16_text+"()']\");\n";

	# If 100% correct: engage success pill and disable Check
	js_content += "\t\tif (score === possible) {\n";
	js_content += "\t\t\tresultDiv.className = 'qti-feedback-result qti-feedback-success';\n";
	js_content += "\t\t\tif (checkBtn) { checkBtn.disabled = true; }\n";

	# Otherwise: engage error pill
	js_content += "\t\t} else {\n";
	js_content += "\t\t\tresultDiv.className = 'qti-feedback-result qti-feedback-error';\n";
	js_content += "\t\t}\n";

	# Set the result text (textContent preserves exact strings for bp-website classifier)
	js_content += "\t\tresultDiv.textContent = feedbackText;\n";

	# Close function
	js_content += "\t}\n"

	# Close script tag
	js_content += "</script>\n"

	return js_content

#============================================
def generate_prompts_table(crc16_text: str, prompts_list: list):
	"""
	Build the prompts table for a matching item.
	"""
	table_content = ""
	# Start table
	table_content += "<!-- Matching Table -->\n"
	table_content += "<table style=\"border: 1px solid var(--qti-border, #999999); border-collapse: collapse;\">\n"
	table_content += "\t<thead>\n"
	table_content += "\t\t<tr>\n"
	table_content += "\t\t\t<th style=\"width: 20px;\"></th>\n"  # Feedback Column
	table_content += "\t\t\t<th style=\"padding: 10px; width: 180px; text-align: center;\">Your Choice</th>\n"
	table_content += "\t\t\t<th style=\"padding: 10px;\">Prompt</th>\n"
	table_content += "\t\t</tr>\n"
	table_content += "\t</thead>\n"
	table_content += "\t<tbody>\n"
	# Generate rows for each prompt
	for index, prompt_text in enumerate(prompts_list, start=1):
		# Assign code for data-correct
		choice_data_value =  f"{crc16_text}_{index:03d}"
		table_content += '\t\t<tr>\n'
		table_content += "\t\t\t<td class=\"feedback\" style=\"border: 1px solid var(--qti-border, #999999); text-align: center; padding: 3px;\"></td>\n"
		table_content += f"\t\t\t<td class=\"dropzone qti-dropzone\" data-correct=\"{choice_data_value}\" title=\"Drop Your Choice Here\" "
		table_content += "style=\"border: 2px dashed var(--qti-dropzone-border, #bbbbbb); padding: 8px; text-align: center; "
		table_content += "font-size: 12px; min-width: 120px; max-width: 200px; overflow: hidden; white-space: nowrap; "
		table_content += "text-overflow: ellipsis;\">"
		table_content += "<span style=\"font-style: italic;\">Drop Your Choice Here</span></td>\n"
		table_content += "\t\t\t<td style=\"border: 1px solid var(--qti-border, #999999); padding: 10px;\">"
		table_content += f"{index}. {prompt_text}</td>\n"
		table_content += "\t\t</tr>\n"
	# Close table
	table_content += "\t</tbody>\n"
	table_content += "</table>\n"
	return table_content

#============================================
def generate_choices_list(crc16_text: str, choices_list: list):
	"""
	Build the draggable choices list for a matching item.
	"""
	html_content = ""
	# Add instructions
	html_content += '<p style="font-style: italic; font-size: 14px; margin-top: 10px;">Drag one of the choices below:</p>\n'
	html_content += '<ul id="choiceList" style="list-style: none; padding: 0;">\n'
	# Define colors for choices
	colors = [
		("var(--qti-choice-1-fg)", "var(--qti-choice-1-bg)"),
		("var(--qti-choice-2-fg)", "var(--qti-choice-2-bg)"),
		("var(--qti-choice-3-fg)", "var(--qti-choice-3-bg)"),
		("var(--qti-choice-4-fg)", "var(--qti-choice-4-bg)"),
		("var(--qti-choice-5-fg)", "var(--qti-choice-5-bg)")
	]
	# Zip choices with their original index (1-based)
	original_choices = [(i, choice) for i, choice in enumerate(choices_list, start=1)]
	random.shuffle(original_choices)  # Shuffle the display order

	# Generate list items
	for display_index, (original_index, choice_text) in enumerate(original_choices, start=1):
		clean_title = string_functions.make_question_pretty(choice_text)
		letter_label = string_functions.number_to_letter(display_index)
		choice_data_value =  f"{crc16_text}_{original_index:03d}"
		color_index = display_index % len(colors)
		text_color, bg_color = colors[color_index]  # Cycle through colors
		palette_index = color_index + 1
		html_content += f'\t<li class="draggable qti-choice-{palette_index}" draggable="true" data-value="{choice_data_value}" title="{clean_title}" '
		html_content += 'style="border: 1px solid var(--qti-border, #999999); padding: 8px; margin: 5px; cursor: grab; '
		html_content += f'background-color: {bg_color}; display: inline-block;">\n'
		html_content += f'\t\t<span style="color: {text_color};"><strong>{letter_label}.</strong> {choice_text}</span>\n'
		html_content += '\t</li>\n'
	# Close list
	html_content += "</ul>\n"
	return html_content

#============================================
# This function generates HTML for a matching question.
def generate_core_html(crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""
	Build the HTML body for a MATCH item (no script).
	"""
	# Start the HTML content with a div containing a unique ID for the question
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	# Add the question text inside another uniquely identified div
	html_content += html_functions.format_question_text(crc16_text, question_text)
	html_content += generate_prompts_table(crc16_text, prompts_list)
	html_content += generate_choices_list(crc16_text, choices_list)
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_reset_game_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	# Close the question div element
	html_content += "</div>"
	# Return the complete HTML content
	return html_content

#============================================
def generate_html(item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""
	Return formatted HTML plus matching scripts.
	"""
	# Generate the HTML content for the question
	raw_html = generate_core_html(crc16_text, question_text, prompts_list, choices_list)
	# Format the generated HTML for better readability, do not use for JavaScript
	formatted_html = string_functions.format_html_lxml(raw_html)
	# Append JavaScript AFTER formatting (to avoid breaking <script> tags)
	full_page_html = formatted_html
	full_page_html += generate_drag_and_drop_js(crc16_text)
	full_page_html += generate_check_answers_js(crc16_text)
	full_page_html += javascript_functions.add_reset_game_javascript(crc16_text)
	return full_page_html
