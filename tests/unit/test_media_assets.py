# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.common import media_assets


# Inline byte constants (reusable pattern for the integration test layer).
# Tiny but real, decodable images so extension and payload agree; content
# validity is irrelevant to media_assets (it routes on extension), but real
# bytes keep the fixtures honest and unsurprising.

# 1x1 transparent PNG, 68 bytes.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# A second, distinct 1x1 PNG (opaque red) for the same-basename collision case.
PNG_BYTES_ALT = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)

# 1x1 transparent GIF, 34 bytes.
GIF_BYTES = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==")

# 1x1 opaque red JPEG, 633 bytes.
JPEG_BYTES = base64.b64decode(
	"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
	"HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
	"MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIA"
	"AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
	"AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
	"ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
	"p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
	"AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
	"BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElK"
	"U1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3"
	"uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDi6KKK"
	"+ZP3E//Z"
)

# Minimal SVG document, 67 bytes.
SVG_BYTES = b"<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1'></svg>"

ENGINE_NAME = "unit-test-engine"
ITEM_CRC = "abcd1234"


#========================================================
# Row 1: scan finds src in question_text and a choice, resolves, names, rewrites.
#========================================================
def test_scan_finds_img_src_in_question_and_choice_fields() -> None:
	question_html = "<p>Look at <img src='images/foo.png' alt='fig'> above.</p>"
	choice_html = "<span>Compare to <img src='images/foo.png' alt='fig'></span>"
	question_srcs = media_assets.scan_html_for_assets(question_html)
	choice_srcs = media_assets.scan_html_for_assets(choice_html)
	assert question_srcs == ["images/foo.png"]
	assert choice_srcs == ["images/foo.png"]


def test_resolve_and_name_asset_from_scanned_src(tmp_path: pathlib.Path) -> None:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	asset = media_assets.resolve_asset("images/foo.png", base_dir=str(tmp_path))
	named_assets = media_assets.assign_output_names([asset])
	assert named_assets[0].output_name == "foo.png"
	assert asset.read_bytes() == PNG_BYTES


def test_rewrite_html_srcs_only_touches_img_tags() -> None:
	html = "<p><a href='images/foo.png'>link</a> <img src='images/foo.png'></p>"
	rewritten = media_assets.rewrite_html_srcs(html, lambda src: "packaged/" + src.split("/")[-1])
	# the <a href> is untouched; only the <img src> is remapped
	assert "href='images/foo.png'" in rewritten
	assert "<img src='packaged/foo.png'>" in rewritten


def test_rewrite_html_srcs_leaves_data_src_untouched() -> None:
	# a leading lazy-load "data-src" attribute must never be mistaken for "src"
	# ("-" is a non-word char, so a plain \b boundary matches there too)
	html = '<img data-src="lazy.png" src="real.png">'
	rewritten = media_assets.rewrite_html_srcs(html, lambda src: "packaged/" + src)
	assert 'data-src="lazy.png"' in rewritten
	assert 'src="packaged/real.png"' in rewritten


