"""
Behavioral read tests for the blackboard_export_zip read path.

Self-contained: every test builds its own minimal pool in tmp_path via a shared
helper, so no external sample data is committed or referenced at runtime.

Tests in this file:

- test_unknown_question_type_is_skipped_with_warning: unknown bbmd_questiontype
  is skipped, warning printed (unchanged from before WP-1).
- test_ma_reader_real_shape_multi_correct: reader recovers the correct
  answers_list from a real-shape MA item with 11 choices and 5 correct.
  Inline XML derived from BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Haworth_FURAN_MA/res00002.dat
  item #1 with generated hex idents replaced by stable named placeholders.
- test_ma_reader_real_shape_few_correct: reader recovers the correct
  answers_list from a real-shape MA item with 9 choices and 3 correct.
  Inline XML derived from BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Fischer_MA/res00002.dat
  item #1 with generated hex idents replaced by stable named placeholders.
- test_ma_reader_legacy_shape: reader still recovers answers from the old
  engine-emitted MA shape (bare varequals in conditionvar, no <and>/<not>),
  keeping backward-read compatibility explicit and tested.
"""

# Standard Library
import pathlib

# PIP3 modules
import lxml.etree

# QTI Package Maker
from qti_package_maker.engines.blackboard_export_zip import assessment_meta
from qti_package_maker.engines.blackboard_export_zip import read_package

#============================================
# Real-shape MA inline XML constants
# (provenance: derived from real pool .dat files with hex idents replaced by
# stable named placeholders; structure is never hand-authored from memory)
#============================================

# Derived from: BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Haworth_FURAN_MA/res00002.dat item #1
# 11 choices (A-K), 5 correct (A pentose, D D-config, F aldose, H furanose, J alpha-anomer).
# Verified: real resprocessing uses <and> with bare <varequal> for correct choices and
# <not><varequal/></not> for incorrect choices. Idents replaced: IDENT_A through IDENT_K.
REAL_SHAPE_MA_11CH_5CORRECT_XML = """\
<item maxattempts="0">
  <itemmetadata>
    <bbmd_questiontype>Multiple Answer</bbmd_questiontype>
  </itemmetadata>
  <presentation>
    <flow class="Block">
      <flow class="QUESTION_BLOCK">
        <flow class="FORMATTED_TEXT_BLOCK">
          <material>
            <mat_extension>
              <mat_formattedtext type="SMART_TEXT">Which categories apply to a furanose?</mat_formattedtext>
            </mat_extension>
          </material>
        </flow>
      </flow>
      <flow class="RESPONSE_BLOCK">
        <response_lid ident="response" rcardinality="Multiple" rtiming="No">
          <render_choice shuffle="No" minnumber="0" maxnumber="0">
            <flow_label class="Block">
              <response_label ident="IDENT_A" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">pentose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_B" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">hexose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_C" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">septose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_D" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">D-configuration</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_E" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">L-configuration</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_F" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">aldose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_G" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">ketose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_H" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">furanose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_I" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">pyranose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_J" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">alpha-anomer</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_K" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">beta-anomer</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
          </render_choice>
        </response_lid>
      </flow>
    </flow>
  </presentation>
  <resprocessing scoremodel="SumOfScores">
    <outcomes>
      <decvar varname="SCORE" vartype="Decimal" defaultval="0" minvalue="0" maxvalue="1.00000"/>
    </outcomes>
    <respcondition title="correct">
      <conditionvar>
        <and>
          <varequal respident="response" case="No">IDENT_A</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_B</varequal>
          </not>
          <not>
            <varequal respident="response" case="No">IDENT_C</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_D</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_E</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_F</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_G</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_H</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_I</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_J</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_K</varequal>
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
        <varequal respident="IDENT_A" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_B" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_C" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_D" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_E" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_F" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_G" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_H" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_I" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_J" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_K" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
  </resprocessing>
</item>"""

