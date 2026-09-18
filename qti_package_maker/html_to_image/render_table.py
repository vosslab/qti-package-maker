"""Screenshot a table-cell drawing with headless Chromium."""

# PIP3 modules
from playwright.sync_api import sync_playwright


WRAPPER_BODY_STYLE = "margin:16px;background:#fff;font-family:sans-serif"
DEVICE_SCALE_FACTOR = 2


#============================================
class TableRenderer:
	"""Hold one Chromium browser for a whole bank convert."""

	def __init__(self) -> None:
		self._playwright = None
		self._browser = None
		self._context = None

	#============================================
	def __enter__(self) -> "TableRenderer":
		self._playwright = sync_playwright().start()
		self._browser = self._playwright.chromium.launch()
		self._context = self._browser.new_context(device_scale_factor=DEVICE_SCALE_FACTOR)
		return self

	#============================================
	def __exit__(
				self,
				exc_type: type | None,
				exc: BaseException | None,
				tb: object) -> None:
		if self._context is not None:
			self._context.close()
		if self._browser is not None:
			self._browser.close()
		if self._playwright is not None:
			self._playwright.stop()

	#============================================
	def render_table_png(self, table_html: str) -> bytes:
		"""
		Screenshot one table fragment.

		Args:
			table_html: The selected table's HTML.

		Returns:
			PNG bytes of the table element.
		"""
		html_doc = (
			"<html><body style='"
			+ WRAPPER_BODY_STYLE
			+ "'>"
			+ table_html
			+ "</body></html>"
		)
		page = self._context.new_page()
		page.set_content(html_doc)
		locator = page.locator("table").first
		png_bytes = locator.screenshot(type="png")
		page.close()
		return png_bytes


#============================================
def render_table_png(table_html: str) -> bytes:
	"""
	Screenshot one table fragment with a short-lived browser.

	Args:
		table_html: The selected table's HTML.

	Returns:
		PNG bytes of the table element.
	"""
	with TableRenderer() as renderer:
		png_bytes = renderer.render_table_png(table_html)
	return png_bytes
