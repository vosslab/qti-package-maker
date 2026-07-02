ENGINE_NAME = "html_selftest"

#from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.html_selftest import add_MC
from qti_package_maker.engines.html_selftest import add_MA
from qti_package_maker.engines.html_selftest import add_MATCH
from qti_package_maker.engines.html_selftest import add_NUM
from qti_package_maker.engines.html_selftest import add_FIB
from qti_package_maker.engines.html_selftest import add_MULTI_FIB
from qti_package_maker.engines.html_selftest import add_ORDER
from qti_package_maker.engines.html_selftest import html_functions

#==============================================================
def _wrap_selftest_html(html_text: str) -> str:
	theme_css = html_functions.add_selftest_theme_css()
	wrapped = f"{theme_css}<div class=\"qti-selftest\">\n{html_text}\n</div>\n"
	return html_functions.escape_non_ascii(wrapped)

#==============================================================
def MC(item_cls: item_types.MC) -> str:
	#item_number: int, item_crc16: str, question_text: str, choices_list: list, answer_text: str):
	"""Render an MC item as HTML self-test content."""
	html_text = add_MC.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.choices_list,
		item_cls.answer_text,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
def MA(item_cls: item_types.MA) -> str:
	#item_number: int, item_crc16: str, question_text: str, choices_list: list, answers_list: list):
	"""Render an MA item as HTML self-test content."""
	html_text = add_MA.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.choices_list,
		item_cls.answers_list,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
def MATCH(item_cls: item_types.MATCH) -> str:
	#item_number: int, item_crc16: str, question_text: str, prompts_list: list, choices_list: list):
	"""Render a MATCH item as HTML self-test content."""
	html_text = add_MATCH.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.prompts_list,
		item_cls.choices_list,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
def NUM(item_cls: item_types.NUM) -> str:
	#item_number: int, item_crc16: str,
	#question_text: str, answer_float: float, tolerance_float: float, tolerance_message=True):
	"""Render a NUM item as HTML self-test content."""
	html_text = add_NUM.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.answer_float,
		item_cls.tolerance_float,
		item_cls.tolerance_message,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
def FIB(item_cls: item_types.FIB) -> str:
	#item_number: int, item_crc16: str, question_text: str, answers_list: list):
	"""Render a FIB item as HTML self-test content."""
	html_text = add_FIB.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.answers_list,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> str:
	#item_number: int, item_crc16: str, question_text: str, answer_map: dict) -> str:
	"""Render a MULTI_FIB item as HTML self-test content."""
	html_text = add_MULTI_FIB.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.answer_map,
	)
	return _wrap_selftest_html(html_text)

#==============================================================
def ORDER(item_cls: item_types.ORDER) -> str:
	#item_number: int, item_crc16: str, question_text: str, ordered_answers_list: list):
	"""Render an ORDER item as HTML self-test content."""
	html_text = add_ORDER.generate_html(
		item_cls.item_number,
		item_cls.item_crc16,
		item_cls.question_text,
		item_cls.ordered_answers_list,
	)
	return _wrap_selftest_html(html_text)