# Derived from: BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Fischer_MA/res00002.dat item #1
# 9 choices (A-I), 3 correct (B tetrose, E D-config, G aldose).
# Verified: real resprocessing uses <and> with bare <varequal> for correct choices and
# <not><varequal/></not> for incorrect choices. Idents replaced: IDENT_A through IDENT_I.
REAL_SHAPE_MA_9CH_3CORRECT_XML = """\
<item maxattempts="0">
  <itemmetadata>
    <bbmd_questiontype>Multiple Answer</bbmd_questiontype>
  </itemmetadata>
  <presentation>
    <flow class="Block">
      <flow class="QUESTION_BLOCK">
        <flow class="FORMATTED_TEXT_BLOCK">
          <material>
            <mat_extension>
              <mat_formattedtext type="SMART_TEXT">Classify this Fischer projection monosaccharide.</mat_formattedtext>
            </mat_extension>
          </material>
        </flow>
      </flow>
      <flow class="RESPONSE_BLOCK">
        <response_lid ident="response" rcardinality="Multiple" rtiming="No">
          <render_choice shuffle="No" minnumber="0" maxnumber="0">
            <flow_label class="Block">
              <response_label ident="IDENT_A" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">triose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_B" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">tetrose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_C" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">pentose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_D" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">hexose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_E" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">D-configuration</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_F" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">L-configuration</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_G" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">aldose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_H" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">ketose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_I" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">3-ketose</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
          </render_choice>
        </response_lid>
      </flow>
    </flow>
  </presentation>
  <resprocessing scoremodel="SumOfScores">
    <outcomes>
      <decvar varname="SCORE" vartype="Decimal" defaultval="0" minvalue="0" maxvalue="1.00000"/>
    </outcomes>
    <respcondition title="correct">
      <conditionvar>
        <and>
          <not>
            <varequal respident="response" case="No">IDENT_A</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_B</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_C</varequal>
          </not>
          <not>
            <varequal respident="response" case="No">IDENT_D</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_E</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_F</varequal>
          </not>
          <varequal respident="response" case="No">IDENT_G</varequal>
          <not>
            <varequal respident="response" case="No">IDENT_H</varequal>
          </not>
          <not>
            <varequal respident="response" case="No">IDENT_I</varequal>
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
        <varequal respident="IDENT_A" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_B" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_C" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_D" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_E" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_F" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_G" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_H" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
    <respcondition>
      <conditionvar>
        <varequal respident="IDENT_I" case="No"/>
      </conditionvar>
      <setvar variablename="SCORE" action="Set">0</setvar>
    </respcondition>
  </resprocessing>
</item>"""

# Old engine-emitted MA shape: bare <varequal respident="response"> directly in
# <conditionvar> without any <and>/<not> wrapper. This was the engine's original
# incorrect output; the reader must still recover answers from it for packages
# written before the WP-2 MA writer fix.
OLD_ENGINE_MA_XML = """\
<item maxattempts="0">
  <itemmetadata>
    <bbmd_questiontype>Multiple Answer</bbmd_questiontype>
  </itemmetadata>
  <presentation>
    <flow class="Block">
      <flow class="QUESTION_BLOCK">
        <flow class="FORMATTED_TEXT_BLOCK">
          <material>
            <mat_extension>
              <mat_formattedtext type="SMART_TEXT">Which are noble gases?</mat_formattedtext>
            </mat_extension>
          </material>
        </flow>
      </flow>
      <flow class="RESPONSE_BLOCK">
        <response_lid ident="response" rcardinality="Multiple" rtiming="No">
          <render_choice shuffle="No" minnumber="0" maxnumber="0">
            <flow_label class="Block">
              <response_label ident="IDENT_1" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">Helium</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_2" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">Neon</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_3" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">Oxygen</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
            <flow_label class="Block">
              <response_label ident="IDENT_4" shuffle="Yes" rarea="Ellipse" rrange="Exact">
                <flow_mat class="FORMATTED_TEXT_BLOCK">
                  <material>
                    <mat_extension>
                      <mat_formattedtext type="SMART_TEXT">Argon</mat_formattedtext>
                    </mat_extension>
                  </material>
                </flow_mat>
              </response_label>
            </flow_label>
          </render_choice>
        </response_lid>
      </flow>
    </flow>
  </presentation>
  <resprocessing scoremodel="SumOfScores">
    <outcomes>
      <decvar varname="SCORE" vartype="Decimal" defaultval="0" minvalue="0" maxvalue="1.00000"/>
    </outcomes>
    <respcondition title="correct">
      <conditionvar>
        <varequal respident="response" case="No">IDENT_1</varequal>
        <varequal respident="response" case="No">IDENT_2</varequal>
        <varequal respident="response" case="No">IDENT_4</varequal>
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
  </resprocessing>
</item>"""

