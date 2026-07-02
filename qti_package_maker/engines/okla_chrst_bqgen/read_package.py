# Standard Library
import re

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types


def _split_blocks(text: str) -> list:
	blocks = []
	current = []
	for line in text.splitlines():
		if line.strip() == "":
			if current:
				blocks.append("\n".join(current))
				current = []
		else:
			current.append(line.rstrip())
	if current:
		blocks.append("\n".join(current))
	return blocks


def _parse_choice_line(line: str) -> tuple | None:
	match = re.match(r"(\*?)([a-zA-Z])[\)\.]?\s*(.+)", line.strip())
	if not match:
		return None
	return bool(match.group(1)), match.group(3).strip()


def _read_mc_ma(block: str, item_number: int) -> item_types.BaseItem | None:
	lines = block.strip().split("\n")
	stem = re.sub(r"^\d+\.\s*", "", lines[0]).strip()
	choices = []
	correct = []
	for line in lines[1:]:
		parsed = _parse_choice_line(line)
		if not parsed:
			continue
		is_correct, text = parsed
		choices.append(text)
		if is_correct:
			correct.append(text)
	if not choices:
		return None
	if len(correct) == 1:
		item = item_types.MC(stem, choices, correct[0])
	else:
		item = item_types.MA(stem, choices, correct)
	item.item_number = item_number
	return item


def _read_fib(block: str, item_number: int) -> item_types.BaseItem | None:
	lines = block.strip().split("\n")
	stem = re.sub(r"^blank\s*\d*\.\s*", "", lines[0], flags=re.IGNORECASE).strip()
	answers = []
	for line in lines[1:]:
		parsed = _parse_choice_line(line)
		if parsed:
			_, text = parsed
			answers.append(text)
		elif line.strip():
			answers.append(line.strip())
	if not answers:
		return None
	item = item_types.FIB(stem, answers)
	item.item_number = item_number
	return item


def _read_match(block: str, item_number: int) -> item_types.BaseItem | None:
	lines = block.strip().split("\n")
	stem = re.sub(r"^match\s*\d*\.\s*", "", lines[0], flags=re.IGNORECASE).strip()
	prompts = []
	choices = []
	for line in lines[1:]:
		parsed = _parse_choice_line(line)
		if not parsed:
			continue
		_, text = parsed
		if "/" in text:
			prompt, answer = text.split("/", 1)
			prompts.append(prompt.strip())
			choices.append(answer.strip())
	if not prompts or not choices:
		return None
	item = item_types.MATCH(stem, prompts, choices)
	item.item_number = item_number
	return item


def read_items_from_file(infile: str, allow_mixed: bool = False) -> item_bank.ItemBank:
	with open(infile, "r", encoding="utf-8") as f:
		content = f.read()
	blocks = _split_blocks(content)
	bank = item_bank.ItemBank(allow_mixed=allow_mixed)
	for idx, block in enumerate(blocks, start=1):
		header = block.strip().split("\n", 1)[0].lower()
		item = None
		if header.startswith("match"):
			item = _read_match(block, idx)
		elif header.startswith("blank"):
			item = _read_fib(block, idx)
		elif re.match(r"\d+\.", header):
			item = _read_mc_ma(block, idx)
		if item:
			bank.add_item_cls(item)
	return bank
