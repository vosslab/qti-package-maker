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
import os
import math
import pathlib
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
def _compare_item(item_a: object, item_b: object) -> list[str]:
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
def test_round_trip_all_types(tmp_path: pathlib.Path) -> None:
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


#============================================
# Image embedding round-trip
#============================================
# A minimal but valid PNG header plus filler; content is opaque to the engine,
# which copies the bytes verbatim, so the exact pixels do not matter.
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"stem-image-bytes" + b"\x00" * 8
# A minimal JPEG (SOI ... EOI) with opaque filler bytes.
_JPG_BYTES = b"\xff\xd8\xff\xe0" + b"choice-image-bytes" + b"\xff\xd9"

#============================================
def test_round_trip_preserves_image_bytes_and_refs(tmp_path: pathlib.Path) -> None:
	# Acceptance: an item whose stem carries one image and an item whose
	# choice carries another are written through the csfiles mechanism, read
	# back, and must preserve both the <img src> references (basename-level, as
	# the reader rewrites to the recovered filename) and the exact image bytes.
	qti = package_interface.QTIPackageInterface(
		package_name="image_roundtrip",
		verbose=False,
		allow_mixed=True,
	)
	# The srcs are plain basenames so the reader's recovered filename equals the
	# authored src, keeping the reference identical across the round-trip.
	qti.add_item("MC", ('Identify the organelle <img src="stem.png"/>',
		["Nucleus", "Golgi", "Ribosome"], "Nucleus"))
	qti.add_item("MA", ("Which of these are metals?",
		['Iron <img src="metal.jpg"/>', "Oxygen", "Gold"],
		['Iron <img src="metal.jpg"/>', "Gold"]))
	qti.item_bank.add_image("stem.png", _PNG_BYTES)
	qti.item_bank.add_image("metal.jpg", _JPG_BYTES)

	outfile = str(tmp_path / "image_roundtrip.zip")
	result_path = qti.save_package("blackboard_export_zip", outfile)

	bank_b = read_package.read_items_from_file(result_path, allow_mixed=True)
	items_b = _index_by_question(list(bank_b))

	# The MC stem reference survives and the @X@ token is gone after read.
	mc_item = items_b["Identify the organelle <img src=\"stem.png\"/>"]
	assert '<img src="stem.png"' in mc_item.question_text
	assert "@X@EmbeddedFile.requestUrlStub" not in mc_item.question_text

	# The MA choice reference survives on the choice HTML.
	ma_item = items_b["Which of these are metals?"]
	assert any('<img src="metal.jpg"' in choice for choice in ma_item.choices_list)
	for choice in ma_item.choices_list:
		assert "@X@EmbeddedFile.requestUrlStub" not in choice

	# The extracted image bytes are byte-identical to what was embedded.
	assert bank_b.media_base_dir is not None
	stem_path = os.path.join(bank_b.media_base_dir, "stem.png")
	with open(stem_path, "rb") as stem_file:
		assert stem_file.read() == _PNG_BYTES
	metal_path = os.path.join(bank_b.media_base_dir, "metal.jpg")
	with open(metal_path, "rb") as metal_file:
		assert metal_file.read() == _JPG_BYTES
