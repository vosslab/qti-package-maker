
# Standard Library
import os
import re

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types

#=====================================================
def strip_question_number(question_text: str) -> str:
	"""Strip the leading number and period from a text2qti question stem."""
	return re.sub(r"^\d+\.\s*", "", question_text).strip()

#=====================================================
def parse_MC_lines(lines: list, start_index: int) -> tuple:
	"""Parse multiple-choice options and feedback from text2qti lines."""
	choices_list = []
	choice_feedback = {}
	answer_text = None
	current_choice = None
	current_feedback = []
	is_correct_answer = False
	for i in range(start_index, len(lines)):
		line = lines[i]
		# Detect choice line (e.g., "a) Option" or "*b) Correct Option")
		match = re.match(r"(\*?)([a-zA-Z])\)\s*(.*)", line)
		if match:
			if current_choice:
				# Store previous choice and feedback
				choices_list.append(current_choice)
				choice_feedback[current_choice] = " ".join(current_feedback).strip()
				if is_correct_answer and answer_text is None:
					answer_text = current_choice
			# Process the new choice
			is_correct_answer = bool(match.group(1))  # "*" indicates correct answer
			current_choice = match.group(3).strip()
			current_feedback = []  # Reset feedback
		# Detect feedback lines (e.g., "... Feedback text", "+ Correct feedback", "- Incorrect feedback")
		elif line.startswith("... ") or line.startswith("+ ") or line.startswith("- "):
			current_feedback.append(" ".join(line.split(" ")[1:]))
		# Multi-line choice handling (continued text)
		elif current_choice is not None:
			current_choice += " " + line.strip()  # Append to the last choice
	# Store the last choice after the loop
	if current_choice:
		choices_list.append(current_choice)
		choice_feedback[current_choice] = " ".join(current_feedback).strip()
		if is_correct_answer:
			if answer_text is None:
				answer_text = current_choice
			else:
				raise ValueError("Only one correct answer is allowed for multiple-choice")
	return choices_list, answer_text, choice_feedback

#=====================================================
def read_MC(question_block: str, item_number: int) -> item_types.BaseItem:
	"""Read a text2qti multiple-choice block into an MC item."""
	lines = [line.rstrip() for line in question_block.strip().split("\n")]
	question_text_lines = []
	answer_start_index = None
	# Extract multi-line question text
	for i, line in enumerate(lines):
		if re.match(r"^\*?[a-zA-Z]\)\s*.+", line):  # First answer choice detected
			answer_start_index = i
			break
		question_text_lines.append(line.strip())
	# Merge multi-line question text
	question_text = " ".join(question_text_lines)
	question_text = strip_question_number(question_text)
	# Process choices using the helper function
	choices_list, answer_text, choice_feedback = parse_MC_lines(lines, answer_start_index)
	# Create the MC item
	item_cls = item_types.MC(question_text, choices_list, answer_text)
	item_cls.item_number = item_number
	# Store feedback dictionary
	item_cls.choice_feedback = choice_feedback
	return item_cls

#=====================================================
#=====================================================
def parse_MA_lines(lines: list, start_index: int) -> tuple:
	"""Parse multiple-answer options and feedback from text2qti lines."""
	choices_list = []
	choice_feedback = {}
	answers_list = []
	current_choice = None
	current_feedback = []
	is_correct_answer = False
	#print(f"lines = {lines}")
	#print(f"start_index = {start_index}")
	for i in range(start_index, len(lines)):
		line = lines[i].strip()  # Strip whitespace early
		# Detect choice line (e.g., "[ ] Incorrect Option" or "[*] Correct Option")
		match = re.match(r"^\[(\*| )?]\s*(.+)", line)
		if match:
			if current_choice is not None:  # Store previous choice **before resetting**
				choices_list.append(current_choice)
				choice_feedback[current_choice] = " ".join(current_feedback).strip()
				if is_correct_answer:
					answers_list.append(current_choice)
			# Start a new choice
			is_correct_answer = match.group(1) == "*"  # Correct if `*` is found
			current_choice = match.group(2).strip()
			current_feedback = []  # Reset feedback list
			#print(f"match.groups() = {match.groups()}")
		# Detect feedback lines (e.g., "... Feedback text", "+ Correct feedback", "- Incorrect feedback")
		elif line.startswith("... ") or line.startswith("+ ") or line.startswith("- "):
			current_feedback.append(" ".join(line.split(" ")[1:]))
		# Multi-line choice handling (continued text)
		elif current_choice is not None and not re.match(r"^\[\s*(\*)?\s*\]\s*.+", line):
			#print(f"extra line = {line}")
			current_choice += " " + line.strip()  # Append only if it's a continuation
	if current_choice and current_choice not in choices_list:
		#print(f"extra current_choice = {current_choice}")
		choices_list.append(current_choice)
		choice_feedback[current_choice] = " ".join(current_feedback).strip()
		if is_correct_answer:
			answers_list.append(current_choice)
	return choices_list, answers_list, choice_feedback

