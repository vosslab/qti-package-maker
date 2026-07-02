# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker import package_interface


def test_package_interface_rejects_empty_name() -> None:
	with pytest.raises(ValueError):
		package_interface.QTIPackageInterface("", verbose=False)


def test_package_interface_add_item() -> None:
	qti = package_interface.QTIPackageInterface("sample", verbose=False, allow_mixed=True)
	qti.add_item("MC", ("Q1?", ["A", "B"], "A"))
	assert len(qti.item_bank) == 1
	assert "MC" in qti.get_available_item_types()


def test_package_interface_init_engine_unknown() -> None:
	qti = package_interface.QTIPackageInterface("sample", verbose=False)
	with pytest.raises(ValueError):
		qti.init_engine("nope")


def test_package_interface_init_engine_exact_match() -> None:
	qti = package_interface.QTIPackageInterface("sample", verbose=False)
	engine = qti.init_engine("bbq_text_upload")
	assert engine.name == "bbq_text_upload"


def test_package_interface_init_engine_unique_prefix() -> None:
	qti = package_interface.QTIPackageInterface("sample", verbose=False)
	engine = qti.init_engine("bbq")
	assert engine.name == "bbq_text_upload"


def test_package_interface_init_engine_ambiguous_prefix() -> None:
	qti = package_interface.QTIPackageInterface("sample", verbose=False)
	with pytest.raises(ValueError) as excinfo:
		qti.init_engine("b")
	message = str(excinfo.value)
	assert "bbq_text_upload" in message
	assert "blackboard_qti_v2_1" in message
