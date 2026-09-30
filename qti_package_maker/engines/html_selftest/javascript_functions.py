

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
	# Close function
	javascript_text += "\t}\n"
	# Close script tag
	javascript_text += "</script>\n"
	return javascript_text

#==============
def add_reset_game_javascript(crc16_text: str) -> str:
	"""Clear stale grades and delegate reset to the item's controls."""
	js = '<script>\n'
	js += f'function clearFeedback_{crc16_text}() {{\n'
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  container.querySelectorAll('.feedback').forEach(cell => {\n"
	js += "    cell.textContent = '';\n"
	js += "    cell.style.backgroundColor = 'transparent';\n"
	js += "    cell.removeAttribute('aria-label');\n"
	js += "  });\n"
	js += f"  const resultDiv = container.querySelector('#result_{crc16_text}');\n"
	js += "  resultDiv.textContent = '';\n"
	js += "  resultDiv.className = 'qti-feedback-result';\n"
	js += '}\n'
	js += f'function resetGame_{crc16_text}() {{\n'
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	js += "  container.qtiResetGame();\n"
	js += f"  clearFeedback_{crc16_text}();\n"
	js += '}\n</script>\n'
	return js

#==============
def add_check_rows_javascript(crc16_text: str, item_type: str) -> str:
	"""Keep row feedback and the website's exact ORDER/MATCH grading strings."""
	js = '<script>\n'
	js += f'function checkAnswer_{crc16_text}() {{\n'
	js += f"  const container = document.getElementById('question_html_{crc16_text}');\n"
	selector = '.qti-order-row' if item_type == 'ORDER' else '.qti-match-slot'
	js += f"  const rows = container.querySelectorAll('{selector}');\n"
	js += "  const feedbackCells = container.querySelectorAll('.feedback');\n"
	js += "  let score = 0;\n"
	js += "  rows.forEach((row, index) => {\n"
	if item_type == 'ORDER':
		js += f"    const expected = '{crc16_text}_' + String(index + 1).padStart(3, '0');\n"
	else:
		js += "    const expected = row.dataset.correct;\n"
	js += "    const right = row.dataset.value === expected;\n"
	js += "    if (right) score++;\n"
	js += "    const cell = feedbackCells[index];\n"
	js += "    cell.innerHTML = right ? '&#9989;' : '&#10060;';\n"
	js += "    cell.setAttribute('aria-label', right ? 'Correct' : 'Incorrect');\n"
	js += "    cell.style.backgroundColor = right ? 'var(--qti-success-bg)' : 'var(--qti-error-bg)';\n"
	js += "  });\n"
	js += f"  const resultDiv = container.querySelector('#result_{crc16_text}');\n"
	if item_type == 'ORDER':
		js += "  const correct = score, total = rows.length;\n"
		js += "  resultDiv.textContent = `Correct positions: ${correct} of ${total}`;\n"
	else:
		js += "  const possible = rows.length;\n"
		js += "  resultDiv.textContent = `Total Score: ${score} out of ${possible}`;\n"
	js += "  resultDiv.className = 'qti-feedback-result ' +\n"
	js += "    (score === rows.length ? 'qti-feedback-success' : 'qti-feedback-error');\n"
	js += "  container.querySelector('[role=status]').textContent = resultDiv.textContent;\n"
	js += '}\n</script>\n'
	return js
