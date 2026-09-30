"""Run selftest control journeys: source source_me.sh && python3 <this file>.

Failure means drag support or its shared state has regressed. Repair the failing
interaction before accepting an ORDER/MATCH UI change. Browser checks run outside pytest.
"""

# Standard Library
import argparse
import json
from pathlib import Path

# Third-party libraries
from playwright.sync_api import BrowserType, Error, Locator, Page, sync_playwright

# Local libraries
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.html_selftest import write_item


#==============
def build_page() -> tuple[str, list[str]]:
	"""Render real items together so question isolation is part of the journey."""
	items = [
		item_types.ORDER('Arrange stages.', ['First', '<b>Middle</b>', 'Last']),
		item_types.MATCH('Match concepts.', ['Prompt one', 'Prompt two'],
			['<b>Alpha is a long formatted answer that remains in the bank</b>', 'A "quote"', 'Distractor']),
		item_types.MATCH('Match other concepts.', ['Other one', 'Other two'],
			['Other alpha', 'Other beta']),
	]
	fragments = [getattr(write_item, item.item_type)(item) for item in items]
	html = '<!doctype html><html><head><meta charset="utf-8">'
	html += '<meta name="viewport" content="width=device-width,initial-scale=1">'
	html += '</head><body style="margin:16px;font-family:Arial">'
	html += ''.join(fragments) + '</body></html>'
	return html, [item.item_crc16 for item in items]


#==============
def values(rows: Locator) -> list[str]:
	return rows.evaluate_all('(rows) => rows.map(row => row.dataset.value)')


#==============
def drag(source: Locator, target: Locator, after: bool = False) -> None:
	"""Use real mouse input, including the target half for ORDER insertion."""
	bounds = target.bounding_box()
	source_bounds = source.bounding_box()
	assert bounds is not None and source_bounds is not None
	source.drag_to(target, source_position={'x': min(80, source_bounds['width'] / 2), 'y': 18},
		target_position={'x': min(80, bounds['width'] / 2),
			'y': bounds['height'] - 8 if after else 8})


