# Standard Library

# Pip3 Library

# QTI Package Maker
import qti_package_maker.engines.engine_registration


def test_engine_registry_includes_expected_engines():
	qti_package_maker.engines.engine_registration.register_engines()
	available = set(qti_package_maker.engines.engine_registration.ENGINE_REGISTRY.keys())
	expected = {
		"bbq_text_upload",
		"blackboard_qti_v2_1",
		"canvas_qti_v1_2",
		"html_selftest",
		"human_readable",
		"text2qti",
	}
	assert expected.issubset(available)


def test_engine_read_write_flags():
	qti_package_maker.engines.engine_registration.register_engines()
	canvas = qti_package_maker.engines.engine_registration.ENGINE_REGISTRY["canvas_qti_v1_2"]
	blackboard = qti_package_maker.engines.engine_registration.ENGINE_REGISTRY["blackboard_qti_v2_1"]
	bbq = qti_package_maker.engines.engine_registration.ENGINE_REGISTRY["bbq_text_upload"]

	assert canvas["can_read"] is False
	assert canvas["can_write"] is True
	assert blackboard["can_read"] is False
	assert blackboard["can_write"] is True
	assert bbq["can_read"] is True
	assert bbq["can_write"] is True


def test_engine_registry_names_match_keys():
	qti_package_maker.engines.engine_registration.register_engines()
	for key, info in qti_package_maker.engines.engine_registration.ENGINE_REGISTRY.items():
		assert info["engine_name"] == key


def test_is_method_implemented_detects_stub():
	class DummyImplemented:
		def do_work(self):
			return "ok"

	class DummyNotImplemented:
		def do_work(self):
			raise NotImplementedError

	assert qti_package_maker.engines.engine_registration.is_method_implemented(DummyImplemented, "do_work") is True
	assert qti_package_maker.engines.engine_registration.is_method_implemented(DummyNotImplemented, "do_work") is False
	assert qti_package_maker.engines.engine_registration.is_method_implemented(DummyImplemented, "missing") is False
