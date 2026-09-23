"""Select HTML fragments that lose meaning when Blackboard Ultra strips styles.

A table is a drawing when any descendant td/th carries a bgcolor attribute, or a
style containing border, background, or exact padding: 0. Those are the
attributes Ultra strips that carry visual meaning. A data table whose cells
carry no style, or only text-align, is left alone. padding: 0 2px is not
exact padding: 0 and does not select.

A canvas is an RDKit drawing when a following script sibling (of the canvas, or
of a wrapping parent) contains RDKitModule. The record carries SMILES, legend,
explicitMethyl, highlights, width, and height so a later renderer can redraw
offline. Only the supported static bptools forms are parsed; JavaScript is
never executed.
"""

# Standard Library
import dataclasses
import re

# PIP3 modules
import lxml.html


# Exact padding: 0 (optional px), not multi-value padding: 0 2px.
_PADDING_ZERO_RE = re.compile(r"padding:\s*0(?:px)?\s*(;|$)", re.IGNORECASE)
_PADDING_MULTI_RE = re.compile(r"padding:\s*0(?:px)?\s+\S", re.IGNORECASE)
_SMILES_RE = re.compile(r'\bsmiles\s*=\s*"([^"]*)"\s*;')
_LEGEND_RE = re.compile(
	r'mdetails\s*\[\s*"legend"\s*\]\s*=\s*"([^"\\\r\n]*)"\s*;')
_EXPLICIT_METHYL_RE = re.compile(
	r'mdetails\s*\[\s*"explicitMethyl"\s*\]\s*=\s*(true|false)\b')
_ATOMS_RE = re.compile(
	r'mdetails\s*\[\s*"atoms"\s*\]\s*=\s*(\[[^]]*\])')
_BONDS_RE = re.compile(
	r'mdetails\s*\[\s*"bonds"\s*\]\s*=\s*([^;]+)')
_HIGHLIGHT_COLOUR_RE = re.compile(
	r'mdetails\s*\[\s*"highlightColour"\s*\]\s*=\s*(\[[^]]*\])')
_MDETAILS_ASSIGNMENT_RE = re.compile(
	r'\bmdetails\s*\[\s*"([^"]+)"\s*\]\s*=')
_MDETAILS_MEMBER_ASSIGNMENT_RE = re.compile(
	r'\bmdetails\s*(?:\[[^]]+\]|\.\s*[A-Za-z_$][\w$]*)\s*=')
_MDETAILS_INIT_RE = re.compile(r'\bmdetails\s*=(?!=)\s*([^;]+)')
_DRAW_CALL_RE = re.compile(r'\.draw_to_canvas(?:_with_highlights)?\s*\(')
_GET_MOL_RE = re.compile(r'get_mol\s*\(\s*smiles\s*\)')
_INTEGER_LIST_RE = re.compile(r'\[\s*(?:[0-9]+\s*(?:,\s*[0-9]+\s*)*)?\]')
_INTEGER_ITEMS_RE = re.compile(r'[0-9]+(?:\s*,\s*[0-9]+)*')
_RGB_LIST_RE = re.compile(
	r'\[\s*([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*,'
	r'\s*([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*,'
	r'\s*([0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*\]')
_CANVAS_TARGET_RE = re.compile(r'getElementById\(\s*(["\'])([^"\']+)\1\s*\)')
_CANVAS_DIMENSION_LIMIT = 4096
_SMILES_LENGTH_LIMIT = 4096


#============================================
def _parse_integer_list(value: str, description: str) -> tuple[int, ...]:
	"""Parse a JavaScript integer-array literal without evaluating source."""
	if _INTEGER_LIST_RE.fullmatch(value) is None:
		raise ValueError(f"RDKit {description} must be an integer list")
	contents = value[1:-1].strip()
	if not contents:
		return ()
	if _INTEGER_ITEMS_RE.fullmatch(contents) is None:
		raise ValueError(f"RDKit {description} must be an integer list")
	values = tuple(int(item.strip()) for item in contents.split(','))
	return values


