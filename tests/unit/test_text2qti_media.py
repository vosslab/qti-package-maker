# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.text2qti import engine_class
from qti_package_maker.engines.text2qti import read_package


# 1x1 transparent PNG, 68 bytes. Inline per the PYTEST_STYLE fixture policy:
# a real, decodable image so extension and payload agree, with no committed
# image file on disk.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


#============================================
def _make_bank_with_image(tmp_path: pathlib.Path) -> item_bank.ItemBank:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	bank = item_bank.ItemBank(media_base_dir=str(tmp_path))
	question_text = '<p>See figure</p><img src="images/foo.png" alt="fig"/>'
	bank.add_item("MC", (question_text, ["A", "B"], "A"))
	return bank


#============================================
def test_save_package_emits_markdown_and_copies_file(
			tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "text2qti-out.txt")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "![fig](media/foo.png)" in written_text
	assert "<img" not in written_text
	copied_bytes = (tmp_path / "media" / "foo.png").read_bytes()
	assert copied_bytes == PNG_BYTES
	warning_output = capsys.readouterr().out
	assert "images/foo.png" in warning_output


#============================================
def _make_bank_with_data_src_decoy(tmp_path: pathlib.Path) -> item_bank.ItemBank:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bank = item_bank.ItemBank(media_base_dir=str(tmp_path))
	# a data-src lazy-load decoy sits before the real src attribute
	question_text = (
		'<p>See figure</p>'
		'<img data-src="lazy.png" src="images/figure.png" alt="fig"/>'
	)
	bank.add_item("MC", (question_text, ["A", "B"], "A"))
	return bank


#============================================
def test_save_package_ignores_data_src_decoy(tmp_path: pathlib.Path) -> None:
	# the real src attribute must resolve to its copied media file even when a
	# data-src decoy attribute appears earlier in the tag
	bank = _make_bank_with_data_src_decoy(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "text2qti-out-datasrc.txt")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "![fig](media/figure.png)" in written_text
	assert "<img" not in written_text
	assert "lazy.png" not in written_text
	copied_bytes = (tmp_path / "media" / "figure.png").read_bytes()
	assert copied_bytes == PNG_BYTES


#============================================
def test_read_write_roundtrip_keeps_image_as_img_tag(tmp_path: pathlib.Path) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "text2qti-out.txt")
	engine.save_package(bank, outfile=outfile)
	roundtripped_bank = read_package.read_items_from_file(outfile, allow_mixed=True)
	roundtripped_item = next(iter(roundtripped_bank.items_dict.values()))
	assert '<img src="media/foo.png"' in roundtripped_item.question_text
	assert "asset:" not in roundtripped_item.question_text
	# the reader points media_base_dir at the output file's directory, so the
	# copied "media/foo.png" resolves and collect_assets() reads the same bytes
	collected = roundtripped_bank.collect_assets()
	assert collected.assets[0].read_bytes() == PNG_BYTES
