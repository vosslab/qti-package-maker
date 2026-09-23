# Standard Library
import os
import base64
import pathlib
import tempfile

# PIP3 modules
import pytest

# local repo modules
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.html_to_image import selectors
from qti_package_maker.html_to_image import transform


# 8x8 PNG above package_integrity.MIN_IMAGE_DIMENSION_PX.
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
def test_convert_replaces_drawing_and_leaves_source_bank() -> None:
	table = (
		'<table><tr>'
		'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
		"</tr></table>"
	)
	question = f"<p>Which lane matches?</p>{table}"
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (question, ["lane A", "lane B"], "lane A"))
	new_bank = transform.convert_bank(bank, renderers=_stub_renderers())
	original = list(bank)[0]
	converted = list(new_bank)[0]
	assert original.question_text == question
	assert "<table" not in converted.question_text
	assert "<img" in converted.question_text
	collected = new_bank.collect_assets()
	assert len(collected.assets) == 1
	media_dir = new_bank.media_base_dir
	new_bank.cleanup()
	assert os.path.isdir(media_dir) is False


#============================================
def test_convert_keeps_mc_answer_in_choices() -> None:
	table = (
		'<table><tr>'
		'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
		"</tr></table>"
	)
	choice_a = f"<p>yes</p>{table}"
	choice_b = "<p>no</p>"
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (f"<p>q</p>{table}", [choice_a, choice_b], choice_a))
	new_bank = transform.convert_bank(bank, renderers=_stub_renderers())
	item = list(new_bank)[0]
	assert item.answer_text in item.choices_list
	assert "<table" not in item.answer_text
	assert "<img" in item.answer_text
	new_bank.cleanup()


#============================================
def test_render_error_does_not_create_a_media_directory(
			tmp_path: pathlib.Path,
			monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setenv("TMPDIR", str(tmp_path))
	monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
	table = (
		'<table><tr>'
		'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
		"</tr></table>"
	)
	question = f"<p>Which lane matches?</p>{table}"
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (question, ["lane A", "lane B"], "lane A"))

	def raising_png(table_html: str) -> bytes:
		raise RuntimeError("renderer failed")

	renderers = [
		(selectors.find_table_fragments, raising_png, "table"),
	]
	with pytest.raises(RuntimeError):
		transform.convert_bank(bank, renderers=renderers)
	leftovers = list(tmp_path.iterdir())
	assert leftovers == []


#============================================
def test_canvas_conversion_removes_loader_and_drawing_scripts() -> None:
	loader = (
		'<script src="https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js">'
		"</script>")
	canvas = (
		'<p><canvas id="canvas_test" width="120" height="80"></canvas></p>'
		'<script>initRDKitModule().then(function(i){RDKitModule=i;'
		'let smiles="CCO";let mol=RDKitModule.get_mol(smiles);'
		'let mdetails={};mdetails["explicitMethyl"]=true;'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));});</script>')
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (loader + canvas, ["ethanol", "water"], "ethanol"))
	renderers = [(selectors.find_canvas_fragments, lambda source: PNG_BYTES, "canvas")]
	converted_bank = transform.convert_bank(bank, renderers=renderers)
	converted = list(converted_bank)[0]
	assert "<img" in converted.question_text
	assert "initRDKitModule" not in converted.question_text
	assert "RDKit_minimal.js" not in converted.question_text
	converted_bank.cleanup()


#============================================
def test_canvas_in_choice_becomes_a_packaged_image() -> None:
	canvas = (
		'<canvas id="canvas_choice" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CCO";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'mdetails["explicitMethyl"]=true;'
		'canvas=document.getElementById("canvas_choice");'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));'
		'</script>')
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", ("<p>Which structure?</p>", [canvas, "water"], canvas))
	renderers = [
		(selectors.find_canvas_fragments, lambda source: PNG_BYTES, "canvas")]
	converted_bank = transform.convert_bank(bank, renderers=renderers)
	item = list(converted_bank)[0]
	assert item.answer_text in item.choices_list
	assert "<canvas" not in item.choices_list[0]
	assert "<img" in item.choices_list[0]
	assert len(converted_bank.collect_assets().assets) == 1
	converted_bank.cleanup()


#============================================
def test_table_conversion_removes_recognized_rdkit_loader() -> None:
	loader = (
		'<script src="https://unpkg.com/@rdkit/rdkit/dist/RDKit_minimal.js">'
		"</script>")
	table = '<table><tr><td style="border: 1px solid black">A</td></tr></table>'
	bank = ItemBank(allow_mixed=False)
	bank.add_item("MC", (loader + table, ["A", "B"], "A"))
	renderers = [(selectors.find_table_fragments, stub_table_png, "table")]
	converted_bank = transform.convert_bank(bank, renderers=renderers)
	converted = list(converted_bank)[0]
	assert "<img" in converted.question_text
	assert "RDKit_minimal.js" not in converted.question_text
	converted_bank.cleanup()