#============================================
# Temp pool package builder
#============================================
#============================================
def _write_ma_pool_package(tmp_path: pathlib.Path, item_xml_str: str) -> pathlib.Path:
	"""
	Write a minimal Blackboard pool package directory containing one MA item.

	Builds the package using engine helpers so filenames and manifest structure
	exactly match what read_items_from_file expects. The pool .dat filename comes
	from assessment_meta.POOL_DAT_FILENAME; the manifest filename comes from
	read_package.MANIFEST_FILENAME.

	Args:
		tmp_path: The pytest tmp_path fixture base; the pool lands in tmp_path/pool/.
		item_xml_str: A well-formed XML string for one <item> element.

	Returns:
		The pool directory path (suitable for read_items_from_file).
	"""
	pool_dir = tmp_path / "pool"
	pool_dir.mkdir()

	# Parse the inline item XML and wrap it in the real pool envelope.
	item_el = lxml.etree.fromstring(item_xml_str.encode())
	pool_root = assessment_meta.build_pool_wrapper(
		item_elements=[item_el],
		pool_title="test_pool",
		question_type="Multiple Answer",
		total_score=1.0,
	)
	pool_bytes = assessment_meta.serialize_xml(pool_root)
	# Pool .dat filename sourced from the engine constant, not a hardcoded literal.
	(pool_dir / assessment_meta.POOL_DAT_FILENAME).write_bytes(pool_bytes)

	# Build the manifest and write it under the manifest filename constant.
	manifest_el = assessment_meta.build_manifest(pool_title="test_pool")
	manifest_bytes = assessment_meta.serialize_xml(manifest_el)
	(pool_dir / read_package.MANIFEST_FILENAME).write_bytes(manifest_bytes)

	return pool_dir

#============================================
# Tests
#============================================
#============================================
def test_unknown_question_type_is_skipped_with_warning(tmp_path: pathlib.Path, capsys) -> None:
	# An unknown bbmd_questiontype must be skipped with a warning naming the type
	# and source item, leaving the rest of the pool parseable.
	pool_dir = tmp_path / "pool"
	pool_dir.mkdir()
	_write_minimal_pool_with_unknown_type(pool_dir)
	bank = read_package.read_items_from_file(str(pool_dir), allow_mixed=True)
	# The unknown item is dropped; the bank parses without error.
	assert len(bank) == 0
	captured = capsys.readouterr()
	# The warning names the unknown type and identifies the source item.
	assert "Reticulating Splines" in captured.out
	assert "res00002.dat" in captured.out

#============================================
def test_ma_reader_real_shape_multi_correct(tmp_path: pathlib.Path) -> None:
	# Real-shape MA (11 choices, 5 correct) from FURAN MA pool: the reader must
	# recover only the 5 correct choices and not include the 6 negated ones.
	# Primary gate: recovered MA.answers_list text equals the expected correct choices.
	# Source: BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Haworth_FURAN_MA/res00002.dat item #1
	pool_dir = _write_ma_pool_package(tmp_path, REAL_SHAPE_MA_11CH_5CORRECT_XML)
	bank = read_package.read_items_from_file(str(pool_dir), allow_mixed=True)
	assert len(bank) == 1
	item = list(bank)[0]
	# The correct answers are A (pentose), D (D-config), F (aldose), H (furanose), J (alpha-anomer).
	# The reader must not include B, C, E, G, I, K (the <not>-wrapped incorrect choices).
	expected_answers = ["pentose", "D-configuration", "aldose", "furanose", "alpha-anomer"]
	assert item.answers_list == expected_answers

