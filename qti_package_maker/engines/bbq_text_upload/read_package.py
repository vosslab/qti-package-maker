
# Standard Library
import os

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types

"""
Read Blackboard "BBQ" text upload files into ItemBank items.
See the Blackboard upload format documentation for field layout and question types.
"""

#=====================================================
def read_MC(parts: list[str]) -> item_types.MC:
	question_text = parts[1].strip()
	choices_list = parts[2::2]
	correct_status = [element.lower() for element in parts[3::2]]
	answer_index = correct_status.index('correct')
	answer_text = choices_list[answer_index]
	item_cls = item_types.MC(question_text, choices_list, answer_text)
	return item_cls

#=====================================================
def indices(lst: list[str], element: str) -> list[int]:
	result = []
	for i, x in enumerate(lst):
		if x == element:
			result.append(i)
	return result

#=====================================================
def read_MA(parts: list[str]) -> item_types.MA:
	question_text = parts[1].strip()
	choices_list = parts[2::2]
	correct_status = [element.lower() for element in parts[3::2]]
	answers_indices = indices(correct_status, 'correct')
	answers_list = [choices_list[i] for i in answers_indices]
	item_cls = item_types.MA(question_text, choices_list, answers_list)
	return item_cls

#=====================================================
def read_MATCH(parts: list[str]) -> item_types.MATCH:
	question_text = parts[1].strip()
	#MAT TAB question text TAB answer text TAB matching text TAB answer two text TAB matching two text
	prompts_list = parts[2::2]
	choices_list = parts[3::2]
	item_cls = item_types.MATCH(question_text, prompts_list, choices_list)
	return item_cls

#=====================================================
def read_ORDER(parts: list[str]) -> item_types.ORDER:
	question_text = parts[1].strip()
	ordered_answers_list = parts[2:]  # All subsequent fields are answers in order
	item_cls = item_types.ORDER(question_text, ordered_answers_list)
	return item_cls

#=====================================================
def read_FIB(parts: list[str]) -> item_types.FIB:
	question_text = parts[1].strip()
	answers_list = parts[2:]  # All subsequent fields are valid answers
	item_cls = item_types.FIB(question_text, answers_list)
	return item_cls

#=====================================================
def read_MULTI_FIB(parts: list[str]) -> item_types.MULTI_FIB:
	# Extract the main question text
	question_text = parts[1].strip()
	# Dictionary to store variable names and their corresponding answer lists
	answer_map = {}
	# Start processing from index 2, where the first variable should appear
	i = 2
	# Iterate over the parts list to extract variable-answer mappings
	while i < len(parts):
		# Read the variable name and remove surrounding whitespace
		variable_name = parts[i].strip()
		# If an empty field is encountered, it separates variable-answer groups
		if not variable_name:
			i += 1  # Move to the next field
			continue  # Skip this iteration
		# Move to the next index where answers for this variable should begin
		i += 1
		# Initialize an empty list to store all valid answers for this variable
		answers_list = []
		# Collect answers until an empty field or the end of the list is reached
		while i < len(parts) and parts[i].strip():
			answers_list.append(parts[i].strip())  # Add answer to the list
			i += 1  # Move to the next part
		# Store the variable and its corresponding list of answers in the dictionary
		answer_map[variable_name] = answers_list
		# Move to the next field, which should be an empty separator before another variable
		i += 1
	# Create a MULTI_FIB question object using the extracted data
	item_cls = item_types.MULTI_FIB(question_text, answer_map)
	# Return the constructed MULTI_FIB question object
	return item_cls

#=====================================================
def read_NUM(parts: list[str]) -> item_types.NUM:
	question_text = parts[1].strip()
	answer_float = float(parts[2].strip())  # Convert answer to float
	if len(parts) <= 3 or parts[3].strip() == "":
		print("Warning: NUM question missing tolerance, defaulting to 0.0.")
		tolerance_float = 0.0
	else:
		tolerance_float = float(parts[3].strip())
	item_cls = item_types.NUM(question_text, answer_float, tolerance_float)
	return item_cls

