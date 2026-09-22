"""Select HTML fragments that lose meaning when Blackboard Ultra strips styles.

A table is a drawing when any descendant td/th carries a bgcolor attribute, or a
style containing border, background, or exact padding: 0. Those are the
attributes Ultra strips that carry visual meaning. A data table whose cells
carry no style, or only text-align, is left alone. padding: 0 2px is not
exact padding: 0 and does not select.

A canvas is an RDKit drawing when a following script sibling (of the canvas, or
of a wrapping parent) contains RDKitModule. The record carries SMILES, legend,
explicitMethyl, width, and height so a later renderer can redraw offline.
"""

# Standard Library
import re
import dataclasses

# PIP3 modules
import lxml.html


# Exact padding: 0 (optional px), not multi-value padding: 0 2px.
_PADDING_ZERO_RE = re.compile(r"padding:\s*0(?:px)?\s*(;|$)", re.IGNORECASE)
_PADDING_MULTI_RE = re.compile(r"padding:\s*0(?:px)?\s+\S", re.IGNORECASE)
_SMILES_RE = re.compile(r'smiles="([^"]*)"')
_LEGEND_RE = re.compile(r'mdetails\["legend"\]="([^"]*)"')
_EXPLICIT_METHYL_RE = re.compile(r'mdetails\["explicitMethyl"\]\s*=\s*true')


#============================================
@dataclasses.dataclass
class CanvasSource:
	"""SMILES and draw options extracted from an RDKit JavaScript canvas."""

	smiles: str
	legend: str | None
	explicit_methyl: bool
	width: int
	height: int


#============================================
def parse_html_fragment(html: str) -> lxml.html.HtmlElement:
	"""
	Parse an HTML snippet into a wrapper element.

	Args:
		html: Item HTML that may contain multiple top-level nodes.

	Returns:
		A wrapper HtmlElement whose children are the snippet's top-level nodes.
	"""
	root = lxml.html.fragment_fromstring(html, create_parent="div")
	return root


#============================================
def serialize_fragment(root: lxml.html.HtmlElement) -> str:
	"""
	Serialize a wrapper element back to an HTML snippet.

	Args:
		root: Wrapper produced by parse_html_fragment.

	Returns:
		The inner HTML of the wrapper, including text nodes.
	"""
	# lxml decodes &nbsp; to U+00A0. Item CRC requires ASCII, so re-escape
	# text nodes and serialized markup the same way blackboard ZIP repair does.
	parts = []
	if root.text:
		parts.append(root.text.encode("ascii", "xmlcharrefreplace").decode("ascii"))
	for child in root:
		child_bytes = lxml.html.tostring(
			child, encoding="ascii", method="xml", with_tail=False)
		parts.append(child_bytes.decode("ascii"))
		if child.tail:
			parts.append(child.tail.encode("ascii", "xmlcharrefreplace").decode("ascii"))
	html = "".join(parts)
	return html


#============================================
def outer_html(element: lxml.html.HtmlElement) -> str:
	"""
	Serialize one element without its tail text.

	Args:
		element: The element to serialize.

	Returns:
		The element's HTML string.
	"""
	html = lxml.html.tostring(element, encoding="unicode", with_tail=False, method="xml")
	return html


#============================================
def _style_has_drawing_attr(style: str) -> bool:
	"""
	Return True when a cell style carries a stripped drawing attribute.

	Args:
		style: The cell's style attribute value.

	Returns:
		True when border, background, or exact padding: 0 is present.
	"""
	style_lower = style.lower()
	if "border" in style_lower or "background" in style_lower:
		return True
	if _PADDING_MULTI_RE.search(style):
		return False
	if _PADDING_ZERO_RE.search(style):
		return True
	return False


#============================================
def is_drawing_table(table_el: lxml.html.HtmlElement) -> bool:
	"""
	Return True when a table uses Ultra-stripped drawing attributes.

	Args:
		table_el: A table element.

	Returns:
		True when any descendant cell is a drawing cell.
	"""
	for cell in table_el.xpath(".//td|.//th"):
		if cell.get("bgcolor") is not None:
			return True
		style = cell.get("style")
		if style and _style_has_drawing_attr(style):
			return True
	return False


