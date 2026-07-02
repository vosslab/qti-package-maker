
# Standard Library
import re

# QTI Package Maker
from qti_package_maker.common import media_assets
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

"""
Render assessment items into the plain-text format used by text2qti. See the
text2qti project (https://github.com/gpoore/text2qti) for the full grammar.

Any <img> tag inside item HTML is carried through verbatim by the MC/MA/NUM/FIB
functions below; EngineClass.save_package (media_policy reference_warn) rewrites
each one to text2qti's own markdown image syntax `![alt](media/name.png)` and
copies the referenced bytes into a `media/` folder beside the output file. This
engine's own reader (read_package.restore_img_tags_from_markdown) converts that
markdown back into a normal `<img src>` field on read, so a read-write roundtrip
never stores an `asset:` scheme in item content.
"""

# whole <img ...> tag / src="..." patterns come from media_assets (single owner);
# only the alt attribute pattern is local to this engine
_ALT_ATTR_PATTERN = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)

#==============================================================
def MC(item_cls: item_types.BaseItem) -> str:
	"""Render an MC item in text2qti format."""
	output = [f"{item_cls.item_number}. {item_cls.question_text}"]
	for i, choice_text in enumerate(item_cls.choices_list, start=1):
		prefix = "*" if choice_text == item_cls.answer_text else ""
		letter = string_functions.number_to_letter(i)
		output.append(f"{prefix}{letter}) {choice_text}")
	return "\n".join(output) + "\n"

#==============================================================
def MA(item_cls: item_types.BaseItem) -> str:
	"""Render an MA item in text2qti format."""
	output = [f"{item_cls.item_number}. {item_cls.question_text}"]
	for choice_text in item_cls.choices_list:
		prefix = "[*]" if choice_text in item_cls.answers_list else "[ ]"
		output.append(f"{prefix} {choice_text}")
	return "\n".join(output) + "\n"

#==============================================================
def NUM(item_cls: item_types.BaseItem) -> str:
	"""Render a NUM item in text2qti format."""
	output = [f"{item_cls.item_number}. {item_cls.question_text}"]
	if item_cls.tolerance_float is None:
		output.append(f"= {item_cls.answer_float}")
	else:
		output.append(f"= {item_cls.answer_float} +- {item_cls.tolerance_float}")
	return "\n".join(output) + "\n"

#==============================================================
def FIB(item_cls: item_types.BaseItem) -> str:
	"""Render a FIB item in text2qti format."""
	output = [f"{item_cls.item_number}. {item_cls.question_text}"]
	for answer_text in item_cls.answers_list:
		output.append(f"* {answer_text}")
	return "\n".join(output) + "\n"

#==============================================================
def MATCH(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, prompts_list: list, choices_list: list):
	"""Text2qti does not define MATCH items."""
	raise NotImplementedError("text2qti does not have documentations on MATCH assessment items")

#==============================================================
# Create a Fill-in-the-Blank (Multiple Blanks) question using answer mapping.
def MULTI_FIB(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, answer_map: dict) -> str:
	"""Text2qti does not define MULTI_FIB items."""
	raise NotImplementedError("text2qti does not have documentations on MULTI_FIB assessment items")

#==============================================================
def ORDER(item_cls: item_types.BaseItem) -> None:
	#item_number: int, crc16_text: str, question_text: str, ordered_answers_list: list):
	"""Text2qti does not define ORDER items."""
	raise NotImplementedError("text2qti does not have documentations on ORDER assessment items")

#==============================================================
def replace_images_with_markdown(text: str, markdown_target_by_src: dict) -> str:
	"""
	Replace every <img src=...> tag in rendered writer output with text2qti
	markdown image syntax.

	Args:
		text: rendered writer output containing zero or more <img> tags.
		markdown_target_by_src: maps the item-authored src to the markdown link
			target (a copied-file path such as "media/foo.png", or the original
			src unchanged for external/data-uri references that were not copied).

	Returns:
		The text with every <img> tag replaced by `![alt](target)`.
	"""
	#----------------------------------------------------
	def _substitute(tag_match: re.Match) -> str:
		tag = tag_match.group(0)
		src_match = media_assets.SRC_ATTR_PATTERN.search(tag)
		if src_match is None:
			return tag
		src = src_match.group(3)
		alt_match = _ALT_ATTR_PATTERN.search(tag)
		alt_text = alt_match.group(2) if alt_match else ""
		target = markdown_target_by_src.get(src, src)
		return f"![{alt_text}]({target})"

	return media_assets.IMG_TAG_PATTERN.sub(_substitute, text)
