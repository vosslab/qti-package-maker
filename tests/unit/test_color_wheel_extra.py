# Standard Library
import random

# QTI Package Maker
from qti_package_maker.common.color_theory.legacy_color_wheel import (
	get_indices_for_color_wheel,
)


def test_get_indices_wraps_when_too_many() -> None:
	indices = get_indices_for_color_wheel(10, 4)
	assert len(indices) == 10
	assert set(indices) == {0, 1, 2, 3}


def test_get_indices_deterministic_with_seed() -> None:
	random.seed(0)
	indices = get_indices_for_color_wheel(3, 10)
	assert len(indices) == 3
	assert all(0 <= idx < 10 for idx in indices)
