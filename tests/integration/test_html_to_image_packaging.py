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
