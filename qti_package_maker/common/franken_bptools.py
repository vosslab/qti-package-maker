#General Toosl for These Problems
import sys

# QTI Package Maker
from qti_package_maker.common import anti_cheat
from qti_package_maker.common import string_functions

answer_histogram = {}
question_count = 0
crc16_dict = {}

#====================================================================
def question_header_classic(question: str, N: int, big_question: str = None, crc16: str = None) -> str:
	#global use_nocopy_script
	if crc16 is None:
		if big_question is not None:
			crc16 = string_functions.getCrc16_FromString(big_question)
		else:
			crc16 = string_functions.getCrc16_FromString(question)
	if crc16_dict.get(crc16) == 1:
		print('crc16 first hash collision', crc16)
		crc16_dict[crc16] += 1
	elif crc16_dict.get(crc16) == 3:
		print('crc16 third hash collision', crc16, 'after question #', question_count)
		crc16_dict[crc16] += 1
	else:
		crc16_dict[crc16] = 1
	#header = '<p>{0:03d}. {1}</p> {2}'.format(N, crc16, question)
	pretty_question = string_functions.make_question_pretty(question)
	print('{0:03d}. {1} -- {2}'.format(N, crc16, pretty_question))
	noisy_question = anti_cheat.insert_hidden_terms(question)
	text = '<p>{0}</p> {1}'.format(crc16, noisy_question)
	header = ''
	if anti_cheat.use_nocopy_script is True:
		js_function_string = anti_cheat.generate_js_function()
		header += js_function_string
	header += anti_cheat.add_no_click_div(text)
	return header

#====================================================================
def question_header(question: str, N: int, crc16: str = None) -> str:
	"""
	Generate a standardized header for a question.
	"""
	# Generate a CRC16 if not provided
	if crc16 is None:
		crc16 = string_functions.get_crc16_from_string(question)

	# Log the question header
	print(f"{N:03d}. {crc16} -- {string_functions.make_question_pretty(question)}")

	# Generate the header
	header = f"<p>{crc16}</p>\n"
	header += anti_cheat.insert_hidden_terms(question)

	return header

#====================================================================
def choice_header_classic(choice_text: str) -> str:
	noisy_choice_text = anti_cheat.insert_hidden_terms(choice_text)
	output = anti_cheat.add_no_click_div(noisy_choice_text)
	return output

#====================================================================
def choice_header(choice_text: str, index: int) -> str:
	"""
	Format a choice in a standardized way.
	"""
	# Generate a label for the choice (e.g., A, B, C, ...)
	letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
	label = letters[index]

	# Log the choice
	print(f"- [{label}] {string_functions.make_question_pretty(choice_text)}")

	# Add hidden terms for obfuscation, if needed
	noisy_choice_text = anti_cheat.insert_hidden_terms(choice_text)

	# Wrap in a div or any other required format
	return anti_cheat.add_no_click_div(f"{label}. {noisy_choice_text}")

#====================================================================
def print_histogram() -> None:
	sys.stderr.write("=== Answer Choice Histogram ===\n")
	keys = list(answer_histogram.keys())
	keys.sort()
	total_answers = 0
	for key in keys:
		total_answers += answer_histogram[key]
		sys.stderr.write("{0}: {1},  ".format(key, answer_histogram[key]))
	sys.stderr.write("\n")
	sys.stderr.write("Total Questions = {0:d}; Total Answers = {1:d}\n".format(question_count, total_answers))
