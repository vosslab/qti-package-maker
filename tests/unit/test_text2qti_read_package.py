# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.text2qti import read_package


def test_read_mc_multiline_stem_and_feedback() -> None:
	question_block = """1. What is 2+3?
Consider basic math.
a) 6
... not right
*b) 5
... correct
c) 7
"""
	item = read_package.read_MC(question_block, 1)
	assert isinstance(item, item_types.MC)
	assert item.question_text == "What is 2+3? Consider basic math."
	assert item.answer_text == "5"
	assert item.choice_feedback["6"] == "not right"
	assert item.choice_feedback["5"] == "correct"


def test_read_ma_multiline_stem_and_feedback() -> None:
	question_block = """1. Which are primes?
Choose all that apply.
[ ] 4
[*] 2
[*] 3
... nice pick
[ ] 9
"""
	item = read_package.read_MA(question_block, 1)
	assert isinstance(item, item_types.MA)
	assert item.question_text == "Which are primes? Choose all that apply."
	assert set(item.answers_list) == {"2", "3"}
	assert item.choice_feedback["3"] == "nice pick"


def test_read_num_range_and_tolerance() -> None:
	question_block = """1. What is sqrt(2)?
= [1.4140, 1.4144]
... use a calculator
"""
	item = read_package.read_NUM(question_block, 1)
	assert isinstance(item, item_types.NUM)
	assert item.answer_float == pytest.approx(1.4142)
	assert item.tolerance_float == pytest.approx(0.0002)
	assert item.answer_feedback == "use a calculator"


def test_read_num_missing_tolerance_defaults() -> None:
	question_block = """1. Approx pi?
= 3.14
"""
	item = read_package.read_NUM(question_block, 1)
	assert item.answer_float == pytest.approx(3.14)
	assert item.tolerance_float == 0.0


def test_read_fib_multiple_answers_with_feedback() -> None:
	question_block = """1. Who lives at the North Pole?
* Santa
* Santa Claus
... winter folklore
"""
	item = read_package.read_FIB(question_block, 1)
	assert isinstance(item, item_types.FIB)
	assert set(item.answers_list) == {"Santa", "Santa Claus"}
	assert item.answer_feedback == "winter folklore"


def test_split_questions_requires_blank_line_between_blocks() -> None:
	text = """1. What is 2+2?
*a) 4
b) 3

2. Which are vowels?
[ ] B
[*] A
[*] E
"""
	blocks = read_package.split_questions(text)
	assert len(blocks) == 2


def test_process_text_lines_rejects_mixed_when_disallowed() -> None:
	text = """1. What is 2+2?
*a) 4
b) 3

2. Who lives at the North Pole?
* Santa
"""
	with pytest.raises(ValueError):
		read_package.process_text_lines(text, allow_mixed=False)


def test_make_item_cls_from_block_unknown() -> None:
	assert read_package.make_item_cls_from_block("Not a question block") is None
