# Standard Library
import os
import re

# QTI Package Maker
import qti_package_maker.engines.engine_registration


def test_docs_engine_names_in_registry():
	qti_package_maker.engines.engine_registration.register_engines()
	repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	engines_doc = os.path.join(repo_root, "docs", "ENGINES.md")
	with open(engines_doc, "r", encoding="utf-8") as f:
		text = f.read()
	doc_engine_names = {
		name for name in re.findall(r"`([a-z0-9_]+)`", text)
		if "_" in name
	}
	registry_names = set(qti_package_maker.engines.engine_registration.ENGINE_REGISTRY.keys())
	assert doc_engine_names.issubset(registry_names)