#========================================================
# Row 2: identical bytes via the same src dedup to one output name.
#========================================================
def test_identical_src_dedups_to_one_output_name(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	# two independent resolutions of the same src (e.g. from two item fields)
	asset_one = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	asset_two = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	named_assets = media_assets.assign_output_names([asset_one, asset_two])
	assert named_assets[0].output_name == named_assets[1].output_name


def test_compute_content_hash_matches_for_identical_bytes(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	asset_one = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	asset_two = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	assert media_assets.compute_content_hash(asset_one) == media_assets.compute_content_hash(asset_two)


#========================================================
# Row 3: same basename, different bytes at different paths -> deterministic rename.
#========================================================
def test_same_basename_different_paths_gets_disambiguated(tmp_path: pathlib.Path) -> None:
	images_dir = tmp_path / "images"
	figures_dir = tmp_path / "figures"
	images_dir.mkdir()
	figures_dir.mkdir()
	(images_dir / "foo.png").write_bytes(PNG_BYTES)
	(figures_dir / "foo.png").write_bytes(PNG_BYTES_ALT)
	asset_from_images = media_assets.resolve_asset("images/foo.png", base_dir=str(tmp_path))
	asset_from_figures = media_assets.resolve_asset("figures/foo.png", base_dir=str(tmp_path))
	named_assets = media_assets.assign_output_names([asset_from_images, asset_from_figures])
	output_names = {asset.output_name for asset in named_assets}
	# both srcs are packaged, distinct output names, and path identity survives
	assert len(output_names) == 2
	assert asset_from_images.file_path != asset_from_figures.file_path
	assert asset_from_images.read_bytes() != asset_from_figures.read_bytes()


#========================================================
# Row 4: external https URL -> classified external, warned, never resolved to a file.
#========================================================
def test_external_url_classified_and_not_resolved_to_file() -> None:
	src = "https://example.com/diagram.png"
	assert media_assets.classify_src(src) == media_assets.KIND_EXTERNAL
	asset = media_assets.resolve_asset(src)
	assert asset.file_path is None
	assert asset.data_bytes is None


def test_external_url_warns_under_package_policy() -> None:
	asset = media_assets.resolve_asset("https://example.com/diagram.png")
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PACKAGE, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert len(decision.warnings) == 1
	assert decision.warnings[0].src == asset.src


#========================================================
# Row 5 (media_assets layer only): data URI resolves without base_dir.
# The engine-level split (html_selftest passes / packaging QTI writers raise)
# is asserted later in integration tests once those writers exist.
#========================================================
def test_data_uri_resolves_without_base_dir_and_reads_payload() -> None:
	encoded = base64.b64encode(GIF_BYTES).decode("ascii")
	src = f"data:image/gif;base64,{encoded}"
	assert media_assets.classify_src(src) == media_assets.KIND_DATA_URI
	asset = media_assets.resolve_asset(src)
	assert asset.read_bytes() == GIF_BYTES


def test_data_uri_warns_under_package_policy() -> None:
	encoded = base64.b64encode(GIF_BYTES).decode("ascii")
	asset = media_assets.resolve_asset(f"data:image/gif;base64,{encoded}")
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PACKAGE, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert len(decision.warnings) == 1
	assert decision.warnings[0].src == asset.src


#========================================================
# Row 6: SVG resolves, packages, and is warned under the package policy.
#========================================================
def test_svg_resolves_and_packages(tmp_path: pathlib.Path) -> None:
	(tmp_path / "icon.svg").write_bytes(SVG_BYTES)
	asset = media_assets.resolve_asset("icon.svg", base_dir=str(tmp_path))
	assert asset.mime_type == media_assets.SVG_MIME_TYPE
	assert asset.read_bytes() == SVG_BYTES


def test_svg_warns_under_package_policy(tmp_path: pathlib.Path) -> None:
	(tmp_path / "icon.svg").write_bytes(SVG_BYTES)
	asset = media_assets.resolve_asset("icon.svg", base_dir=str(tmp_path))
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PACKAGE, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert len(decision.warnings) == 1
	assert decision.warnings[0].src == "icon.svg"


#========================================================
# Row 7: error inputs each raise, naming the offending src.
#========================================================
def test_missing_local_file_raises_file_not_found_error(tmp_path: pathlib.Path) -> None:
	with pytest.raises(FileNotFoundError, match="missing.png"):
		media_assets.resolve_asset("missing.png", base_dir=str(tmp_path))


def test_unsupported_extension_raises_value_error(tmp_path: pathlib.Path) -> None:
	(tmp_path / "photo.webp").write_bytes(b"fake webp bytes")
	with pytest.raises(ValueError, match="photo.webp"):
		media_assets.resolve_asset("photo.webp", base_dir=str(tmp_path))


def test_traversal_outside_base_dir_raises_value_error(tmp_path: pathlib.Path) -> None:
	src = "../escape.png"
	with pytest.raises(ValueError, match=r"\.\./escape\.png"):
		media_assets.resolve_asset(src, base_dir=str(tmp_path))


#========================================================
# Row 8: the four media policies route correctly.
#========================================================
def test_package_policy_is_silent_for_first_class_raster(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	asset = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PACKAGE, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert decision.warnings == []


def test_jpeg_resolves_as_first_class_raster(tmp_path: pathlib.Path) -> None:
	(tmp_path / "photo.jpg").write_bytes(JPEG_BYTES)
	asset = media_assets.resolve_asset("photo.jpg", base_dir=str(tmp_path))
	assert asset.mime_type == "image/jpeg"
	assert asset.read_bytes() == JPEG_BYTES
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PACKAGE, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert decision.warnings == []


def test_reference_warn_policy_emits_one_warning_per_asset(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	asset = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_REFERENCE_WARN, [asset], ENGINE_NAME, ITEM_CRC
	)
	assert len(decision.warnings) == 1
	assert decision.placeholders == {}


def test_placeholder_warn_policy_fills_readable_placeholder_text(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	asset = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	named_assets = media_assets.assign_output_names([asset])
	decision = media_assets.apply_media_policy(
		media_assets.POLICY_PLACEHOLDER_WARN, named_assets, ENGINE_NAME, ITEM_CRC
	)
	assert len(decision.warnings) == 1
	assert decision.placeholders["foo.png"] == "[image: foo.png]"


def test_fail_policy_raises_and_lists_offending_srcs(tmp_path: pathlib.Path) -> None:
	(tmp_path / "foo.png").write_bytes(PNG_BYTES)
	asset = media_assets.resolve_asset("foo.png", base_dir=str(tmp_path))
	with pytest.raises(media_assets.MediaPolicyError, match="foo.png"):
		media_assets.apply_media_policy(media_assets.POLICY_FAIL, [asset], ENGINE_NAME, ITEM_CRC)


def test_fail_policy_permits_items_with_no_images() -> None:
	decision = media_assets.apply_media_policy(media_assets.POLICY_FAIL, [], ENGINE_NAME, ITEM_CRC)
	assert decision.warnings == []
