"""
Public API for color wheel generation.

Provides perceptually-distinct colors for multiple-choice answer highlighting.
"""

# Standard Library
import sys

# QTI Package Maker
from qti_package_maker.common.color_theory import legacy_color_wheel as _legacy_color_wheel

__all__ = [
	"generate_color_wheel",
	"dark_color_wheel",
	"light_color_wheel",
	"extra_light_color_wheel",
	"default_color_wheel",
	"light_and_dark_color_wheel",
	"get_indices_for_color_wheel",
	"min_difference",
	"write_html_color_table",
	"default_color_wheel_calc",
	"make_color_wheel",
]


def generate_color_wheel(num_colors: int, backend: str = "cam16", **kwargs) -> list:
	"""
	Generate a list of perceptually-distinct hex color codes.

	Args:
		num_colors: Number of colors to generate.
		backend: Color generation algorithm ("cam16" or "legacy").
		**kwargs: Backend-specific options (e.g., mode="dark" for cam16).

	Returns:
		List of hex color strings (e.g., ["a83232", "32a848", ...]).
	"""
	if backend == "legacy":
		return _legacy_color_wheel.default_color_wheel(num_colors, **kwargs)
	if backend == "cam16":
		from qti_package_maker.common.color_theory import next_gen
		return next_gen.generate_color_wheel(num_colors, **kwargs)
	raise ValueError(f"Unknown backend: {backend}")


def _build_named_wheel(mode: str, names: list, num_colors: int) -> dict:
	colors = generate_color_wheel(num_colors, backend="cam16", mode=mode)
	if len(colors) != num_colors:
		raise ValueError(f"Expected {num_colors} colors for mode {mode}, got {len(colors)}")
	return dict(zip(names, colors))


_NAMED_WHEEL_NAMES = list(_legacy_color_wheel.dark_color_wheel.keys())
_NAMED_WHEEL_SIZE = len(_NAMED_WHEEL_NAMES)

_DEFAULT_DARK_WHEEL = _build_named_wheel("dark", _NAMED_WHEEL_NAMES, _NAMED_WHEEL_SIZE)
_DEFAULT_LIGHT_WHEEL = _build_named_wheel("light", _NAMED_WHEEL_NAMES, _NAMED_WHEEL_SIZE)
_DEFAULT_EXTRA_LIGHT_WHEEL = _build_named_wheel("xlight", _NAMED_WHEEL_NAMES, _NAMED_WHEEL_SIZE)

dark_color_wheel = _DEFAULT_DARK_WHEEL
light_color_wheel = _DEFAULT_LIGHT_WHEEL
extra_light_color_wheel = _DEFAULT_EXTRA_LIGHT_WHEEL

get_indices_for_color_wheel = _legacy_color_wheel.get_indices_for_color_wheel
min_difference = _legacy_color_wheel.min_difference
default_color_wheel_calc = _legacy_color_wheel.default_color_wheel_calc
make_color_wheel = _legacy_color_wheel.make_color_wheel


def default_color_wheel(num_colors: int, color_wheel: dict | None = None) -> list:
	if color_wheel is None:
		color_wheel = dark_color_wheel
	return _legacy_color_wheel.default_color_wheel(num_colors, color_wheel=color_wheel)


def light_and_dark_color_wheel(num_colors: int, dark_color_wheel: dict | None = None, light_color_wheel: dict | None = None) -> tuple:
	if dark_color_wheel is None:
		dark_color_wheel = _DEFAULT_DARK_WHEEL
	if light_color_wheel is None:
		light_color_wheel = _DEFAULT_LIGHT_WHEEL
	return _legacy_color_wheel.light_and_dark_color_wheel(
		num_colors,
		dark_color_wheel=dark_color_wheel,
		light_color_wheel=light_color_wheel,
	)


def write_html_color_table(filename: str, num_colors: int | None = None) -> None:
	return _legacy_color_wheel.write_html_color_table(filename, num_colors=num_colors)


def main() -> None:
	filename = "color_table.html"
	num_colors = None

	if len(sys.argv) > 1:
		filename = sys.argv[1]
	if len(sys.argv) > 2:
		num_colors = int(sys.argv[2])

	write_html_color_table(filename, num_colors=num_colors)


if __name__ == "__main__":
	main()
