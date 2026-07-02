"""CAM16 wheel generation and shared helpers."""

# Standard Library
import random

# QTI Package Maker
from qti_package_maker.common.color_theory import legacy_color_wheel
from qti_package_maker.common.color_theory.cam16_utils import cam16_jmh_to_xyz, cam16_ucs_radius_from_jmh, _linear_rgb_in_gamut, _xyz_to_srgb
from qti_package_maker.common.color_theory.color_utils import _hex_to_rgb, _rgb_distance, _srgb_to_hex
from qti_package_maker.common.color_theory.hue_layout import (
	_generate_hues_anchor,
	_generate_hues_offset,
	_generate_hues_optimized,
)
from qti_package_maker.common.color_theory.wheel_specs import DEFAULT_WHEEL_SPECS, WheelSpec

_MAX_M_CACHE = {}


def _resolve_anchor_hex(anchor_hex: str | None) -> str:
	if anchor_hex:
		if anchor_hex == "legacy":
			return legacy_color_wheel.dark_color_wheel["red"]
		return anchor_hex.lower()
	return "ff0000"


def _rotate_colors_to_target(colors: list, target_hex: str | None) -> list:
	if not colors:
		return colors
	target_hex = _resolve_anchor_hex(target_hex)
	if target_hex == "ff0000":
		red_index = min(range(len(colors)), key=lambda idx: _redness_score(colors[idx]))
	else:
		red_index = min(range(len(colors)), key=lambda idx: _rgb_distance(colors[idx], target_hex))
	if red_index == 0:
		return colors
	return colors[red_index:] + colors[:red_index]


def _print_legacy_red_comparison(dark_hex: str, light_hex: str, extra_light_hex: str, labels: tuple | None = None) -> None:
	legacy_dark = legacy_color_wheel.dark_color_wheel["red"]
	legacy_light = legacy_color_wheel.light_color_wheel["red"]
	legacy_extra_light = legacy_color_wheel.extra_light_color_wheel["red"]
	if labels is None:
		labels = ("dark", "light", "extra light")

	print("Legacy red RGB distance:")
	print(f"- {labels[0]}: {legacy_dark} -> {dark_hex} (diff {_rgb_distance(legacy_dark, dark_hex):.1f})")
	print(f"- {labels[1]}: {legacy_light} -> {light_hex} (diff {_rgb_distance(legacy_light, light_hex):.1f})")
	print(f"- {labels[2]}: {legacy_extra_light} -> {extra_light_hex} (diff {_rgb_distance(legacy_extra_light, extra_light_hex):.1f})")


def _redness_score(hex_value: str) -> tuple:
	r, g, b = _hex_to_rgb(hex_value)
	gb = g + b
	gb_safe = max(gb, 1.0)
	r_safe = max(r, 1.0)
	gb_balance = abs(g - b) / gb_safe
	gb_over_2r = gb / (2.0 * r_safe)
	penalty = 10.0 if r == 0 else 0.0
	return (gb_balance + gb_over_2r + penalty, gb_balance, gb_over_2r, -r)


def _quantile(values: list, q: float) -> float:
	if not values:
		return 0.0
	sorted_vals = sorted(values)
	index = max(0, min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1)))))
	return sorted_vals[index]


def _max_m_for_hue(j: float, h: float, steps: int = 12, m_hi: float = 100.0, cache_key: tuple | None = None) -> float:
	if cache_key in _MAX_M_CACHE:
		return _MAX_M_CACHE[cache_key]

	lo = 0.0
	hi = m_hi
	for _ in range(steps):
		mid = (lo + hi) / 2.0
		XYZ = cam16_jmh_to_xyz(j, mid, h)
		rgb = _xyz_to_srgb(XYZ, apply_encoding=False)
		if _linear_rgb_in_gamut(rgb):
			lo = mid
		else:
			hi = mid

	result = lo
	if cache_key is not None:
		_MAX_M_CACHE[cache_key] = result
	return result


def _m_for_target_ucs_r(j: float, h: float, target_ucs_r: float, max_m: float, steps: int = 12) -> float:
	lo = 0.0
	hi = max_m
	for _ in range(steps):
		mid = (lo + hi) / 2.0
		radius = cam16_ucs_radius_from_jmh(j, mid, h)
		if radius < target_ucs_r:
			lo = mid
		else:
			hi = mid
	return hi