#============================================
@dataclasses.dataclass
class CanvasSource:
	"""SMILES and supported draw options extracted from an RDKit canvas."""

	smiles: str
	legend: str | None
	explicit_methyl: bool
	width: int
	height: int
	highlight_atoms: tuple[int, ...] = ()
	highlight_bonds: tuple[int, ...] = ()
	highlight_peptide_bonds: bool = False
	highlight_colour: tuple[float, float, float] | None = None


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
	if "RDKitModule" not in text and "initRDKitModule" not in text:
		return False
	return True


#============================================
def _script_canvas_id(script_el: lxml.html.HtmlElement) -> str | None:
	"""Return the literal canvas ID named by a drawing script, if present."""
	match = _CANVAS_TARGET_RE.search(script_el.text_content())
	if match is None:
		return None
	return match.group(2)


#============================================
def is_rdkit_loader_script(element: lxml.html.HtmlElement) -> bool:
	"""Return True for the known external RDKit.js loader emitted by bptools."""
	if element.tag != "script":
		return False
	source = element.get("src", "")
	return source == "https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js"


#============================================
def remove_rdkit_loader_scripts(root: lxml.html.HtmlElement) -> None:
	"""Remove recognized RDKit CDN loader scripts from a parsed HTML fragment."""
	for script_el in root.xpath(".//script"):
		if is_rdkit_loader_script(script_el):
			script_el.getparent().remove(script_el)


