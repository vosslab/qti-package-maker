"""RDKit canvas rendering preserves supported molecule drawing options."""

# Standard Library
import struct
import unittest.mock

# PIP3 modules
import pytest

# local repo modules
from qti_package_maker.html_to_image import selectors
from qti_package_maker.html_to_image.render_canvas import render_canvas_png


#============================================
def _canvas_source(smiles: str, details: str,
			width: int, height: int) -> selectors.CanvasSource:
	"""Parse one synthetic bptools canvas pair."""
	html = (
		f'<canvas id="canvas_test" width="{width}" height="{height}"></canvas>'
		'<script>initRDKitModule();'
		f'let smiles="{smiles}";'
		'let mol=RDKitModule.get_mol(smiles);'
		'let mdetails={};'
		f"{details}"
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));'
		'</script>')
	return selectors.find_canvas_fragments(html)[0]


#============================================
def _png_dimensions(png: bytes) -> tuple[int, int]:
	"""Read dimensions from the fixed PNG IHDR fields."""
	assert png.startswith(b"\x89PNG\r\n\x1a\n")
	return struct.unpack(">II", png[16:24])


#============================================
def test_render_molecule_canvas_preserves_requested_dimensions() -> None:
	pytest.importorskip("rdkit")
	source = _canvas_source(
		'CC(=O)Oc1ccccc1C(=O)O',
		'mdetails["legend"]="aspirin";mdetails["explicitMethyl"]=true;',
		320, 240)
	assert _png_dimensions(render_canvas_png(source)) == (320, 240)


#============================================
def test_render_peptide_canvas_passes_bright_green_highlights(
			monkeypatch: pytest.MonkeyPatch) -> None:
	pytest.importorskip("rdkit")
	from rdkit.Chem.Draw import rdMolDraw2D
	source = _canvas_source(
		'CC(=O)NCC(=O)NCC(=O)O',
		'mdetails["legend"]="gly-gly";mdetails["explicitMethyl"]=true;'
		'mdetails["bonds"]=getPeptideBonds(mol);'
		'mdetails["atoms"]=[0];mdetails["highlightColour"]=[0,1,0];',
		240, 256)
	drawer = unittest.mock.MagicMock()
	drawer.drawOptions.return_value.explicitMethyl = False
	drawer.GetDrawingText.return_value = b"PNG"
	constructor = unittest.mock.MagicMock(return_value=drawer)
	monkeypatch.setattr(rdMolDraw2D, "MolDraw2DCairo", constructor)
	render_canvas_png(source)
	constructor.assert_called_once_with(240, 256)
	assert drawer.drawOptions.return_value.explicitMethyl is True
	draw_options = drawer.DrawMolecule.call_args.kwargs
	assert draw_options["highlightAtoms"] == [0]
	assert draw_options["highlightAtomColors"] == {0: (0.0, 1.0, 0.0)}
	assert len(draw_options["highlightBonds"]) == 2
	assert draw_options["highlightBondColors"] == {
		bond: (0.0, 1.0, 0.0) for bond in draw_options["highlightBonds"]}


#============================================
def test_render_rejects_negative_highlight_indices() -> None:
	pytest.importorskip("rdkit")
	source = selectors.CanvasSource(
		smiles="CCO",
		legend=None,
		explicit_methyl=False,
		width=120,
		height=80,
		highlight_atoms=(-1,),
	)
	with pytest.raises(ValueError, match="atom highlight index"):
		render_canvas_png(source)