def _shared_m_and_max_ms(hues: list, spec: WheelSpec, mode: str) -> tuple:
	max_ms = []
	for hue in hues:
		cache_key = (mode, round(spec.target_j, 2), round(hue, 1))
		max_ms.append(_max_m_for_hue(spec.target_j, hue, cache_key=cache_key))

	if spec.shared_m_quantile is None:
		shared_m = None
	else:
		shared_m = _quantile(max_ms, spec.shared_m_quantile)
		shared_m = max(spec.m_min, min(spec.m_max, shared_m))
	return shared_m, max_ms


def _colors_for_hues(hues: list, spec: WheelSpec, mode: str, apply_variation: bool = True) -> list:
	shared_m, max_ms = _shared_m_and_max_ms(hues, spec, mode)

	colors = []
	for hue, max_m in zip(hues, max_ms):
		if spec.target_ucs_r is None:
			m_cap = min(max_m, spec.m_max)
			if shared_m is None:
				raise ValueError(f"Mode '{mode}' must define shared_m_quantile or target_ucs_r")
			m = shared_m
			if spec.max_m_blend > 0:
				m = shared_m + (max_m - shared_m) * spec.max_m_blend
			if apply_variation and spec.allow_m_variation > 0:
				variation = (random.random() * 2.0 - 1.0) * spec.allow_m_variation * shared_m
				m = m + variation

			m = max(spec.m_min, min(spec.m_max, m))
			m = min(m, m_cap)
		else:
			m_cap = max_m
			m = _m_for_target_ucs_r(spec.target_j, hue, spec.target_ucs_r, m_cap)
			if apply_variation and spec.allow_m_variation > 0:
				variation = (random.random() * 2.0 - 1.0) * spec.allow_m_variation * m
				m = m + variation
			m = max(spec.m_min, min(m_cap, m))

		XYZ = cam16_jmh_to_xyz(spec.target_j, m, hue)
		rgb = _xyz_to_srgb(XYZ, apply_encoding=True)
		colors.append(_srgb_to_hex(rgb))

	return colors


def _color_for_hue(hue: float, spec: WheelSpec, mode: str, m_override: float | None = None) -> str:
	cache_key = (mode, round(spec.target_j, 2), round(hue, 1))
	max_m = _max_m_for_hue(spec.target_j, hue, cache_key=cache_key)
	if m_override is None:
		m = min(spec.m_max, max_m)
	else:
		m = min(m_override, max_m)

	m = max(spec.m_min, min(spec.m_max, m))
	XYZ = cam16_jmh_to_xyz(spec.target_j, m, hue)
	rgb = _xyz_to_srgb(XYZ, apply_encoding=True)
	return _srgb_to_hex(rgb)


def generate_color_wheel(
	num_colors: int,
	mode: str | None = None,
	hue_layout: str = "offset",
	anchor_hue: float = 0.0,
	samples: int = 24,
	wheel_specs: dict | None = None,
	anchor_hex: str | None = None,
	hues: list | None = None,
	apply_variation: bool = True,
	rotate_to_anchor: bool = True,
) -> list:
	if num_colors <= 0:
		raise ValueError("num_colors must be positive")

	specs = wheel_specs or DEFAULT_WHEEL_SPECS
	if mode is None:
		mode = list(specs.keys())[0]
	spec = specs.get(mode)
	if spec is None:
		raise ValueError(f"Unknown mode: {mode}")

	if hues is None:
		if hue_layout == "anchor":
			hues = _generate_hues_anchor(num_colors, anchor_hue)
		elif hue_layout == "optimize":
			def _score(hues_list: list) -> float:
				values = [
					_max_m_for_hue(spec.target_j, hue, cache_key=(mode, round(spec.target_j, 2), round(hue, 1)))
					for hue in hues_list
				]
				return _quantile(values, spec.shared_m_quantile)
			hues = _generate_hues_optimized(num_colors, _score, samples=samples)
		else:
			hues = _generate_hues_offset(num_colors)

	colors = _colors_for_hues(hues, spec, mode, apply_variation=apply_variation)

	if rotate_to_anchor:
		return _rotate_colors_to_target(colors, anchor_hex)
	return colors
