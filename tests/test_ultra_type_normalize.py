"""Unit tests for bb_ultra_qti_v2_1.type_normalize module."""

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.bb_ultra_qti_v2_1 import type_normalize


#============================================
def _mc():
	return item_types.MC(
		question_text="What is 2+2?",
		choices_list=["3", "4", "5"],
		answer_text="4",
	)


def _order(n: int):
	labels = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth"][:n]
	return item_types.ORDER(
		question_text="Order these",
		ordered_answers_list=labels,
	)


#============================================
def test_supported_types_pass_through_unchanged():
	# The six non-ORDER types must be returned as-is with no warnings.
	items = [
		_mc(),
		item_types.MA(
			question_text="Primes?",
			choices_list=["2", "3", "4", "5"],
			answers_list=["2", "3", "5"],
		),
		item_types.MATCH(
			question_text="Match",
			prompts_list=["A", "B"],
			choices_list=["1", "2"],
		),
		item_types.NUM(
			question_text="Pi?",
			answer_float=3.14,
			tolerance_float=0.01,
		),
		item_types.FIB(
			question_text="Capital?",
			answers_list=["Paris"],
		),
		item_types.MULTI_FIB(
			question_text="The [a] is [b].",
			answer_map={"a": ["sky"], "b": ["blue"]},
		),
	]
	kept, warnings = type_normalize.normalize_items(items)
	assert kept == items
	assert warnings == []


#============================================
def test_skip_policy_drops_order_with_warning():
	kept, warnings = type_normalize.normalize_items(
		[_mc(), _order(3)],
		ultra_order_mapping="skip",
	)
	assert len(kept) == 1
	assert isinstance(kept[0], item_types.MC)
	assert warnings


#============================================
def test_mc_policy_converts_order_to_permutation_mc():
	# 3! = 6 unique permutation choices; correct answer must be among them
	# and every choice must mention every original item.
	kept, warnings = type_normalize.normalize_items(
		[_order(3)],
		ultra_order_mapping="mc",
	)
	assert warnings == []
	converted = kept[0]
	assert isinstance(converted, item_types.MC)
	choices = converted.choices_list
	assert len(set(choices)) == 6
	assert converted.answer_text in choices
	for label in ("First", "Second", "Third"):
		assert all(label in choice for choice in choices)


#============================================
def test_mc_policy_falls_back_when_order_too_large():
	# 6! = 720 choices is unusable, so mc policy falls back to skip.
	kept, warnings = type_normalize.normalize_items(
		[_order(6)],
		ultra_order_mapping="mc",
	)
	assert kept == []
	assert warnings


#============================================
def test_match_policy_converts_order_deterministically():
	# Two runs of MATCH conversion must shuffle identically so that
	# re-running the exporter produces byte-stable output.
	kept1, _ = type_normalize.normalize_items([_order(4)], ultra_order_mapping="match")
	kept2, _ = type_normalize.normalize_items([_order(4)], ultra_order_mapping="match")
	match1 = kept1[0]
	match2 = kept2[0]
	assert isinstance(match1, item_types.MATCH)
	assert match1.prompts_list == match2.prompts_list
	# Every original ORDER label must survive the conversion.
	assert set(match1.prompts_list) == {"First", "Second", "Third", "Fourth"}
