# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
import qti_package_maker.engines.bbq_text_upload.read_package


def test_make_item_cls_from_line_requires_correct_flag() -> None:
	line = "MC\t2+2?\t3\tincorrect\t4\tincorrect"
	with pytest.raises(ValueError):
		qti_package_maker.engines.bbq_text_upload.read_package.make_item_cls_from_line(line)
