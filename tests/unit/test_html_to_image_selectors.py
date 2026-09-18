# local repo modules
from qti_package_maker.html_to_image import selectors


# Gel-style drawing: bgcolor plus a cell border (who_father / gellib).
DRAWING_TABLE = (
	'<table><tr>'
	'<td bgcolor="#000000" style="border-top: 1px solid #111111;"></td>'
	"</tr></table>"
)

# Agglutination wells are border-only (no bgcolor).
BORDER_ONLY_TABLE = (
	'<table><tr>'
	'<td style="border: 2px solid gray; width: 48px; height: 48px;">+</td>'
	"</tr></table>"
)

# Exact padding: 0 is a drawing attribute (sugarlib Fischer cells).
PADDING_ZERO_TABLE = (
	'<table><tr>'
	'<td style="padding: 0; text-align: center;">C</td>'
	"</tr></table>"
)

# Plain data table: no drawing attributes.
DATA_TABLE = (
	"<table><tr><th>Substrate</th><th>Velocity</th></tr>"
	"<tr><td>1.0</td><td>12.3</td></tr></table>"
)

# Label table: padding: 0 2px is not exact padding: 0 (metaboliclib).
LABEL_TABLE = (
	'<table><tr>'
	'<td style="text-align: center; padding: 0 2px;">glucose</td>'
	"</tr></table>"
)

CANVAS_WITH_LEGEND = (
	'<p><canvas id="canvas_a" width="256" height="256"></canvas></p>'
	"<script>initRDKitModule().then(function(instance){"
	"RDKitModule=instance;"
	'let/* */smiles="CC(N)C(=O)O";'
	'mdetails["legend"]="alanine";'
	'mdetails["explicitMethyl"]=true;'
	"});</script>"
)


#============================================
def test_drawing_tables_are_selected_data_tables_are_not() -> None:
	assert len(selectors.find_table_fragments(DRAWING_TABLE)) == 1
	assert len(selectors.find_table_fragments(BORDER_ONLY_TABLE)) == 1
	assert len(selectors.find_table_fragments(PADDING_ZERO_TABLE)) == 1
	assert selectors.find_table_fragments(DATA_TABLE) == []
	assert selectors.find_table_fragments(LABEL_TABLE) == []


#============================================
def test_rdkit_canvas_extracts_smiles_and_draw_options() -> None:
	fragments = selectors.find_canvas_fragments(CANVAS_WITH_LEGEND)
	assert len(fragments) == 1
	source = fragments[0]
	assert source.smiles == "CC(N)C(=O)O"
	assert source.legend == "alanine"
	assert source.explicit_methyl is True
	assert source.width == 256
	assert source.height == 256
