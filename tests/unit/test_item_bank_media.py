# Standard Library
import os
import re
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items.item_bank import ItemBank
from qti_package_maker.assessment_items import item_types


# Inline byte constants, same pattern as tests/unit/test_media_assets.py: tiny
# but real, decodable images written to tmp_path per PYTEST_STYLE fixture policy.

# 1x1 transparent PNG, 68 bytes.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# A second, distinct 1x1 PNG (opaque red), used for same-basename collision cases.
PNG_BYTES_ALT = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)

# 1x1 transparent GIF, 34 bytes.
GIF_BYTES = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")


#========================================================
def _mc_item(question_text: str, choice_a: str, choice_b: str) -> item_types.MC:
	"""Build a two-choice MC item whose first choice is the correct answer."""
	return item_types.MC(question_text, [choice_a, choice_b], choice_a)


#========================================================
# Dedup-by-src: two items referencing the same src share one MediaAsset record.
#========================================================
def test_two_items_sharing_a_src_dedup_to_one_asset(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	bank = ItemBank(media_base_dir=str(tmp_path))
	item1 = _mc_item("<p>Item1 <img src='foo.png' alt='fig'/></p>", "Choice A1", "Choice B1")
	item2 = _mc_item("<p>Item2 <img src='foo.png' alt='fig'/></p>", "Choice A2", "Choice B2")
	bank.add_item_cls(item1)
	bank.add_item_cls(item2)

	collected = bank.collect_assets()

	assert len(collected.assets) == 1
	asset_from_item1 = collected.item_dependencies[item1.item_crc16][0]
	asset_from_item2 = collected.item_dependencies[item2.item_crc16][0]
	assert asset_from_item1 is asset_from_item2


#========================================================
# Per-item dependency order + dedup: question_text and a choice sharing a src
# list it once; a distinct src in a later choice appears after it, in order.
#========================================================
def test_per_item_dependencies_are_ordered_and_deduped(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	(tmp_path / "bar.gif").write_bytes(GIF_BYTES)
	bank = ItemBank(media_base_dir=str(tmp_path))
	# choice_a repeats the question_text's src (foo.png); choice_b introduces bar.gif
	choice_a = "Choice one <img src='foo.png' alt='a'/>"
	choice_b = "Choice two <img src='bar.gif' alt='b'/>"
	item = _mc_item("<p><img src='foo.png' alt='a'/> question</p>", choice_a, choice_b)
	bank.add_item_cls(item)

	collected = bank.collect_assets()

	dependency_srcs = [asset.src for asset in collected.item_dependencies[item.item_crc16]]
	assert dependency_srcs == ["foo.png", "bar.gif"]


#========================================================
# Cross-item basename collision: same basename, different directories and
# bytes, resolves to two assets with distinct output_names.
#========================================================
def test_cross_item_basename_collision_gets_distinct_output_names(tmp_path: pathlib.Path) -> None:
	(tmp_path / "images").mkdir()
	(tmp_path / "figures").mkdir()
	(tmp_path / "images" / "foo.png").write_bytes(PNG_BYTES)
	(tmp_path / "figures" / "foo.png").write_bytes(PNG_BYTES_ALT)
	bank = ItemBank(media_base_dir=str(tmp_path))
	item1 = _mc_item("<img src='images/foo.png' alt='a'/>", "A1", "B1")
	item2 = _mc_item("<img src='figures/foo.png' alt='a'/>", "A2", "B2")
	bank.add_item_cls(item1)
	bank.add_item_cls(item2)

	collected = bank.collect_assets()

	output_names = {asset.output_name for asset in collected.assets}
	assert len(collected.assets) == 2
	assert len(output_names) == 2


#========================================================
# Local src with no media_base_dir raises.
#========================================================
def test_local_src_without_media_base_dir_raises() -> None:
	bank = ItemBank(media_base_dir=None)
	item = _mc_item("<img src='foo.png' alt='a'/>", "A", "B")
	bank.add_item_cls(item)

	with pytest.raises(ValueError):
		bank.collect_assets()


#========================================================
# Missing local file raises FileNotFoundError naming the file.
#========================================================
def test_missing_local_file_raises_file_not_found_error(tmp_path: pathlib.Path) -> None:
	bank = ItemBank(media_base_dir=str(tmp_path))
	item = _mc_item("<img src='missing.png' alt='a'/>", "A", "B")
	bank.add_item_cls(item)

	with pytest.raises(FileNotFoundError, match="missing.png"):
		bank.collect_assets()


#========================================================
# add_image traversal escape raises ValueError (routes through the shared
# media_assets.resolve_local_path traversal guard).
#========================================================
def test_add_image_traversal_escape_raises_value_error(tmp_path: pathlib.Path) -> None:
	bank = ItemBank(media_base_dir=str(tmp_path))
	src = "../escape.png"

	with pytest.raises(ValueError, match=re.escape(src)):
		bank.add_image(src, PNG_BYTES)


#========================================================
# add_image round-trip: registered bytes resolve through collect_assets()
# and read back identically.
#========================================================
def test_add_image_round_trips_through_collect_assets(tmp_path: pathlib.Path) -> None:
	bank = ItemBank(media_base_dir=str(tmp_path))
	bank.add_image("added/foo.png", PNG_BYTES)
	item = _mc_item("<img src='added/foo.png' alt='a'/>", "A", "B")
	bank.add_item_cls(item)

	collected = bank.collect_assets()

	asset = collected.item_dependencies[item.item_crc16][0]
	assert asset.read_bytes() == PNG_BYTES


#========================================================
# Purely-derived: repeated collect_assets() calls agree (no durable registry).
#========================================================
def test_collect_assets_is_purely_derived_and_repeatable(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	bank = ItemBank(media_base_dir=str(tmp_path))
	item1 = _mc_item("<p>Item1 <img src='foo.png' alt='fig'/></p>", "Choice A1", "Choice B1")
	item2 = _mc_item("<p>Item2 <img src='foo.png' alt='fig'/></p>", "Choice A2", "Choice B2")
	bank.add_item_cls(item1)
	bank.add_item_cls(item2)

	first_collected = bank.collect_assets()
	second_collected = bank.collect_assets()

	assert first_collected == second_collected


#========================================================
# cleanup() removes only the media_base_dir add_image() lazily created itself.
#========================================================
def test_cleanup_removes_lazily_created_tempdir() -> None:
	bank = ItemBank()
	path = bank.add_image("foo.png", PNG_BYTES)
	assert os.path.isdir(bank.media_base_dir)

	bank.cleanup()

	assert bank.media_base_dir is None
	assert not os.path.isdir(os.path.dirname(path))


#========================================================
# cleanup() leaves a constructor-supplied media_base_dir untouched.
#========================================================
def test_cleanup_leaves_caller_supplied_dir_untouched(tmp_path: pathlib.Path) -> None:
	bank = ItemBank(media_base_dir=str(tmp_path))
	(tmp_path / "keep.png").write_bytes(PNG_BYTES)

	bank.cleanup()

	assert tmp_path.is_dir()
	assert (tmp_path / "keep.png").is_file()
	assert bank.media_base_dir == str(tmp_path)


#========================================================
# cleanup() also leaves a directly-assigned media_base_dir untouched (the
# shape a ZIP reader uses to point a bank at its extraction directory).
#========================================================
def test_cleanup_leaves_directly_assigned_dir_untouched(tmp_path: pathlib.Path) -> None:
	bank = ItemBank()
	bank.media_base_dir = str(tmp_path)
	(tmp_path / "keep.png").write_bytes(PNG_BYTES)

	bank.cleanup()

	assert tmp_path.is_dir()
	assert bank.media_base_dir == str(tmp_path)


#========================================================
# cleanup() is idempotent: a second call is a no-op, not an error.
#========================================================
def test_cleanup_is_idempotent() -> None:
	bank = ItemBank()
	bank.add_image("foo.png", PNG_BYTES)

	bank.cleanup()
	bank.cleanup()

	assert bank.media_base_dir is None


#========================================================
# set_media_base_dir(path, owned=True) makes cleanup() remove that directory,
# unlike plain attribute assignment (see test_cleanup_leaves_directly_assigned
# _dir_untouched above). This is the ownership seam a reader that creates its
# own extraction directory (e.g. blackboard_export_zip) should use.
#========================================================
def test_set_media_base_dir_owned_true_is_removed_by_cleanup(tmp_path: pathlib.Path) -> None:
	media_dir = tmp_path / "extracted"
	media_dir.mkdir()
	(media_dir / "image-1.jpg").write_bytes(PNG_BYTES)
	bank = ItemBank()

	bank.set_media_base_dir(str(media_dir), owned=True)
	bank.cleanup()

	assert bank.media_base_dir is None
	assert not media_dir.is_dir()


#========================================================
# set_media_base_dir(path) with owned left at its default (False) stays
# caller-owned, matching direct attribute assignment.
#========================================================
def test_set_media_base_dir_defaults_to_caller_owned(tmp_path: pathlib.Path) -> None:
	bank = ItemBank()

	bank.set_media_base_dir(str(tmp_path))
	bank.cleanup()

	assert tmp_path.is_dir()
	assert bank.media_base_dir == str(tmp_path)


#========================================================
# Calling set_media_base_dir again while this bank still owns a different
# directory raises rather than silently leaking the first directory.
#========================================================
def test_set_media_base_dir_raises_when_replacing_owned_dir(tmp_path: pathlib.Path) -> None:
	first_dir = tmp_path / "first"
	second_dir = tmp_path / "second"
	first_dir.mkdir()
	second_dir.mkdir()
	bank = ItemBank()
	bank.set_media_base_dir(str(first_dir), owned=True)

	with pytest.raises(ValueError, match=re.escape(str(first_dir))):
		bank.set_media_base_dir(str(second_dir), owned=True)


#========================================================
# merge() carries self.media_base_dir forward when only self has one.
#========================================================
def test_merge_carries_media_base_dir_from_self(tmp_path: pathlib.Path) -> None:
	left = ItemBank(media_base_dir=str(tmp_path))
	right = ItemBank()

	merged = left.merge(right)

	assert merged.media_base_dir == str(tmp_path)


#========================================================
# merge() carries other.media_base_dir forward when only other has one.
#========================================================
def test_merge_carries_media_base_dir_from_other(tmp_path: pathlib.Path) -> None:
	left = ItemBank()
	right = ItemBank(media_base_dir=str(tmp_path))

	merged = left.merge(right)

	assert merged.media_base_dir == str(tmp_path)


#========================================================
# merge() with both banks on the same media_base_dir stays silent and carries it.
#========================================================
def test_merge_same_media_base_dir_is_silent(tmp_path: pathlib.Path) -> None:
	left = ItemBank(media_base_dir=str(tmp_path))
	right = ItemBank(media_base_dir=str(tmp_path))

	merged = left.merge(right)

	assert merged.media_base_dir == str(tmp_path)


#========================================================
# merge() with both banks on DIFFERENT media_base_dir raises loudly, naming a dir.
#========================================================
def test_merge_different_media_base_dir_raises(tmp_path: pathlib.Path) -> None:
	left_dir = tmp_path / "left"
	right_dir = tmp_path / "right"
	left_dir.mkdir()
	right_dir.mkdir()
	left = ItemBank(media_base_dir=str(left_dir))
	right = ItemBank(media_base_dir=str(right_dir))

	with pytest.raises(ValueError, match=re.escape(str(right_dir))):
		left.merge(right)


#========================================================
# merge() gives the merged bank a non-owning reference: merged.cleanup() leaves
# the lazily-created dir intact, and the owning source bank frees it exactly once.
#========================================================
def test_merge_non_owning_reference_leaves_cleanup_to_source() -> None:
	owner_bank = ItemBank()
	owner_bank.add_image("foo.png", PNG_BYTES)
	media_dir = owner_bank.media_base_dir
	merged = owner_bank.merge(ItemBank())

	merged.cleanup()
	assert os.path.isdir(media_dir)

	owner_bank.cleanup()
	assert not os.path.isdir(media_dir)
