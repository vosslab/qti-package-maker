# Standard Library
import sys

# Pip3 Library
import pytest
import six

if "six.moves" not in sys.modules:
	sys.modules["six.moves"] = six.moves

import seaborn as sns

# QTI Package Maker
from qti_package_maker.common.color_theory import rgb_color_name_match


def test_hex_to_best_xkcd_name_exact() -> None:
	red_hex = sns.xkcd_rgb["red"]
	blue_hex = sns.xkcd_rgb["blue"]
	assert rgb_color_name_match.hex_to_best_xkcd_name(red_hex) == "red"
	assert rgb_color_name_match.hex_to_best_xkcd_name(blue_hex) == "blue"


def test_hex_to_best_xkcd_name_closest() -> None:
	assert rgb_color_name_match.hex_to_best_xkcd_name("#f10000") == "red"


def test_hex_to_best_xkcd_name_with_distance_exact() -> None:
	red_hex = sns.xkcd_rgb["red"]
	name, distance = rgb_color_name_match.hex_to_best_xkcd_name_with_distance(red_hex)
	assert name == "red"
	assert distance == 0


def test_rgb_to_best_xkcd_name_exact() -> None:
	red_hex = sns.xkcd_rgb["red"]
	rgb = (int(red_hex[1:3], 16), int(red_hex[3:5], 16), int(red_hex[5:7], 16))
	assert rgb_color_name_match.rgb_to_best_xkcd_name(rgb) == "red"


def test_rgb_to_best_xkcd_name_invalid() -> None:
	with pytest.raises(ValueError):
		rgb_color_name_match.rgb_to_best_xkcd_name((255, 0))
