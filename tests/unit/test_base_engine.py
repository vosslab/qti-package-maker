# Standard Library
import pathlib
import types

# Pip3 Library
import pytest

# QTI Package Maker
import qti_package_maker.engines.base_engine
import qti_package_maker.assessment_items.item_bank
import qti_package_maker.assessment_items.item_types


class _DummyWriteItem:
	@staticmethod
	def MC(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
		return "ok"


class DummyEngine(qti_package_maker.engines.base_engine.BaseEngine):
	def __init__(self, package_name: str) -> None:
		super().__init__(package_name, verbose=False)
		self.write_item = _DummyWriteItem

	def _get_name(self) -> str:
		return "dummy"

	def read_package(self, infile: str) -> None:
		raise NotImplementedError

	def save_package(
		self, item_bank: qti_package_maker.assessment_items.item_bank.ItemBank, outfile: str = None
	) -> None:
		raise NotImplementedError


class EngineWithModuleWriteItem(qti_package_maker.engines.base_engine.BaseEngine):
	def __init__(self, package_name: str, write_item_module: types.SimpleNamespace) -> None:
		super().__init__(package_name, verbose=False)
		self.write_item = write_item_module

	def _get_name(self) -> str:
		return "dummy"

	def read_package(self, infile: str) -> None:
		raise NotImplementedError

	def save_package(
		self, item_bank: qti_package_maker.assessment_items.item_bank.ItemBank, outfile: str = None
	) -> None:
		raise NotImplementedError


def test_get_outfile_name_default_prefix() -> None:
	engine = DummyEngine("sample")
	assert engine.get_outfile_name("qti12", "zip") == "qti12-sample.zip"


def test_get_outfile_name_respects_existing_prefix() -> None:
	engine = DummyEngine("sample")
	assert engine.get_outfile_name("qti12", "zip", "qti12-sample.zip") == "qti12-sample.zip"


def test_process_item_bank_empty() -> None:
	engine = DummyEngine("sample")
	empty_bank = qti_package_maker.assessment_items.item_bank.ItemBank()
	assert engine.process_item_bank(empty_bank) == []
	assert engine.process_random_item_from_item_bank(empty_bank) is None


def test_validate_write_item_module_accepts_correct_path(tmp_path: pathlib.Path) -> None:
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	engine.validate_write_item_module()


def test_validate_write_item_module_rejects_wrong_path(tmp_path: pathlib.Path) -> None:
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "not_dummy" / "write_item.py")
	def mc_writer(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
		return "ok"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	with pytest.raises(ImportError):
		engine.validate_write_item_module()


def test_get_available_question_types(tmp_path: pathlib.Path) -> None:
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
		return "ok"
	def hidden_writer(item_cls: object) -> str:
		return "skip"
	write_item_module.MC = mc_writer
	write_item_module._hidden = hidden_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	available = engine.get_available_question_types()
	assert "MC" in available


def test_process_item_bank_skips_unsupported(
	capsys: pytest.CaptureFixture, tmp_path: pathlib.Path
) -> None:
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
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


def test_process_item_bank_pre_render_transform_feeds_write_function(
	tmp_path: pathlib.Path,
) -> None:
	# The write function echoes whatever object it is handed, so the returned
	# render proves item_transform_fn ran BEFORE the write function.
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: object) -> object:
		return item_cls
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	bank = qti_package_maker.assessment_items.item_bank.ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	def transform(item_cls: object) -> str:
		return "TRANSFORMED"
	rendered = engine.process_item_bank(bank, item_transform_fn=transform)
	assert rendered == ["TRANSFORMED"]


def test_process_item_bank_post_render_transform_rewrites_output(
	tmp_path: pathlib.Path,
) -> None:
	# post_render_fn runs on the rendered output only, so the returned render
	# proves it ran AFTER the write function produced "raw".
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: object) -> str:
		return "raw"
	write_item_module.MC = mc_writer
	engine = EngineWithModuleWriteItem("sample", write_item_module)
	bank = qti_package_maker.assessment_items.item_bank.ItemBank()
	bank.add_item("MC", ("Q1?", ["A", "B"], "A"))
	def post(item_cls: object, rendered: str) -> str:
		return rendered + "-post"
	rendered = engine.process_item_bank(bank, post_render_fn=post)
	assert rendered == ["raw-post"]


def test_process_random_item_does_not_reorder(tmp_path: pathlib.Path) -> None:
	write_item_module = types.SimpleNamespace()
	write_item_module.__file__ = str(tmp_path / "dummy" / "write_item.py")
	def mc_writer(item_cls: qti_package_maker.assessment_items.item_types.MC) -> str:
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
