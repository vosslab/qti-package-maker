"""Rewrite an ItemBank, replacing selected HTML fragments with packaged PNGs."""

# PIP3 modules
import lxml.html

# local repo modules
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.html_to_image import selectors
from qti_package_maker.html_to_image.render_canvas import render_canvas_png
from qti_package_maker.html_to_image.render_table import TableRenderer
from qti_package_maker.html_to_image.selectors import CanvasSource


#============================================
def _table_alt_text(table_html: str) -> str:
	"""
	Collapse a table to one-line ASCII alt text.

	Args:
		table_html: Selected table HTML.

	Returns:
		Whitespace-collapsed plain text.
	"""
	root = lxml.html.fromstring(table_html)
	texts = []
	for cell in root.xpath(".//td|.//th"):
		cell_text = " ".join(cell.text_content().split())
		if cell_text:
			texts.append(cell_text)
	alt = " ".join(texts)
	ascii_chars = []
	for ch in alt:
		if ord(ch) < 128:
			ascii_chars.append(ch)
	alt = "".join(ascii_chars)
	alt = " ".join(alt.split())
	if not alt:
		alt = "table drawing"
	return alt


#============================================
def _canvas_alt_text(source: CanvasSource) -> str:
	"""
	Build alt text from a canvas SMILES and optional legend.

	Args:
		source: Extracted canvas record.

	Returns:
		Alt text naming the legend and SMILES.
	"""
	if source.legend is None:
		alt = f"SMILES {source.smiles}"
		return alt
	alt = f"{source.legend} (SMILES {source.smiles})"
	return alt


#============================================
def _alt_for_fragment(fragment: object, family: str) -> str:
	"""
	Choose alt text for a selected fragment.

	Args:
		fragment: Table HTML string or CanvasSource.
		family: table or canvas.

	Returns:
		Alt text for the replacement img.
	"""
	if family == "canvas":
		alt = _canvas_alt_text(fragment)
		return alt
	alt = _table_alt_text(fragment)
	return alt


#============================================
def _make_img_element(src: str, alt: str) -> lxml.html.HtmlElement:
	"""
	Build an img element with src and alt.

	Args:
		src: Packaged image filename.
		alt: Plain-text alternative.

	Returns:
		An img HtmlElement.
	"""
	img = lxml.html.Element("img")
	img.set("src", src)
	img.set("alt", alt)
	return img


#============================================
def _replace_canvas(
			canvas_el: lxml.html.HtmlElement,
			script_el: lxml.html.HtmlElement,
			img_el: lxml.html.HtmlElement) -> None:
	"""
	Replace a canvas (and empty wrapper) plus its script with an img.

	Args:
		canvas_el: The canvas element.
		script_el: The following RDKit script.
		img_el: The replacement image.
	"""
	parent = canvas_el.getparent()
	wrapper_is_lone_paragraph = (
		parent is not None
		and parent.tag == "p"
		and list(parent) == [canvas_el]
		and not (canvas_el.tail or "").strip()
		and not (parent.text or "").strip()
	)
	if wrapper_is_lone_paragraph:
		parent.getparent().replace(parent, img_el)
	else:
		parent.replace(canvas_el, img_el)
	script_el.getparent().remove(script_el)


#============================================
def _apply_jobs(html: str, grouped_jobs: list) -> str:
	"""
	Replace selected fragments in html with img tags.

	Args:
		html: Original field HTML.
		grouped_jobs: (family, list of (name, alt)) in finder order.

	Returns:
		HTML with selected fragments replaced.
	"""
	root = selectors.parse_html_fragment(html)
	for family, jobs in grouped_jobs:
		if family == "table":
			tables = selectors.iter_drawing_tables(root)
			if len(tables) != len(jobs):
				raise ValueError(
					f"table render plan length {len(jobs)} does not match "
					f"{len(tables)} selected tables"
				)
			for table_el, (name, alt) in zip(tables, jobs):
				img_el = _make_img_element(name, alt)
				table_el.getparent().replace(table_el, img_el)
			continue
		if family == "canvas":
			targets = selectors.iter_canvas_targets(root)
			if len(targets) != len(jobs):
				raise ValueError(
					f"canvas render plan length {len(jobs)} does not match "
					f"{len(targets)} selected canvases"
				)
			for (canvas_el, script_el, _source), (name, alt) in zip(targets, jobs):
				img_el = _make_img_element(name, alt)
				_replace_canvas(canvas_el, script_el, img_el)
			continue
		raise ValueError(f"unknown fragment family: {family}")
	new_html = selectors.serialize_fragment(root)
	return new_html


