"""Run native selftest drag journeys: source source_me.sh && python3 <this file>.

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
	assert order.locator('.qti-btn:not(.qti-btn-reset)').is_disabled()
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
	assert extra.is_disabled()
	assert extra.get_attribute('draggable') == 'false'
	drag(alpha, slots.first)
	full_text = alpha.inner_text().strip()
	assert slots.first.inner_text() == full_text[:27] + '...', 'Assigned answer was not compact'
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
	assert match.locator('.qti-btn:not(.qti-btn-reset)').is_disabled()
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
	drops = page.evaluate('window.nativeDrops')
	assert drops and all(drop['trusted'] and drop['value'] for drop in drops)
	assert not errors, errors
	assert page.locator('.qti-dragging, .qti-drop-target').count() == 0
	page.screenshot(path=str(output / 'desktop-light.png'), full_page=True)
	page.emulate_media(color_scheme='dark')
	page.locator('body').evaluate("(body) => { body.style.background = '#202020'; body.style.color = '#eee'; }")
	page.screenshot(path=str(output / 'desktop-dark.png'), full_page=True)
	for width in [320, 390, 768, 1100]:
		page.set_viewport_size({'width': width, 'height': 1300})
		assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
	print(f'{output.name}: native ORDER/MATCH drag, grading, recovery, keyboard, isolation passed')


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
			if name != 'firefox':
				verify_touch(browser_type, html, crcs)
			results.append({'browser': name, 'desktop_drag': 'passed',
				'touch_alternative': 'passed' if name != 'firefox' else 'not checked'})
	(args.output_dir / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
	main()
