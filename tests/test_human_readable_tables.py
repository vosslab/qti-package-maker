# Standard Library
import pathlib

# QTI Package Maker
import qti_package_maker.package_interface


def test_human_readable_tables(tmp_path: pathlib.Path) -> None:
	qti_packer = qti_package_maker.package_interface.QTIPackageInterface("human-table", verbose=False, allow_mixed=True)
	question_text = (
		"<p>Use the table below.</p>"
		"<table>"
		"<tr><th>Col A</th><th>Col B</th></tr>"
		"<tr><td>1</td><td>2</td></tr>"
		"</table>"
		"<p>Done.</p>"
	)
	choices_list = ["Option 1", "Option 2"]
	qti_packer.add_item("MC", (question_text, choices_list, "Option 1"))

	outfile = tmp_path / "human-table.html"
	qti_packer.save_package("human", str(outfile))

	with open(outfile, "r", encoding="utf-8") as f:
		contents = f.read()

	assert "[TABLE]" not in contents
	for required in ("Col A", "Col B", "1", "2"):
		assert required in contents
