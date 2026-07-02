# Standard Library
import pytest

# QTI Package Maker
import qti_package_maker.assessment_items.item_types
import qti_package_maker.engines.html_selftest.add_FIB
import qti_package_maker.engines.html_selftest.write_item
import qti_package_maker.engines.html_selftest.html_functions


def _build_item(
	item_type: str, item_tuple: tuple
) -> qti_package_maker.assessment_items.item_types.BaseItem:
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


@pytest.mark.parametrize("item_type", ["MC", "MA", "MATCH", "NUM", "FIB", "MULTI_FIB", "ORDER"])
def test_html_selftest_outputs_are_valid_html(sample_items: dict, item_type: str) -> None:
	item_cls = _build_item(item_type, sample_items[item_type])
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	assert html_text
	assert "qti-selftest" in html_text
	qti_package_maker.engines.html_selftest.html_functions.validate_selftest_html(html_text)


def test_html_selftest_theme_css_contains_palette_selectors(sample_items: dict) -> None:
	item_cls = _build_item("MC", sample_items["MC"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MC(item_cls)
	assert "qti-selftest-theme" in html_text
	assert "prefers-color-scheme: dark" in html_text
	assert "data-md-color-scheme" in html_text
	assert "slate" in html_text
	assert "default" in html_text
	assert "--qti-choice-1-bg" in html_text


@pytest.mark.parametrize("item_type", ["MATCH", "ORDER"])
def test_html_selftest_choice_palette_classes(sample_items: dict, item_type: str) -> None:
	item_cls = _build_item(item_type, sample_items[item_type])
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	assert "qti-choice-" in html_text
	assert "var(--qti-choice-" in html_text
	assert "qti-dropzone" in html_text


def test_html_selftest_num_input_uses_theme_class(sample_items: dict) -> None:
	item_cls = _build_item("NUM", sample_items["NUM"])
	html_text = qti_package_maker.engines.html_selftest.write_item.NUM(item_cls)
	assert "qti-input" in html_text


def _assert_scoped_dropzone_queries(html_text: str, crc16_text: str) -> None:
	container_marker = f"question_html_{crc16_text}"
	assert container_marker in html_text
	assert f"document.getElementById('question_html_{crc16_text}')" in html_text
	assert (
		'container.querySelectorAll(".dropzone")' in html_text
		or "container.querySelectorAll('.dropzone')" in html_text
	)
	assert (
		'container.querySelectorAll(".feedback")' in html_text
		or "container.querySelectorAll('.feedback')" in html_text
	)
	assert 'document.querySelectorAll(".dropzone")' not in html_text
	assert "document.querySelectorAll('.dropzone')" not in html_text
	assert 'document.querySelectorAll(".feedback")' not in html_text
	assert "document.querySelectorAll('.feedback')" not in html_text


def test_html_selftest_match_scopes_dropzone_queries(sample_items: dict) -> None:
	item_cls = _build_item("MATCH", sample_items["MATCH"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MATCH(item_cls)
	_assert_scoped_dropzone_queries(html_text, item_cls.item_crc16)


def test_html_selftest_order_scopes_dropzone_queries(sample_items: dict) -> None:
	item_cls = _build_item("ORDER", sample_items["ORDER"])
	html_text = qti_package_maker.engines.html_selftest.write_item.ORDER(item_cls)
	_assert_scoped_dropzone_queries(html_text, item_cls.item_crc16)


@pytest.mark.parametrize("num_choices,expected_class", [
	(2, ""),  # 2 choices: vertical layout (no class)
	(3, ""),  # 3 choices: vertical layout (no class)
	(4, "qti-auto-grid-compact"),  # 4 choices: compact grid
	(5, "qti-auto-grid-compact"),  # 5 choices: compact grid
	(6, "qti-auto-grid"),  # 6 choices: standard grid
	(7, "qti-auto-grid"),  # 7 choices: standard grid
	(8, "qti-auto-grid"),  # 8+ choices: standard grid
])
def test_determine_choice_layout_class(num_choices: int, expected_class: str) -> None:
	"""Test that determine_choice_layout_class returns correct classes for different choice counts."""
	choices_list = [f"Choice {i}" for i in range(num_choices)]
	result = qti_package_maker.engines.html_selftest.html_functions.determine_choice_layout_class(choices_list)
	assert result == expected_class


@pytest.mark.parametrize("num_choices,expected_class", [
	(3, None),  # 3 choices: no grid class expected
	(4, "qti-auto-grid-compact"),
	(6, "qti-auto-grid"),
])
def test_html_selftest_mc_adaptive_grid_classes(num_choices: int, expected_class: str | None) -> None:
	"""Test that MC items get correct adaptive grid classes in HTML output."""
	choices_list = [f"Choice {chr(65 + i)}" for i in range(num_choices)]
	item = qti_package_maker.assessment_items.item_types.MC(
		question_text="Test question",
		choices_list=choices_list,
		answer_text=choices_list[0]
	)
	html_text = qti_package_maker.engines.html_selftest.write_item.MC(item)

	if expected_class:
		assert f'class="{expected_class}"' in html_text
	else:
		# For 3 choices, should have <ul id="choices_..."> with no class attribute
		assert '<ul id="choices_' in html_text
		assert 'class="qti-auto-grid' not in html_text


@pytest.mark.parametrize("num_choices,expected_class", [
	(3, None),  # 3 choices: no grid class expected
	(4, "qti-auto-grid-compact"),
	(6, "qti-auto-grid"),
])
def test_html_selftest_ma_adaptive_grid_classes(num_choices: int, expected_class: str | None) -> None:
	"""Test that MA items get correct adaptive grid classes in HTML output."""
	choices_list = [f"Choice {chr(65 + i)}" for i in range(num_choices)]
	item = qti_package_maker.assessment_items.item_types.MA(
		question_text="Select all that apply",
		choices_list=choices_list,
		answers_list=[choices_list[0], choices_list[1]]
	)
	html_text = qti_package_maker.engines.html_selftest.write_item.MA(item)

	if expected_class:
		assert f'class="{expected_class}"' in html_text
	else:
		# For 3 choices, should have <ul id="choices_..."> with no class attribute
		assert '<ul id="choices_' in html_text
		assert 'class="qti-auto-grid' not in html_text


def test_fib_js_uses_crc_not_literal_placeholder() -> None:
	# Verify the f-string fix: emitted JS must reference the actual crc, not the literal placeholder
	sample_crc = "ab12"
	js = qti_package_maker.engines.html_selftest.add_FIB.generate_javascript(sample_crc, ["answer"])
	assert f"fibAnswers_{sample_crc}.includes" in js
	assert "{crc16_text}" not in js


def test_fib_js_answers_array_is_valid_js_with_special_chars() -> None:
	# Python repr of ["it's correct"] emits ['it\'s correct'] - a JS syntax error.
	# json.dumps emits ["it's correct"] - valid JS where the apostrophe is inside double quotes.
	sample_crc = "cd34"
	tricky_answers = ["it's correct", "cafe"]
	js = qti_package_maker.engines.html_selftest.add_FIB.generate_javascript(sample_crc, tricky_answers)
	# Locate the array assignment line
	array_line = next(
		(line for line in js.splitlines() if f"fibAnswers_{sample_crc} =" in line),
		None,
	)
	assert array_line is not None, f"No fibAnswers_{sample_crc} assignment line found in generated JS"
	# The RHS must be a JSON array (starts with "["), not a Python repr list (starts with "['" or "['")
	rhs = array_line.split("= ", 1)[1].rstrip(";")
	assert rhs.startswith("["), f"Expected JSON array starting with '[', got: {rhs[:20]!r}"
	# json.dumps always wraps string elements in double quotes
	assert rhs.startswith('["'), f"Array elements should be double-quoted JSON strings: {rhs!r}"


def test_fib_js_uses_feedback_classes() -> None:
	# Verify feedback uses pill classes instead of inline hardcoded colors
	sample_crc = "ab12"
	js = qti_package_maker.engines.html_selftest.add_FIB.generate_javascript(sample_crc, ["answer"])
	# Classes carry theme-var colors via CSS; no hardcoded color strings should appear
	assert "qti-feedback-success" in js
	assert "qti-feedback-error" in js
	assert "'green'" not in js
	assert "'red'" not in js


def test_mc_js_sets_feedback_classes_and_disables_check(sample_items: dict) -> None:
	"""
	MC generated JS must:
	- set qti-feedback-success on the result element when the answer is CORRECT
	- set qti-feedback-error on the result element when the answer is incorrect
	- still emit the literal string 'CORRECT' as the textContent value
	- disable the Check button (checkBtn.disabled = true) on correct
	"""
	item_cls = qti_package_maker.assessment_items.item_types.MC(*sample_items["MC"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MC(item_cls)
	# Feedback pill classes must be set in the JS
	assert "qti-feedback-success" in html_text
	assert "qti-feedback-error" in html_text
	# The textContent for full-correct must still be the exact string the bp-website classifier reads
	assert "'CORRECT'" in html_text
	# Check button must be disabled on correct (not relabeled or hidden)
	assert "checkBtn.disabled = true" in html_text


def test_ma_clear_selection_button_has_reset_class(sample_items: dict) -> None:
	"""
	MA Clear Selection button must carry qti-btn-reset so it renders as a ghost button.
	"""
	item_cls = qti_package_maker.assessment_items.item_types.MA(*sample_items["MA"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MA(item_cls)
	# The Clear Selection button must have the ghost/secondary class
	assert "qti-btn-reset" in html_text