#=====================================================
def read_MA(question_block: str, item_number: int) -> item_types.BaseItem:
	"""Read a text2qti multiple-answer block into an MA item."""
	lines = [line.rstrip() for line in question_block.strip().split("\n")]
	question_text_lines = []
	answer_start_index = None
	# Extract multi-line question text
	for i, line in enumerate(lines):
		if re.match(r"^\[(\*| )?]\s*(.+)", line):  # First answer choice detected
			answer_start_index = i
			break
		question_text_lines.append(line.strip())
	question_text = " ".join(question_text_lines)  # Merge multi-line question text
	question_text = strip_question_number(question_text)
	# Process choices using the helper function
	choices_list, answers_list, choice_feedback = parse_MA_lines(lines, answer_start_index)
	# Create the MA item
	#print(f"question_text = {question_text}")
	#print(f"choices_list = {choices_list}")
	#print(f"answers_list = {answers_list}")
	#print(f"choice_feedback = {choice_feedback}")
	item_cls = item_types.MA(question_text, choices_list, answers_list)
	item_cls.item_number = item_number
	item_cls.choice_feedback = choice_feedback  # Store feedback dictionary
	return item_cls

#=====================================================
#=====================================================
def parse_NUM_lines(lines: list, start_index: int) -> tuple:
	"""Parse a numerical answer line and feedback from text2qti lines."""
	answer_float = None
	tolerance_float = 0
	answer_feedback = []
	# Get the answer line
	answer_line = lines[start_index]
	# Match exact, tolerance, or range-based format
	# match_exact e.g., `= 5`
	match_exact = re.match(r"^=\s*([+-]?[\d_]+(?:\.[\d_]+)?)$", answer_line)
	# match_tolerance `= 1.4142 +- 0.0001`
	match_tolerance = re.match(r"^=\s*([\d._]+)\s*\+\-\s*([\d._]+)", answer_line)
	# match_range `= [1.2598, 1.2600]`
	match_range = re.match(r"^=\s*\[\s*([\d._]+)\s*,\s*([\d._]+)\s*\]", answer_line)
	if match_exact:
		answer_float = float(match_exact.group(1).replace("_", ""))
	elif match_tolerance:
		answer_float = float(match_tolerance.group(1).replace("_", ""))
		tolerance_float = float(match_tolerance.group(2).replace("_", ""))
	elif match_range:
		low = float(match_range.group(1).replace("_", ""))
		high = float(match_range.group(2).replace("_", ""))
		answer_float = (low + high) / 2  # Store midpoint
		tolerance_float = (high - low) / 2  # Store half-range as tolerance
	else:
		raise ValueError(f"Invalid numerical answer format: {answer_line}")
	# Capture feedback (lines after `=` that start with "...", "+", or "-")
	for i in range(start_index + 1, len(lines)):
		line = lines[i]
		if line.startswith("... ") or line.startswith("+ ") or line.startswith("- "):
			answer_feedback.append(" ".join(line.split(" ")[1:]))
	return answer_float, tolerance_float, " ".join(answer_feedback).strip()

#=====================================================
def read_NUM(question_block: str, item_number: int) -> item_types.BaseItem:
	"""Read a text2qti numeric block into a NUM item."""
	lines = [line.rstrip() for line in question_block.strip().split("\n")]
	question_text_lines = []
	answer_start_index = None
	# Extract multi-line question text
	for i, line in enumerate(lines):
		if re.match(r"^=\s*.+", line):  # First `=` answer line detected
			answer_start_index = i
			break
		question_text_lines.append(line.strip())
	if answer_start_index is None:
		raise ValueError("NUM question missing an answer line.")
	question_text = " ".join(question_text_lines)  # Merge multi-line question text
	question_text = strip_question_number(question_text)
	# Process numerical answer using the helper function
	answer_float, tolerance_float, answer_feedback = parse_NUM_lines(lines, answer_start_index)
	# Create the NUM item
	item_cls = item_types.NUM(question_text, answer_float, tolerance_float)
	item_cls.item_number = item_number
	item_cls.answer_feedback = answer_feedback  # Store feedback
	return item_cls

#=====================================================
#=====================================================
def parse_FIB_lines(lines: list, start_index: int) -> tuple:
	"""Parse fill-in-the-blank answers and feedback from text2qti lines."""
	answers_list = []
	answer_feedback = []
	for i in range(start_index, len(lines)):
		line = lines[i]
		# Detect answer lines (e.g., "* CorrectAnswer")
		match = re.match(r"^\*\s*(.+)", line)
		if match:
			answers_list.append(match.group(1).strip())
		# Detect feedback lines (e.g., "... Feedback text", "+ Correct feedback", "- Incorrect feedback")
		elif line.startswith("... ") or line.startswith("+ ") or line.startswith("- "):
			answer_feedback.append(" ".join(line.split(" ")[1:]))
	return answers_list, " ".join(answer_feedback).strip()

