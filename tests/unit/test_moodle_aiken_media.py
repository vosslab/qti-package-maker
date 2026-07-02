# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.moodle_aiken import engine_class


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
def test_save_package_emits_placeholder_and_warns(
			tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "aiken-out.txt")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "[image: foo.png]" in written_text
	assert "<img" not in written_text
	warning_output = capsys.readouterr().out
	assert "images/foo.png" in warning_output
	assert "carries no image markup" in warning_output


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
	# the real src attribute must be substituted even when a data-src decoy
	# attribute appears earlier in the tag
	bank = _make_bank_with_data_src_decoy(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "aiken-out-datasrc.txt")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "[image: figure.png]" in written_text
	assert "<img" not in written_text
	assert "lazy.png" not in written_text
