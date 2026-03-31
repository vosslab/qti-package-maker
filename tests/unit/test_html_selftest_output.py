# Standard Library
import pytest

# QTI Package Maker
import qti_package_maker.assessment_items.item_types
import qti_package_maker.engines.html_selftest.write_item
import qti_package_maker.engines.html_selftest.html_functions


def _build_item(item_type: str, item_tuple):
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
def test_html_selftest_outputs_are_valid_html(sample_items, item_type):
	item_cls = _build_item(item_type, sample_items[item_type])
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	assert html_text
	assert "qti-selftest" in html_text
	qti_package_maker.engines.html_selftest.html_functions.validate_selftest_html(html_text)


def test_html_selftest_theme_css_contains_palette_selectors(sample_items):
	item_cls = _build_item("MC", sample_items["MC"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MC(item_cls)
	assert "qti-selftest-theme" in html_text
	assert "prefers-color-scheme: dark" in html_text
	assert "data-md-color-scheme" in html_text
	assert "slate" in html_text
	assert "default" in html_text
	assert "--qti-choice-1-bg" in html_text


@pytest.mark.parametrize("item_type", ["MATCH", "ORDER"])
def test_html_selftest_choice_palette_classes(sample_items, item_type):
	item_cls = _build_item(item_type, sample_items[item_type])
	html_text = getattr(qti_package_maker.engines.html_selftest.write_item, item_type)(item_cls)
	assert "qti-choice-" in html_text
	assert "var(--qti-choice-" in html_text
	assert "qti-dropzone" in html_text


def test_html_selftest_num_input_uses_theme_class(sample_items):
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


def test_html_selftest_match_scopes_dropzone_queries(sample_items):
	item_cls = _build_item("MATCH", sample_items["MATCH"])
	html_text = qti_package_maker.engines.html_selftest.write_item.MATCH(item_cls)
	_assert_scoped_dropzone_queries(html_text, item_cls.item_crc16)


def test_html_selftest_order_scopes_dropzone_queries(sample_items):
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
def test_determine_choice_layout_class(num_choices, expected_class):
	"""Test that determine_choice_layout_class returns correct classes for different choice counts."""
	choices_list = [f"Choice {i}" for i in range(num_choices)]
	result = qti_package_maker.engines.html_selftest.html_functions.determine_choice_layout_class(choices_list)
	assert result == expected_class


@pytest.mark.parametrize("num_choices,expected_class", [
	(3, None),  # 3 choices: no grid class expected
	(4, "qti-auto-grid-compact"),
	(6, "qti-auto-grid"),
])
def test_html_selftest_mc_adaptive_grid_classes(num_choices, expected_class):
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
def test_html_selftest_ma_adaptive_grid_classes(num_choices, expected_class):
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
