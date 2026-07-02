# Standard Library
# none

# QTI Package Maker
import qti_package_maker.common.string_functions

#============================
def test_strip_prefix_preserves_decimals_plain() -> None:
	decimal_cases = [
		"0.0089",
		"0.089",
		"1.9",
		"12.5",
		"7.5 mL stock solution",
		"3.14",
		"1.2 mM glucose",
	]
	for case in decimal_cases:
		assert qti_package_maker.common.string_functions.strip_prefix_from_string(case) == case

#============================
def test_strip_prefix_preserves_decimals_html() -> None:
	decimal_cases = [
		"<span>0.0089</span>",
		"<span>0.089</span>",
		"<span>1.9</span>",
		"<span>12.5</span>",
		"<p>7.5 mL stock solution</p>",
		"<span style=\"color:red\">3.14</span>",
	]
	for case in decimal_cases:
		assert qti_package_maker.common.string_functions.strip_prefix_from_string(case) == case

#============================
def test_strip_prefix_removes_list_prefixes() -> None:
	cases = {
		"A. Glucose": "Glucose",
		"b: Option B": "Option B",
		"2) Fructose": "Fructose",
		"1) Option 1": "Option 1",
		"A. 0.089": "0.089",
	}
	for raw, expected in cases.items():
		assert qti_package_maker.common.string_functions.strip_prefix_from_string(raw) == expected

#============================
def test_has_prefix_handles_decimals() -> None:
	assert qti_package_maker.common.string_functions.has_prefix(["A. One", "B. Two"]) is True
	assert qti_package_maker.common.string_functions.has_prefix(["1) One", "2) Two"]) is True
	assert qti_package_maker.common.string_functions.has_prefix(["0.0089", "0.089"]) is False
	assert qti_package_maker.common.string_functions.has_prefix(["1.9", "12.5"]) is False
	assert qti_package_maker.common.string_functions.has_prefix(["7.5 mL", "3.14"]) is False

#============================
def test_has_prefix_with_html_and_decimals() -> None:
	assert qti_package_maker.common.string_functions.has_prefix(["<p>A. One</p>", "<span>B. Two</span>"]) is True
	assert qti_package_maker.common.string_functions.has_prefix(["<span>0.089</span>", "<p>1.2</p>"]) is False
	assert qti_package_maker.common.string_functions.has_prefix(["<span>0.0089</span>", "<p>12.5</p>"]) is False
