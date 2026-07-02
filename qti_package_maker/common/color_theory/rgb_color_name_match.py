"""Closest xkcd color name helpers using seaborn."""

# Standard Library
import sys

# Third Party
import six

if "six.moves" not in sys.modules:
	sys.modules["six.moves"] = six.moves

import seaborn as sns

_XKCD_RGB_TABLE = None


def _normalize_hex(hex_color: str) -> str:
	if not hex_color:
		raise ValueError("hex_color must be a non-empty string")
	if not hex_color.startswith("#"):
		hex_color = f"#{hex_color}"
	hex_color = hex_color.lower()
	if len(hex_color) == 4:
		hex_color = "#" + "".join([c * 2 for c in hex_color[1:]])
	if len(hex_color) != 7:
		raise ValueError(f"Invalid hex color: {hex_color}")
	return hex_color


def _load_xkcd_rgb_table() -> list:
	global _XKCD_RGB_TABLE
	if _XKCD_RGB_TABLE is None:
		table = []
		for name, hex_value in sns.xkcd_rgb.items():
			normalized = _normalize_hex(hex_value)
			rgb = (
				int(normalized[1:3], 16),
				int(normalized[3:5], 16),
				int(normalized[5:7], 16),
			)
			table.append((name, rgb))
		_XKCD_RGB_TABLE = table
	return _XKCD_RGB_TABLE


def _rgb_distance_squared(rgb_a: tuple, rgb_b: tuple) -> int:
	return (
		(rgb_a[0] - rgb_b[0]) ** 2
		+ (rgb_a[1] - rgb_b[1]) ** 2
		+ (rgb_a[2] - rgb_b[2]) ** 2
	)


def hex_to_best_xkcd_name(hex_color: str) -> str:
	"""
	Return the closest xkcd color name for the given hex color.
	Uses an exact match fast path and falls back to nearest RGB distance.
	"""
	normalized = _normalize_hex(hex_color)
	for name, rgb in _load_xkcd_rgb_table():
		if normalized == _normalize_hex(sns.xkcd_rgb[name]):
			return name

	target = (int(normalized[1:3], 16), int(normalized[3:5], 16), int(normalized[5:7], 16))
	best_name = None
	best_dist = None
	for name, sample_rgb in _load_xkcd_rgb_table():
		dist = _rgb_distance_squared(target, sample_rgb)
		if best_dist is None or dist < best_dist:
			best_dist = dist
			best_name = name
	return best_name


def hex_to_best_xkcd_name_with_distance(hex_color: str) -> tuple:
	"""
	Return the closest xkcd name and squared RGB distance for a hex color.
	"""
	normalized = _normalize_hex(hex_color)
	for name, rgb in _load_xkcd_rgb_table():
		if normalized == _normalize_hex(sns.xkcd_rgb[name]):
			return name, 0

	target = (int(normalized[1:3], 16), int(normalized[3:5], 16), int(normalized[5:7], 16))
	best_name = ""
	best_dist = None
	for name, sample_rgb in _load_xkcd_rgb_table():
		dist = _rgb_distance_squared(target, sample_rgb)
		if best_dist is None or dist < best_dist:
			best_dist = dist
			best_name = name
	return best_name, best_dist or 0


def rgb_to_best_xkcd_name(rgb: list | tuple) -> str:
	"""
	Return the closest xkcd color name for an RGB tuple (0-255 ints).
	"""
	if not isinstance(rgb, (list, tuple)) or len(rgb) != 3:
		raise ValueError("rgb must be a 3-item tuple or list")
	target = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
	best_name = None
	best_dist = None
	for name, sample_rgb in _load_xkcd_rgb_table():
		dist = _rgb_distance_squared(target, sample_rgb)
		if best_dist is None or dist < best_dist:
			best_dist = dist
			best_name = name
	return best_name
