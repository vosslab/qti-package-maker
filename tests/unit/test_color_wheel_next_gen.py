# Standard Library
from pathlib import Path
import re

# Pip3 Library
import pytest
import yaml

# QTI Package Maker
from qti_package_maker.common.color_theory import next_gen
from qti_package_maker.common.color_theory.cam16_utils import _srgb_hex_to_cam16_spec
from qti_package_maker.common.color_theory.generator import (
	_max_m_for_hue,
	_m_for_target_ucs_r,
	_redness_score,
)
from qti_package_maker.common.color_theory.hue_layout import _generate_hues_equal
from qti_package_maker.common.color_theory.red_scan import _select_hues_for_anchor
from qti_package_maker.common.color_theory.wheel_specs import (
	DEFAULT_WHEEL_SPECS,
	_build_wheel_spec,
	_validate_colorfulness_control,
)


def test_generate_color_wheel_returns_hex() -> None:
	first_mode = next_gen.DEFAULT_WHEEL_MODE_ORDER[0]
	colors = next_gen.generate_color_wheel(4, mode=first_mode)
	assert len(colors) == 4
	assert all(re.match(r"^[0-9a-f]{6}$", value) for value in colors)


def test_redness_score_prefers_red() -> None:
	assert _redness_score("ff0000") < _redness_score("0000ff")
	assert _redness_score("ff0000") < _redness_score("000000")


def test_write_html_color_table(tmp_path: Path) -> None:
	output = tmp_path / "next_gen_table.html"
	required = ["dark", "light", "xlight"]
	modes = [mode for mode in next_gen.DEFAULT_WHEEL_MODE_ORDER if mode in required]
	assert modes == required
	next_gen.write_html_color_table(str(output), num_colors=4, modes=modes)
	content = output.read_text()
	assert "Color Name" in content
	assert "White / Dark" in content


def test_write_red_scan_bundle_html(tmp_path: Path) -> None:
	output = tmp_path / "red_scan.html"
	modes = list(next_gen.DEFAULT_WHEEL_MODE_ORDER)
	next_gen._write_red_scan_bundle_html(str(output), num_colors=4, modes=modes[:2])
	content = output.read_text()
	assert f"<h1>{modes[0]}</h1>" in content
	assert "Step 0.2 (micro)" in content


def test_write_html_color_table_cam16_debug(tmp_path: Path) -> None:
	output = tmp_path / "cam16_debug.html"
	modes = list(next_gen.DEFAULT_WHEEL_MODE_ORDER)
	next_gen.write_html_color_table_cam16_debug(str(output), num_colors=4, modes=modes)
	content = output.read_text()
	assert "CAM16 Debug" in content
	for mode in modes:
		assert f"<h1>{mode}" in content
	assert "target J" in content
	assert "XKCD Name" in content
	assert "UCS_r" in content
	assert "target_ucs_r" in content
	assert "ucs_r_err" in content
	assert "control=" in content
	assert "clamp_reason" in content
	assert "gamut_margin" in content
	assert "M_max_hue" in content


def test_cam16_j_m_q_ranges() -> None:
	num_colors = 8
	for mode, spec in DEFAULT_WHEEL_SPECS.items():
		hues = _generate_hues_equal(num_colors, offset=0.0)
		colors = next_gen.generate_color_wheel(
			num_colors,
			mode=mode,
			hues=hues,
			rotate_to_anchor=False,
			apply_variation=False,
		)

		for hue, hex_value in zip(hues, colors):
			cam = _srgb_hex_to_cam16_spec(hex_value)
			assert abs(cam.J - spec.target_j) <= 5.0

			max_m = _max_m_for_hue(
				spec.target_j,
				hue,
				cache_key=(mode, round(spec.target_j, 2), round(hue, 1)),
			)
			min_expected = min(spec.m_min, max_m)
			assert cam.M >= (min_expected - 2.0)
			if spec.shared_m_quantile is not None:
				max_expected = min(spec.m_max, max_m)
				assert cam.M <= (max_expected + 2.0)

			assert cam.Q > 0.0
			assert cam.Q < 260.0


def test_target_ucs_r_increases_m() -> None:
	j = 75.0
	h = 0.0
	max_m = 20.0
	low = _m_for_target_ucs_r(j, h, 6.0, max_m=max_m, steps=8)
	high = _m_for_target_ucs_r(j, h, 12.0, max_m=max_m, steps=8)
	assert high >= low


def test_colorfulness_control_xor() -> None:
	for mode, spec in DEFAULT_WHEEL_SPECS.items():
		has_shared = spec.shared_m_quantile is not None
		has_ucs = spec.target_ucs_r is not None
		assert has_shared != has_ucs, mode


def test_shared_m_quantile_range_validation() -> None:
	bad_yaml = """
viewing:
  surround: Average
  white_point: D65
  adapting_luminance: 64.0
  background_luminance: 20.0
modes:
  dark:
    target_j: 40.0
    red_offset: 25.0
    shared_m_quantile: 1.10
    target_ucs_r: null
"""
	data = yaml.safe_load(bad_yaml)
	modes = data.get("modes") or {}
	see = modes.get("dark") or {}
	defaults = DEFAULT_WHEEL_SPECS["dark"]
	spec = _build_wheel_spec(see, defaults=defaults)
	with pytest.raises(ValueError):
		_validate_colorfulness_control("dark", spec)


def test_yaml_mode_order_matches_default() -> None:
	yaml_path = Path(next_gen.__file__).with_name("wheel_specs.yaml")
	data = yaml.safe_load(yaml_path.read_text()) or {}
	mode_order = list((data.get("modes") or {}).keys())
	assert mode_order == list(next_gen.DEFAULT_WHEEL_MODE_ORDER)


def test_yaml_offsets_used_for_anchor() -> None:
	yaml_path = Path(next_gen.__file__).with_name("wheel_specs.yaml")
	data = yaml.safe_load(yaml_path.read_text()) or {}
	modes = data.get("modes") or {}
	for mode, values in modes.items():
		offset = (values or {}).get("red_offset")
		if offset is None:
			continue
		hues = _select_hues_for_anchor(16, mode, None)
		assert abs(hues[0] - float(offset)) < 1e-6
