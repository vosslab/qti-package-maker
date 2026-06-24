"""
Engine smoke tests for the blackboard_export_zip write path.

Exercises the full EngineClass.save_package pipeline end-to-end:
  - The ZIP contains no .bb-package-sig (server-side only).
  - An ORDER item emits a warning (via base_engine dispatch) and is absent from
    the pool.
  - RIGHT_MATCH_BLOCK is a sibling of RESPONSE_BLOCK (not nested inside it).

The basic "writes a valid ZIP with manifest + pool dat" path is covered by the
round-trip test, which writes via the engine and reads the result back.

These tests write only inside tmp_path and finish well under a second.
"""

# Standard Library
import re
import zipfile

# PIP3 modules
import lxml.html
import lxml.etree

# QTI Package Maker
from qti_package_maker.assessment_items import item_types
from qti_package_maker.engines.blackboard_export_zip import read_package
from qti_package_maker.engines.blackboard_export_zip import MC
from qti_package_maker.engines.blackboard_export_zip import MA
from qti_package_maker.engines.blackboard_export_zip import FIB
from qti_package_maker.engines.blackboard_export_zip import MATCH
from qti_package_maker.engines.blackboard_export_zip import common_xml
from qti_package_maker.package_interface import QTIPackageInterface

# Matches the engine's 32-char lowercase hex idents (dashless UUID shape).
_HEX_IDENT_RE = re.compile(r"^[0-9a-f]{32}$")

# Real-shape MA resprocessing, masked. Provenance: extracted from the real pool
# BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Haworth_FURAN_MA/res00002.dat
# (item #1, 11 choices, correct at positions 0, 3, 5, 7, 9), then every generated
# 32-hex ident replaced with a stable IDENT_<n> placeholder in first-seen document
# order. NOT authored from memory: the <and> ordering, <not> placement, penalty
# branch count (one per choice), and the ident dual-role (each correct choice's
# ident reused as a penalty-branch respident) all come straight from the sample.
_REAL_SHAPE_MA_RESPROCESSING = """\
<resprocessing scoremodel="SumOfScores">
  <outcomes>
    <decvar varname="SCORE" vartype="Decimal" defaultval="0" minvalue="0" maxvalue="1.00000"/>
  </outcomes>
  <respcondition title="correct">
    <conditionvar>
      <and>
        <varequal respident="response" case="No">IDENT_0</varequal>
        <not>
          <varequal respident="response" case="No">IDENT_1</varequal>
        </not>
        <not>
          <varequal respident="response" case="No">IDENT_2</varequal>
        </not>
        <varequal respident="response" case="No">IDENT_3</varequal>
        <not>
          <varequal respident="response" case="No">IDENT_4</varequal>
        </not>
        <varequal respident="response" case="No">IDENT_5</varequal>
        <not>
          <varequal respident="response" case="No">IDENT_6</varequal>
        </not>
        <varequal respident="response" case="No">IDENT_7</varequal>
        <not>
          <varequal respident="response" case="No">IDENT_8</varequal>
        </not>
        <varequal respident="response" case="No">IDENT_9</varequal>
        <not>
          <varequal respident="response" case="No">IDENT_10</varequal>
        </not>
      </and>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">SCORE.max</setvar>
    <displayfeedback linkrefid="correct" feedbacktype="Response"/>
  </respcondition>
  <respcondition title="incorrect">
    <conditionvar>
      <other/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
    <displayfeedback linkrefid="incorrect" feedbacktype="Response"/>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_0" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_1" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_2" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_3" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_4" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_5" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_6" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_7" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_8" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_9" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
  <respcondition>
    <conditionvar>
      <varequal respident="IDENT_10" case="No"/>
    </conditionvar>
    <setvar variablename="SCORE" action="Set">0</setvar>
  </respcondition>
</resprocessing>
"""


