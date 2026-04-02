ENGINE_NAME = "exam_yaml"

# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.common import string_functions

"""
Render assessment items into exam YAML question dicts.
Each function returns a Python dict representing a single question object
in the exam YAML format. The engine_class assembles these into the full
YAML document structure.

This is a lossy export: exam YAML is a print-oriented format without
answer keys or scoring metadata.
"""

#==============================================================
def MC(item_cls) -> dict:
	"""Render an MC item as an exam YAML question dict."""
	question_text = item_cls.question_text
	# Strip letter prefixes from choices (exam YAML uses plain text)
	choices_list = string_functions.remove_prefix_from_list(
		list(item_cls.choices_list)
	)
	question_dict = {
		"statement": question_text,
		"choices": choices_list,
	}
	return question_dict

#==============================================================
def MA(item_cls) -> dict:
	"""Render an MA item as an exam YAML question dict.
	Multiple-correct answer info is lost in exam YAML.
	"""
	question_text = item_cls.question_text
	# Strip letter prefixes from choices
	choices_list = string_functions.remove_prefix_from_list(
		list(item_cls.choices_list)
	)
	question_dict = {
		"statement": question_text,
		"choices": choices_list,
	}
	return question_dict

#==============================================================
def MATCH(item_cls) -> dict:
	"""Render a MATCH item as an exam YAML question dict with a 2-column table."""
	question_text = item_cls.question_text
	# Build a 2-column table from prompts and choices
	columns = ["Prompt", "Answer"]
	rows = []
	for i in range(len(item_cls.prompts_list)):
		prompt_text = item_cls.prompts_list[i]
		choice_text = item_cls.choices_list[i]
		rows.append([prompt_text, choice_text])
	question_dict = {
		"statement": question_text,
		"table": {
			"columns": columns,
			"rows": rows,
		},
	}
	return question_dict

#==============================================================
def NUM(item_cls) -> dict:
	"""Render a NUM item as an exam YAML question dict.
	Numeric answer and tolerance are lost in exam YAML.
	"""
	question_dict = {
		"statement": item_cls.question_text,
	}
	return question_dict

#==============================================================
def FIB(item_cls) -> dict:
	"""Render a FIB item as an exam YAML question dict.
	Fill-in-blank answers are lost in exam YAML.
	"""
	question_dict = {
		"statement": item_cls.question_text,
	}
	return question_dict

#==============================================================
def MULTI_FIB(item_cls) -> dict:
	"""Render a MULTI_FIB item as an exam YAML question dict.
	Answer map is lost in exam YAML.
	"""
	question_dict = {
		"statement": item_cls.question_text,
	}
	return question_dict

#==============================================================
def ORDER(item_cls) -> dict:
	"""Render an ORDER item as an exam YAML question dict.
	Ordering semantics are lost; choices are written but order meaning is gone.
	"""
	question_text = item_cls.question_text
	# Use ordered_answers_list as choices
	choices_list = list(item_cls.ordered_answers_list)
	question_dict = {
		"statement": question_text,
		"choices": choices_list,
	}
	return question_dict