#============================================
def _following_rdkit_script(
			canvas_el: lxml.html.HtmlElement,
			root: lxml.html.HtmlElement) -> lxml.html.HtmlElement | None:
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
			target_id = _script_canvas_id(sibling)
			if target_id is None or target_id == canvas_el.get("id"):
				return sibling
		sibling = sibling.getnext()
	parent = canvas_el.getparent()
	if parent is None:
		return None
	sibling = parent.getnext()
	while sibling is not None:
		if _is_rdkit_script(sibling):
			target_id = _script_canvas_id(sibling)
			if target_id is None or target_id == canvas_el.get("id"):
				return sibling
		sibling = sibling.getnext()
	for script_el in root.xpath(".//script"):
		if (_is_rdkit_script(script_el)
				and _script_canvas_id(script_el) == canvas_el.get("id")):
			return script_el
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
	# ASVS V1.3.2, V1.3.3, and V2.2.1: parse static inputs only and bound
	# dimensions and SMILES before passing them to RDKit; never execute scripts.
	if len(_GET_MOL_RE.findall(script_text)) != 1:
		raise ValueError("RDKit script must call get_mol(smiles) exactly once")
	if len(_DRAW_CALL_RE.findall(script_text)) != 1:
		raise ValueError("RDKit script must contain one supported canvas draw call")
	smiles_matches = _SMILES_RE.findall(script_text)
	if len(smiles_matches) != 1:
		raise ValueError("RDKit script must define one static SMILES string")
	smiles = smiles_matches[0]
	if not smiles:
		raise ValueError("RDKit canvas SMILES must not be empty")
	if len(smiles) > _SMILES_LENGTH_LIMIT:
		raise ValueError("RDKit canvas SMILES exceeds the supported length")
	mdetails_initializers = _MDETAILS_INIT_RE.findall(script_text)
	if (len(mdetails_initializers) != 1
			or any(initializer.strip() != "{}" for initializer in mdetails_initializers)):
		raise ValueError("RDKit drawing options must use a static empty mdetails object")
	option_assignments = _MDETAILS_ASSIGNMENT_RE.findall(script_text)
	member_assignments = _MDETAILS_MEMBER_ASSIGNMENT_RE.findall(script_text)
	if len(option_assignments) != len(member_assignments):
		raise ValueError("RDKit drawing options must use static string keys")
	if len(option_assignments) != len(set(option_assignments)):
		raise ValueError("RDKit drawing options must not assign a key more than once")
	supported_details = {
		"legend", "explicitMethyl", "atoms", "bonds", "highlightColour"}
	for option_name in option_assignments:
		if option_name not in supported_details:
			raise ValueError(f"unsupported RDKit drawing option: {option_name}")
	legend_match = _LEGEND_RE.search(script_text)
	if "legend" in option_assignments and legend_match is None:
		raise ValueError("RDKit canvas legend must be a static string")
	legend = legend_match.group(1) if legend_match is not None else None
	explicit_methyl_match = _EXPLICIT_METHYL_RE.search(script_text)
	if "explicitMethyl" in option_assignments and explicit_methyl_match is None:
		raise ValueError("RDKit explicitMethyl must be a boolean")
	explicit_methyl = (
		explicit_methyl_match is not None
		and explicit_methyl_match.group(1) == "true")
	if not width_text.isascii() or not width_text.isdigit():
		raise ValueError("RDKit canvas width and height must be integers")
	if not height_text.isascii() or not height_text.isdigit():
		raise ValueError("RDKit canvas width and height must be integers")
	if len(width_text) > 4 or len(height_text) > 4:
		raise ValueError("RDKit canvas dimensions exceed the supported limit")
	width = int(width_text)
	height = int(height_text)
	if (width <= 0 or height <= 0
			or width > _CANVAS_DIMENSION_LIMIT
			or height > _CANVAS_DIMENSION_LIMIT):
		raise ValueError(
			"RDKit canvas dimensions must be positive and within the supported limit "
			f"({width}x{height})")
	atom_match = _ATOMS_RE.search(script_text)
	if "atoms" in option_assignments and atom_match is None:
		raise ValueError("RDKit atom highlights must be a static integer list")
	if atom_match is None:
		highlight_atoms = ()
	else:
		highlight_atoms = _parse_integer_list(atom_match.group(1), "atom highlights")
	bond_match = _BONDS_RE.search(script_text)
	if "bonds" in option_assignments and bond_match is None:
		raise ValueError("RDKit bond highlights must be a static list or peptide bonds")
	highlight_peptide_bonds = False
	highlight_bonds: tuple[int, ...] = ()
	if bond_match is not None:
		bond_expression = bond_match.group(1).strip()
		if bond_expression != "getPeptideBonds(mol)":
			highlight_bonds = _parse_integer_list(
				bond_expression, "bond highlights")
		else:
			highlight_peptide_bonds = True
	colour_match = _HIGHLIGHT_COLOUR_RE.search(script_text)
	if "highlightColour" in option_assignments and colour_match is None:
		raise ValueError("RDKit highlight colour must be a static RGB list")
	highlight_colour = None
	if colour_match is not None:
		colour_match_values = _RGB_LIST_RE.fullmatch(colour_match.group(1))
		if colour_match_values is None:
			raise ValueError("RDKit highlight colour must be an RGB list")
		colour_values = tuple(float(value) for value in colour_match_values.groups())
		if any(not 0 <= value <= 1 for value in colour_values):
			raise ValueError("RDKit highlight colour components must be between 0 and 1")
		highlight_colour = colour_values
	source = CanvasSource(
		smiles=smiles,
		legend=legend,
		explicit_methyl=explicit_methyl,
		width=width,
		height=height,
		highlight_atoms=highlight_atoms,
		highlight_bonds=highlight_bonds,
		highlight_peptide_bonds=highlight_peptide_bonds,
		highlight_colour=highlight_colour,
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
	matched_scripts = set()
	for canvas_el in root.xpath(".//canvas"):
		script_el = _following_rdkit_script(canvas_el, root)
		if script_el is None:
			canvas_id = canvas_el.get("id", "")
			if canvas_id.startswith("canvas_"):
				raise ValueError(
					f"RDKit canvas {canvas_id!r} has no supported drawing script")
			continue
		if script_el in matched_scripts:
			raise ValueError("RDKit drawing script matches more than one canvas")
		source = _canvas_source_from_elements(canvas_el, script_el)
		targets.append((canvas_el, script_el, source))
		matched_scripts.add(script_el)
	for script_el in root.xpath(".//script"):
		if _is_rdkit_script(script_el) and script_el not in matched_scripts:
			raise ValueError("RDKit drawing script has no matching canvas")
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
