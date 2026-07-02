"""
Regression (fixed): QTIPackageInterface.read_package() preserves the
reader-set media_base_dir on every image-bearing read.

ItemBank.merge() (qti_package_maker/assessment_items/item_bank.py) carries the
surviving media_base_dir forward (self wins when set, else other), so the
reader-set base directory is no longer dropped.
QTIPackageInterface.read_package() merges the freshly read bank into
self.item_bank via `self.item_bank += new_item_bank`
(ItemBank.__add__ -> ItemBank.merge()) on EVERY read, so a caller who reads an
image-bearing package and then calls save_package() on an image-aware engine
resolves the source file's <img src> through collect_assets() without a
ValueError. Bug originally found during integration testing and fixed in
ItemBank.merge().
"""

# Standard Library
import base64
import pathlib

# QTI Package Maker
from qti_package_maker import package_interface


# 1x1 transparent PNG, 68 bytes. Inline per the PYTEST_STYLE fixture policy.
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


#============================================
def _write_bbq_with_image(tmp_path: pathlib.Path) -> pathlib.Path:
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bbq_file = tmp_path / "bbq-with-image.txt"
	question = '<p>See figure</p><img src="images/figure.png" alt="fig"/>'
	bbq_file.write_text(f"MC\t{question}\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")
	return bbq_file


#============================================
def test_read_package_preserves_media_base_dir_for_downstream_collect_assets(
			tmp_path: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_path)
	qti = package_interface.QTIPackageInterface("bug-finding", verbose=False)
	qti.read_package(str(bbq_file), "bbq_text_upload")
	# The reader's media_base_dir survives the merge into self.item_bank.
	assert qti.item_bank.media_base_dir is not None
	collected = qti.item_bank.collect_assets()
	assert collected.assets[0].read_bytes() == PNG_BYTES
