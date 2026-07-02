# Standard Library
import base64
import pathlib

# Pip3 Library

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.html_selftest import engine_class


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
def test_save_package_embeds_image_as_base64_data_uri(tmp_path: pathlib.Path) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "selftest-out.html")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	assert "data:image/png;base64," in written_text
	assert 'src="images/' not in written_text


#============================================
def test_save_package_ignores_data_src_and_embeds_only_real_src(tmp_path: pathlib.Path) -> None:
	# a lazy-load "data-src" attribute alongside a real "src" previously crashed
	# _to_data_uri with a KeyError (the old regex matched "data-src" as "src")
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "foo.png").write_bytes(PNG_BYTES)
	bank = item_bank.ItemBank(media_base_dir=str(tmp_path))
	question_text = (
		'<p>See figure</p>'
		'<img data-src="images/lazy-placeholder.png" src="images/foo.png" alt="fig"/>'
	)
	bank.add_item("MC", (question_text, ["A", "B"], "A"))
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "selftest-out.html")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	# only the real src is embedded; the data-src attribute survives verbatim
	assert 'data-src="images/lazy-placeholder.png"' in written_text
	assert "data:image/png;base64," in written_text
	assert 'src="images/foo.png"' not in written_text


#============================================
def test_save_package_data_uri_decodes_back_to_original_bytes(tmp_path: pathlib.Path) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "selftest-out.html")
	engine.save_package(bank, outfile=outfile)
	written_text = pathlib.Path(outfile).read_text(encoding="utf-8")
	data_uri_start = written_text.index("data:image/png;base64,") + len("data:image/png;base64,")
	data_uri_end = written_text.index('"', data_uri_start)
	encoded_payload = written_text[data_uri_start:data_uri_end]
	assert base64.b64decode(encoded_payload) == PNG_BYTES