#==============
def verify_desktop(page: Page, html: str, crcs: list[str], output: Path) -> None:
	errors: list[str] = []
	def capture_error(error: Error) -> None:
		errors.append(str(error))
	page.on('pageerror', capture_error)
	page.set_content(html)
	page.evaluate("""() => {
		window.nativeDrops = [];
		document.addEventListener('drop', event => {
			window.nativeDrops.push({trusted: event.isTrusted,
				value: event.dataTransfer.getData('text/plain')});
		});
	}""")
	order = page.locator('#question_html_' + crcs[0])
	rows = order.locator('.qti-order-row')
	initial = values(rows)
	first = rows.first
	first_token = first.get_attribute('data-value')
	order.locator('.qti-btn:not(.qti-btn-reset)').click()
	drag(first, rows.last, after=True)
	assert values(rows) == initial[1:] + initial[:1], 'ORDER downward drag failed'
	assert order.locator('.qti-feedback-result').inner_text() == ''
	assert order.locator('.feedback').all_inner_texts() == ['', '', '']
	assert rows.last.get_attribute('data-value') == first_token
	drag(rows.last, rows.first)
	assert values(rows) == initial, 'ORDER upward drag failed'
	assert rows.evaluate_all('(rs) => rs.map(r => r.querySelector("strong").textContent)') == ['1', '2', '3']
	# Both halves of a row must allow positioning without replacing row content.
	for index in range(3):
		token = crcs[0] + '_' + str(index + 1).zfill(3)
		source = order.locator('.qti-order-row[data-value="' + token + '"]')
		if rows.nth(index).get_attribute('data-value') != token:
			drag(source, rows.nth(index))
	order.locator('.qti-btn:not(.qti-btn-reset)').click()
	assert order.locator('.qti-feedback-result').inner_text() == 'Correct positions: 3 of 3'
	assert order.locator('.qti-btn:not(.qti-btn-reset)').is_enabled()
	order.locator('.qti-btn:not(.qti-btn-reset)').click()
	assert order.locator('.qti-feedback-result').inner_text() == 'Correct positions: 3 of 3'
	assert order.locator('.qti-choice-content b').inner_text() == 'Middle'
	drag(rows.first, rows.last, after=True)
	assert order.locator('.qti-btn:not(.qti-btn-reset)').is_enabled()
	order.locator('.qti-btn-reset').click()
	assert values(rows) == initial, 'ORDER reset lost original shuffle'
	# The added keyboard path must continue using the same reordered nodes.
	token = rows.first.get_attribute('data-value')
	rows.first.locator('[data-direction=down]').press('ArrowDown')
	assert rows.nth(1).get_attribute('data-value') == token
	order.locator('.qti-btn-reset').click()

	match = page.locator('#question_html_' + crcs[1])
	other = page.locator('#question_html_' + crcs[2])
	slots = match.locator('.qti-match-slot')
	alpha = match.locator('.qti-match-choice[data-value="' + crcs[1] + '_001"]')
	quote = match.locator('.qti-match-choice[data-value="' + crcs[1] + '_002"]')
	extra = match.locator('.qti-match-choice[data-value="' + crcs[1] + '_003"]')
	reset = match.get_by_role('button', name='Reset', exact=True)
	assert reset.count() == 1 and reset.is_visible() and reset.is_enabled()
	slot_size = slots.first.evaluate('(slot) => [slot.offsetWidth, slot.offsetHeight]')
	drag(extra, slots.first)
	match.locator('.qti-btn:not(.qti-btn-reset)').click()
	assert match.locator('.qti-feedback-result').inner_text() == 'Total Score: 0 out of 2'
	assert extra.is_enabled()
	assert extra.get_attribute('draggable') == 'true'
	drag(alpha, slots.first)
	full_text = alpha.inner_text().strip()
	assert slots.first.inner_text() == full_text, 'CSS truncation must retain the full answer text'
	assert slots.first.evaluate('(slot) => slot.scrollWidth > slot.clientWidth')
	assert slots.first.evaluate('(slot) => getComputedStyle(slot).textOverflow') == 'ellipsis'
	assert slots.first.get_attribute('title') == full_text
	assert full_text in slots.first.get_attribute('aria-label')
	assert alpha.locator('b').inner_text() == 'Alpha is a long formatted answer that remains in the bank'
	assert slots.first.evaluate('(slot) => [slot.offsetWidth, slot.offsetHeight]') == slot_size
	assert slots.last.evaluate('(slot) => [slot.offsetWidth, slot.offsetHeight]') == slot_size
	assert extra.is_enabled(), 'Replacing a match did not free the previous choice'
	assert match.locator('.qti-feedback-result').inner_text() == ''
	drag(quote, slots.last)
	match.locator('.qti-btn:not(.qti-btn-reset)').click()
	assert match.locator('.qti-feedback-result').inner_text() == 'Total Score: 2 out of 2'
	assert match.locator('.qti-btn:not(.qti-btn-reset)').is_enabled()
	match.locator('.qti-btn:not(.qti-btn-reset)').click()
	assert match.locator('.qti-feedback-result').inner_text() == 'Total Score: 2 out of 2'
	reset.click()
	assert match.locator('.qti-match-slot[data-value]').count() == 0
	assert slots.first.get_attribute('title') is None
	assert match.locator('.qti-match-choice:disabled').count() == 0
	assert alpha.is_enabled()
	assert alpha.get_attribute('draggable') == 'true'
	assert match.locator('.qti-btn:not(.qti-btn-reset)').is_enabled()
	drag(alpha, slots.first)
	match.locator('.qti-btn-reset').click()
	assert match.locator('.qti-match-choice:disabled').count() == 0
	assert match.locator('.qti-match-slot[data-value]').count() == 0
	assert reset.is_visible() and reset.is_enabled()
	# A real drag across question boundaries must leave both questions untouched.
	drag(alpha, other.locator('.qti-match-slot').first)
	assert other.locator('.qti-match-slot[data-value]').count() == 0
	assert alpha.is_enabled()
	drag(alpha, slots.first)
	assert slots.first.get_attribute('data-value') == crcs[1] + '_001'
	# Cancel a drag by dropping outside the controls.
	quote.drag_to(page.locator('body'), target_position={'x': 5, 'y': 5})
	assert quote.is_enabled()
	assert match.locator('.qti-dragging, .qti-drop-target').count() == 0
	match.locator('.qti-btn-reset').click()
	quote.press('Space')
	assert quote.get_attribute('aria-pressed') == 'true'
	quote.press('Escape')
	assert quote.get_attribute('aria-pressed') == 'false'
	alpha.press('Enter')
	slots.first.press('Enter')
	assert slots.first.get_attribute('data-value') == crcs[1] + '_001'
	quote.press('Space')
	assert quote.get_attribute('aria-pressed') == 'true'
	match.locator('.qti-btn-reset').click()
	assert quote.get_attribute('aria-pressed') == 'false'
	verify_match_letters(match, other)
	drops = page.evaluate('window.nativeDrops')
	assert drops and all(drop['trusted'] and drop['value'] for drop in drops)
	assert not errors, errors
	assert page.locator('.qti-dragging, .qti-drop-target').count() == 0
	page.evaluate('window.getSelection().removeAllRanges()')
	page.screenshot(path=str(output / 'desktop-light.png'), full_page=True)
	page.emulate_media(color_scheme='dark')
	page.locator('body').evaluate("(body) => { body.style.background = '#202020'; body.style.color = '#eee'; }")
	page.screenshot(path=str(output / 'desktop-dark.png'), full_page=True)
	for width in [320, 390, 768, 1100]:
		page.set_viewport_size({'width': width, 'height': 1300})
		assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
	print(f'{output.name}: native ORDER/MATCH drag, grading, recovery, keyboard, isolation passed')