#============================================
def test_save_package_omits_bb_package_sig(tmp_path):
	"""
	save_package must NOT include .bb-package-sig (server-computed, omission is correct).
	"""
	outfile = str(tmp_path / "out.zip")
	qti = QTIPackageInterface(
		package_name="test_bb_sig",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MC", (
		"What is 2+2?",
		["3", "4", "5"],
		"4",
	))
	result = qti.save_package("blackboard_export_zip", outfile)

	with zipfile.ZipFile(result, "r") as z:
		names = z.namelist()
	assert ".bb-package-sig" not in names


#============================================
def test_order_item_produces_warning_and_is_absent(tmp_path, capsys):
	"""
	An ORDER item causes a base_engine warning and does not appear in the pool dat.
	"""
	outfile = str(tmp_path / "out.zip")
	qti = QTIPackageInterface(
		package_name="test_bb_order",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MC", (
		"What color is the sky?",
		["blue", "red", "green"],
		"blue",
	))
	qti.add_item("ORDER", (
		"Rank these by size.",
		["small", "medium", "large"],
	))
	result = qti.save_package("blackboard_export_zip", outfile)

	# The base_engine warning should mention ORDER
	captured = capsys.readouterr()
	assert "ORDER" in captured.out

	# Pool dat should contain the MC item and no ORDER item.
	with zipfile.ZipFile(result, "r") as z:
		pool_text = z.read("res00002.dat").decode("utf-8")
	# The supported MC item's question text is present in the pool.
	assert "What color is the sky?" in pool_text
	# ORDER items are not serialized by this engine; no ORDER marker should appear.
	assert "ORDER" not in pool_text


#============================================
def test_match_right_match_block_is_sibling_of_response_block() -> None:
	"""
	RIGHT_MATCH_BLOCK must be a sibling of RESPONSE_BLOCK under the outer
	`flow class="Block"`, not nested inside RESPONSE_BLOCK.

	Blackboard Ultra renders an empty answer bank when RIGHT_MATCH_BLOCK is a
	child of RESPONSE_BLOCK instead of a sibling. This guard asserts parent-identity
	equality: both RESPONSE_BLOCK and RIGHT_MATCH_BLOCK share the same parent
	element (the outer flow), and that parent is itself `flow class="Block"`.

	The reader is intentionally lenient (accepts both placements), so this writer
	test is the only barrier against the nesting regression.
	"""
	# Build a minimal MATCH item through the normal item_types path.
	match_item = item_types.MATCH(
		question_text="Match each term to its definition.",
		prompts_list=["Prompt A", "Prompt B"],
		choices_list=["Choice A", "Choice B"],
	)
	# Exercise the full build_MATCH writer path to get the <item> element.
	item_el = MATCH.build_MATCH(match_item)

	# Locate RESPONSE_BLOCK and RIGHT_MATCH_BLOCK inside <presentation>.
	presentation = item_el.find("presentation")
	outer_flow = presentation.find("flow[@class='Block']")

	# Find the two key blocks directly under outer_flow.
	response_block = outer_flow.find("flow[@class='RESPONSE_BLOCK']")
	right_match_block = outer_flow.find("flow[@class='RIGHT_MATCH_BLOCK']")

	assert response_block is not None, "RESPONSE_BLOCK not found under outer flow"
	assert right_match_block is not None, "RIGHT_MATCH_BLOCK not found under outer flow"

	# Assert sibling placement by parent identity: both must share the same parent,
	# and that parent must be the outer flow (i.e. RIGHT_MATCH_BLOCK is NOT inside
	# RESPONSE_BLOCK).
	assert right_match_block.getparent() is outer_flow, (
		"RIGHT_MATCH_BLOCK parent must be the outer flow, not RESPONSE_BLOCK; "
		"nesting RIGHT_MATCH_BLOCK inside RESPONSE_BLOCK breaks Blackboard Ultra rendering"
	)
	assert response_block.getparent() is outer_flow, (
		"RESPONSE_BLOCK parent must be the outer flow (Block)"
	)
	# Confirm the shared parent is the outer `flow class="Block"`.
	assert right_match_block.getparent() is response_block.getparent(), (
		"RIGHT_MATCH_BLOCK and RESPONSE_BLOCK must share the same parent (outer Block flow)"
	)


