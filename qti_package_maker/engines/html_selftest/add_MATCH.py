# Standard Library
import html
import random

# Local libraries
from qti_package_maker.common import string_functions
from qti_package_maker.engines.html_selftest import html_functions
from qti_package_maker.engines.html_selftest import javascript_functions
from qti_package_maker.engines.html_selftest import match_controls
from qti_package_maker.engines.html_selftest import drag_controls

#==============
def generate_check_answers_js(crc16_text: str) -> str:
	js = javascript_functions.add_check_rows_javascript(crc16_text, 'MATCH')
	return js

#==============
def generate_prompts_table(crc16_text: str, prompts_list: list) -> str:
	"""Keep the familiar bordered prompt table with one answer slot per row."""
	table = '<table class="qti-match-table"><thead><tr>'
	table += '<th scope="col"><span class="qti-sr-only">Feedback</span></th>'
	table += '<th scope="col">Your Choice</th><th scope="col">Prompt</th></tr></thead><tbody>\n'
	for index, prompt_text in enumerate(prompts_list, start=1):
		token = f'{crc16_text}_{index:03d}'
		table += '<tr class="qti-match-row"><td class="feedback"></td>'
		table += '<td class="qti-match-answer">'
		table += f'<button type="button" class="qti-match-slot" data-correct="{token}" '
		table += f'data-prompt="{index}" aria-label="Assign a choice to prompt {index}" '
		table += f'aria-describedby="prompt_{crc16_text}_{index}">Drop Your Choice Here</button>'
		table += '</td>'
		table += f'<td class="qti-match-prompt" id="prompt_{crc16_text}_{index}">{index}. {prompt_text}</td></tr>\n'
	table += '</tbody></table>\n'
	return table

#==============
def generate_choices_list(crc16_text: str, choices_list: list) -> str:
	content = f'<ul id="choiceList_{crc16_text}" class="qti-match-bank" aria-label="Answer choices">\n'
	choices = list(enumerate(choices_list, start=1))
	random.shuffle(choices)
	for display_index, (original_index, choice_text) in enumerate(choices, start=1):
		letter = string_functions.number_to_letter(display_index)
		token = f'{crc16_text}_{original_index:03d}'
		palette_index = display_index % 5 + 1
		# ASVS 1.2.1: plain accessible names must be escaped as attributes.
		name = html.escape(string_functions.make_question_pretty(choice_text), quote=True)
		content += f'<li><button type="button" class="qti-match-choice qti-choice-{palette_index}" '
		content += f'data-value="{token}" draggable="true" aria-pressed="false" aria-label="Select {letter}. {name}">'
		content += f'<span class="qti-choice-content"><strong>{letter}.</strong> {choice_text}</span>'
		content += '</button></li>\n'
	content += '</ul>\n'
	return content

#==============
def generate_core_html(crc16_text: str, question_text: str, prompts_list: list, choices_list: list) -> str:
	content = f'<div id="question_html_{crc16_text}">\n'
	content += html_functions.format_question_text(crc16_text, question_text)
	content += generate_prompts_table(crc16_text, prompts_list)
	content += '<p class="qti-control-instructions">Drag a choice to its matching row, '
	content += 'or click a choice and then a row.</p>\n'
	content += generate_choices_list(crc16_text, choices_list)
	content += '<div class="qti-sr-only" role="status" aria-live="polite" '
	content += 'aria-atomic="true"></div>\n'
	content += html_functions.add_check_answer_button(crc16_text)
	content += html_functions.add_reset_game_button(crc16_text, 'Reset')
	content += html_functions.add_result_div(crc16_text)
	content += '</div>'
	return content

#==============
def generate_html(
		item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list
		) -> str:
	raw_html = generate_core_html(crc16_text, question_text, prompts_list, choices_list)
	content = string_functions.format_html_lxml(raw_html)
	content += javascript_functions.add_reset_game_javascript(crc16_text)
	content += drag_controls.generate_javascript(crc16_text)
	content += match_controls.generate_javascript(crc16_text)
	content += generate_check_answers_js(crc16_text)
	return content
