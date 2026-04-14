# Standard Library
import random
import itertools

# QTI Package Maker
from qti_package_maker.assessment_items import item_types

#============================================
class UltraUnsupportedTypeError(Exception):
	"""Raised when an item type is not supported by Blackboard Ultra."""
	pass

#============================================
# Set of item types that Ultra absolutely cannot accept.
# ORDER is handled by policy conversion, not by error.
_ULTRA_UNSUPPORTED_TYPES = frozenset()

#============================================
def normalize_items(items: list, ultra_order_mapping: str = "skip") -> tuple[list, list]:
	"""
	Normalize a list of assessment items for Blackboard Ultra compatibility.

	Ultra does not support ORDER items. This function handles ORDER items
	according to the specified policy and passes through supported types.

	Args:
		items: List of BaseItem subclass instances (MC, MA, MATCH, NUM, FIB, MULTI_FIB, ORDER).
		ultra_order_mapping: Policy for handling ORDER items:
			- "skip" (default): Drop ORDER items, append warning.
			- "mc": Convert ORDER to MC with permutation choices (if <= 4 items).
			- "match": Convert ORDER to MATCH with position labels.

	Returns:
		tuple: (kept_items, warnings)
			- kept_items: List of items to keep (normalized)
			- warnings: List of human-readable warning strings
	"""
	kept_items = []
	warnings = []

	for item in items:
		item_type = item.item_type

		# Check for items in the unsupported set (extensible for future types)
		if item_type in _ULTRA_UNSUPPORTED_TYPES:
			raise UltraUnsupportedTypeError(
				f"Item type '{item_type}' is not supported by Blackboard Ultra: {item.question_text[:60]}"
			)

		# Handle ORDER items according to policy
		if item_type == "ORDER":
			if ultra_order_mapping == "skip":
				warning_msg = f"ORDER item skipped (Ultra does not support): {item.question_text[:60]}"
				warnings.append(warning_msg)
			elif ultra_order_mapping == "mc":
				# Convert ORDER to MC with permutation choices
				converted_item = _order_to_mc(item)
				if converted_item is None:
					# Too many permutations, fall back to skip
					warning_msg = f"ORDER item skipped (too many permutations): {item.question_text[:60]}"
					warnings.append(warning_msg)
				else:
					kept_items.append(converted_item)
			elif ultra_order_mapping == "match":
				# Convert ORDER to MATCH with position labels
				converted_item = _order_to_match(item)
				kept_items.append(converted_item)
			else:
				# Unknown policy, default to skip with warning
				warning_msg = f"ORDER item skipped (unknown mapping policy '{ultra_order_mapping}'): {item.question_text[:60]}"
				warnings.append(warning_msg)
		else:
			# Pass through supported types: MC, MA, MATCH, NUM, FIB, MULTI_FIB
			kept_items.append(item)

	return (kept_items, warnings)

#============================================
def _order_to_mc(order_item: item_types.ORDER) -> item_types.MC | None:
	"""
	Convert an ORDER item to an MC item using permutation choices.

	Creates MC choices where each choice is a permutation of the ordered items
	joined by ' -> '. The correct answer is the original ordering.

	If the number of permutations exceeds a reasonable limit (2^4 = 16), returns None.

	Args:
		order_item: An ORDER assessment item.

	Returns:
		MC item or None if too many permutations.
	"""
	ordered_list = order_item.ordered_answers_list
	num_items = len(ordered_list)

	# Limit permutations: 4 items = 24 perms, 5 items = 120 perms, 6+ = too many
	if num_items > 4:
		return None

	# Generate all permutations
	all_perms = list(itertools.permutations(ordered_list))

	# Build choice strings: each permutation as "item1 -> item2 -> item3"
	choices_list = []
	for perm in all_perms:
		choice_text = " -> ".join(perm)
		choices_list.append(choice_text)

	# The correct answer is the original ordering
	correct_answer = " -> ".join(ordered_list)

	# Create and return the MC item
	new_mc = item_types.MC(
		question_text=order_item.question_text,
		choices_list=choices_list,
		answer_text=correct_answer
	)

	return new_mc

#============================================
def _order_to_match(order_item: item_types.ORDER) -> item_types.MATCH:
	"""
	Convert an ORDER item to a MATCH item using position labels.

	Creates a MATCH question where:
	- Left side (prompts): The items to be ordered, shuffled deterministically.
	- Right side (choices): Position labels ("1", "2", "3", etc.).

	Shuffling uses a deterministic seed derived from the item's CRC16 to ensure
	reproducibility across runs.

	Args:
		order_item: An ORDER assessment item.

	Returns:
		MATCH item with shuffled prompts and position-label choices.
	"""
	ordered_list = order_item.ordered_answers_list
	num_items = len(ordered_list)

	# Create position labels: "1", "2", "3", etc.
	position_labels = [str(i + 1) for i in range(num_items)]

	# Shuffle prompts deterministically using item_crc16 as seed
	# Extract numeric portion of CRC16 (format: "aaaa_bbbb", use first 4 hex digits)
	crc_hex = order_item.item_crc16.split("_")[0]
	seed_value = int(crc_hex, 16) % (2**31)  # Ensure valid seed for random.Random
	rng = random.Random(seed_value)

	# Create shuffled copy of ordered_list
	shuffled_prompts = ordered_list.copy()
	rng.shuffle(shuffled_prompts)

	# Create and return the MATCH item
	new_match = item_types.MATCH(
		question_text=order_item.question_text,
		prompts_list=shuffled_prompts,
		choices_list=position_labels
	)

	return new_match
