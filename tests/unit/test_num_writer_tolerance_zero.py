# Standard Library

# Pip3 Library
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.bbq_text_upload import write_item as bbq_write_item
from qti_package_maker.engines.blackboard_qti_v2_1 import write_item as bb_qti_write_item
from qti_package_maker.engines.canvas_qti_v1_2 import write_item as canvas_write_item
from qti_package_maker.engines.html_selftest import write_item as html_write_item
from qti_package_maker.engines.human_readable import write_item as human_write_item
from qti_package_maker.engines.text2qti import write_item as text2qti_write_item


def _make_num_item() -> item_types.NUM:
	item = item_types.NUM("Approx pi?", 3.14, 0.0, True)
	item.item_number = 1
	return item


def test_bbq_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = bbq_write_item.NUM(item)
	assert "\t0.00000000" in output


def test_text2qti_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = text2qti_write_item.NUM(item)
	assert "+- 0.0" in output


def test_human_readable_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = human_write_item.NUM(item)
	assert "&pm;0.0" in output


def test_html_selftest_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = html_write_item.NUM(item)
	assert "numTolerance_" in output
	assert " = 0.0" in output


def test_canvas_qti_v1_2_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = canvas_write_item.NUM(item)
	assert isinstance(output, lxml.etree._Element)
	vargte = output.findall(".//vargte")
	varlte = output.findall(".//varlte")
	assert len(vargte) == 1
	assert len(varlte) == 1
	assert vargte[0].text == "3.14"
	assert varlte[0].text == "3.14"


def test_blackboard_qti_v2_1_num_writer_zero_tolerance() -> None:
	item = _make_num_item()
	output = bb_qti_write_item.NUM(item)
	equal_nodes = output.xpath("//*[local-name()='equal']")
	assert equal_nodes
	assert equal_nodes[0].attrib.get("tolerance") == "0.0 0.0"
