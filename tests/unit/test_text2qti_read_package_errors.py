# Standard Library

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.engines.text2qti import read_package


def test_read_mc_multiple_correct_raises() -> None:
	question_block = """1. What is 2+2?
*a) 4
b) 3
*c) 5
"""
	with pytest.raises(ValueError):
		read_package.read_MC(question_block, 1)


def test_read_num_invalid_format_raises() -> None:
	question_block = """1. What is 2+2?
= not-a-number
"""
	with pytest.raises(ValueError):
		read_package.read_NUM(question_block, 1)


def test_read_num_with_underscores() -> None:
	question_block = """1. What is 1000?
= 1_000
"""
	item = read_package.read_NUM(question_block, 1)
	assert item.answer_float == 1000.0
	assert item.tolerance_float == 0.0


def test_read_fib_requires_answer() -> None:
	question_block = """1. Who lives at the North Pole?
... hint only
"""
	with pytest.raises(ValueError):
		read_package.read_FIB(question_block, 1)
