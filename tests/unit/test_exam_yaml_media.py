# Standard Library
import base64
import pathlib

# Pip3 Library
import pytest
import yaml

# QTI Package Maker
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.engines.exam_yaml import engine_class


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
def test_save_package_keeps_img_verbatim_in_statement_and_warns(
			tmp_path: pathlib.Path, capsys: pytest.CaptureFixture) -> None:
	bank = _make_bank_with_image(tmp_path)
	engine = engine_class.EngineClass("sample", verbose=False)
	outfile = str(tmp_path / "exam-out.yaml")
	engine.save_package(bank, outfile=outfile)
	exam_data = yaml.safe_load(pathlib.Path(outfile).read_text(encoding="utf-8"))
	statement = exam_data["sections"][0]["questions"][0]["statement"]
	assert '<img src="images/foo.png" alt="fig"/>' in statement
	warning_output = capsys.readouterr().out
	assert "images/foo.png" in warning_output
	assert "does not transport image files" in warning_output
