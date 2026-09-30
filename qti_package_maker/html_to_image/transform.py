"""Rewrite an ItemBank, replacing selected HTML fragments with packaged PNGs."""

# Standard Library
import base64
import dataclasses
import functools

# PIP3 modules
import lxml.html

# local repo modules
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.html_to_image import selectors
from qti_package_maker.html_to_image.render_canvas import render_canvas_png
from qti_package_maker.html_to_image.render_cache import RenderCache
from qti_package_maker.html_to_image.render_table import TableRenderer
from qti_package_maker.html_to_image.selectors import CanvasSource


#============================================
def _table_alt_text(table_el: lxml.html.HtmlElement) -> str:
	"""
	Collapse a table to one-line ASCII alt text.

	Args:
		table_el: Selected table element.

	Returns:
		Whitespace-collapsed plain text.
	"""
	texts = []
	for cell in table_el.xpath(".//td|.//th"):
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
def _make_img_element(src: str, alt: str) -> lxml.html.HtmlElement:
	"""
	Build an img element with src and alt.

	Args:
		src: Packaged image filename.
		alt: Plain-text alternative.

	Returns:
		An img HtmlElement.
	"""
	# ASVS V1.2.1: let lxml serialize src and alt in the HTML attribute context.
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
def _inline_rendered_images(
			table_el: lxml.html.HtmlElement, images: dict[str, bytes]) -> None:
	"""Embed generated canvas PNGs directly in a selected table element."""
	for img in table_el.xpath(".//img"):
		src = img.get("src")
		if src in images:
			# ASVS V1.2.1, V1.3.2: embed only our rendered PNG bytes through
			# an HTML attribute; the canvas drawing script is never evaluated.
			encoded = base64.b64encode(images[src]).decode("ascii")
			img.set("src", f"data:image/png;base64,{encoded}")
	selectors.remove_rdkit_loader_scripts(table_el)


#============================================
def _prepare_custom_table_fragment(
			fragment: str, images: dict[str, bytes]) -> tuple[str, str]:
	"""Inline generated PNGs in a custom finder result for its renderer."""
	fragment_root = selectors.parse_html_fragment(fragment)
	alt = _table_alt_text(fragment_root)
	_inline_rendered_images(fragment_root, images)
	prepared = selectors.serialize_fragment(fragment_root)
	return prepared, alt


#============================================
def _convert_html_field(
			html: str,
			render_pairs: list,
			counters: dict,
			item_crc16: str,
			html_cache: dict,
			render_cache: RenderCache) -> tuple[str, list]:
	"""Convert one field on one tree while retaining custom finder callbacks."""
	if html in html_cache:
		return html_cache[html]
	root = selectors.parse_html_fragment(html)
	images = {}
	any_jobs = False
	# Canvas images must exist before containing tables are rendered.
	ordered_pairs = sorted(render_pairs, key=lambda pair: pair[2] != "canvas")
	for finder, renderer, family, renderer_key in ordered_pairs:
		if family == "canvas":
			is_default_finder = finder is selectors.find_canvas_fragments
			if is_default_finder:
				targets = selectors.iter_canvas_targets(root)
				fragments = [source for _canvas, _script, source in targets]
			else:
				finder_html = html if not any_jobs else selectors.serialize_fragment(root)
				fragments = finder(finder_html)
			if not fragments:
				continue
			if not is_default_finder:
				targets = selectors.iter_canvas_targets(root)
			if len(targets) != len(fragments):
				raise ValueError(
					f"canvas render plan length {len(fragments)} does not match "
					f"{len(targets)} selected canvases")
			for (canvas_el, script_el, source), fragment in zip(targets, fragments):
				any_jobs = True
				key = dataclasses.astuple(fragment) if isinstance(
					fragment, CanvasSource) else fragment
				png_bytes = render_cache.get_or_render(
					family, key, functools.partial(renderer, fragment), renderer=renderer_key)
				counters[family] = counters.get(family, 0) + 1
				name = f"{item_crc16}_{family}_{counters[family]}.png"
				images[name] = png_bytes
				alt_source = source if is_default_finder else fragment
				_replace_canvas(
					canvas_el, script_el,
					_make_img_element(name, _canvas_alt_text(alt_source)))
			continue
		if family == "table":
			is_default_finder = finder is selectors.find_table_fragments
			if is_default_finder:
				tables = selectors.iter_tables(root)
				fragments = tables
			else:
				finder_html = html if not any_jobs else selectors.serialize_fragment(root)
				fragments = finder(finder_html)
			if not fragments:
				continue
			if not is_default_finder:
				tables = selectors.iter_tables(root)
			if len(tables) != len(fragments):
				raise ValueError(
					f"table render plan length {len(fragments)} does not match "
					f"{len(tables)} selected tables")
			for table_el, fragment in zip(tables, fragments):
				any_jobs = True
				if is_default_finder:
					alt = _table_alt_text(table_el)
					_inline_rendered_images(table_el, images)
					prepared = selectors.outer_html(table_el)
				else:
					prepared, alt = _prepare_custom_table_fragment(fragment, images)
				png_bytes = render_cache.get_or_render(
					family, prepared, functools.partial(renderer, prepared), renderer=renderer_key)
				counters[family] = counters.get(family, 0) + 1
				name = f"{item_crc16}_{family}_{counters[family]}.png"
				images[name] = png_bytes
				table_el.getparent().replace(table_el, _make_img_element(name, alt))
			continue
		raise ValueError(f"unknown fragment family: {family}")
	if not any_jobs:
		html_cache[html] = (html, [])
		return html, []
	selectors.remove_rdkit_loader_scripts(root)
	referenced = set(root.xpath(".//img/@src"))
	packaged_images = [
		(name, png) for name, png in images.items() if name in referenced]
	new_html = selectors.serialize_fragment(root)
	html_cache[html] = (new_html, packaged_images)
	return new_html, packaged_images