#============================================
def _convert_html_field(
			html: str,
			render_pairs: list,
			counters: dict,
			item_crc16: str,
			cache: dict) -> tuple[str, list]:
	"""
	Render selected fragments in one HTML field into memory, then replace.

	Args:
		html: One item HTML field.
		render_pairs: (finder, renderer, family) triples.
		counters: Per-family image index, mutated in place.
		item_crc16: Original item CRC used in image names.
		cache: Maps original HTML to (new_html, images) so identical choice
			and answer strings keep the same img src.

	Returns:
		(new_html, list of (src, png_bytes)).
	"""
	if html in cache:
		return cache[html]
	grouped_jobs = []
	images = []
	any_jobs = False
	for finder, renderer, family in render_pairs:
		jobs = []
		for fragment in finder(html):
			any_jobs = True
			png_bytes = renderer(fragment)
			counters[family] = counters.get(family, 0) + 1
			name = f"{item_crc16}_{family}_{counters[family]}.png"
			alt = _alt_for_fragment(fragment, family)
			jobs.append((name, alt))
			images.append((name, png_bytes))
		grouped_jobs.append((family, jobs))
	if not any_jobs:
		cache[html] = (html, [])
		return html, []
	new_html = _apply_jobs(html, grouped_jobs)
	cache[html] = (new_html, images)
	return new_html, images


#============================================
def _convert_value(
			value: object,
			render_pairs: list,
			counters: dict,
			item_crc16: str,
			cache: dict) -> tuple[object, list]:
	"""
	Convert HTML strings nested in an item supporting field.

	Args:
		value: A string, list, dict, or scalar field.
		render_pairs: (finder, renderer, family) triples.
		counters: Per-family image index, mutated in place.
		item_crc16: Original item CRC used in image names.
		cache: Per-item original-HTML to converted-HTML map.

	Returns:
		(new_value, list of (src, png_bytes)).
	"""
	if isinstance(value, str):
		new_html, images = _convert_html_field(
			value, render_pairs, counters, item_crc16, cache)
		return new_html, images
	if isinstance(value, list):
		new_list = []
		images = []
		for element in value:
			new_element, element_images = _convert_value(
				element, render_pairs, counters, item_crc16, cache)
			new_list.append(new_element)
			images.extend(element_images)
		return new_list, images
	if isinstance(value, dict):
		new_dict = {}
		images = []
		for key, element in value.items():
			new_element, element_images = _convert_value(
				element, render_pairs, counters, item_crc16, cache)
			new_dict[key] = new_element
			images.extend(element_images)
		return new_dict, images
	return value, []


#============================================
def _resolve_render_pairs(renderers: list | None) -> list:
	"""
	Normalize caller renderers into (finder, renderer, family) triples.

	Args:
		renderers: None, or a list of pairs/triples.

	Returns:
		Triples ready for convert. None means the caller should use defaults.
	"""
	if renderers is None:
		return None
	pairs = []
	for entry in renderers:
		if len(entry) == 3:
			pairs.append(entry)
			continue
		finder, renderer = entry
		family = "canvas" if finder is selectors.find_canvas_fragments else "table"
		pairs.append((finder, renderer, family))
	return pairs


#============================================
def _default_render_pairs(table_renderer: TableRenderer) -> list:
	"""
	Build the shipped (table screenshot, canvas RDKit) renderer list.

	Args:
		table_renderer: Open TableRenderer holding one browser.

	Returns:
		Default (finder, renderer, family) triples.
	"""
	pairs = [
		(selectors.find_table_fragments, table_renderer.render_table_png, "table"),
		(selectors.find_canvas_fragments, render_canvas_png, "canvas"),
	]
	return pairs


#============================================
def _convert_bank_with_pairs(item_bank: ItemBank, render_pairs: list) -> ItemBank:
	"""
	Render every selected fragment in memory, then copy the bank and attach PNGs.

	Args:
		item_bank: Source bank; not mutated.
		render_pairs: (finder, renderer, family) triples.

	Returns:
		A new bank whose drawing fragments are img references.
	"""
	# Phase 1: render into memory. A renderer error raises before any directory.
	plans = []
	for item in item_bank:
		counters = {}
		cache = {}
		images = []
		new_question, question_images = _convert_html_field(
			item.question_text, render_pairs, counters, item.item_crc16, cache)
		images.extend(question_images)
		new_fields = []
		for field_value in item.get_tuple():
			new_value, field_images = _convert_value(
				field_value, render_pairs, counters, item.item_crc16, cache)
			new_fields.append(new_value)
			images.extend(field_images)
		plans.append((item, new_question, tuple(new_fields), images))
	# Phase 2: copy items and spill PNGs. The new bank owns its media dir.
	new_bank = ItemBank(allow_mixed=item_bank.allow_mixed)
	for item, new_question, new_fields, images in plans:
		new_item = type(item)(new_question, *new_fields)
		new_bank.add_item_cls(new_item)
		for name, png_bytes in images:
			new_bank.add_image(name, png_bytes)
	return new_bank


#============================================
def convert_bank(
			item_bank: ItemBank,
			renderers: list | None = None) -> ItemBank:
	"""
	Return a new bank with selected fragments replaced by packaged PNGs.

	Args:
		item_bank: Source bank; left unchanged.
		renderers: Optional list of (finder, renderer) or
			(finder, renderer, family). None uses Playwright tables and
			RDKit canvases.

	Returns:
		A derived ItemBank. The caller owns cleanup() of its media dir.
	"""
	resolved = _resolve_render_pairs(renderers)
	if resolved is not None:
		new_bank = _convert_bank_with_pairs(item_bank, resolved)
		return new_bank
	with TableRenderer() as table_renderer:
		new_bank = _convert_bank_with_pairs(
			item_bank, _default_render_pairs(table_renderer))
	return new_bank
