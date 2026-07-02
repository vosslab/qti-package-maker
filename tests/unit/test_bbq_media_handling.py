# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest

# QTI Package Maker
from qti_package_maker.engines.bbq_text_upload import engine_class
from qti_package_maker.engines.bbq_text_upload import read_package


# 1x1 transparent PNG, 68 bytes. Inline per the PYTEST_STYLE fixture policy:
# a real, decodable image so extension and payload agree, with no committed
# image file on disk.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


#============================================
def _write_bbq_with_image(tmp_path: pathlib.Path, src: str) -> pathlib.Path:
	"""Write a one-item BBQ text file whose question references an <img src>."""
	bbq_file = tmp_path / "bbq-with-image.txt"
	question = f'<p>See figure</p><img src="{src}" alt="fig"/>'
	bbq_file.write_text(f"MC\t{question}\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")
	return bbq_file


#============================================
def test_reader_sets_media_base_dir_to_input_directory(tmp_path: pathlib.Path) -> None:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	bbq_file = _write_bbq_with_image(tmp_path, "images/foo.png")
	bank = read_package.read_items_from_file(str(bbq_file))
	assert bank.media_base_dir == str(tmp_path)


#============================================
def test_relative_src_resolves_purely_by_derivation(tmp_path: pathlib.Path) -> None:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	bbq_file = _write_bbq_with_image(tmp_path, "images/foo.png")
	# collect_assets() is called twice to confirm the result is derived fresh
	# each time (no durable per-item asset registry attached during read).
	bank = read_package.read_items_from_file(str(bbq_file))
	first_pass = bank.collect_assets()
	second_pass = bank.collect_assets()
	assert len(first_pass.assets) == 1
	assert first_pass.assets[0].read_bytes() == PNG_BYTES
	assert second_pass.assets[0].read_bytes() == PNG_BYTES


#============================================
def test_missing_local_image_raises_with_filename(tmp_path: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_path, "images/missing.png")
	bank = read_package.read_items_from_file(str(bbq_file))
	with pytest.raises(FileNotFoundError, match="missing.png"):
		bank.collect_assets()


#============================================
def test_writer_keeps_img_verbatim_and_warns(
			tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	bbq_file = _write_bbq_with_image(tmp_path, "images/foo.png")
	bank = read_package.read_items_from_file(str(bbq_file))
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "bbq-out.txt")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert '<img src="images/foo.png" alt="fig"/>' in written_text
	warning_output = capsys.readouterr().out
	assert "images/foo.png" in warning_output
	assert "does not transport image files" in warning_output
