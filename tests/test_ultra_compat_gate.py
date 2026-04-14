"""Unit tests for Ultra QTI 2.1 compatibility validation gate."""

# Pip3 Library
import pytest
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.bb_ultra_qti_v2_1 import compat_gate


#============================================
_SCORE_DECL = (
	'<outcomeDeclaration identifier="SCORE" baseType="float" cardinality="single">'
	'<defaultValue><value>0</value></defaultValue>'
	'</outcomeDeclaration>'
)


def _build_item(body_xml: str, include_score: bool = True,
		response_value: str = "answer_1") -> lxml.etree._Element:
	"""
	Build a minimal assessmentItem around a configurable itemBody fragment.

	Args:
		body_xml: Inner HTML of the <itemBody>'s nested <div><div>.
		include_score: If False, omit the SCORE outcomeDeclaration.
		response_value: The value inside <correctResponse>.

	Returns:
		Parsed assessmentItem element.
	"""
	score_decl = _SCORE_DECL if include_score else ""
	xml_string = (
		'<?xml version="1.0" encoding="UTF-8"?>'
		'<assessmentItem identifier="test-item" version="2.1">'
		'<responseDeclaration identifier="RESPONSE" cardinality="multiple" baseType="identifier">'
		f'<correctResponse><value>{response_value}</value></correctResponse>'
		'</responseDeclaration>'
		f'{score_decl}'
		f'<itemBody><div><div>{body_xml}</div></div></itemBody>'
		'</assessmentItem>'
	)
	return lxml.etree.fromstring(xml_string.encode('utf-8'))


#============================================
def test_well_formed_mc_item_passes():
	body = (
		'<p>What is 2 + 2?</p>'
		'<choiceinteraction responseIdentifier="RESPONSE" shuffle="false">'
		'<simplechoice identifier="answer_1"><div><p>4</p></div></simplechoice>'
		'<simplechoice identifier="answer_2"><div><p>5</p></div></simplechoice>'
		'</choiceinteraction>'
	)
	item = _build_item(body, response_value="answer_1")
	warnings = compat_gate.validate_assessment_items([item])
	assert warnings == []


#============================================
HARD_FAIL_CASES = [
	(
		'dangling_correct_response',
		'<choiceinteraction responseIdentifier="RESPONSE">'
		'<simplechoice identifier="answer_1"><div><p>A</p></div></simplechoice>'
		'</choiceinteraction>',
		{'include_score': True, 'response_value': 'answer_nonexistent'},
		'answer_nonexistent',
	),
	(
		'style_attribute',
		'<p style="color:red">Styled text</p>',
		{'include_score': True},
		'style=',
	),
	(
		'script_element',
		'<script>alert("xss");</script>',
		{'include_score': True},
		'script',
	),
	(
		'img_element',
		'<img src="test.png"/>',
		{'include_score': True},
		'img',
	),
	(
		'disallowed_tag',
		'<marquee>Scrolling text</marquee>',
		{'include_score': True},
		'marquee',
	),
	(
		'missing_score_outcome',
		'<p>Test</p>',
		{'include_score': False},
		'SCORE',
	),
]


@pytest.mark.parametrize(
	'body,build_kwargs,substring',
	[(body, kw, sub) for (_label, body, kw, sub) in HARD_FAIL_CASES],
	ids=[label for (label, _b, _k, _s) in HARD_FAIL_CASES],
)
def test_hard_fail_cases_raise(body, build_kwargs, substring):
	item = _build_item(body, **build_kwargs)
	with pytest.raises(compat_gate.UltraCompatibilityError) as exc_info:
		compat_gate.validate_assessment_items([item])
	assert substring.lower() in str(exc_info.value).lower()


#============================================
def test_oversized_cell_text_warns():
	# >1000-char cells survive but should raise a warning for author review.
	body = f'<table><tr><td>{"x" * 1001}</td></tr></table>'
	item = _build_item(body)
	warnings = compat_gate.validate_assessment_items([item])
	assert any("1000" in w for w in warnings)


def test_empty_choice_interaction_warns():
	body = '<choiceinteraction responseIdentifier="RESPONSE"/>'
	item = _build_item(body)
	warnings = compat_gate.validate_assessment_items([item])
	assert any("zero simpleChoice" in w for w in warnings)
