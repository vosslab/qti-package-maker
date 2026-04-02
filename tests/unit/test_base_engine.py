# Standard Library
import types

# Pip3 Library
import pytest

# QTI Package Maker
import qti_package_maker.engines.base_engine
import qti_package_maker.assessment_items.item_bank


class _DummyWriteItem:
	@staticmethod
	def MC(item_cls):
		return "ok"


class DummyEngine(qti_package_maker.engines.base_engine.BaseEngine):
	def __init__(self, package_name: str):
		super().__init__(package_name, verbose=False)
		self.write_item = _DummyWriteItem

	def _get_name(self) -> str:
		return "dummy"

	def read_package(self, infile: str):
		raise NotImplementedError

	def save_package(self, item_bank, outfile: str = None):
		raise NotImplementedError


class EngineWithModuleWriteItem(qti_package_maker.engines.base_engine.BaseEngine):
	def __init__(self, package_name: str, write_item_module):
		super().__init__(package_name, verbose=False)
		self.write_item = write_item_module

	def _get_name(self) -> str:
		return "dummy"

	def read_package(self, infile: str):
		raise NotImplementedError

	def save_package(self, item_bank, outfile: str = None):
		raise NotImplementedError


def test_get_outfile_name_default_prefix():
	engine = DummyEngine("sample")
	assert engine.get_outfile_name("qti12", "zip") == "qti12-sample.zip"


def test_get_outfile_name_respects_existing_prefix():
	engine = DummyEngine("sample")
	assert engine.get_outfile_name("qti12", "zip", "qti12-sample.zip") == "qti12-sample.zip"


def test_process_item_bank_empty():
	engine = DummyEngine("sample")
	empty_bank = qti_package_maker.assessment_items.item_bank.ItemBank()
	assert engine.process_item_bank(empty_bank) == []
	assert engine.process_random_item_from_item_bank(empty_bank) is None


def test_validate_write_item_module_accepts_correct_path(tmp_path):
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls):
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	engine.validate_write_item_module()


def test_validate_write_item_module_rejects_wrong_path(tmp_path):
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "not_dummy" / "write_item.py")
	def mc_writer(item_cls):
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	with pytest.raises(ImportError):
		engine.validate_write_item_module()


def test_get_available_question_types(tmp_path):
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls):
		return "ok"
	def hidden_writer(item_cls):
		return "skip"
	write_item_module.MC = mc_writer
	write_item_module._hidden = hidden_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	available = engine.get_available_question_types()
	assert "MC" in available


def test_process_item_bank_skips_unsupported(capsys, tmp_path):
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls):
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	bank = qti_package_maker.assessment_items.item_bank.ItemBank(allow_mixed=True)
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MA", ("Q2?", ["A", "B", "C"], ["A"]))
	items = engine.process_item_bank(bank)
	out = capsys.readouterr().out
	assert "Warning" in out
	assert items == ["ok"]


def test_process_random_item_does_not_reorder(tmp_path):
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls):
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	bank = qti_package_maker.assessment_items.item_bank.ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	bank.add_item("MC", ("Q2?", ["A", "B"], "B"))
	bank.add_item("MC", ("Q3?", ["A", "B"], "A"))
	before_order = [item.item_crc16 for item in bank]
	engine.process_random_item_from_item_bank(bank)
	after_order = [item.item_crc16 for item in bank]
	assert before_order == after_order
