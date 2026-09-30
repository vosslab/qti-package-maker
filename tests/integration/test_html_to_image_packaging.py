# Standard Library
import os
import zipfile
import base64
import pathlib

# PIP3 modules
import pytest

# local repo modules
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.common import package_integrity
from qti_package_maker.html_to_image import selectors
from qti_package_maker.engines.blackboard_export_zip import engine_class as bb_export_engine
from qti_package_maker.engines.blackboard_qti_v2_1 import engine_class as bb_qti21_engine
from qti_package_maker.engines.canvas_qti_v1_2 import engine_class as canvas_engine
from qti_package_maker.package_interface import QTIPackageInterface


PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGNkaPjPgA0wYRUdtBIALlIBjzTK6JgAAAAASUVORK5CYII="
)


#============================================
def stub_table_png(table_html: str) -> bytes:
	return PNG_BYTES


#============================================
def _stub_renderers() -> list:
	pairs = [
		(selectors.find_table_fragments, stub_table_png, "table"),
	]
	return pairs


#============================================
def _bank_with_table() -> ItemBank:
	table = (
		'<table><tr>'
		'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
		"</tr></table>"
	)
	bank = ItemBank(allow_mixed=False)
	question = f"<p>Which lane matches?</p>{table}"
	bank.add_item("MC", (question, ["lane A", "lane B"], "lane A"))
	bank.renumber_items()
	return bank


#============================================
def _interface_with_repeated_drawings() -> tuple[QTIPackageInterface, str]:
	"""Build distinct items that reuse table and canvas drawing sources."""
	canvas = (
		'<canvas id="canvas_cc" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CCO";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'canvas=document.getElementById("canvas_cc");'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));'
		'</script>'
	)
	shared_table = (
		'<table class="lane-table" cellpadding="2" cellspacing="0" '
		'style="border-collapse: collapse; width: 180px"><tr>'
		'<td align="center" bgcolor="#000000" style="border: 1px solid #111111;">'
		f'fragment {canvas}</td></tr></table>'
	)
	distinct_table = (
		'<table class="lane-table" cellpadding="4" cellspacing="0" '
		'style="border-collapse: collapse; width: 220px"><tr>'
		'<td align="left" bgcolor="#eeeeee" style="border: 1px solid #222222;">'
		'distinct fragment</td></tr></table>'
	)
	qti = QTIPackageInterface("html-to-image-cache", verbose=False)
	qti.add_item("MC", (f"<p>First item</p>{shared_table}{canvas}", ["one", "two"], "one"))
	qti.add_item(
		"MC", (f"<p>Second item</p>{shared_table}{distinct_table}{canvas}",
		["three", "four"], "three"))
	return qti, shared_table


#============================================
def _png_names(zip_path: str) -> list[str]:
	with zipfile.ZipFile(zip_path) as zf:
		names = [name for name in zf.namelist() if name.lower().endswith(".png")]
	return names


#============================================
def _zip_item_text(zip_path: str) -> str:
	parts = []
	with zipfile.ZipFile(zip_path) as zf:
		for name in zf.namelist():
			base = os.path.basename(name).lower()
			if not (base.endswith(".dat") or base.endswith(".xml") or "item_" in base):
				continue
			data = zf.read(name)
			if b"<table" in data or b"<item" in data or b"assessmentItem" in data:
				parts.append(data.decode("utf-8"))
	text = "\n".join(parts)
	return text


ENGINE_FACTORIES = {
	"blackboard_export_zip": bb_export_engine.EngineClass,
	"blackboard_qti_v2_1": bb_qti21_engine.EngineClass,
	"canvas_qti_v1_2": canvas_engine.EngineClass,
}