#============================================
def test_ma_reader_real_shape_few_correct(tmp_path: pathlib.Path) -> None:
	# Real-shape MA (9 choices, 3 correct) from Fischer MA pool: the reader must
	# recover exactly 3 correct answers from the <and>-structured respcondition.
	# Source: BB_Export_ZIP/Pool_ExportFile_E4.202620_Ch10_Classify_Fischer_MA/res00002.dat item #1
	pool_dir = _write_ma_pool_package(tmp_path, REAL_SHAPE_MA_9CH_3CORRECT_XML)
	bank = read_package.read_items_from_file(str(pool_dir), allow_mixed=True)
	assert len(bank) == 1
	item = list(bank)[0]
	# Correct: B (tetrose), E (D-config), G (aldose). Incorrect: A, C, D, F, H, I.
	expected_answers = ["tetrose", "D-configuration", "aldose"]
	assert item.answers_list == expected_answers

#============================================
def test_ma_reader_legacy_shape(tmp_path: pathlib.Path) -> None:
	# Old engine-emitted MA shape (bare varequals in conditionvar, no <and>/<not>):
	# the reader must still recover answers from previously-generated packages.
	# This keeps legacy backward-read tolerance explicit and tested.
	pool_dir = _write_ma_pool_package(tmp_path, OLD_ENGINE_MA_XML)
	bank = read_package.read_items_from_file(str(pool_dir), allow_mixed=True)
	assert len(bank) == 1
	item = list(bank)[0]
	# The legacy correct branch has bare varequals for Helium (IDENT_1), Neon (IDENT_2),
	# Argon (IDENT_4); Oxygen (IDENT_3) is not in the correct branch.
	expected_answers = ["Helium", "Neon", "Argon"]
	assert item.answers_list == expected_answers

#============================================
def _write_minimal_pool_with_unknown_type(pool_dir: pathlib.Path) -> None:
	"""
	Write a minimal pool directory whose single item has an unknown type.

	Args:
		pool_dir: A pathlib directory to populate with a manifest and pool dat.
	"""
	bb_ns = "http://www.blackboard.com/content-packaging/"
	# Minimal manifest declaring one assessment/x-bb-qti-pool resource.
	manifest = lxml.etree.Element(
		"manifest", nsmap={"bb": bb_ns}, attrib={"identifier": "man00001"}
	)
	resources = lxml.etree.SubElement(manifest, "resources")
	resource = lxml.etree.SubElement(resources, "resource")
	resource.set(f"{{{bb_ns}}}file", "res00002.dat")
	resource.set("identifier", "res00002")
	resource.set("type", "assessment/x-bb-qti-pool")
	manifest_bytes = lxml.etree.tostring(manifest, xml_declaration=True, encoding="UTF-8")
	(pool_dir / "imsmanifest.xml").write_bytes(manifest_bytes)

	# Minimal pool dat with one item carrying an unknown question type.
	questestinterop = lxml.etree.Element("questestinterop")
	assessment = lxml.etree.SubElement(questestinterop, "assessment")
	section = lxml.etree.SubElement(assessment, "section")
	item = lxml.etree.SubElement(section, "item")
	itemmetadata = lxml.etree.SubElement(item, "itemmetadata")
	qtype = lxml.etree.SubElement(itemmetadata, "bbmd_questiontype")
	qtype.text = "Reticulating Splines"
	pool_bytes = lxml.etree.tostring(questestinterop, xml_declaration=True, encoding="UTF-8")
	(pool_dir / "res00002.dat").write_bytes(pool_bytes)