#============================================
def _convert_value(
			value: object,
			render_pairs: list,
			counters: dict,
			item_crc16: str,
			html_cache: dict,
			render_cache: RenderCache) -> tuple[object, list]:
	"""
	Convert HTML strings nested in an item supporting field.

	Args:
		value: A string, list, dict, or scalar field.
		render_pairs: (finder, renderer, family) triples.
		counters: Per-family image index, mutated in place.
		item_crc16: Original item CRC used in image names.
		html_cache: Per-item original-HTML to converted-HTML map.
		render_cache: Run-scoped rendered PNG cache.

	Returns:
		(new_value, list of (src, png_bytes)).
	"""
	if isinstance(value, str):
		new_html, images = _convert_html_field(
			value, render_pairs, counters, item_crc16, html_cache, render_cache)
		return new_html, images
	if isinstance(value, list):
		new_list = []
		images = []
		for element in value:
			new_element, element_images = _convert_value(
				element, render_pairs, counters, item_crc16, html_cache, render_cache)
			new_list.append(new_element)
			images.extend(element_images)
		return new_list, images
	if isinstance(value, dict):
		new_dict = {}
		images = []
		for key, element in value.items():
			new_element, element_images = _convert_value(
				element, render_pairs, counters, item_crc16, html_cache, render_cache)
			new_dict[key] = new_element
			images.extend(element_images)
		return new_dict, images
	return value, []


#============================================
def _resolve_render_pairs(renderers: list | None) -> list | None:
	"""
	Attach cache identities to the caller's renderer triples.

	Args:
		renderers: None, or a list of (finder, renderer, family) triples.

	Returns:
		Resolved entries with a renderer identity. None selects the defaults.
	"""
	if renderers is None:
		return None
	pairs = []
	for entry in renderers:
		if len(entry) != 3:
			raise ValueError(
				"renderers must be (finder, renderer, family) triples"
			)
		pairs.append((*entry, entry[1]))
	return pairs


#============================================
def _default_render_pairs(table_renderer: TableRenderer) -> list:
	"""
	Build the shipped renderer list with stable cache identities.

	Args:
		table_renderer: Lazy TableRenderer used for uncached table renders.

	Returns:
		Default (finder, renderer, family, renderer identity) entries.
	"""
	pairs = [
		# Fresh TableRenderer sessions share bytes by the shipped implementation.
		(selectors.find_table_fragments, table_renderer.render_table_png,
			"table", TableRenderer.render_table_png),
		(selectors.find_canvas_fragments, render_canvas_png, "canvas", render_canvas_png),
	]
	return pairs


#============================================
def _convert_bank_with_pairs(
			item_bank: ItemBank, render_pairs: list,
			render_cache: RenderCache) -> ItemBank:
	"""
	Render every selected fragment in memory, then copy the bank and attach PNGs.

	Args:
		item_bank: Source bank; not mutated.
		render_pairs: Resolved finder, renderer, family, and renderer identity entries.

	Returns:
		A new bank whose drawing fragments are img references.
	"""
	# Phase 1: render into memory. A renderer error raises before any directory.
	plans = []
	for item in item_bank:
		counters = {}
		html_cache = {}
		images = []
		new_question, question_images = _convert_html_field(
			item.question_text, render_pairs, counters, item.item_crc16,
			html_cache, render_cache)
		images.extend(question_images)
		new_fields = []
		for field_value in item.get_tuple():
			new_value, field_images = _convert_value(
				field_value, render_pairs, counters, item.item_crc16,
				html_cache, render_cache)
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
			renderers: list | None = None,
			cache: RenderCache | None = None) -> ItemBank:
	"""
	Return a new bank with selected fragments replaced by packaged PNGs.

	Args:
		item_bank: Source bank; left unchanged.
		renderers: Optional list of (finder, renderer, family) triples.
			None uses Playwright tables and RDKit canvases.
		cache: Optional shared rendered PNG cache.

	Returns:
		A derived ItemBank. The caller owns cleanup() of its media dir.
	"""
	render_cache = cache if cache is not None else RenderCache()
	resolved = _resolve_render_pairs(renderers)
	if resolved is not None:
		new_bank = _convert_bank_with_pairs(item_bank, resolved, render_cache)
		return new_bank
	with TableRenderer() as table_renderer:
		new_bank = _convert_bank_with_pairs(
			item_bank, _default_render_pairs(table_renderer), render_cache)
	return new_bank
