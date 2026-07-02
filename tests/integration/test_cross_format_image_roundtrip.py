"""
Cross-format image roundtrip coverage.

Every existing image roundtrip test proves a single engine reading its own
write (bb_export write->read in test_media_end_to_end.py row 9, text2qti
write->read in test_text2qti_media.py). None of them prove a reader from one
engine feeding a WRITER from a different engine and then reading that
writer's own output back -- the seam this module targets.

Known, respected limitations (do not re-litigate here):
  - blackboard_export_zip roundtrips images at basename level only
    ("images/foo.png" reads back as "foo.png"); assertions below check the
    basename, not the original relative path.
  - okla_chrst_bqgen is placeholder_warn: the image is LOST by design (only a
    "[image: name.ext]" placeholder survives), so no okla image roundtrip is
    built here.
  - blackboard_export_zip readers own their extraction directory
    (ItemBank._owns_media_base_dir); every bank read through that reader is
    explicitly cleanup()-ed once its bytes are no longer needed.
"""

# Standard Library
import base64
import pathlib

# QTI Package Maker
from qti_package_maker.engines.bbq_text_upload import read_package as bbq_read_package
from qti_package_maker.engines.blackboard_export_zip import engine_class as bbexport_engine
from qti_package_maker.engines.blackboard_export_zip import read_package as bbexport_read_package
from qti_package_maker.engines.text2qti import engine_class as text2qti_engine
from qti_package_maker.engines.text2qti import read_package as text2qti_read_package


# 1x1 transparent PNG, 68 bytes. Inline per the PYTEST_STYLE fixture policy
# (reused verbatim from tests/unit/test_media_assets.py's constant pattern).
PNG_BYTES = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


#============================================
def _write_bbq_with_image(tmp_path: pathlib.Path) -> pathlib.Path:
	"""Write a one-item BBQ text file whose question references a relative image."""
	image_dir = tmp_path / "images"
	image_dir.mkdir()
	(image_dir / "figure.png").write_bytes(PNG_BYTES)
	bbq_file = tmp_path / "bbq-with-image.txt"
	question = '<p>See figure</p><img src="images/figure.png" alt="fig"/>'
	bbq_file.write_text(f"MC\t{question}\t3\tincorrect\t4\tcorrect\n", encoding="utf-8")
	return bbq_file


#========================================================
# 1. BBQ -> read via bbq -> save via blackboard_export_zip -> read that ZIP
#    back via blackboard_export_zip. Bytes stay identical, and the recovered
#    <img src> is the basename form (blackboard_export_zip's own roundtrip
#    granularity).
#========================================================
def test_bbq_to_bbexport_roundtrip_preserves_bytes_and_basename_src(
			tmp_path: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_path)
	bank_from_bbq = bbq_read_package.read_items_from_file(str(bbq_file))

	engine = bbexport_engine.EngineClass("cross-bbexport", verbose=False)
	bbexport_outfile = tmp_path / "cross_bbexport.zip"
	engine.save_package(bank_from_bbq, outfile=str(bbexport_outfile))

	bank_from_bbexport = bbexport_read_package.read_items_from_file(
		str(bbexport_outfile), allow_mixed=True)
	mc_item = next(iter(bank_from_bbexport))
	assert '<img src="figure.png"' in mc_item.question_text

	recovered_path = pathlib.Path(bank_from_bbexport.media_base_dir) / "figure.png"
	assert recovered_path.read_bytes() == PNG_BYTES

	# bb_export readers own their extraction directory; release it now that
	# the bytes above have already been read.
	bank_from_bbexport.cleanup()


#========================================================
# 2. The same BBQ source -> read via bbq -> save via text2qti -> read the
#    text2qti output back via its own reader -> the restored <img src>
#    resolves through collect_assets() to byte-identical bytes.
#========================================================
def test_bbq_to_text2qti_roundtrip_resolves_identical_bytes(tmp_path: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_path)
	bank_from_bbq = bbq_read_package.read_items_from_file(str(bbq_file))

	engine = text2qti_engine.EngineClass("cross-text2qti", verbose=False)
	text2qti_outfile = tmp_path / "cross_text2qti.txt"
	engine.save_package(bank_from_bbq, outfile=str(text2qti_outfile))

	bank_from_text2qti = text2qti_read_package.read_items_from_file(
		str(text2qti_outfile), allow_mixed=True)
	item = next(iter(bank_from_text2qti))
	assert '<img src="media/figure.png"' in item.question_text

	collected = bank_from_text2qti.collect_assets()
	assert len(collected.assets) == 1
	assert collected.assets[0].read_bytes() == PNG_BYTES


#========================================================
# 3. Chain across three formats: BBQ -> bb_export ZIP -> read -> text2qti ->
#    read -> collect_assets() bytes are still identical to the original
#    inline constant. This is the longest supported reader chain (the
#    blackboard_export_zip reader's basename-level rewrite feeds straight
#    into text2qti's own <img src> resolution without any manual repair).
#========================================================
def test_bbq_to_bbexport_to_text2qti_chain_preserves_bytes(tmp_path: pathlib.Path) -> None:
	bbq_file = _write_bbq_with_image(tmp_path)
	bank_from_bbq = bbq_read_package.read_items_from_file(str(bbq_file))

	bbexport = bbexport_engine.EngineClass("chain-bbexport", verbose=False)
	bbexport_outfile = tmp_path / "chain_bbexport.zip"
	bbexport.save_package(bank_from_bbq, outfile=str(bbexport_outfile))
	bank_from_bbexport = bbexport_read_package.read_items_from_file(
		str(bbexport_outfile), allow_mixed=True)

	text2qti = text2qti_engine.EngineClass("chain-text2qti", verbose=False)
	text2qti_outfile = tmp_path / "chain_text2qti.txt"
	text2qti.save_package(bank_from_bbexport, outfile=str(text2qti_outfile))
	# the bb_export reader's owned extraction dir is no longer needed once
	# the text2qti writer above has copied its bytes onward.
	bank_from_bbexport.cleanup()

	bank_from_text2qti = text2qti_read_package.read_items_from_file(
		str(text2qti_outfile), allow_mixed=True)
	collected = bank_from_text2qti.collect_assets()
	assert len(collected.assets) == 1
	assert collected.assets[0].read_bytes() == PNG_BYTES
