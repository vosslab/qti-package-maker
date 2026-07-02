"""Wheel mode specifications and viewing defaults."""

# Standard Library
from dataclasses import MISSING, dataclass, fields
from pathlib import Path

import yaml


@dataclass(frozen=True)
class WheelSpec:
	"""Policy settings for a specific wheel mode."""
	target_j: float
	m_min: float
	m_max: float
	shared_m_quantile: float | None
	allow_m_variation: float
	max_m_blend: float = 0.0
	brightness_q_cap: float | None = None
	target_ucs_r: float | None = None


_DEFAULT_WHEEL_SPECS = {
	"very_dark": WheelSpec(target_j=25.0, m_min=20.0, m_max=90.0, shared_m_quantile=0.45, allow_m_variation=0.18, max_m_blend=0.45),
	"xdark": WheelSpec(target_j=25.0, m_min=22.0, m_max=95.0, shared_m_quantile=0.50, allow_m_variation=0.18, max_m_blend=0.50),
	"dark": WheelSpec(target_j=40.0, m_min=18.0, m_max=85.0, shared_m_quantile=0.40, allow_m_variation=0.15, max_m_blend=0.40),
	"normal": WheelSpec(target_j=55.0, m_min=8.0, m_max=45.0, shared_m_quantile=0.25, allow_m_variation=0.08, max_m_blend=0.25),
	"light": WheelSpec(target_j=75.0, m_min=1.5, m_max=10.0, shared_m_quantile=None, allow_m_variation=0.03, max_m_blend=0.15, target_ucs_r=14.0),
	"xlight": WheelSpec(target_j=90.0, m_min=1.0, m_max=8.0, shared_m_quantile=None, allow_m_variation=0.02, max_m_blend=0.10, target_ucs_r=12.0),
}

_DEFAULT_VIEWING = {
	"surround": "Average",
	"white_point": "D65",
	"adapting_luminance": 64.0,
	"background_luminance": 20.0,
}

_DEFAULT_RED_OFFSETS = {
	"xdark": 27.2,
	"dark": 25.0,
	"normal": 19.2,
	"light": 20.6,
	"xlight": 17.0,
}


def _build_wheel_spec(values: dict | None, defaults: WheelSpec | None = None) -> WheelSpec:
	base = defaults.__dict__ if defaults is not None else {}
	merged = {**base, **(values or {})}
	kwargs = {}
	for field in fields(WheelSpec):
		if field.name in merged:
			kwargs[field.name] = merged[field.name]
		elif field.default is not MISSING:
			kwargs[field.name] = field.default
		elif field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
			kwargs[field.name] = field.default_factory()  # type: ignore[misc]
		else:
			raise ValueError(f"Missing required wheel spec field: {field.name}")
	return WheelSpec(**kwargs)


def _validate_colorfulness_control(mode: str, spec: WheelSpec) -> None:
	has_shared = spec.shared_m_quantile is not None
	has_ucs = spec.target_ucs_r is not None
	if has_shared == has_ucs:
		raise ValueError(
			"Mode '{mode}' must set exactly one of shared_m_quantile or target_ucs_r; "
			"got shared_m_quantile={shared}, target_ucs_r={ucs}".format(
				mode=mode,
				shared=spec.shared_m_quantile,
				ucs=spec.target_ucs_r,
			)
		)
	if has_shared:
		if not (0.0 <= float(spec.shared_m_quantile) <= 1.0):
			raise ValueError(
				"Mode '{mode}' shared_m_quantile must be between 0.0 and 1.0; got {value}".format(
					mode=mode,
					value=spec.shared_m_quantile,
				)
			)


def _load_wheel_specs_from_yaml() -> tuple:
	yaml_path = Path(__file__).with_name("wheel_specs.yaml")
	if not yaml_path.exists():
		return _DEFAULT_WHEEL_SPECS, _DEFAULT_VIEWING, _DEFAULT_RED_OFFSETS

	with yaml_path.open("r") as handle:
		data = yaml.safe_load(handle) or {}

	viewing = dict(_DEFAULT_VIEWING)
	viewing.update(data.get("viewing", {}) or {})

	specs = {}
	raw_modes = data.get("modes", {}) or data.get("wheel_specs", {}) or {}
	if not raw_modes:
		specs = dict(_DEFAULT_WHEEL_SPECS)
		mode_order = list(_DEFAULT_WHEEL_SPECS.keys())
	else:
		mode_order = list(raw_modes.keys())
		for mode, see in raw_modes.items():
			defaults = _DEFAULT_WHEEL_SPECS.get(mode) or _DEFAULT_WHEEL_SPECS.get("normal")
			specs[mode] = _build_wheel_spec(see, defaults=defaults)

	for mode, spec in specs.items():
		_validate_colorfulness_control(mode, spec)

	red_offsets = dict(_DEFAULT_RED_OFFSETS)
	if raw_modes:
		red_offsets = {}
		for mode, see in raw_modes.items():
			if see is None:
				continue
			value = see.get("red_offset")
			if value is None:
				continue
			red_offsets[mode] = float(value)

	return specs, viewing, red_offsets, mode_order


DEFAULT_WHEEL_SPECS, DEFAULT_VIEWING, DEFAULT_RED_OFFSETS, DEFAULT_WHEEL_MODE_ORDER = _load_wheel_specs_from_yaml()