#=====================================================
def read_FIB(question_block: str, item_number: int) -> item_types.BaseItem:
	"""Read a text2qti fill-in-the-blank block into a FIB item."""
	lines = [line.rstrip() for line in question_block.strip().split("\n")]
	question_text_lines = []
	answer_start_index = None
	# Extract multi-line question text
	for i, line in enumerate(lines):
		if re.match(r"^\*\s*.+", line):  # First answer detected
			answer_start_index = i
			break
		question_text_lines.append(line.strip())
	if answer_start_index is None:
		raise ValueError("FIB question missing answer lines.")
	question_text = " ".join(question_text_lines)  # Merge multi-line question text
	question_text = strip_question_number(question_text)
	# Process answers using the helper function
	answers_list, answer_feedback = parse_FIB_lines(lines, answer_start_index)
	# Create the FIB item
	item_cls = item_types.FIB(question_text, answers_list)
	item_cls.item_number = item_number
	item_cls.answer_feedback = answer_feedback  # Store feedback
	return item_cls

#=====================================================
def read_MATCH(input_data: object) -> None:
	raise NotImplementedError("text2qti does not define MATCH assessment items")

#=====================================================
def read_MULTI_FIB(input_data: object) -> None:
	raise NotImplementedError("text2qti does not define MULTI_FIB assessment items")

#=====================================================
def read_ORDER(input_data: object) -> None:
	raise NotImplementedError("text2qti does not define ORDER assessment items")

#=====================================================
def make_item_cls_from_block(question_block: str) -> item_types.BaseItem | None:
	"""Infer item type from a text2qti block and parse it."""
	question_block = question_block.strip()

	# Extract the question number
	match_question = re.match(r"^(\d+)\.\s+", question_block)
	if not match_question:
		# Invalid format, no question number found
		return None
	item_number = int(match_question.group(1))

	# Check for Multiple-Answers (MA): Requires at least 2 answer choices
	ma_matches = re.findall(r"^\[(\*| )\]\s*.+", question_block, re.MULTILINE)
	if len(ma_matches) >= 3:
		return read_MA(question_block, item_number)

	# Check for Multiple-Choice (MC): Requires at least 2 choices (a) b) etc.)
	mc_matches = re.findall(r"^\*?[a-zA-Z]\)\s*.+", question_block, re.MULTILINE)
	if len(mc_matches) >= 2:
		return read_MC(question_block, item_number)

	# Check for Numerical (NUM): Matches any of the three valid formats
	if (
		re.search(r"^=\s*\d+(\.\d+)?\s*\+\-\s*\d+(\.\d+)?", question_block, re.MULTILINE)
		or re.search(
			r"^=\s*\[\s*\d+(\.\d+)?,\s*\d+(\.\d+)?\s*\]",
			question_block,
			re.MULTILINE,
		)
		or re.search(r"^=\s*\d+(_\d+)*", question_block, re.MULTILINE)
	):
		return read_NUM(question_block, item_number)

	# Check for Fill-in-the-Blank (FIB): Requires at least one "* answer"
	fib_matches = re.findall(r"^\*\s*.+", question_block, re.MULTILINE)
	if len(fib_matches) >= 1:
		return read_FIB(question_block, item_number)

	return None  # Not recognized

#=====================================================
def split_questions(text: str) -> list[str]:
	"""Split text2qti input into individual question blocks."""
	lines = text.strip().split("\n")
	question_blocks = []
	current_question = []
	previous_line_blank = True  # Assume the start of the text acts like a blank line
	for line in lines:
		line = line.rstrip()  # Remove trailing spaces/tabs
		# Detect start of a new question only if the previous line was blank
		if re.match(r"^\d+\.\s+", line) and previous_line_blank and current_question:
			question_blocks.append("\n".join(current_question).strip())
			current_question = [line]
		else:
			current_question.append(line)
		# Update blank line tracker
		previous_line_blank = line == ""
	# Add the last question if any
	if current_question:
		question_blocks.append("\n".join(current_question).strip())
	return question_blocks

#=====================================================
# match text2qti markdown image syntax: ![alt](target)
_MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

