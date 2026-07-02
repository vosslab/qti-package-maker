"""CAM16 conversion helpers backed by colour-science."""

# Standard Library
import math
import sys
import types

# QTI Package Maker
from qti_package_maker.common.color_theory.wheel_specs import DEFAULT_VIEWING

# Third Party
import six
import numpy

if "six.moves" not in sys.modules:
	sys.modules["six.moves"] = six.moves

if "colour.plotting" not in sys.modules:
	sys.modules["colour.plotting"] = types.ModuleType("colour.plotting")

# Third Party
import colour

_VIEWING_CACHE = None


def _get_viewing_conditions() -> tuple:
	global _VIEWING_CACHE
	if _VIEWING_CACHE is not None:
		return _VIEWING_CACHE

	xy_w = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"][DEFAULT_VIEWING["white_point"]]
	XYZ_w = colour.xy_to_XYZ(xy_w) * 100.0
	surround = colour.VIEWING_CONDITIONS_CAM16[DEFAULT_VIEWING["surround"]]
	_VIEWING_CACHE = (XYZ_w, DEFAULT_VIEWING["adapting_luminance"], DEFAULT_VIEWING["background_luminance"], surround, xy_w)
	return _VIEWING_CACHE


def cam16_jmh_to_xyz(
	j: float, m: float, h: float, viewing_conditions: dict | None = None
) -> numpy.ndarray:
	XYZ_w, L_A, Y_b, surround, _xy_w = _get_viewing_conditions()
	if viewing_conditions:
		XYZ_w = viewing_conditions.get("XYZ_w", XYZ_w)
		L_A = viewing_conditions.get("L_A", L_A)
		Y_b = viewing_conditions.get("Y_b", Y_b)
		surround = viewing_conditions.get("surround", surround)

	spec = colour.CAM_Specification_CAM16(J=j, M=m, h=h)
	return colour.CAM16_to_XYZ(spec, XYZ_w, L_A, Y_b, surround)


def _xyz_to_srgb(XYZ: numpy.ndarray, apply_encoding: bool = True) -> numpy.ndarray:
	_xyz = [value / 100.0 for value in XYZ]
	_xyz_w, _L_A, _Y_b, _surround, xy_w = _get_viewing_conditions()
	try:
		return colour.XYZ_to_sRGB(
			_xyz,
			illuminant=xy_w,
			chromatic_adaptation_transform=None,
			apply_cctf_encoding=apply_encoding,
		)
	except TypeError:
		return colour.XYZ_to_sRGB(
			_xyz,
			illuminant=xy_w,
			chromatic_adaptation_transform=None,
			apply_encoding_cctf=apply_encoding,
		)


def _linear_rgb_in_gamut(rgb: numpy.ndarray, epsilon: float = 1e-7) -> bool:
	return all(-epsilon <= channel <= 1.0 + epsilon for channel in rgb)


def _srgb_hex_to_cam16_spec(hex_value: str) -> colour.CAM_Specification_CAM16:
	r = int(hex_value[0:2], 16)
	g = int(hex_value[2:4], 16)
	b = int(hex_value[4:6], 16)
	rgb = [r / 255.0, g / 255.0, b / 255.0]
	rgb_colourspace = colour.RGB_COLOURSPACES["sRGB"]
	XYZ = colour.RGB_to_XYZ(rgb, rgb_colourspace, apply_cctf_decoding=True) * 100.0
	XYZ_w, L_A, Y_b, surround, _xy_w = _get_viewing_conditions()
	return colour.XYZ_to_CAM16(XYZ, XYZ_w, L_A, Y_b, surround)


def _cam16_ucs_radius(cam: colour.CAM_Specification_CAM16) -> float:
	jab = colour.JMh_CAM16_to_CAM16UCS((cam.J, cam.M, cam.h))
	_jp, ap, bp = jab
	return float(math.hypot(ap, bp))


def cam16_ucs_radius_from_jmh(j: float, m: float, h: float) -> float:
	jab = colour.JMh_CAM16_to_CAM16UCS((j, m, h))
	_jp, ap, bp = jab
	return float(math.hypot(ap, bp))


def _gamut_margin(rgb_linear: numpy.ndarray) -> float:
	r, g, b = rgb_linear
	return min(r, g, b, 1.0 - r, 1.0 - g, 1.0 - b)
