
# Standard Library
import re
import random
import importlib.resources

# Pip3 Library

# QTI Package Maker
import qti_package_maker
from qti_package_maker.common import string_functions
from qti_package_maker.assessment_items import item_types

# =====================================================================================

class AntiCheat:
	"""
	Applies anti-cheating protections to assessment content.

	Features:
	- Inserts hidden terms to track unauthorized content sharing.
	- Wraps text in a no-click div to prevent copying, selection, and right-click.
	- Injects anti-copy JavaScript to block printing and screenshots.
	"""

	def __init__(self, hidden_terms: bool = True, no_click_div: bool = True, anticopy_script: bool = False) -> None:
		"""
		Initializes anti-cheating settings.
		"""
		# 1. Hidden Terms: Inserts nearly invisible words to detect unauthorized content-sharing.
		self.use_insert_hidden_terms = hidden_terms
		self.hidden_term_density = 0.7  # Probability of inserting hidden terms
		self._load_hidden_term_bank()
		self.exclude_tags = ["table", "code", "script", "blockquote", "pre", "math"]

		# 2. No-Click Div: Prevents right-click, text selection, copying, and context menu.
		# Enable/Disable anti-click div wrapper
		self.use_no_click_div = no_click_div

		# 3. Anti-Copy JavaScript: Prevents printing, copying, and screenshots.
		self.use_anticopy_script = anticopy_script
		# Additional settings
		self.noPrint = True  # Disable printing
		self.noCopy = True  # Disable copying
		self.noScreenshot = False  # Disable screenshots (not foolproof)
		self.autoBlur = True  # Blur content when switching tabs (prevents screen recording)

	# ============= MODIFY ITEM TYPE CLASS =================

	def modify_item_cls(self, item_cls: item_types.BaseItem) -> item_types.BaseItem:
		"""
		Applies anti-cheating modifications to an assessment item.

		- Modifies `question_text`
		- Modifies each supporting field dynamically

		Args:
				item_cls (BaseItem): The assessment item object.

		Returns:
				BaseItem: A new item instance with anti-cheat modifications.
		"""
		# Copy item to avoid modifying the original
		item_copy = item_cls.copy()
		# Modify question text
		item_copy.question_text = self.modify_string(item_copy.question_text)
		# Modify supporting fields dynamically
		for field_name in item_copy.get_supporting_field_names():
			value = getattr(item_copy, field_name)
			# skip fields where we never want anti-cheat
			if field_name.startswith('answer') or field_name.startswith('tolerance'):
				continue
			elif isinstance(value, str):
				setattr(item_copy, field_name, self.modify_string(value))
			elif isinstance(value, list):
				setattr(item_copy, field_name, self.modify_list(value))
			else:
				print(f"Skipping field name, {field_name}")
		return item_copy

	# ============= MODIFY STRINGS/LISTS =============

	def modify_list(self, string_list: list) -> list:
		"""
		Applies anti-cheating modifications to a list of strings.
		"""
		return [self.modify_string(text) for text in string_list]

	def modify_string(self, string_text: str) -> str:
		"""
		Applies anti-cheating modifications to a single string.

		- Inserts hidden terms (if enabled)
		- Wraps in a no-click div (if enabled)
		- Injects anti-copy JavaScript (if enabled)

		Returns:
				str: Modified text with anti-cheating protections.
		"""
		if self.use_insert_hidden_terms:
			string_text = self.insert_hidden_terms(string_text)
		if self.use_no_click_div:
			string_text = wrap_text_in_no_click_div(string_text)
		if self.use_anticopy_script:
			js_function_string = self.get_anticopy_js_function()
			string_text = js_function_string + string_text  # Prepend JavaScript
		return string_text


	# =======================================================================
	# Anti-Copy JavaScript: Disables printing, copying, and screenshots
	# =======================================================================

	def get_anticopy_js_function(self) -> str:
		"""
		Generates JavaScript to prevent various forms of content theft.

		- `noPrint`: Disables printing via `window.print()`
		- `noCopy`: Disables right-click and copying
		- `noScreenshot`: Attempts to block screenshots (not foolproof)
		- `autoBlur`: Detects tab-switching and blurs content

		Returns:
			str: JavaScript `<script>` tag with anti-copy functionality.
		"""
		js_code = (
			'<script>'
			f'var noPrint={str(self.noPrint).lower()};'
			f'var noCopy={str(self.noCopy).lower()};'
			f'var noScreenshot={str(self.noScreenshot).lower()};'
			f'var autoBlur={str(self.autoBlur).lower()};'
			'</script>'
		)
		js_code += (
			'<script type="text/javascript" '
			'src="https://cdn.jsdelivr.net/gh/vosslab/biology-problems@main/javascript/noprint.js">'
			'</script>'
		)
		return js_code

	# =======================================================================
	# Hidden Terms: Embeds invisible markers to detect unauthorized sharing
	# =======================================================================

	# ============
	def _load_hidden_term_bank(self) -> None:
		"""
		Loads a list of hidden words from a predefined file.

		These words are inserted randomly into assessment content to help detect unauthorized content sharing.

		Returns:
			list: A list of words to be hidden in the text.
		"""
		data_file = importlib.resources.files(qti_package_maker).joinpath("data/all_short_words.txt")
		with data_file.open("r") as file:
			terms = file.readlines()
		self.hidden_term_bank = [term.strip() for term in terms]
		return

	# ============
	def insert_hidden_terms(self, text_content: str) -> str:
		"""
		Randomly inserts hidden words into the text to detect unauthorized distribution.

		- Invisible words are added inside `<span>` elements with `font-size: 1px; color: white;`
		- Spaces between words are replaced with '@' to create valid insertion points.
		- Words inside specified HTML tags are left untouched to avoid breaking syntax.

		Args:
			text_content (str): The original assessment content.
			exclude_tags (list[str], optional): List of HTML tags to exclude from modification.
				Defaults to `["table", "code"]`.

		Returns:
			str: The modified content with hidden words.
		"""
		if self.hidden_term_bank is None:
			raise ValueError("Hidden term bank is not initialized.")
		# Default tags to exclude if none are provided
		# Create a regex pattern to match any of the excluded tags
		tag_pattern = r"(" + "|".join(f"<{tag}>.*?</{tag}>" for tag in self.exclude_tags) + r")"
		# Split the content into sections, preserving excluded blocks
		parts = re.split(tag_pattern, text_content, flags=re.DOTALL | re.IGNORECASE)
		new_parts = []
		for part in parts:
			if any(part.lower().startswith(f"<{tag}") for tag in self.exclude_tags):
				new_parts.append(part)
			else:
				new_parts.append(self.process_text_segment(part))
		return "".join(new_parts)

	# ============
	def process_text_segment(self, segment: str) -> str:
		"""
		Processes a segment of text by inserting hidden terms at random positions.

		Args:
			segment (str): A non-excluded text segment.

		Returns:
			str: The processed segment with hidden terms inserted.
		"""
		# Preserve inline elements
		segment = re.sub(r"([a-z]) +([a-z])(?![^<>]*>)", r"\1@\2", segment)
		# Split words where spaces were
		words = segment.split("@")
		new_words = []
		for word in words:
			new_words.append(word)
			if random.random() < self.hidden_term_density:
				hidden_term = random.choice(self.hidden_term_bank)
				new_words.append(f"<span style='font-size: 1px; color: white;'>{hidden_term}</span>")
			else:
				# Restore spaces
				new_words.append(" ")
		return "".join(new_words)