#============================================
def iter_drawing_tables(root: lxml.html.HtmlElement) -> list:
	"""
	Return drawing tables under root in document order.

	Args:
		root: Parsed HTML wrapper.

	Returns:
		The matching table elements.
	"""
	tables = []
	for table_el in root.xpath(".//table"):
		if is_drawing_table(table_el):
			tables.append(table_el)
	return tables


#============================================
def find_table_fragments(html: str) -> list[str]:
	"""
	Return outer HTML of each drawing table in html.

	Args:
		html: Item HTML.

	Returns:
		One HTML string per selected table, in document order.
	"""
	root = parse_html_fragment(html)
	fragments = []
	for table_el in iter_drawing_tables(root):
		fragments.append(outer_html(table_el))
	return fragments


#============================================
def _is_rdkit_script(element: lxml.html.HtmlElement) -> bool:
	"""
	Return True when element is a script that loads RDKitModule.

	Args:
		element: A candidate following sibling.

	Returns:
		True when the sibling is an RDKit drawing script.
	"""
	if element.tag != "script":
		return False
	text = element.text_content()
	if "RDKitModule" not in text:
		return False
	return True


#============================================
def _following_rdkit_script(canvas_el: lxml.html.HtmlElement) -> lxml.html.HtmlElement | None:
	"""
	Find the RDKit script that follows a canvas.

	The generator wraps the canvas in a p, so the script is a sibling of the
	wrapper rather than of the canvas itself.

	Args:
		canvas_el: A canvas element.

	Returns:
		The matching script element, or None.
	"""
	sibling = canvas_el.getnext()
	while sibling is not None:
		if _is_rdkit_script(sibling):
			return sibling
		sibling = sibling.getnext()
	parent = canvas_el.getparent()
	if parent is None:
		return None
	sibling = parent.getnext()
	while sibling is not None:
		if _is_rdkit_script(sibling):
			return sibling
		sibling = sibling.getnext()
	return None


#============================================
def _canvas_source_from_elements(
			canvas_el: lxml.html.HtmlElement,
			script_el: lxml.html.HtmlElement) -> CanvasSource:
	"""
	Build a CanvasSource from a canvas and its RDKit script.

	Args:
		canvas_el: The canvas element.
		script_el: The following RDKit script.

	Returns:
		The extracted SMILES and draw options.

	Raises:
		ValueError: width, height, or SMILES is missing.
	"""
	width_text = canvas_el.get("width")
	height_text = canvas_el.get("height")
	if width_text is None or height_text is None:
		raise ValueError("RDKit canvas is missing width or height")
	script_text = script_el.text_content()
	smiles_match = _SMILES_RE.search(script_text)
	if smiles_match is None:
		raise ValueError("RDKit script is missing a SMILES literal")
	smiles = smiles_match.group(1)
	legend_match = _LEGEND_RE.search(script_text)
	legend = legend_match.group(1) if legend_match is not None else None
	explicit_methyl = _EXPLICIT_METHYL_RE.search(script_text) is not None
	source = CanvasSource(
		smiles=smiles,
		legend=legend,
		explicit_methyl=explicit_methyl,
		width=int(width_text),
		height=int(height_text),
	)
	return source


#============================================
def iter_canvas_targets(root: lxml.html.HtmlElement) -> list:
	"""
	Return (canvas, script, CanvasSource) triples in document order.

	Args:
		root: Parsed HTML wrapper.

	Returns:
		One triple per RDKit canvas.
	"""
	targets = []
	for canvas_el in root.xpath(".//canvas"):
		script_el = _following_rdkit_script(canvas_el)
		if script_el is None:
			continue
		source = _canvas_source_from_elements(canvas_el, script_el)
		targets.append((canvas_el, script_el, source))
	return targets


#============================================
def find_canvas_fragments(html: str) -> list[CanvasSource]:
	"""
	Return CanvasSource records for each RDKit canvas in html.

	Args:
		html: Item HTML.

	Returns:
		One CanvasSource per selected canvas, in document order.
	"""
	root = parse_html_fragment(html)
	sources = []
	for _canvas_el, _script_el, source in iter_canvas_targets(root):
		sources.append(source)
	return sources