#==============
def verify_match_letters(match: Locator, other: Locator) -> None:
	"""Letters move every prior placement; drag/click allow independent duplicate guesses."""
	slots = match.locator('.qti-match-slot')
	choice = match.locator('.qti-match-choice').first
	replacement = match.locator('.qti-match-choice').nth(1)
	token = choice.get_attribute('data-value')
	letter = choice.get_attribute('data-letter')
	other_values = values(other.locator('.qti-match-slot'))
	# Both input paths can reuse an already assigned bank choice.
	drag(choice, slots.first)
	drag(choice, slots.last)
	assert values(slots) == [token, token]
	match.locator('.qti-btn-reset').click()
	for slot in [slots.first, slots.last]:
		choice.click()
		slot.click()
	assert values(slots) == [token, token]
	match.locator('.qti-btn:not(.qti-btn-reset)').click()
	correct = sum(slot.get_attribute('data-correct') == token for slot in [slots.first, slots.last])
	assert match.locator('.qti-feedback-result').inner_text() == f'Total Score: {correct} out of 2'
	slots.last.press(letter.lower())
	assert values(slots) == [None, token]
	assert 'moved from prompt 1 to prompt 2' in match.locator('[role=status]').inner_text()
	assert slots.first.get_attribute('title') is None
	assert match.locator('.qti-feedback-result').inner_text() == ''
	assert match.locator('.feedback').all_inner_texts() == ['', '']
	assert slots.last.evaluate('(slot) => slot === document.activeElement')
	# A move replaces the destination's old answer and keeps both choices available.
	replacement.click()
	slots.first.click()
	slots.first.press(letter.upper())
	assert values(slots) == [token, None]
	assert 'Replaced ' + replacement.get_attribute('data-letter') in match.locator('[role=status]').inner_text()
	assert choice.is_enabled() and replacement.is_enabled()
	assert choice.get_attribute('draggable') == 'true'
	# Browser shortcuts and letters outside answer slots must not change assignments.
	slots.last.press('Control+' + letter)
	slots.last.press('Meta+' + letter)
	slots.last.press('Alt+' + letter)
	slots.last.press('z')
	slots.last.dispatch_event('keydown', {'key': letter, 'isComposing': True})
	choice.press(letter)
	assert values(slots) == [token, None]
	assert values(other.locator('.qti-match-slot')) == other_values
	match.locator('.qti-btn-reset').click()
	assert values(slots) == [None, None]
	assert match.locator('.qti-match-choice[aria-pressed=true]').count() == 0