# =======================================================================
# Anti-Copy Protection: Prevents text selection, copying, right-clicking
# =======================================================================

def wrap_text_in_no_click_div(string_text: str) -> str:
	"""
	Wraps the given text in a non-clickable <div> to prevent copying, selecting, and right-clicking.

	- Blocks text selection
	- Disables context menu (right-click)
	- Prevents pasting and cutting
	- Stops onmousedown selection

	Args:
		string_text (str): The text content to be protected.

	Returns:
		str: Wrapped HTML string with anti-cheating properties.
	"""
	rand_crc16 = string_functions.get_random_crc16()  # Generate a unique identifier
	output = (
		f'<div id="drv_{rand_crc16}" '
			'oncopy="return false;" '
			'onpaste="return false;" '
			'oncut="return false;" '
			'oncontextmenu="return false;" '
			'onmousedown="return false;" '
			'onselectstart="return false;" '
		'>')
	output += string_text
	output += '</div>'
	return output

# ============
def main() -> None:
	"""
	Unit test for the AntiCheat class.
	"""
	print("\n===== Running AntiCheat Unit Tests =====")

	# Create AntiCheat instances with different settings
	term_adder = AntiCheat(hidden_terms=True, no_click_div=False, anticopy_script=False)
	div_adder = AntiCheat(hidden_terms=False, no_click_div=True, anticopy_script=False)

	# Sample text for testing
	original_text = """
	<p>This is a test paragraph. It should have hidden terms.</p>
	<table><tr><td>Do not modify this table content.</td></tr></table>
	<code>print('This should not be changed')</code>
	"""

	# ========= Test insert_hidden_terms() (term_adder) =========
	print("\n-- Testing insert_hidden_terms() --")
	modified_text = term_adder.insert_hidden_terms(original_text)

	# Ensure text was modified (hidden terms added)
	assert modified_text != original_text, "insert_hidden_terms() failed to modify text."

	# Ensure text length increased (hidden terms were inserted)
	assert len(modified_text) > len(original_text), "Hidden terms were not inserted properly."

	# Ensure <table> and <code> blocks remain unchanged
	assert "<table><tr><td>Do not modify this table content.</td></tr></table>" in modified_text
	assert "<code>print('This should not be changed')</code>" in modified_text

	print("[OK] insert_hidden_terms() passed all tests.")

	# ========= Test wrap_text_in_no_click_div() (div_adder) =========
	print("\n-- Testing wrap_text_in_no_click_div() --")
	protected_text = div_adder.modify_string("Protected text")

	# Ensure the text is wrapped in a <div>
	assert protected_text.startswith("<div "), "wrap_text_in_no_click_div() did not wrap correctly."
	assert protected_text.endswith("</div>"), "wrap_text_in_no_click_div() did not wrap correctly."

	print("[OK] wrap_text_in_no_click_div() passed all tests.")

	print("\n[OK] All tests passed successfully!")

if __name__ == "__main__":
	main()


