"""Contract tests for lazy Chromium startup in the table renderer."""

# Standard Library
import base64

# PIP3 modules
import pytest

# local repo modules
from qti_package_maker.html_to_image import render_table
from qti_package_maker.html_to_image import selectors
from qti_package_maker.html_to_image import transform
from qti_package_maker.html_to_image.render_cache import RenderCache
from qti_package_maker.assessment_items.item_bank import ItemBank


PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGNkaPjPgA0wYRUdtBIALlIBjzTK6JgAAAAASUVORK5CYII="
)


#============================================
def test_table_renderer_context_does_not_start_browser(
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""Opening a renderer context without a table miss has no Playwright cost."""
	def fail_if_called() -> None:
		raise AssertionError("sync_playwright must stay lazy until a render is needed")

	monkeypatch.setattr(render_table, "sync_playwright", fail_if_called)
	with render_table.TableRenderer():
		pass


#============================================
def test_canvas_only_bank_does_not_start_table_browser(
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""Canvas conversion does not pay for Chromium when no table exists."""
	canvas = (
		'<canvas id="canvas_cc" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CCO";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'canvas=document.getElementById("canvas_cc");'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));'
		'</script>'
	)
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (canvas, ["ethanol", "water"], "ethanol"))

	def fail_if_called() -> None:
		raise AssertionError("canvas-only conversion must not start Playwright")

	monkeypatch.setattr(render_table, "sync_playwright", fail_if_called)
	monkeypatch.setattr(transform, "render_canvas_png", lambda source: PNG_BYTES)
	converted_bank = transform.convert_bank(bank)
	assert "<img" in list(converted_bank)[0].question_text
	converted_bank.cleanup()


#============================================
def test_cached_table_does_not_start_browser(
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""A cache hit avoids Chromium even when the source field contains a table."""
	table = '<table><tr><td style="border: 1px solid black">cached</td></tr></table>'
	root = selectors.parse_html_fragment(table)
	prepared = selectors.outer_html(selectors.iter_tables(root)[0])
	cache = RenderCache()
	cache.get_or_render(
		"table", prepared, lambda: PNG_BYTES, renderer=render_table.TableRenderer.render_table_png)
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (table, ["one", "two"], "one"))

	def fail_if_called() -> None:
		raise AssertionError("cached table conversion must not start Playwright")

	monkeypatch.setattr(render_table, "sync_playwright", fail_if_called)
	converted_bank = transform.convert_bank(bank, cache=cache)
	assert "<img" in list(converted_bank)[0].question_text
	converted_bank.cleanup()