#============================================
def _mask_idents(resprocessing: lxml.etree.Element) -> str:
	"""
	Serialize a resprocessing subtree with generated hex idents masked.

	Every 32-hex ident (as a varequal respident attribute or as varequal text) is
	replaced by a stable IDENT_<n> placeholder assigned in first-seen document
	order. Stable strings ("response", "SCORE.max", "correct", "incorrect") are
	left untouched. This preserves correct-vs-incorrect position, branch order,
	`<not>` placement, the respident relationships, and the penalty-branch count
	while erasing only the run-specific ident values.

	Args:
		resprocessing: The generated `<resprocessing>` element.

	Returns:
		A pretty-printed XML string with idents replaced by placeholders.
	"""
	mapping: dict[str, str] = {}
	# Assign placeholders in first-seen order so the generated and expected
	# subtrees agree as long as their node visitation order matches.
	def placeholder(ident: str) -> str:
		if ident not in mapping:
			mapping[ident] = f"IDENT_{len(mapping)}"
		return mapping[ident]
	for element in resprocessing.iter():
		if element.tag != "varequal":
			continue
		respident = element.get("respident")
		if respident is not None and _HEX_IDENT_RE.match(respident):
			element.set("respident", placeholder(respident))
		if element.text is not None and _HEX_IDENT_RE.match(element.text.strip()):
			element.text = placeholder(element.text.strip())
	return lxml.etree.tostring(resprocessing, pretty_print=True).decode()


#============================================
def test_ma_writer_resprocessing_matches_real_shape() -> None:
	"""
	The MA writer must emit the real Blackboard MA resprocessing structure.

	Builds an 11-choice MA with correct answers at positions 0, 3, 5, 7, 9 (the
	exact correct positions of the real FURAN sample), then masks the generated
	idents and compares the `<resprocessing>` subtree to the masked real-sample
	literal. This locks the `<and>`-of-all-choices correct branch (correct bare,
	incorrect under `<not>`, in choice order), the `setvar SCORE.max` pair, and the
	one-penalty-branch-per-choice structure against the real shape.
	"""
	# 11 distinct choices; correct at positions 0, 3, 5, 7, 9 to match the sample.
	choices_list = [f"choice text {index}" for index in range(11)]
	correct_positions = (0, 3, 5, 7, 9)
	answers_list = [choices_list[position] for position in correct_positions]
	ma_item = item_types.MA(
		question_text="Which categories apply to this molecule?",
		choices_list=choices_list,
		answers_list=answers_list,
	)
	item_el = MA.build_MA(ma_item)
	resprocessing = item_el.find("resprocessing")

	# Mask the generated idents, then compare to the masked real-sample literal.
	masked_generated = _mask_idents(resprocessing)
	expected_resprocessing = lxml.etree.fromstring(_REAL_SHAPE_MA_RESPROCESSING)
	expected_masked = lxml.etree.tostring(expected_resprocessing, pretty_print=True).decode()
	assert masked_generated == expected_masked, (
		"MA resprocessing does not match the real Blackboard MA shape "
		"(see FURAN sample provenance above)"
	)


#============================================
def test_ma_writer_penalty_branch_count_equals_choice_count() -> None:
	"""
	The MA writer must emit exactly one penalty branch per choice.

	The real samples carry one SCORE-0 penalty `<respcondition>` per choice (not
	per incorrect choice). This guards that count independently of the full-shape
	comparison, since a penalty branch holds an empty varequal keyed to a choice
	ident with no `<displayfeedback>`.
	"""
	choices_list = ["alpha", "beta", "gamma", "delta"]
	answers_list = ["alpha", "gamma"]
	ma_item = item_types.MA(
		question_text="Which letters are listed first and third?",
		choices_list=choices_list,
		answers_list=answers_list,
	)
	item_el = MA.build_MA(ma_item)
	resprocessing = item_el.find("resprocessing")

	# A penalty branch is an untitled respcondition with an empty-valued varequal
	# keyed to a choice ident and no displayfeedback child.
	penalty_branches = []
	for respcondition in resprocessing.findall("respcondition"):
		if respcondition.get("title") is not None:
			continue
		penalty_branches.append(respcondition)
	assert len(penalty_branches) == len(choices_list), (
		"MA must emit one penalty branch per choice "
		f"(got {len(penalty_branches)} for {len(choices_list)} choices)"
	)


