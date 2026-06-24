"""
Self-contained behavior round-trip for the blackboard_export_zip engine.

Builds one item of every first-class type in code (no external sample data),
writes them through the engine to a ZIP in tmp_path, reads that ZIP back with
the engine reader, and asserts behavior-level equality. This exercises the
writer and reader together across all six types in a single fast, deterministic
test that depends on nothing outside the repo.

The comparator is type-aware: it compares only the fields item_types.* stores
(the fields that survive the write<->read cycle) and ignores Blackboard metadata
the model discards (idents, scores, serialization differences). Items are
aligned by question_text, which is unique per built item.

An ORDER item is included to confirm the engine drops unsupported types.
"""

# Standard Library
import math
import zipfile

# QTI Package Maker
from qti_package_maker import package_interface
from qti_package_maker.engines.blackboard_export_zip import read_package

# Absolute tolerance for NUM float comparison: text serialises to 6 d.p., so
# 1e-5 absorbs formatting round-trip noise without masking real errors.
_FLOAT_ATOL = 1e-5

#============================================
def _build_round_trip_bank() -> package_interface.QTIPackageInterface:
	"""
	Build a packer holding one item of every first-class type plus an ORDER.

	Each question_text is unique so items can be aligned after the round-trip.
	Content is ASCII with distinct choices so the reader accepts every item.

	Returns:
		A QTIPackageInterface loaded with the test items.
	"""
	qti = package_interface.QTIPackageInterface(
		package_name="roundtrip_test",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MC", ("Which planet is closest to the Sun?",
		["Mercury", "Venus", "Earth", "Mars"], "Mercury"))
	qti.add_item("MA", ("Which of these are noble gases?",
		["Helium", "Neon", "Oxygen", "Argon"], ["Helium", "Neon", "Argon"]))
	qti.add_item("MATCH", ("Match each element to its symbol.",
		["Hydrogen", "Helium", "Lithium"], ["H", "He", "Li"]))
	qti.add_item("FIB", ("The powerhouse of the cell is the ____.",
		["mitochondria", "mitochondrion"]))
	qti.add_item("NUM", ("What is two plus two?", 4.0, 0.1))
	qti.add_item("MULTI_FIB", ("An [acid] plus a [base] makes salt and water.",
		{"acid": ["acid"], "base": ["base"]}))
	# ORDER has no write function; the engine must drop it with a warning.
	qti.add_item("ORDER", ("Rank these by size.", ["small", "medium", "large"]))
	return qti

#============================================
def _index_by_question(items: list) -> dict:
	"""Index item instances by their question_text (unique per built item)."""
	return {item.question_text: item for item in items}

#============================================
def _compare_item(item_a, item_b) -> list[str]:
	"""
	Compare a built item to its round-tripped counterpart at the behavior level.

	Args:
		item_a: The original built item.
		item_b: The round-tripped item read back from the ZIP.

	Returns:
		A list of failure strings; empty means behavior-equal.
	"""
	failures = []
	type_name = item_a.item_type
	if item_b.item_type != type_name:
		failures.append(f"{type_name}: item type changed to {item_b.item_type}")
		return failures
	if type_name == "MC":
		if set(item_a.choices_list) != set(item_b.choices_list):
			failures.append("MC choices mismatch")
		if item_a.answer_text != item_b.answer_text:
			failures.append("MC answer mismatch")
	elif type_name == "MA":
		if set(item_a.choices_list) != set(item_b.choices_list):
			failures.append("MA choices mismatch")
		if set(item_a.answers_list) != set(item_b.answers_list):
			failures.append("MA answers mismatch")
	elif type_name == "MATCH":
		# Prompt->choice mapping must survive (order-insensitive, pairing-sensitive).
		pairing_a = dict(zip(item_a.prompts_list, item_a.choices_list))
		pairing_b = dict(zip(item_b.prompts_list, item_b.choices_list))
		if pairing_a != pairing_b:
			failures.append(f"MATCH pairing mismatch: A={pairing_a} B={pairing_b}")
	elif type_name == "FIB":
		if set(item_a.answers_list) != set(item_b.answers_list):
			failures.append("FIB answers mismatch")
	elif type_name == "NUM":
		if not math.isclose(item_a.answer_float, item_b.answer_float, abs_tol=_FLOAT_ATOL):
			failures.append("NUM answer_float mismatch")
		if not math.isclose(item_a.tolerance_float, item_b.tolerance_float, abs_tol=_FLOAT_ATOL):
			failures.append("NUM tolerance_float mismatch")
	elif type_name == "MULTI_FIB":
		keys_a = set(item_a.answer_map.keys())
		keys_b = set(item_b.answer_map.keys())
		if keys_a != keys_b:
			failures.append(f"MULTI_FIB blank keys mismatch: A={sorted(keys_a)} B={sorted(keys_b)}")
		for key in keys_a & keys_b:
			if set(item_a.answer_map[key]) != set(item_b.answer_map[key]):
				failures.append(f"MULTI_FIB blank '{key}' answers mismatch")
	return failures

#============================================
def test_round_trip_all_types(tmp_path) -> None:
	# Write every first-class type through the engine, read it back, and assert
	# behavior-level equality. ORDER is dropped by the engine and must be absent.
	qti = _build_round_trip_bank()
	items_a = [item for item in qti.item_bank if item.item_type != "ORDER"]

	outfile = str(tmp_path / "roundtrip.zip")
	result_path = qti.save_package("blackboard_export_zip", outfile)
	assert zipfile.is_zipfile(result_path), f"save_package did not produce a ZIP: {result_path}"

	bank_b = read_package.read_items_from_file(result_path, allow_mixed=True)
	items_b_by_question = _index_by_question(list(bank_b))

	# ORDER was added but has no write function, so it must not appear.
	assert "Rank these by size." not in items_b_by_question, \
		"ORDER item should have been dropped by the engine"

	all_failures = []
	for item_a in items_a:
		item_b = items_b_by_question.get(item_a.question_text)
		if item_b is None:
			all_failures.append(f"{item_a.item_type}: item missing after round-trip")
			continue
		all_failures.extend(_compare_item(item_a, item_b))

	assert not all_failures, "Round-trip behavior failures:\n" + "\n".join(all_failures)
