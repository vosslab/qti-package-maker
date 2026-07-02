

#==============
def add_mathml_javascript() -> str:
	javascript_text = ""
	javascript_text += "<script type='text/javascript' async "
	javascript_text += "  src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'>"
	javascript_text += "</script>"
	return javascript_text

#==============
def add_clear_selection_javascript(crc16_text: str) -> str:
	"""
	Build JavaScript that clears MA selections and resets the result display.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	javascript_text = "<script>\n"
	# Function definition with unique identifier
	javascript_text += f"\tfunction clearSelection_{crc16_text}() {{\n"
	# Get all checkboxes by name
	javascript_text += f"\t\tconst checkboxes = document.getElementsByName('answer_{crc16_text}');\n"
	# Convert NodeList to an array and uncheck each checkbox
	javascript_text += "\t\tArray.from(checkboxes).forEach(checkbox => checkbox.checked = false);\n"
	# Clear the result div and reset pill classes back to neutral
	javascript_text += f"\t\tconst resultDiv = document.getElementById('result_{crc16_text}');\n"
	javascript_text += "\t\tif (resultDiv) {\n"
	javascript_text += "\t\t\tresultDiv.textContent = '';\n"  # Clear result message
	# Reset to neutral base class (remove success/error)
	javascript_text += "\t\t\tresultDiv.className = 'qti-feedback-result';\n"
	javascript_text += "\t\t}\n"
	# Re-enable the Check Answer button (it may have been disabled on correct)
	javascript_text += f"\t\tconst checkBtn = document.querySelector(\"[onclick='checkAnswer_{crc16_text}()']\");\n"
	javascript_text += "\t\tif (checkBtn) { checkBtn.disabled = false; }\n"
	# Close function
	javascript_text += "\t}\n"
	# Close script tag
	javascript_text += "</script>\n"
	return javascript_text

#==============
def add_reset_game_javascript(crc16_text: str) -> str:
	"""
	Build JavaScript that resets matching dropzones and feedback.
	The function name is suffixed with the item CRC to avoid collisions when multiple
	items are embedded on the same page.
	"""
	javascript_text = "<script>\n"
	# Function definition with unique identifier
	javascript_text += f"\tfunction resetGame_{crc16_text}() {{\n"
	javascript_text += f"\t\tconst container = document.getElementById('question_html_{crc16_text}');\n"
	javascript_text += "\t\tif (!container) {\n"
	javascript_text += "\t\t\treturn;\n"
	javascript_text += "\t\t}\n"

	# Reset all dropzones
	javascript_text += '\t\tcontainer.querySelectorAll(".dropzone").forEach(zone => {\n'
	javascript_text += '\t\t\tzone.textContent = "Drop Your Choice Here";\n'
	javascript_text += '\t\t\tdelete zone.dataset.value;\n'
	javascript_text += '\t\t\tzone.style.backgroundColor = "var(--qti-dropzone-bg, #f8f8f8)";\n'
	javascript_text += '\t\t\tzone.style.border = "2px dashed var(--qti-dropzone-border, #bbbbbb)";\n'
	javascript_text += '\t\t\tzone.style.color = "inherit";\n'
	javascript_text += '\t\t\tzone.style.fontWeight = "normal";\n'
	javascript_text += "\t\t});\n\n"

	# Clear the feedback column AND reset its color
	javascript_text += '\t\tcontainer.querySelectorAll(".feedback").forEach(cell => {\n'
	javascript_text += '\t\t\tcell.textContent = "";\n'
	javascript_text += '\t\t\tcell.style.backgroundColor = "transparent";\n'
	javascript_text += "\t\t});\n"

	# Clear score result div and reset pill classes back to neutral
	javascript_text += f'\t\tconst resultDiv_{crc16_text} = document.getElementById("result_{crc16_text}");\n'
	javascript_text += '\t\tif (resultDiv_' + crc16_text + ') {\n'
	javascript_text += '\t\t\tresultDiv_' + crc16_text + '.textContent = "";\n'
	javascript_text += '\t\t\tresultDiv_' + crc16_text + '.className = "qti-feedback-result";\n'
	javascript_text += '\t\t}\n'
	# Re-enable the Check Answer button
	javascript_text += '\t\tconst checkBtn_' + crc16_text + ' = document.querySelector("' + "[onclick='checkAnswer_" + crc16_text + "()']" + '");\n'
	javascript_text += '\t\tif (checkBtn_' + crc16_text + ') { checkBtn_' + crc16_text + '.disabled = false; }\n'

	# Close function
	javascript_text += "\t}\n"
	# Close script tag
	javascript_text += "</script>\n"
	return javascript_text