#============================================
def test_mc_correct_branch_unchanged_after_ma_split() -> None:
	"""
	MC's correct branch must stay the single-bare-varequal shape after the MA split.

	The MA rewrite factored the shared `setvar SCORE.max` + `displayfeedback`
	tail into a helper but must not alter MC. MC's correct branch is one
	`<varequal respident="response">CORRECT_IDENT</varequal>` directly under
	`<conditionvar>` (no `<and>`, no `<not>`), followed by `setvar SCORE.max`.
	"""
	mc_item = item_types.MC(
		question_text="Which planet is closest to the Sun?",
		choices_list=["Mercury", "Venus", "Earth"],
		answer_text="Mercury",
	)
	item_el = MC.build_MC(mc_item)
	correct_branch = item_el.find("resprocessing/respcondition[@title='correct']")
	conditionvar = correct_branch.find("conditionvar")

	# No <and> or <not> wrapping: the varequal sits directly in conditionvar.
	assert conditionvar.find("and") is None, "MC correct branch must not use <and>"
	assert conditionvar.find(".//not") is None, "MC correct branch must not use <not>"
	varequals = conditionvar.findall("varequal")
	assert len(varequals) == 1, "MC correct branch must hold exactly one varequal"
	assert varequals[0].get("respident") == "response", (
		"MC correct varequal must test respident='response'"
	)
	assert varequals[0].text, "MC correct varequal must carry the correct label ident"
	# The shared tail: setvar SCORE.max.
	setvar = correct_branch.find("setvar")
	assert setvar is not None and setvar.text == "SCORE.max", (
		"MC correct branch must set SCORE to SCORE.max"
	)


