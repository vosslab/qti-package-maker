# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker import package_interface


def test_init_engine_accepts_partial_name() -> None:
	qti_packer = package_interface.QTIPackageInterface("dummy", verbose=False)
	engine = qti_packer.init_engine("canvas")
	assert engine.name == "canvas_qti_v1_2"


def test_init_engine_rejects_unknown() -> None:
	qti_packer = package_interface.QTIPackageInterface("dummy", verbose=False)
	with pytest.raises(ValueError):
		qti_packer.init_engine("does-not-exist")


def test_trim_item_bank_reduces_count(sample_items: dict) -> None:
	qti_packer = package_interface.QTIPackageInterface("dummy", verbose=False, allow_mixed=True)
	qti_packer.add_item("MC", sample_items["MC"])
	qti_packer.add_item("MA", sample_items["MA"])
	qti_packer.add_item("NUM", sample_items["NUM"])
	assert len(qti_packer.item_bank) == 3
	qti_packer.trim_item_bank(1)
	assert len(qti_packer.item_bank) == 1


def test_save_package_empty_item_bank(capsys: pytest.CaptureFixture) -> None:
	qti_packer = package_interface.QTIPackageInterface("dummy", verbose=False)
	result = qti_packer.save_package("human_readable")
	out = capsys.readouterr().out
	assert result is None
	assert "No assessment items to write" in out
