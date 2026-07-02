ENGINE_NAME = "okla_chrst_bqgen"

# Standard Library
import re

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

"""
Render assessment items into the okla_chrst_bqgen plain-text format. This is
an internal, repo-defined format with no external spec; okla_chrst_bqgen/
read_package.py is the source of truth for the accepted grammar. It carries
no image markup, so EngineClass.save_package (media_policy placeholder_warn)
replaces every <img> tag with a readable `[image: name.ext]` placeholder plus
an itemized warning before writing. The placeholder is plain text embedded
inline in the stem or choice line, so this engine's own reader round-trips it
unchanged (as ordinary text, not as a MediaAsset reference).
"""

#==============================================================
def _format_choices(choices_list: list, correct_set: set) -> str:
	lines = []
	for idx, choice in enumerate(choices_list, start=1):
		prefix = string_functions.number_to_lowercase(idx)  # a, b, c...
		marker = "*" if choice in correct_set else ""
		lines.append(f"{marker}{prefix}) {choice}")
	return "\n".join(lines) + "\n\n"

#==============================================================
def MC(item_cls: item_types.BaseItem) -> str:
	"""Render an MC item in okla_chrst_bqgen format."""
	header = f"{item_cls.item_number}. {item_cls.question_text}\n"
	correct_set = {item_cls.answer_text}
	return header + _format_choices(item_cls.choices_list, correct_set)

#==============================================================
def MA(item_cls: item_types.BaseItem) -> str:
	"""Render an MA item in okla_chrst_bqgen format."""
	header = f"{item_cls.item_number}. {item_cls.question_text}\n"
	correct_set = set(item_cls.answers_list)
	return header + _format_choices(item_cls.choices_list, correct_set)

#==============================================================
def MATCH(item_cls: item_types.BaseItem) -> str:
	"""Render a MATCH item as prompt/answer pairs separated by '/'."""
	header = f"match {item_cls.item_number}. {item_cls.question_text}\n"
	lines = []
	for idx, (prompt, choice) in enumerate(zip(item_cls.prompts_list, item_cls.choices_list), start=1):
		prefix = string_functions.number_to_lowercase(idx)
		lines.append(f"{prefix}) {prompt}/{choice}")
	return header + "\n".join(lines) + "\n\n"

#==============================================================
def NUM(item_cls: item_types.BaseItem) -> None:
	"""Okla CHRST BQGEN writer does not implement NUM items."""
	return None

#==============================================================
def FIB(item_cls: item_types.BaseItem) -> str:
	"""Render a FIB item with acceptable answers."""
	header = f"blank {item_cls.item_number}. {item_cls.question_text}\n"
	lines = []
	for idx, ans in enumerate(item_cls.answers_list, start=1):
		prefix = string_functions.number_to_lowercase(idx)
		lines.append(f"*{prefix}. {ans}")
	return header + "\n".join(lines) + "\n\n"

#==============================================================
def MULTI_FIB(item_cls: item_types.BaseItem) -> None:
	"""Okla CHRST BQGEN writer does not implement MULTI_FIB items."""
	return None

#==============================================================
def ORDER(item_cls: item_types.BaseItem) -> None:
	"""Okla CHRST BQGEN writer does not implement ORDER items."""
	return None

#==============================================================
# whole <img ...> tag / src="..." patterns come from media_assets (single owner)

def replace_images_with_placeholders(text: str, placeholders_by_src: dict) -> str:
	"""
	Replace every <img src=...> tag in rendered writer output with its
	`[image: name.ext]` placeholder text (media_assets.placeholder_text via
	apply_media_policy's placeholder_warn decision).
	"""
	#----------------------------------------------------
	def _substitute(tag_match: re.Match) -> str:
		tag = tag_match.group(0)
		src_match = media_assets.SRC_ATTR_PATTERN.search(tag)
		if src_match is None:
			return tag
		src = src_match.group(3)
		return placeholders_by_src.get(src, tag)

	return media_assets.IMG_TAG_PATTERN.sub(_substitute, text)
