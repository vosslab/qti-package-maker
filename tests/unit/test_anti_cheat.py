# Standard Library
import random

# Pip3 Library

# QTI Package Maker
import qti_package_maker.common.anti_cheat


def test_insert_hidden_terms_skips_excluded_tags():
	random.seed(0)
	term_adder = qti_package_maker.common.anti_cheat.AntiCheat(hidden_terms=True, no_click_div=False, anticopy_script=False)
	term_adder.hidden_term_density = 1.0
	original_text = (
		"<p>This is a test paragraph. It should have hidden terms.</p>"
		"<table><tr><td>Do not modify this table content.</td></tr></table>"
		"<code>print('This should not be changed')</code>"
	)
	modified_text = term_adder.insert_hidden_terms(original_text)
	assert modified_text != original_text
	assert len(modified_text) > len(original_text)
	assert "<table><tr><td>Do not modify this table content.</td></tr></table>" in modified_text
	assert "<code>print('This should not be changed')</code>" in modified_text


def test_wrap_text_in_no_click_div():
	div_adder = qti_package_maker.common.anti_cheat.AntiCheat(hidden_terms=False, no_click_div=True, anticopy_script=False)
	protected_text = div_adder.modify_string("Protected text")
	assert protected_text.startswith("<div ")
	assert protected_text.endswith("</div>")


def test_insert_hidden_terms_density_zero_no_change():
	random.seed(1)
	term_adder = qti_package_maker.common.anti_cheat.AntiCheat(hidden_terms=True, no_click_div=False, anticopy_script=False)
	term_adder.hidden_term_density = 0.0
	original_text = "<p>Simple text for testing.</p>"
	modified_text = term_adder.insert_hidden_terms(original_text)
	assert modified_text.strip() == original_text
