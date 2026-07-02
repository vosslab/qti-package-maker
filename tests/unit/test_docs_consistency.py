# Standard Library
import os
import re

# QTI Package Maker
import qti_package_maker.engines.engine_registration

# Backticked, underscore-containing identifiers in docs/ENGINES.md that are
# documented but are not engine names (for example EngineClass constructor
# kwargs). Kept small and explicit so this test still fails on a misspelled
# or unregistered engine-like name; only add a name here after confirming it
# refers to a real, intentional non-engine identifier documented elsewhere.
DOC_NON_ENGINE_IDENTIFIERS = {
	# EngineClass constructor kwarg documented in docs/ENGINES.md and
	# docs/MEDIA_LMS_PROBES.md; selects the canvas_qti_v1_2 <img src> variant.
	"canvas_src_variant",
}


def test_docs_engine_names_in_registry() -> None:
	qti_package_maker.engines.engine_registration.register_engines()
	repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	engines_doc = os.path.join(repo_root, "docs", "ENGINES.md")
	with open(engines_doc, "r", encoding="utf-8") as f:
		text = f.read()
	doc_engine_names = {
		name for name in re.findall(r"`([a-z0-9_]+)`", text)
		if "_" in name
	}
	# Drop known non-engine identifiers before checking against the registry.
	doc_engine_names -= DOC_NON_ENGINE_IDENTIFIERS
	registry_names = set(qti_package_maker.engines.engine_registration.ENGINE_REGISTRY.keys())
	assert doc_engine_names.issubset(registry_names)
