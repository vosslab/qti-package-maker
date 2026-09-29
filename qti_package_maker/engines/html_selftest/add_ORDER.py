# Standard Library
import random
import re

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions
from qti_package_maker.engines.html_selftest import javascript_functions
from qti_package_maker.engines.html_selftest import order_controls
from qti_package_maker.engines.html_selftest import drag_controls

#==============
def _choice_token(crc16_text: str, idx: int) -> str:
	token = f"{crc16_text}_{idx:03d}"
	return token

#==============
def generate_check_answers_js(crc16_text: str) -> str:
	js = javascript_functions.add_check_rows_javascript(crc16_text, 'ORDER')
	return js

#==============
def generate_choices_list(crc16_text: str, ordered_answers_list: list) -> str:
	html_text = '<p class="qti-control-instructions">Drag and drop rows to arrange the answers, '
	html_text += 'or use Move up and Move down. '
	html_text += 'You can also use the arrow keys while a move button is focused.</p>\n'
	html_text += '<ol class="qti-order-list" aria-label="Your answer order">\n'
	choices = list(enumerate(ordered_answers_list, start=1))
	random.shuffle(choices)
	for display_idx, (orig_idx, choice_text) in enumerate(choices, start=1):
		token = _choice_token(crc16_text, orig_idx)
		palette_index = display_idx % 5 + 1
		html_text += f'<li class="qti-order-row qti-choice-{palette_index}" data-value="{token}" draggable="true">'
		html_text += '<span class="feedback"></span>'
		html_text += f'<strong class="qti-order-position">{display_idx}</strong>'
		# Oversized diagrams retain local scrolling and a keyboard-accessible scroll region.
		scroll_attributes = ''
		if re.search(r'<\s*(?:table|div|pre|svg|canvas|img)\b', choice_text, re.I):
			scroll_attributes = ' tabindex="0" role="group" aria-label="Answer content"'
		html_text += f'<div class="qti-choice-content"{scroll_attributes}>{choice_text}</div>'
		html_text += '<div class="qti-order-actions">'
		for direction, label, relative in [('up', 'Move up', 'earlier'), ('down', 'Move down', 'later')]:
			disabled = (direction == 'up' and display_idx == 1)
			disabled = disabled or (direction == 'down' and display_idx == len(choices))
			disabled_attr = ' disabled' if disabled else ''
			html_text += f'<button type="button" class="qti-order-move" data-direction="{direction}" '
			html_text += f'aria-label="Move item {display_idx} {relative}"{disabled_attr}>{label}</button>'
		html_text += '</div></li>\n'
	html_text += '</ol>\n<div class="qti-sr-only" role="status" aria-live="polite" aria-atomic="true"></div>\n'
	return html_text

#==============
def generate_core_html(crc16_text: str, question_text: str, ordered_answers_list: list) -> str:
	html_text = f'<div id="question_html_{crc16_text}">\n'
	html_text += html_functions.format_question_text(crc16_text, question_text)
	html_text += generate_choices_list(crc16_text, ordered_answers_list)
	html_text += html_functions.add_check_answer_button(crc16_text)
	html_text += html_functions.add_reset_game_button(crc16_text)
	html_text += html_functions.add_result_div(crc16_text)
	html_text += '</div>'
	return html_text

#==============
def generate_html(
		item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list
		) -> str:
	raw_html = generate_core_html(crc16_text, question_text, ordered_answers_list)
	full_html = string_functions.format_html_lxml(raw_html)
	full_html += javascript_functions.add_reset_game_javascript(crc16_text)
	full_html += drag_controls.generate_javascript(crc16_text)
	full_html += order_controls.generate_javascript(crc16_text)
	full_html += generate_check_answers_js(crc16_text)
	return full_html