def restore_img_tags_from_markdown(text: str) -> str:
	"""
	Convert text2qti markdown image syntax back into <img> tags.

	write_item.replace_images_with_markdown() emits `![alt](media/name.png)`
	on write; this is the matching reverse step on read, so a read-write
	roundtrip keeps item content as a normal <img src> field (no `asset:`
	scheme is ever stored in item content).

	Args:
		text: raw text2qti file content, before block splitting.

	Returns:
		The text with every markdown image replaced by an <img> tag.
	"""
	#----------------------------------------------------
	def _substitute(image_match: re.Match) -> str:
		alt_text = image_match.group(1)
		target = image_match.group(2)
		return f'<img src="{target}" alt="{alt_text}"/>'

	return _MARKDOWN_IMAGE_PATTERN.sub(_substitute, text)

#=====================================================
#=====================================================
def read_items_from_file(input_file: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	"""Read a text2qti file and return an ItemBank."""
	# Read entire file content as a single string
	with open(input_file, 'r') as f:
		text_lines = f.read()
	# restore markdown image syntax into <img> tags before block parsing
	text_lines = restore_img_tags_from_markdown(text_lines)
	new_item_bank = process_text_lines(text_lines, allow_mixed)
	# local images referenced as "media/name.png" resolve against the file's directory
	new_item_bank.media_base_dir = os.path.dirname(os.path.abspath(input_file))
	return new_item_bank

#=====================================================
#=====================================================
def process_text_lines(text_lines: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	# Split into question blocks
	question_blocks = split_questions(text_lines)
	# Convert each question block into an item_cls and add to the item bank
	new_item_bank = item_bank.ItemBank(allow_mixed)
	for block_index, question_block in enumerate(question_blocks, start=1):
		try:
			item_cls = make_item_cls_from_block(question_block)
		except (ValueError, IndexError) as exc:
			print(f"Warning: skipping question block {block_index}: {exc}")
			continue
		if item_cls:
			new_item_bank.add_item_cls(item_cls)
		else:
			print(f"Warning: skipping unrecognized question block {block_index}.")
	return new_item_bank

#=====================================================
def main() -> None:
	"""Run local parser sanity checks for text2qti."""
	print("\n===== Running Unit Tests =====")
	all_text = []

	# -------------------------------
	# Multiple-Choice (MC) Test
	# -------------------------------
	mc_text = """1. What is 2+3?
a) 6
b) 1
... one is the loneliest number
*c) 5
"""
	all_text.append(mc_text)
	mc_question_cls = read_MC(mc_text, 1)
	#print(f"mc_question_cls = {mc_question_cls}")
	assert mc_question_cls.question_text == "What is 2+3?"
	assert mc_question_cls.choices_list == ["6", "1", "5"]
	assert mc_question_cls.answer_text == "5"
	print("[OK] Multiple-Choice test passed.\n")

	# -------------------------------
	# Multiple-Answers (MA) Test
	# -------------------------------
	ma_text = """1. Which are dinosaurs?
[ ] Mammoth
[*] T.
rex
[*] Triceratops
[ ] Smilodon
"""
	all_text.append(ma_text)
	ma_question = read_MA(ma_text, 2)
	assert "Smilodon" in ma_question.choices_list
	assert "Triceratops" in ma_question.answers_list
	assert "T. rex" in ma_question.answers_list
	assert len(ma_question.answers_list) == 2
	print("[OK] Multiple-Answers test passed.\n")

	# -------------------------------
	# Numerical (NUM) Test - Exact
	# -------------------------------
	num_text = """1. What is 2+3?
= 5
"""
	all_text.append(num_text)
	num_question = read_NUM(num_text, 3)
	assert num_question.answer_float == 5.0
	assert num_question.tolerance_float == 0.0
	print("[OK] Numerical test (exact) passed.\n")

	# -------------------------------
	# Numerical (NUM) Test - Tolerance
	# -------------------------------
	num_tolerance_text = """1. What is the square root of 2?
= 1.4142 +- 0.0001
... use a calculator
"""
	all_text.append(num_tolerance_text)
	num_tol_question = read_NUM(num_tolerance_text, 4)
	assert num_tol_question.answer_float == 1.4142
	assert num_tol_question.tolerance_float == 0.0001
	print("[OK] Numerical test (tolerance) passed.\n")

	# -------------------------------
	# Fill-in-the-Blank (FIB) Test
	# -------------------------------
	fib_text = """1. Who lives at the North Pole?
* Santa
* Santa Claus
* Saint Nicholas
"""
	all_text.append(fib_text)
	fib_question = read_FIB(fib_text, 5)
	assert set(fib_question.answers_list) == {"Santa", "Santa Claus", "Saint Nicholas"}
	print("[OK] Fill-in-the-Blank test passed.\n")

	import random
	random.shuffle(all_text)
	all_text = '\n'.join(all_text)
	process_text_lines(all_text, allow_mixed=True)
	print("[OK] All at once test passed.\n")


	print("[OK] All tests passed successfully!")

if __name__ == "__main__":
	main()