#============================================
def test_ma_in_code_round_trip_recovers_answers(tmp_path) -> None:
	"""
	An MA built in code, written, and read back must recover the same answers_list.

	This focused MA round-trip confirms the new `<and>`/`<not>` correct branch is
	readable by the engine reader and yields the original answer set
	(order-insensitive, set-equal).
	"""
	question_text = "Which of these are prime numbers under ten?"
	choices_list = ["two", "three", "four", "five", "six", "seven"]
	answers_list = ["two", "three", "five", "seven"]
	qti = QTIPackageInterface(
		package_name="ma_round_trip",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("MA", (question_text, choices_list, answers_list))

	outfile = str(tmp_path / "ma_round_trip.zip")
	result_path = qti.save_package("blackboard_export_zip", outfile)

	bank_b = read_package.read_items_from_file(result_path, allow_mixed=True)
	read_items = [item for item in bank_b if item.question_text == question_text]
	assert len(read_items) == 1, "expected exactly one MA item after round-trip"
	assert set(read_items[0].answers_list) == set(answers_list), (
		"MA round-trip did not recover the original answers_list"
	)


#============================================
def test_fib_writer_correct_branch_has_dual_displayfeedback() -> None:
	"""
	build_FIB correct branches must match the real Blackboard FIB shape:
	no <setvar> on each per-answer respcondition; two <displayfeedback> children,
	the first linkrefid="correct", the second linkrefid equal to that branch's own
	hex title ident.

	Provenance: shape derived from real pool
	BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB/res00002.dat
	(single-answer items) and
	BB_Export_ZIP/Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB/res00002.dat
	(3-answer items).
	"""
	question_text = "The powerhouse of the cell is the ____."
	# Two accepted answers to exercise the multi-answer code path.
	answers_list = ["mitochondria", "mitochondrion"]
	fib_item = item_types.FIB(question_text, answers_list)

	item_el = FIB.build_FIB(fib_item)

	resprocessing = item_el.find("resprocessing")
	assert resprocessing is not None, "resprocessing element missing"

	# Collect per-answer respconditions (those whose title is not "incorrect").
	answer_conds = [
		rc for rc in resprocessing.findall("respcondition")
		if rc.get("title") and rc.get("title") != "incorrect"
	]
	assert len(answer_conds) == len(answers_list), (
		f"expected {len(answers_list)} per-answer respconditions, got {len(answer_conds)}"
	)

	for respcond in answer_conds:
		branch_title = respcond.get("title")
		assert branch_title is not None, "per-answer respcondition missing title"
		# Real BB FIB correct branches carry no <setvar>.
		setvar_el = respcond.find("setvar")
		assert setvar_el is None, (
			f"branch title={branch_title}: <setvar> must be absent on correct FIB branch"
		)
		# Exactly two <displayfeedback> children.
		df_els = respcond.findall("displayfeedback")
		assert len(df_els) == 2, (
			f"branch title={branch_title}: expected 2 displayfeedback, got {len(df_els)}"
		)
		# First: linkrefid="correct".
		assert df_els[0].get("linkrefid") == "correct", (
			f"branch title={branch_title}: first displayfeedback must link to 'correct'"
		)
		assert df_els[0].get("feedbacktype") == "Response", (
			f"branch title={branch_title}: first displayfeedback feedbacktype must be 'Response'"
		)
		# Second: linkrefid equals the branch's own title ident.
		assert df_els[1].get("linkrefid") == branch_title, (
			f"branch title={branch_title}: second displayfeedback linkrefid must equal branch title"
		)
		assert df_els[1].get("feedbacktype") == "Response", (
			f"branch title={branch_title}: second displayfeedback feedbacktype must be 'Response'"
		)


#============================================
def test_fib_writer_emits_per_answer_itemfeedback() -> None:
	"""
	build_FIB must emit one <itemfeedback ident="<hex>"> per accepted answer,
	in addition to the standard correct/incorrect pair.

	Each per-answer itemfeedback carries a <solution feedbackstyle="Complete">
	wrapper, matching the real Blackboard shape confirmed in:
	BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch03a_Peptide_Side_Chain_2aa_FIB/res00002.dat
	BB_Export_ZIP/Pool_ExportFile_GC.202610_Ch02.4_Overhang_Sequence_FiB/res00002.dat
	"""
	question_text = "Fill: the sun is a ____."
	answers_list = ["star", "Sol"]
	fib_item = item_types.FIB(question_text, answers_list)

	item_el = FIB.build_FIB(fib_item)

	# Collect all itemfeedback idents.
	all_feedbacks = item_el.findall("itemfeedback")
	fb_idents = [fb.get("ident") for fb in all_feedbacks]
	assert "correct" in fb_idents, "standard 'correct' itemfeedback missing"
	assert "incorrect" in fb_idents, "standard 'incorrect' itemfeedback missing"

	# Collect the per-answer respcondition title idents.
	resprocessing = item_el.find("resprocessing")
	answer_titles = [
		rc.get("title") for rc in resprocessing.findall("respcondition")
		if rc.get("title") and rc.get("title") != "incorrect"
	]
	# Every per-answer title must have a matching itemfeedback.
	for title in answer_titles:
		assert title in fb_idents, (
			f"per-answer itemfeedback ident={title!r} missing from item"
		)
		# The per-answer itemfeedback carries a <solution> wrapper.
		fb_el = item_el.find(f"itemfeedback[@ident='{title}']")
		solution_el = fb_el.find("solution")
		assert solution_el is not None, (
			f"per-answer itemfeedback ident={title!r}: <solution> element missing"
		)
		assert solution_el.get("feedbackstyle") == "Complete", (
			f"per-answer itemfeedback ident={title!r}: <solution feedbackstyle='Complete'> required"
		)


#============================================
def test_fib_in_code_round_trip_recovers_answers(tmp_path) -> None:
	"""
	A FIB built in code, written, and read back must recover the same answers_list.

	Confirms that dropping <setvar> from the correct branches does not break the
	reader: answer recovery depends only on the <varequal respident="response">
	match path, which is unchanged.
	"""
	question_text = "The powerhouse of the cell is the ____."
	answers_list = ["mitochondria", "mitochondrion"]
	qti = QTIPackageInterface(
		package_name="fib_round_trip",
		verbose=False,
		allow_mixed=True,
	)
	qti.add_item("FIB", (question_text, answers_list))

	outfile = str(tmp_path / "fib_round_trip.zip")
	result_path = qti.save_package("blackboard_export_zip", outfile)

	bank_b = read_package.read_items_from_file(result_path, allow_mixed=True)
	read_items = [item for item in bank_b if item.question_text == question_text]
	assert len(read_items) == 1, "expected exactly one FIB item after round-trip"
	assert set(read_items[0].answers_list) == set(answers_list), (
		"FIB round-trip did not recover the original answers_list"
	)


#============================================
def test_question_html_strips_whitespace_inside_table_structure() -> None:
	"""
	Whitespace text directly inside a table-structure element must be removed.

	A whitespace text node directly inside a <tr> (between the <tr> and its first
	cell, or between cells) crashes the Blackboard Ultra question-expand renderer
	for MC/MA/NUM items when the table carries a text-align style and the row does
	not end with whitespace. The minimal crash is
	`<table style="text-align:center"><tr> <td>x</td></tr></table>`. build_smart_text
	must drop whitespace-only text nodes directly inside
	<table>/<thead>/<tbody>/<tfoot>/<tr>.
	"""
	payload = "<table style='text-align: center;'><tr> <td>x</td> <td>y</td></tr></table>"
	mat = common_xml.build_smart_text(payload)
	# mat.text holds the un-escaped HTML carried into the package.
	root = lxml.html.fromstring(f"<div>{mat.text}</div>")
	for structure in root.iter("table", "thead", "tbody", "tfoot", "tr"):
		assert not (structure.text and structure.text.strip() == ""), (
			"whitespace text node directly inside a table-structure element survived"
		)
		for child in structure:
			assert not (child.tail and child.tail.strip() == ""), (
				"whitespace tail directly inside a table-structure element survived"
			)


#============================================
def test_question_html_preserves_table_cells_and_styles() -> None:
	"""
	The whitespace fix keeps the table, its cells, content, and inline styles.

	Only whitespace-only text nodes in table structure are removed; cell text,
	the <table> style attribute, and cell content survive. Whitespace inside a
	cell (<td> content) is also preserved.
	"""
	payload = "<table style='text-align: center;'><tr> <td>the answer</td></tr></table>"
	mat = common_xml.build_smart_text(payload)
	carried = mat.text
	assert "<table" in carried, "fix dropped the table"
	assert "text-align" in carried, "fix dropped the table style"
	# Cell content (including its internal space) survives.
	assert "the answer" in carried, "fix dropped or altered cell content"


#============================================
def test_question_html_passes_plain_text_through_unchanged() -> None:
	"""
	A bare-text payload (no element markup) is carried verbatim.

	Plain NUM/MC content with no tags has no table structure to sanitize, so it
	passes through unchanged.
	"""
	plain = "What is two plus two?"
	mat = common_xml.build_smart_text(plain)
	assert mat.text == plain


#============================================
def test_question_html_passes_non_table_markup_through_unchanged() -> None:
	"""
	Inline (non-table) markup is carried verbatim, not round-tripped through lxml.

	The sanitizer only touches table-containing payloads, so common inline markup
	(superscripts, bold, spans) must pass through byte-for-byte; the lxml HTML
	parse/re-serialize must never alter non-table content (e.g. <br/> vs <br>).
	"""
	markup = "K<sup>+</sup> and Cl<sup>-</sup> with a <b>bold</b> note<br/>line two"
	mat = common_xml.build_smart_text(markup)
	assert mat.text == markup
