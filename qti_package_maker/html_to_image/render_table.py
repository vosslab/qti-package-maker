"""Screenshot a table-cell drawing with headless Chromium."""

# Standard Library
import base64
import importlib.resources

# PIP3 modules
from playwright.sync_api import sync_playwright


WRAPPER_BODY_STYLE = (
	'margin:16px;background:#fff;'
	'font-family:"Atkinson Hyperlegible Next",sans-serif'
)
DEVICE_SCALE_FACTOR = 2
FONT_FILES = (
	("atkinson_hyperlegible_next_variable.ttf", "Atkinson Hyperlegible Next"),
	("atkinson_hyperlegible_mono_variable.ttf", "Atkinson Hyperlegible Mono"),
)


#============================================
def _font_face_css() -> str:
	"""Build embedded faces for the packaged fonts that are available."""
	font_faces = []
	for filename, family in FONT_FILES:
		try:
			font_bytes = importlib.resources.files("qti_package_maker").joinpath(
				"data", "fonts", filename).read_bytes()
		except OSError:
			continue
		encoded_font = base64.b64encode(font_bytes).decode("ascii")
		font_face = (
			"@font-face{"
			f'font-family:"{family}";'
			f"src:url(data:font/ttf;base64,{encoded_font}) format('truetype');"
			"font-weight:200 800;"
			"font-style:normal;"
			"}"
		)
		font_faces.append(font_face)
	css = "\n".join(font_faces)
	return css


TABLE_FONT_MAPPING_SCRIPT = """
() => {
	for (const element of document.querySelectorAll("table, table *")) {
		const family = getComputedStyle(element).fontFamily.trim().toLowerCase();
		if (family === "monospace") {
			element.style.setProperty(
				"font-family", '"Atkinson Hyperlegible Mono", monospace', "important");
		} else if (family === "sans-serif") {
			element.style.setProperty(
				"font-family", '"Atkinson Hyperlegible Next", sans-serif', "important");
		}
	}
}
"""


#============================================
class TableRenderer:
	"""Hold one Chromium browser for a whole bank convert."""

	def __init__(self) -> None:
		self._playwright = None
		self._browser = None
		self._context = None
		self._font_face_css = ""

	#============================================
	def __enter__(self) -> "TableRenderer":
		self._playwright = sync_playwright().start()
		self._browser = self._playwright.chromium.launch()
		self._context = self._browser.new_context(device_scale_factor=DEVICE_SCALE_FACTOR)
		self._font_face_css = _font_face_css()
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
		font_styles = ""
		if self._font_face_css:
			font_styles = "<style>" + self._font_face_css + "</style>"
		html_doc = (
			"<html><head>" + font_styles + "</head><body style='"
			+ WRAPPER_BODY_STYLE
			+ "'>"
			+ table_html
			+ "</body></html>"
		)
		page = self._context.new_page()
		page.set_content(html_doc)
		page.evaluate(TABLE_FONT_MAPPING_SCRIPT)
		page.evaluate("async () => { await document.fonts.ready; }")
		locator = page.locator("table").first
		png_bytes = locator.screenshot(type="png")
		page.close()
		return png_bytes
