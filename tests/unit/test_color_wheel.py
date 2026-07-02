# Standard Library
import random
import re

# QTI Package Maker
from qti_package_maker.common import color_wheel
from qti_package_maker.common.color_theory import next_gen
from qti_package_maker.common.color_theory.legacy_color_wheel import (
	default_color_wheel as legacy_default_color_wheel,
	min_difference,
)


def test_min_difference_cases() -> None:
	assert min_difference([40, 41]) == 1
	assert min_difference([30, 15, 36]) == 6
	assert min_difference([84, 25, 24, 37]) == 1
	assert min_difference([84, 30, 30, 42, 56, 72]) == 0


def test_facade_legacy_backend_matches_legacy() -> None:
	random.seed(0)
	legacy_colors = legacy_default_color_wheel(5)
	random.seed(0)
	facade_colors = color_wheel.generate_color_wheel(5, backend="legacy")
	assert facade_colors == legacy_colors


def test_cam16_backend_returns_hex() -> None:
	random.seed(0)
	first_mode = next_gen.DEFAULT_WHEEL_MODE_ORDER[0]
	colors = color_wheel.generate_color_wheel(3, backend="cam16", mode=first_mode)
	assert len(colors) == 3
	assert all(re.match(r"^[0-9a-f]{6}$", value) for value in colors)

	def red_score(hex_value: str) -> tuple:
		r = int(hex_value[0:2], 16)
		g = int(hex_value[2:4], 16)
		b = int(hex_value[4:6], 16)
		gb = g + b
		gb_balance = abs(g - b) / (gb + 1e-6)
		gb_over_2r = gb / (2.0 * r + 1e-6)
		return (gb_balance + gb_over_2r, gb_balance, gb_over_2r, -r)

	scores = [red_score(value) for value in colors]
	assert scores[0] == min(scores)
