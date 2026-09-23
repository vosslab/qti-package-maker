# local repo modules
import pytest

from qti_package_maker.html_to_image import selectors


#============================================
def test_drawing_tables_are_selected_data_tables_are_not() -> None:
	gel = (
		'<table><tr>'
		'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
		"</tr></table>"
	)
	border_only = (
		'<table><tr>'
		'<td style="border: 2px solid gray;">+</td>'
		"</tr></table>"
	)
	data_table = (
		"<table><tr><th>Substrate</th><th>Velocity</th></tr>"
		"<tr><td>1.0</td><td>12.3</td></tr></table>"
	)
	label_table = (
		'<table><tr>'
		'<td style="text-align: center; padding: 0 2px;">glucose</td>'
		"</tr></table>"
	)
	assert len(selectors.find_table_fragments(gel)) == 1
	assert len(selectors.find_table_fragments(border_only)) == 1
	assert selectors.find_table_fragments(data_table) == []
	assert selectors.find_table_fragments(label_table) == []


#============================================
def test_moleculelib_canvas_source_keeps_label_size_and_explicit_methyl() -> None:
	html = (
		'<canvas id="canvas_1" width="320" height="240"></canvas>'
		'<script>initRDKitModule().then(function(instance){RDKitModule=instance;'
		'let/* */smiles="CCO";let/* */mol=RDKitModule.get_mol(smiles);'
		'let/* */mdetails={};mdetails["legend"]="ethanol";'
		'mdetails["explicitMethyl"]=true;'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));});</script>'
	)
	source = selectors.find_canvas_fragments(html)[0]
	assert (source.smiles, source.legend, source.explicit_methyl) == (
		"CCO", "ethanol", True)
	assert (source.width, source.height) == (320, 240)
	assert source.highlight_atoms == ()
	assert source.highlight_peptide_bonds is False


#============================================
def test_aminoacidlib_canvas_source_keeps_peptide_highlights() -> None:
	html = (
		'<canvas id="canvas_2" width="480" height="512"></canvas>'
		'<script>initRDKitModule().then(function(instance){RDKitModule=instance;'
		'let/* */smiles="CC(=O)NCC(=O)O";let/* */mol=RDKitModule.get_mol(smiles);'
		'let/* */mdetails={};mdetails["bonds"]=getPeptideBonds(mol);'
		'mdetails["atoms"]=[0];mdetails["highlightColour"]=[0,1,0];'
		'mdetails["legend"]="peptide_ab12";mdetails["explicitMethyl"]=true;'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));});</script>'
	)
	source = selectors.find_canvas_fragments(html)[0]
	assert source.highlight_atoms == (0,)
	assert source.highlight_peptide_bonds is True
	assert source.highlight_colour == (0.0, 1.0, 0.0)
	assert source.legend == "peptide_ab12"


#============================================
def test_canvas_dimensions_and_unmatched_markup_fail_clearly() -> None:
	too_large = (
		'<canvas id="canvas_3" width="5000" height="20"></canvas>'
		'<script>initRDKitModule();let smiles="CC";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>'
	)
	with pytest.raises(ValueError, match="dimensions"):
		selectors.find_canvas_fragments(too_large)
	with pytest.raises(ValueError, match="no supported drawing script"):
		selectors.find_canvas_fragments('<canvas id="canvas_orphan"></canvas>')
	long_smiles = "C" * 4097
	long_smiles_html = (
		'<canvas id="canvas_long" width="120" height="80"></canvas>'
		f'<script>initRDKitModule();let smiles="{long_smiles}";'
		'let mol=RDKitModule.get_mol(smiles);'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify({}));</script>')
	with pytest.raises(ValueError, match="supported length"):
		selectors.find_canvas_fragments(long_smiles_html)


#============================================
def test_nested_canvas_uses_its_canvas_id_to_find_choice_script() -> None:
	html = (
		'<div><div><div><canvas id="canvas_choice_1" width="120" '
		'height="80"></canvas></div></div></div>'
		'<script>initRDKitModule().then(function(i){RDKitModule=i;'
		'let smiles="CCO";let mol=RDKitModule.get_mol(smiles);'
		'let mdetails={};'
		'canvas=document.getElementById("canvas_choice_1");'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));});</script>')
	source = selectors.find_canvas_fragments(html)[0]
	assert source.smiles == "CCO"
	assert (source.width, source.height) == (120, 80)


#============================================
def test_unsupported_drawing_options_fail_instead_of_being_dropped() -> None:
	html = (
		'<canvas id="canvas_4" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CCO";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'mdetails["addBondIndices"]=true;'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));'
		'</script>')
	with pytest.raises(ValueError, match="unsupported RDKit drawing option"):
		selectors.find_canvas_fragments(html)


#============================================
def test_dynamic_or_object_literal_drawing_options_fail() -> None:
	missing_initializer = (
		'<canvas id="canvas_missing" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CC";'
		'let mol=RDKitModule.get_mol(smiles);'
		'mdetails["atoms"]=[0];'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>')
	object_options = (
		'<canvas id="canvas_object" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CC";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={"atoms":[0]};'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>')
	dynamic_options = (
		'<canvas id="canvas_dynamic" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CC";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'mdetails["atoms"]=getAtoms(mol);'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>')
	with pytest.raises(ValueError, match="static empty mdetails object"):
		selectors.find_canvas_fragments(missing_initializer)
	with pytest.raises(ValueError, match="static empty mdetails object"):
		selectors.find_canvas_fragments(object_options)
	with pytest.raises(ValueError, match="static integer list"):
		selectors.find_canvas_fragments(dynamic_options)


#============================================
def test_one_rdkit_drawing_script_cannot_match_multiple_canvases() -> None:
	html = (
		'<canvas id="canvas_a" width="120" height="80"></canvas>'
		'<canvas id="canvas_b" width="120" height="80"></canvas>'
		'<script>initRDKitModule();let smiles="CCO";'
		'let mol=RDKitModule.get_mol(smiles);let mdetails={};'
		'mol.draw_to_canvas_with_highlights(canvas,JSON.stringify(mdetails));</script>')
	with pytest.raises(ValueError, match="more than one canvas"):
		selectors.find_canvas_fragments(html)
