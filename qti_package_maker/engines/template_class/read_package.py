
# Standard Library

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types

#=====================================================
def read_MC(input_data: object) -> item_types.MC:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	choices_list = input_data
	answer_text = input_data
	item_cls = item_types.MC(question_text, choices_list, answer_text)
	return item_cls

#=====================================================
def read_MA(input_data: object) -> item_types.MA:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	choices_list = input_data
	answers_list = input_data
	item_cls = item_types.MA(question_text, choices_list, answers_list)
	return item_cls

#=====================================================
def read_MATCH(input_data: object) -> item_types.MATCH:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	prompts_list = input_data
	choices_list = input_data
	item_cls = item_types.MATCH(question_text, prompts_list, choices_list)
	return item_cls

#=====================================================
def read_NUM(input_data: object) -> item_types.NUM:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	answer_float = input_data
	tolerance_float = input_data
	item_cls = item_types.NUM(question_text, answer_float, tolerance_float)
	return item_cls

#=====================================================
def read_FIB(input_data: object) -> item_types.FIB:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	answers_list = input_data
	item_cls = item_types.FIB(question_text, answers_list)
	return item_cls

#=====================================================
def read_MULTI_FIB(input_data: object) -> item_types.MULTI_FIB:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	answer_map = input_data
	item_cls = item_types.MULTI_FIB(question_text, answer_map)
	return item_cls

#=====================================================
def read_ORDER(input_data: object) -> item_types.ORDER:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	question_text = input_data
	ordered_answers_list = input_data
	item_cls = item_types.ORDER(question_text, ordered_answers_list)
	return item_cls

#=====================================================
def make_item_cls_from_line(text_line: str) -> None:
	raise NotImplementedError("this is a template class, each engine must write their own function")
	return

#=====================================================
#=====================================================
def read_items_from_file(input_file: str, allow_mixed: bool=False) -> list:
	"""
	Template placeholder for read_items_from_file implementations.
	"""
	raise NotImplementedError("this is a template class, each engine must write their own function")
	new_item_bank = item_bank.ItemBank(allow_mixed)
	# Step 1: Read and process questions from the input file
	with open(input_file, 'r') as f:
		for line in f:
			item_cls = make_item_cls_from_line(line)
			if not item_cls:
				continue
			new_item_bank.add_item_cls(item_cls)
	return new_item_bank

#=====================================================
def main() -> None:
	# put some unit tests here
	pass


if __name__ == "__main__":
	main()
