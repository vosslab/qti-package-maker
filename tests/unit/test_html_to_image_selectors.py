# local repo modules
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