#============================================
@pytest.mark.parametrize("engine_name", sorted(ENGINE_FACTORIES.keys()))
def test_html_to_image_on_packages_one_png(
			engine_name: str,
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = _bank_with_table()
	engine_cls = ENGINE_FACTORIES[engine_name]
	engine = engine_cls(
		"html-to-image-on",
		verbose=False,
		html_to_image=True,
		html_to_image_renderers=_stub_renderers(),
	)
	outfile = str(tmp_path / f"{engine_name}-on.zip")
	engine.save_package(bank, outfile=outfile)
	assert package_integrity.check_package(outfile) == []
	assert len(_png_names(outfile)) == 1


#============================================
@pytest.mark.parametrize("engine_name", sorted(ENGINE_FACTORIES.keys()))
def test_html_to_image_off_keeps_table_html(
			engine_name: str,
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.chdir(tmp_path)
	bank = _bank_with_table()
	engine_cls = ENGINE_FACTORIES[engine_name]
	engine = engine_cls("html-to-image-off", verbose=False, html_to_image=False)
	outfile = str(tmp_path / f"{engine_name}-off.zip")
	engine.save_package(bank, outfile=outfile)
	assert _png_names(outfile) == []
	item_text = _zip_item_text(outfile)
	has_table = "<table" in item_text or "&lt;table" in item_text
	assert has_table is True


#============================================
def test_interface_shares_html_render_cache_across_engines(
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""Each source fragment renders once while each package keeps its item PNGs."""
	monkeypatch.chdir(tmp_path)
	qti, source_table = _interface_with_repeated_drawings()
	rendered_tables = []
	rendered_canvases = []

	def count_table_png(table_html: str) -> bytes:
		rendered_tables.append(table_html)
		return PNG_BYTES

	def count_canvas_png(source: selectors.CanvasSource) -> bytes:
		rendered_canvases.append(source)
		return PNG_BYTES

	renderers = [
		(selectors.find_table_fragments, count_table_png, "table"),
		(selectors.find_canvas_fragments, count_canvas_png, "canvas"),
	]
	package_names = ("canvas_qti_v1_2", "blackboard_qti_v2_1", "blackboard_export_zip")
	packages = []
	for engine_name in package_names:
		outfile = str(tmp_path / f"{engine_name}.zip")
		package = qti.save_package(
			engine_name,
			outfile=outfile,
			engine_options={
				"html_to_image": True,
				"html_to_image_renderers": renderers,
			},
		)
		assert package == outfile
		assert package_integrity.check_package(outfile) == []
		packages.append(outfile)

	assert len(rendered_tables) == 2
	assert len(rendered_canvases) == 1
	package_png_names = [
		sorted(os.path.basename(name) for name in _png_names(package))
		for package in packages
	]
	# Blackboard export embeds the same assets under its own csfiles xid names.
	assert package_png_names[0] == package_png_names[1]
	assert all(len(names) == 5 for names in package_png_names)
	assert any("_table_" in name for name in package_png_names[0])
	assert any("_canvas_" in name for name in package_png_names[0])
	assert len(set(package_png_names[0])) == 5
	original_questions = [item.question_text for item in qti.item_bank]
	assert all(source_table in question for question in original_questions)


#============================================
@pytest.mark.parametrize("engine_name", sorted(ENGINE_FACTORIES))
def test_interface_cache_respects_renderer_changes(
			engine_name: str,
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	"""Switching callbacks must change package images even for identical content."""
	monkeypatch.chdir(tmp_path)
	qti, _source_table = _interface_with_repeated_drawings()
	render_calls = {"red": 0, "blue": 0}
	# Inline 8x8 solid RGB PNGs keep this regression offline and dependency-free.
	color_pngs = {
		"red": base64.b64decode(
			"iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGP8z4Ad"
			"MOEQH6QSAM1BAQ/oQeJvAAAAAElFTkSuQmCC"),
		"blue": base64.b64decode(
			"iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAFElEQVR4nGNkYPjP"
			"gA0wYRUdtBIAy0MBD1YkjLoAAAAASUVORK5CYII="),
	}

	def render_red(fragment: object) -> bytes:
		render_calls["red"] += 1
		return color_pngs["red"]

	def render_blue(fragment: object) -> bytes:
		render_calls["blue"] += 1
		return color_pngs["blue"]

	# Returning to the first callback should reuse its own images.
	for index, (color, renderer) in enumerate([
			("red", render_red), ("blue", render_blue), ("red", render_red)]):
		outfile = str(tmp_path / f"{engine_name}-{index}.zip")
		qti.save_package(engine_name, outfile=outfile, engine_options={
			"html_to_image": True,
			"html_to_image_renderers": [
				(selectors.find_table_fragments, renderer, "table"),
				(selectors.find_canvas_fragments, renderer, "canvas"),
			],
		})
		assert package_integrity.check_package(outfile) == []
		with zipfile.ZipFile(outfile) as package:
			pngs = [package.read(name) for name in _png_names(outfile)]
		assert pngs
		assert all(png == color_pngs[color] for png in pngs)
	assert render_calls == {"red": 3, "blue": 3}
