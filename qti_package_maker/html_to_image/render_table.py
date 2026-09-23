"""Screenshot a table-cell drawing with headless Chromium."""

# Standard Library
import base64
import importlib.resources

# PIP3 modules
import lxml.html
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
MATHML_TAGS = {"math", "mi", "mn", "mo", "mrow", "msub", "msup", "mfrac", "mfenced"}
MATHML_ATTRIBUTES = {
	"math": {"xmlns"},
	"mi": {"mathvariant"},
	"mo": {"stretchy"},
	"mfenced": set(),
}


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


#============================================
def _prepare_mathml_html(mathml_html: str) -> str:
	"""Validate the supported MathML subset and expand legacy mfenced markup."""
	root = lxml.html.fragment_fromstring(mathml_html, create_parent="div")
	if len(root) != 1 or root[0].tag != "math":
		raise ValueError("expected one MathML <math> element")
	math_el = root[0]
	for element in math_el.iter():
		if not isinstance(element.tag, str) or element.tag not in MATHML_TAGS:
			tag = element.tag if isinstance(element.tag, str) else "unknown"
			raise ValueError(f"unsupported MathML element <{tag}>")
		allowed_attributes = MATHML_ATTRIBUTES.get(element.tag, set())
		unknown_attributes = set(element.attrib) - allowed_attributes
		if unknown_attributes:
			raise ValueError(
				f"unsupported MathML attributes on <{element.tag}>: "
				f"{sorted(unknown_attributes)}")
		if element.tag == "mi" and element.get("mathvariant", "normal") != "normal":
			raise ValueError("unsupported MathML mathvariant")
		if element.tag == "mo" and element.get("stretchy", "true") != "true":
			raise ValueError("unsupported MathML stretchy value")
		if element is not math_el and element.tag == "math":
			raise ValueError("nested MathML <math> elements are unsupported")
		if element.tag in {"mi", "mn", "mo"}:
			if len(element) != 0 or element.text in {None, ""}:
				raise ValueError(f"MathML <{element.tag}> must contain text only")
		if element.tag in {"msub", "msup", "mfrac"} and len(element) != 2:
			raise ValueError(f"MathML <{element.tag}> must have two expressions")
		if element.tag == "mfenced" and len(element) != 1:
			raise ValueError("MathML <mfenced> must contain one expression")
		if element.tag == "mrow" and len(element) == 0:
			raise ValueError("MathML <mrow> must contain an expression")
	for fenced in math_el.xpath(".//mfenced"):
		parent = fenced.getparent()
		row = lxml.html.Element("mrow")
		row.text = fenced.text
		opening = lxml.html.Element("mo")
		opening.text = "("
		row.append(opening)
		row.append(fenced[0])
		closing = lxml.html.Element("mo")
		closing.text = ")"
		row.append(closing)
		row.tail = fenced.tail
		parent.replace(fenced, row)
	prepared = lxml.html.tostring(math_el, encoding="unicode", method="xml")
	return prepared


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

	#============================================
	def render_mathml_png(self, mathml_html: str) -> bytes:
		"""Render one supported MathML equation to a PNG without page scripts."""
		# ASVS V1.2.1, V1.3.2, and V2.2.1: pass only validated MathML markup
		# to Chromium; scripts, external resources, and arbitrary HTML are excluded.
		prepared_mathml = _prepare_mathml_html(mathml_html)
		font_styles = ""
		if self._font_face_css:
			font_styles = "<style>" + self._font_face_css + "</style>"
		equation_style = "<style>math { font-size: 1.2em; }</style>"
		html_doc = (
			"<html><head>" + font_styles + equation_style + "</head><body style='"
			+ WRAPPER_BODY_STYLE
			+ "'>"
			+ prepared_mathml
			+ "</body></html>"
		)
		page = self._context.new_page()
		page.set_content(html_doc)
		page.evaluate("async () => { await document.fonts.ready; }")
		png_bytes = page.locator("math").screenshot(type="png")
		page.close()
		return png_bytes
