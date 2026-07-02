# Standard Library
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
import qti_package_maker.engines.engine_registration


def test_engine_classes_import_and_validate(
	tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
	monkeypatch.chdir(tmp_path)
	qti_package_maker.engines.engine_registration.register_engines()
	for engine_info in qti_package_maker.engines.engine_registration.ENGINE_REGISTRY.values():
		engine_cls = engine_info["engine_class"]
		engine = engine_cls("dummy", verbose=False)
		assert engine.name
		assert engine.write_item is not None
