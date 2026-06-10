# Import modules from the standard library

# Import modules from external pypi libraries

# Import modules from local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions
from qti_package_maker.engines.html_selftest import javascript_functions

#==============
# This function generates HTML for a multiple-answer question.
def generate_core_html(crc16_text: str, question_text: str, choices_list: list, answers_list: list):
	"""
	Build the HTML body for an MA item (no script).
	"""
	# Start the HTML content with a div containing a unique ID for the question
	html_content = f"<div id=\"question_html_{crc16_text}\">\n"
	# Add the question text inside another uniquely identified div
	html_content += html_functions.format_question_text(crc16_text, question_text)
	# Begin the form for the multiple-choice options
	html_content += "<form>\n"
	# Determine the best layout class based on choice count and text length
	layout_class = html_functions.determine_choice_layout_class(choices_list)
	class_attr = f' class="{layout_class}"' if layout_class else ""
	# Add an unordered list to contain the choices, identified by a unique ID
	html_content += f"<ul id=\"choices_{crc16_text}\"{class_attr}>\n"
	# Loop through each answer choice
	# Loop through each answer choice
	for idx, choice_text in enumerate(choices_list, start=1):
		# Extract the choice text and whether it is the correct answer
		is_correct_bool = (choice_text in answers_list)
		# Generate the letter prefix (A, B, C, ...)
		choice_letter = chr(64 + idx)
		# Add a list item to contain the checkbox button and label
		html_content += "  <li>\n"
		# Add an input element of type "checkbox"
		html_content += f"    <input type=\"checkbox\" id=\"option_{crc16_text}_{idx}\" "
		# Set the name attribute to group checkbox buttons together under the question's hex value
		html_content += f" name=\"answer_{crc16_text}\" "
		# Store whether the choice is correct as a custom data attribute
		html_content += f" data-correct=\"{str(is_correct_bool).lower()}\">\n"
		# Add a label with bold letter prefix and text wrapped in span for proper sub/sup rendering
		html_content += f"    <label for=\"option_{crc16_text}_{idx}\">"
		html_content += f"<span style=\"font-weight: bold;\">{choice_letter}.</span> "
		html_content += f"<span>{choice_text}</span></label>\n"
		# Close the list item
		html_content += "  </li>\n"
	# Close the unordered list of choices
	html_content += "</ul>\n"
	html_content += html_functions.add_check_answer_button(crc16_text)
	html_content += html_functions.add_clear_selection_button(crc16_text)
	html_content += html_functions.add_result_div(crc16_text)
	# Close the form element
	html_content += "</form><br/>\n"
	# Close the question div element
	html_content += "</div>"
	# Return the complete HTML content
	return html_content

def generate_javascript(crc16_text) -> str:
	"""
	Build JavaScript that checks multiple-answer selections.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	# Begin the JavaScript with a script tag
	javascript_html = "<script>\n"

	# Define the function to check selected answers
	javascript_html += f"function checkAnswer_{crc16_text}() {{\n"

	# Get all checkbox options for this question
	javascript_html += f"\tconst options = Array.from(document.getElementsByName('answer_{crc16_text}'));\n"

	# Find all correct answers using data attribute
	javascript_html += "\tconst correctOptions = options.filter(option => option.dataset.correct === 'true');\n"

	# Find selected answers
	javascript_html += "\tconst selectedOptions = options.filter(option => option.checked);\n"

	# Get the result display element
	javascript_html += f"\tconst resultDiv = document.getElementById('result_{crc16_text}');\n"

	# Locate the Check Answer button for this question (used to disable on correct)
	javascript_html += f"\tconst checkBtn = document.querySelector(\"[onclick='checkAnswer_{crc16_text}()']\");\n"

	# Count correct and incorrect selections
	javascript_html += "\tconst numCorrectSelected = selectedOptions.filter(option => correctOptions.includes(option)).length;\n"
	javascript_html += "\tconst numIncorrectSelected = selectedOptions.length - numCorrectSelected;\n"
	javascript_html += "\tconst totalCorrect = correctOptions.length;\n"
	javascript_html += "\tconst totalSelected = selectedOptions.length;\n"

	# Check for a fully correct answer: engage success pill and disable Check
	javascript_html += "\tif (numCorrectSelected === totalCorrect && totalSelected === totalCorrect) {\n"
	javascript_html += "\t\tresultDiv.className = 'qti-feedback-result qti-feedback-success';\n"
	javascript_html += "\t\tresultDiv.textContent = 'CORRECT';\n"
	javascript_html += "\t\tif (checkBtn) { checkBtn.disabled = true; }\n"

	# Case: Too many choices (some correct, some incorrect): error pill
	javascript_html += "\t} else if (totalSelected > totalCorrect) {\n"
	javascript_html += "\t\tresultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	javascript_html += "\t\tresultDiv.textContent = `Too many answers selected. You selected ${numCorrectSelected} correct answers, but also included ${numIncorrectSelected} incorrect choices.`;\n"

	# Case: Too few correct answers selected: error pill
	javascript_html += "\t} else if (numCorrectSelected < totalCorrect && totalSelected < totalCorrect) {\n"
	javascript_html += "\t\tresultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	javascript_html += "\t\tresultDiv.textContent = `Too few answers selected. You got ${numCorrectSelected} out of ${totalCorrect} correct.`;\n"

	# Case: Correct number of boxes checked, but contains incorrect answers: error pill
	javascript_html += "\t} else if (totalSelected === totalCorrect && numCorrectSelected < totalCorrect) {\n"
	javascript_html += "\t\tresultDiv.className = 'qti-feedback-result qti-feedback-error';\n"
	javascript_html += "\t\tresultDiv.textContent = `You selected the right number of choices, but only ${numCorrectSelected} out of ${totalCorrect} are correct.`;\n"

	# Case: No selection: neutral pill
	javascript_html += "\t} else if (totalSelected === 0) {\n"
	javascript_html += "\t\tresultDiv.className = 'qti-feedback-result';\n"
	javascript_html += "\t\tresultDiv.textContent = 'Please select an answer.';\n"

	javascript_html += "\t}\n"  # Close the if statement

	# Close function
	javascript_html += "}\n"

	# Close script tag
	javascript_html += "</script>\n"

	return javascript_html

#==============

def generate_html(item_number: int, crc16_text: str, question_text: str, choices_list: list, answer_text: str):
	"""
	Return formatted HTML plus the MA answer-check script.
	"""
	# Generate the HTML content for the question
	raw_html = generate_core_html(crc16_text, question_text, choices_list, answer_text)
	# Format the generated HTML for better readability, do not use for JavaScript
	formatted_html = string_functions.format_html_lxml(raw_html)
	# Append JavaScript AFTER formatting (to avoid breaking <script> tags)
	full_page_html = formatted_html
	full_page_html += generate_javascript(crc16_text)
	full_page_html += javascript_functions.add_clear_selection_javascript(crc16_text)
	return full_page_html