#==============
def verify_match_layout(page: Page, output: Path) -> None:
	"""Content and container bounds must survive long prompts, assignment, and grading."""
	items = [
		item_types.MATCH('Short prompts.', ['Primary', 'Secondary', 'Tertiary'],
			['i' * 150, 'W' * 150, '<b>Third description</b>']),
		item_types.MATCH('Long prompts.', ['A long prompt with explanatory words. ' * 8, 'W' * 150],
			['First description', 'Second description']),
		item_types.MATCH('Rich prompts.',
			['<div style="width:1200px">A wide authored diagram</div>',
				'<table style="width:1200px"><tr><td>Wide authored table</td></tr></table>'],
			['Diagram', 'Table']),
	]
	page.emulate_media(color_scheme='light')
	fragments = ''.join(write_item.MATCH(item) for item in items)
	page.set_content('<!doctype html><html><body style="margin:16px;font-family:Arial">'
		+ '<main>' + fragments + '</main></body></html>')
	main = page.locator('main')
	for width in [288, 390, 430, 640, 1000]:
		main.evaluate('(main, width) => main.style.width = width + "px"', width)
		for item in items:
			question = page.locator('#question_html_' + item.item_crc16)
			table = question.locator('.qti-match-table')
			slot = question.locator('.qti-match-slot').first
			bounds = table.bounding_box()
			container = question.bounding_box()
			assert bounds['width'] <= container['width'] + 1, 'MATCH table escaped its container'
			cell = question.locator('.qti-match-answer').first.bounding_box()
			slot_bounds = slot.bounding_box()
			assert abs(slot_bounds['width'] - cell['width']) <= 2, 'Slot leaves wasted cell width'
			assert abs(slot_bounds['height'] - cell['height']) <= 2, 'Slot leaves wasted cell height'
			feedback = question.locator('.feedback').first.bounding_box()
			assert feedback['width'] >= feedback['height'], 'Feedback marks must not be portrait'
			check_button = question.get_by_role('button', name='Check Answer', exact=True)
			reset_button = question.get_by_role('button', name='Reset', exact=True)
			check = check_button.bounding_box()
			reset = reset_button.bounding_box()
			bank = question.locator('.qti-match-bank').bounding_box()
			assert check_button.evaluate('(button) => button.offsetHeight') >= 44
			assert reset_button.evaluate('(button) => button.offsetHeight') >= 44
			assert abs(check['y'] - reset['y']) <= 1, 'Buttons must stay on the same row'
			assert check['y'] >= bounds['y'] + bounds['height']
			assert check['y'] + check['height'] <= bank['y']
			if width > 420:
				assert question.locator('.qti-match-table thead').is_visible()
			else:
				assert not question.locator('.qti-match-table thead').is_visible()
		assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
		page.screenshot(path=str(output / f'layout-{width}.png'), full_page=True)
	# Short labels must not inherit the width needed by a long description.
	short = page.locator('#question_html_' + items[0].item_crc16)
	short_table = short.locator('.qti-match-table')
	short_size = short_table.bounding_box()
	long_table = page.locator('#question_html_' + items[1].item_crc16 + ' .qti-match-table')
	assert short_size['width'] < long_table.bounding_box()['width']
	assert long_table.bounding_box()['width'] < main.bounding_box()['width']
	choice = short.locator('.qti-match-choice[data-value="' + items[0].item_crc16 + '_001"]')
	slot = short.locator('.qti-match-slot').first
	slot.press(choice.get_attribute('data-letter'))
	short.get_by_role('button', name='Check Answer', exact=True).click()
	assert short_table.bounding_box() == short_size, 'Answer text or grading changed table dimensions'
	assert slot.evaluate('(slot) => slot.scrollWidth > slot.clientWidth')
	assert short.locator('.qti-game-actions .qti-feedback-result').is_visible()
	# Moving a repeated guess must clear all previous copies, not only the first one.
	slots = short.locator('.qti-match-slot')
	for index in range(slots.count()):
		choice.click()
		slots.nth(index).click()
	slots.last.press(choice.get_attribute('data-letter'))
	assert values(slots) == [None, None, choice.get_attribute('data-value')]
	assert 'prompt 1, 2 to prompt 3' in short.locator('[role=status]').inner_text()
	print(f'{output.name}: bounded MATCH layout, responsive slots, controls and score passed')


#==============
def verify_touch(browser_type: BrowserType, html: str, crcs: list[str]) -> None:
	with browser_type.launch() as browser:
		context = browser.new_context(has_touch=True, viewport={'width': 390, 'height': 844})
		page = context.new_page()
		page.set_content(html)
		match = page.locator('#question_html_' + crcs[1])
		for index in range(2):
			token = crcs[1] + '_' + str(index + 1).zfill(3)
			match.locator('.qti-match-choice[data-value="' + token + '"]').tap()
			match.locator('.qti-match-slot').nth(index).tap()
		match.locator('.qti-btn:not(.qti-btn-reset)').tap()
		assert match.locator('.qti-feedback-result').inner_text() == 'Total Score: 2 out of 2'
		match.locator('.qti-btn-reset').tap()
		assert match.locator('.qti-match-slot[data-value]').count() == 0
		order = page.locator('#question_html_' + crcs[0])
		initial = values(order.locator('.qti-order-row'))
		order.locator('.qti-order-row').first.locator('[data-direction=down]').tap()
		assert values(order.locator('.qti-order-row'))[1] == initial[0]
		order.locator('.qti-btn-reset').tap()
		assert values(order.locator('.qti-order-row')) == initial
		context.close()
	print(f'{browser_type.name}: touch alternatives passed')