#=====================================================
# Mapping BBQ question types to parsing functions
question_function_map = {
	"MC": read_MC,
	"MA": read_MA,
	"MAT": read_MATCH,
	"NUM": read_NUM,
	"FIB": read_FIB,
	"FIB_PLUS": read_MULTI_FIB,
	"ORD": read_ORDER
}

#=====================================================
def make_item_cls_from_line(text_line: str) -> item_types.BaseItem | None:
	# Remove leading/trailing whitespace
	text_line = text_line.strip()
	# Skip blank lines to avoid processing empty lines
	if not text_line or len(text_line) == 0:
		return None
	# Split the line into parts using tab delimiters
	parts = text_line.split('\t')
	# Extract the question type from the first column
	bbq_question_header = parts[0].strip()
	if len(bbq_question_header) == 0:
		print("Warning: Empty bbq_question_header skipping.")
		return None
	# Look up the function for the given question type
	read_function = question_function_map.get(bbq_question_header)
	if read_function is None:
		raise ValueError(f"Unsupported question type: '{bbq_question_header}' in line: {text_line}")
	# Call the function and return the created item
	item_cls = read_function(parts)
	return item_cls

#=====================================================
#=====================================================
def read_items_from_file(input_file: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	"""
	Read a BBQ text upload file and return an ItemBank.

	The bank's media_base_dir is set to the input file's directory, so any
	relative <img src> referenced in item HTML (e.g. "images/foo.jpg") later
	resolves purely by derivation through ItemBank.collect_assets(). No
	per-item media state is attached here; a missing local image only
	surfaces (naming the src) when collect_assets() is called downstream.
	"""
	media_base_dir = os.path.dirname(os.path.abspath(input_file))
	new_item_bank = item_bank.ItemBank(allow_mixed, media_base_dir=media_base_dir)
	# Step 1: Read and process questions from the input file
	with open(input_file, 'r') as f:
		for line_num, line in enumerate(f, start=1):
			try:
				item_cls = make_item_cls_from_line(line)
			except (ValueError, IndexError) as exc:
				print(f"Warning: skipping line {line_num}: {exc}")
				continue
			if not item_cls:
				continue
			# Store the processed question type and its associated parts
			#print(f"len(new_item_bank) = {len(new_item_bank)}")
			new_item_bank.add_item_cls(item_cls)
	return new_item_bank

#=====================================================
def main() -> None:
	# Sample question lines
	good_question_lines = [
		"MC\t2+2?\t3\tincorrect\t4\tcorrect",
		"MA\tPrime numbers?\t3\tcorrect\t4\tincorrect\t5\tcorrect",
		"MAT\tMatch Capital?\tUSA\tWashington\tFrance\tParis",
		"ORD\tOrder these\tOne\tTwo\tThree",
		"FIB\tCapital of France?\tParis",
		"FIB_PLUS\tFill in: The [animal] has milk\tanimal\tcow",
		"NUM\tApprox pi?\t3.14\t0.01",
	]
	bad_question_lines = [
		"",  # Empty line (should be skipped)
		"INVALID\tThis should not work"  # Unsupported question type
	]

	# Process each question line and print the result
	for line in good_question_lines:
		item_cls = make_item_cls_from_line(line)
		if not isinstance(item_cls, item_types.BaseItem):
			raise ValueError
		print(f"Input: {line}\nOutput: {item_cls.item_type}, {item_cls.item_crc16}\n{'-'*50}")
	# Process each question line and print the result
	for line in bad_question_lines:
		result = make_item_cls_from_line(line)
		if result is not None:
			raise ValueError
		print(f"Input: {line}\nOutput: {result}\n{'-'*50}")


if __name__ == "__main__":
	main()
