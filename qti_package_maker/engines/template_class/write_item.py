ENGINE_NAME = "template_class"

#from qti_package_maker.common import string_functions

# QTI Package Maker
from qti_package_maker.assessment_items import item_types

#==============================================================
def MC(item_cls: item_types.MC) -> None:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answer_text: str):
	"""Template placeholder for MC writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
def MA(item_cls: item_types.MA) -> None:
	#item_number: int, crc16_text: str, question_text: str, choices_list: list, answers_list: list):
	"""Template placeholder for MA writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
def MATCH(item_cls: item_types.MATCH) -> None:
	#item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""Template placeholder for MATCH writers."""
	#MAT TAB question text TAB answer text TAB matching text TAB answer two text TAB matching two text
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
def NUM(item_cls: item_types.NUM) -> None:
	#item_number: int, crc16_text: str,
	#question_text: str, answer_float: float, tolerance_float: float, tolerance_message=True):
	"""Template placeholder for NUM writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
def FIB(item_cls: item_types.FIB) -> None:
	#item_number: int, crc16_text: str, question_text: str, answers_list: list):
	"""Template placeholder for FIB writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.MULTI_FIB) -> None:
	#item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Template placeholder for MULTI_FIB writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")

#==============================================================
def ORDER(item_cls: item_types.ORDER) -> None:
	#item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Template placeholder for ORDER writers."""
	raise NotImplementedError("this is a template class, each engine must write their own function")
