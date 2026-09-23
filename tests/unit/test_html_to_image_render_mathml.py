"""Validate the MathML subset used by the exam importer."""

# PIP3 modules
import pytest

# local repo modules
from qti_package_maker.html_to_image.render_table import _prepare_mathml_html


#============================================
def test_prepare_mathml_expands_legacy_fenced_fraction() -> None:
	"""The current Henderson-Hasselbalch markup becomes MathML Core markup."""
	mathml = (
		'<math xmlns="http://www.w3.org/1998/Math/MathML">'
		'<mi>pH</mi><mo>&#8201;</mo><mo>=</mo><mfenced><mfrac>'
		'<mrow><msup><mi mathvariant="normal">A</mi>'
		'<mo>&#8211;</mo></msup></mrow>'
		'<mrow><mi>HA</mi></mrow>'
		'</mfrac></mfenced></math>')
	prepared = _prepare_mathml_html(mathml)
	assert '<mfenced' not in prepared
	assert '<mo>(</mo>' in prepared
	assert '<mfrac>' in prepared
	assert '<mo>)</mo>' in prepared
	assert '<script' not in prepared


#============================================
def test_prepare_mathml_rejects_scripts_attributes_and_bad_arity() -> None:
	"""Unsupported markup fails before it can reach the browser renderer."""
	with pytest.raises(ValueError, match='unsupported MathML element <script>'):
		_prepare_mathml_html('<math><mi>x</mi><script>run()</script></math>')
	with pytest.raises(ValueError, match='unsupported MathML attributes'):
		_prepare_mathml_html('<math><mi onclick="run()">x</mi></math>')
	with pytest.raises(ValueError, match='must have two expressions'):
		_prepare_mathml_html('<math><msub><mi>x</mi></msub></math>')