#==============
def verify_check_buttons(page: Page, output: Path) -> None:
	"""Every question type must allow a correct answer to be checked again and revised."""
	items = [
		item_types.MC('Choose blue.', ['Blue', 'Red'], 'Blue'),
		item_types.MA('Choose two colors.', ['Blue', 'Red', 'Cat'], ['Blue', 'Red']),
		item_types.FIB('Name the animal.', ['cat']),
		item_types.NUM('Two plus two?', 4, 0),
		item_types.MULTI_FIB('Name an [animal].', {'animal': ['cat']}),
	]
	fragments = ''.join(getattr(write_item, item.item_type)(item) for item in items)
	page.set_content('<!doctype html><html><body style="margin:16px;font-family:Arial">'
		+ fragments + '</body></html>')
	for item in items:
		question = page.locator('#question_html_' + item.item_crc16)
		check = question.get_by_role('button', name='Check Answer', exact=True)
		result = question.locator('.qti-feedback-result')
		assert check.evaluate('(button) => button.offsetHeight') >= 44
		if item.item_type in ['MC', 'MA']:
			for option in question.locator('input[data-correct=true]').all():
				option.check()
		else:
			question.locator('input').fill('4' if item.item_type == 'NUM' else 'cat')
		check.click()
		assert result.inner_text() == 'CORRECT'
		assert check.is_enabled()
		check.press('Enter')
		assert result.inner_text() == 'CORRECT'
		assert check.is_enabled()
		if item.item_type == 'MC':
			question.locator('input[data-correct=false]').check()
		elif item.item_type == 'MA':
			question.get_by_role('button', name='Clear Selection', exact=True).click()
			assert result.inner_text() == ''
			question.locator('input[data-correct=false]').check()
		else:
			question.locator('input').fill('10' if item.item_type == 'NUM' else 'dog')
		check.click()
		assert result.inner_text() != 'CORRECT'
		assert 'qti-feedback-error' in result.get_attribute('class')
	check = page.get_by_role('button', name='Check Answer', exact=True).first
	verify_button_press(page, check)
	page.screenshot(path=str(output / 'check-buttons.png'), full_page=True)
	print(f'{output.name}: MC/MA/FIB/NUM/MULTI_FIB rechecking and button press feedback passed')


#==============
def verify_button_press(page: Page, button: Locator) -> None:
	"""Mouse/Space/Enter feedback must not shift layout or stick; honor reduced motion."""
	page.emulate_media(reduced_motion='no-preference')
	button.hover()
	element = button.element_handle()
	page.wait_for_function('(b) => getComputedStyle(b).transform === "none"', arg=element)
	layout_width = button.evaluate('(b) => b.offsetWidth')
	for method in ['mouse', 'Space', 'Enter']:
		button.focus()
		if method == 'mouse':
			page.mouse.down()
		else:
			page.keyboard.down(method)
		page.wait_for_function('(b) => b.getBoundingClientRect().width < b.offsetWidth * 0.99',
			arg=element)
		assert button.evaluate('(b) => b.offsetWidth') == layout_width
		if method == 'mouse':
			page.mouse.up()
		else:
			page.keyboard.up(method)
		page.wait_for_function('(b) => getComputedStyle(b).transform === "none"', arg=element)
	button.focus()
	page.keyboard.down('Space')
	page.locator('input').first.focus()
	page.keyboard.up('Space')
	page.wait_for_function('(b) => getComputedStyle(b).transform === "none"', arg=element)
	page.emulate_media(reduced_motion='reduce')
	button.hover()
	page.mouse.down()
	assert button.evaluate('(b) => getComputedStyle(b).transform') == 'none'
	assert button.evaluate('(b) => getComputedStyle(b).filter') != 'none'
	page.mouse.up()
	page.emulate_media(reduced_motion='no-preference')


#==============
def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--browser', choices=['firefox', 'chromium', 'webkit', 'all'], default='all')
	parser.add_argument('--output-dir', type=Path, default=Path('output_smoke/drag-drop'))
	args = parser.parse_args()
	args.output_dir.mkdir(parents=True, exist_ok=True)
	html, crcs = build_page()
	(args.output_dir / 'controls.html').write_text(html, encoding='ascii')
	results = []
	with sync_playwright() as playwright:
		names = ['firefox', 'chromium', 'webkit'] if args.browser == 'all' else [args.browser]
		for name in names:
			browser_type = getattr(playwright, name)
			output = args.output_dir / name
			output.mkdir(exist_ok=True)
			with browser_type.launch() as browser:
				page = browser.new_page(viewport={'width': 1100, 'height': 1300})
				verify_desktop(page, html, crcs, output)
				verify_match_layout(page, output)
				verify_check_buttons(page, output)
			if name != 'firefox':
				verify_touch(browser_type, html, crcs)
			results.append({'browser': name, 'desktop_drag': 'passed',
				'touch_alternative': 'passed' if name != 'firefox' else 'not checked'})
	(args.output_dir / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
	main()
