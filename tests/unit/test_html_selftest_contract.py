"""
Result-string contract tests for html_selftest engines.

The bp-website runtime (site_docs/assets/scripts/selftest_progress.js) classifies
a self-test answer as "full-correct" (marks complete, plays sound/confetti) only
when the generated result text matches one of these exact patterns:
  - literal 'CORRECT'
  - 'Total Score: X out of Y' with X == Y
  - 'Correct positions: X of Y' with X == Y
  - 'Correct: X of Y' with X == Y    (NOTE: MULTI_FIB partial only; full-correct emits 'CORRECT')

The runtime also relies on element IDs:
  - question_html_<crc>
  - result_<crc>
And the global function:
  - checkAnswer_<crc>()

If a future engine edit rewords any result string or renames any identifier, these
tests will catch the regression before the website silently stops marking questions
complete.

Coverage note: MULTI_FIB's full-correct case emits 'CORRECT' (same as MC/MA/NUM/FIB),
not 'Correct: X of Y'. The 'Correct: X of Y' string only appears in the partial-correct
branch. Both strings are asserted here because the runtime grep checks both.
"""

# PIP3 modules
import pytest

# QTI Package Maker
import qti_package_maker.assessment_items.item_types
import qti_package_maker.engines.html_selftest.add_FIB
import qti_package_maker.engines.html_selftest.add_MA
import qti_package_maker.engines.html_selftest.add_MATCH
import qti_package_maker.engines.html_selftest.add_MC
import qti_package_maker.engines.html_selftest.add_MULTI_FIB
import qti_package_maker.engines.html_selftest.add_NUM
import qti_package_maker.engines.html_selftest.add_ORDER
import qti_package_maker.engines.html_selftest.write_item

#============================================
def _full_html(item_type: str, sample_items: dict) -> str:
	"""
	Build the complete selftest HTML for an item type using the write_item API.
	"""
	tuples = sample_items[item_type]
	item_cls = _build_item(item_type, tuples)
	return getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)

#============================================
def _build_item(
	item_type: str, item_tuple: tuple
) -> qti_package_maker.assessment_items.item_types.BaseItem:
	"""Construct an assessment item object from a tuple of constructor args."""
	if item_type == "MC":
		return qti_package_maker.assessment_items.item_types.MC(*item_tuple)
	if item_type == "MA":
		return qti_package_maker.assessment_items.item_types.MA(*item_tuple)
	if item_type == "MATCH":
		return qti_package_maker.assessment_items.item_types.MATCH(*item_tuple)
	if item_type == "NUM":
		return qti_package_maker.assessment_items.item_types.NUM(*item_tuple)
	if item_type == "FIB":
		return qti_package_maker.assessment_items.item_types.FIB(*item_tuple)
	if item_type == "MULTI_FIB":
		return qti_package_maker.assessment_items.item_types.MULTI_FIB(*item_tuple)
	if item_type == "ORDER":
		return qti_package_maker.assessment_items.item_types.ORDER(*item_tuple)
	raise ValueError(f"Unsupported item type: {item_type}")

#============================================
# Identifier contract: question_html_<crc>, result_<crc>, checkAnswer_<crc>
#============================================

@pytest.mark.parametrize("item_type", ["MC", "MA", "MATCH", "NUM", "FIB", "MULTI_FIB", "ORDER"])
def test_contract_element_ids_present(sample_items: dict, item_type: str) -> None:
	"""
	Every engine must emit the element IDs and function name that selftest_progress.js
	relies on: question_html_<crc>, result_<crc>, and checkAnswer_<crc>().
	"""
	item_cls = _build_item(item_type, sample_items[item_type])
	crc = item_cls.item_crc16
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	# Verify scoped container ID
	assert f"question_html_{crc}" in html_text
	# Verify result div ID
	assert f"result_{crc}" in html_text
	# Verify checkAnswer function name
	assert f"checkAnswer_{crc}" in html_text

#============================================
# Result-string contract: 'CORRECT' for MC, MA, NUM, FIB, MULTI_FIB (full-correct path)
#============================================

@pytest.mark.parametrize("item_type", ["MC", "MA", "NUM", "FIB", "MULTI_FIB"])
def test_contract_correct_string_emitted(sample_items: dict, item_type: str) -> None:
	"""
	MC, MA, NUM, FIB, and MULTI_FIB (full-correct path) all emit the literal string
	'CORRECT' in their generated JavaScript. selftest_progress.js checks for this
	exact string to trigger the completion animation.
	"""
	item_cls = _build_item(item_type, sample_items[item_type])
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	assert "'CORRECT'" in html_text

#============================================
# Result-string contract: MATCH emits 'Total Score: ${score} out of ${possible}'
#============================================

def test_contract_match_total_score_string(sample_items: dict) -> None:
	"""
	MATCH engine emits the JS template literal 'Total Score: ${score} out of ${possible}'.
	selftest_progress.js matches 'Total Score: X out of Y' with X==Y for full-correct.
	"""
	item_cls = _build_item("MATCH", sample_items["MATCH"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MATCH(item_cls)
	# The template literal in generated JS must contain this exact substring
	assert "Total Score: ${score} out of ${possible}" in html_text

#============================================
# Result-string contract: ORDER emits 'Correct positions: ${correct} of ${total}'
#============================================

def test_contract_order_correct_positions_string(sample_items: dict) -> None:
	"""
	ORDER engine emits the JS template literal 'Correct positions: ${correct} of ${total}'.
	selftest_progress.js matches 'Correct positions: X of Y' with X==Y for full-correct.
	"""
	item_cls = _build_item("ORDER", sample_items["ORDER"])
	html_text = qti_package_maker.engines.html_selftest.write_item.ORDER(item_cls)
	# The template literal in generated JS must contain this exact substring
	assert "Correct positions: ${correct} of ${total}" in html_text

#============================================
# Result-string contract: MULTI_FIB partial path emits 'Correct: ${correctCount} of ${inputs.length}'
#============================================

def test_contract_multi_fib_partial_correct_string(sample_items: dict) -> None:
	"""
	MULTI_FIB emits 'Correct: ${correctCount} of ${inputs.length}' for the partial-correct
	path. selftest_progress.js also checks for 'Correct: X of Y' to show partial feedback.
	Note: full-correct emits 'CORRECT' (covered by test_contract_correct_string_emitted).
	"""
	item_cls = _build_item("MULTI_FIB", sample_items["MULTI_FIB"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MULTI_FIB(item_cls)
	# The template literal in generated JS must contain this exact substring
	assert "Correct: ${correctCount} of ${inputs.length}" in html_text
