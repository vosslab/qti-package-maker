"""Hue layout helpers."""

# Standard Library
import random
import collections.abc


def _generate_hues_equal(num_colors: int, offset: float = 0.0) -> list:
	step = 360.0 / float(num_colors)
	return [(offset + step * i) % 360.0 for i in range(num_colors)]


def _generate_hues_anchor(num_colors: int, anchor_hue: float) -> list:
	return _generate_hues_equal(num_colors, offset=anchor_hue)


def _generate_hues_offset(num_colors: int) -> list:
	offset = random.random() * 360.0
	return _generate_hues_equal(num_colors, offset=offset)


def _generate_hues_optimized(num_colors: int, score_fn: collections.abc.Callable, samples: int = 24) -> list:
	best_offset = None
	best_score = None
	for _ in range(samples):
		offset = random.random() * 360.0
		hues = _generate_hues_equal(num_colors, offset=offset)
		score = score_fn(hues)
		if best_score is None or score > best_score:
			best_score = score
			best_offset = offset
	return _generate_hues_equal(num_colors, offset=best_offset or 0.0)
