# Standard Library
import zipfile

# QTI Package Maker
import qti_package_maker.package_interface


def _make_packer():
	qti_packer = qti_package_maker.package_interface.QTIPackageInterface("engine-out", verbose=False, allow_mixed=True)
	qti_packer.add_item("MC", ("What is 2 + 2?", ["3", "4"], "4"))
	return qti_packer


def test_canvas_qti_v1_2_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("canvas_qti_v1_2")
	assert outfile
	with zipfile.ZipFile(outfile, "r") as zf:
		names = zf.namelist()
		assert "imsmanifest.xml" in names
		assert any(name.endswith(".xml") for name in names)


def test_blackboard_qti_v2_1_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("blackboard_qti_v2_1")
	assert outfile
	with zipfile.ZipFile(outfile, "r") as zf:
		names = zf.namelist()
		assert "imsmanifest.xml" in names
		assert any(name.endswith(".xml") for name in names)


def test_human_readable_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("human_readable")
	assert outfile
	with open(outfile, "r", encoding="utf-8") as f:
		contents = f.read()
	assert "What is 2 + 2?" in contents


def test_html_selftest_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("html_selftest")
	assert outfile
	with open(outfile, "r", encoding="utf-8") as f:
		contents = f.read()
	assert "<div" in contents.lower()
	assert "What is 2 + 2?" in contents


def test_bbq_text_upload_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("bbq_text_upload")
	assert outfile
	with open(outfile, "r", encoding="utf-8") as f:
		contents = f.read()
	assert contents.startswith("MC\t")
	assert "correct" in contents


def test_text2qti_output(tmp_cwd):
	qti_packer = _make_packer()
	outfile = qti_packer.save_package("text2qti")
	assert outfile
	with open(outfile, "r", encoding="utf-8") as f:
		contents = f.read()
	assert "What is 2 + 2?" in contents
