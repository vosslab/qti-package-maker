"""Red scan tools and best-red offset selection."""

# QTI Package Maker
from qti_package_maker.common.color_theory.generator import _color_for_hue, _redness_score
from qti_package_maker.common.color_theory.hue_layout import _generate_hues_equal
from qti_package_maker.common.color_theory.wheel_specs import DEFAULT_RED_OFFSETS, DEFAULT_WHEEL_MODE_ORDER, DEFAULT_WHEEL_SPECS

_BEST_RED_OFFSETS = {}
for mode, value in (DEFAULT_RED_OFFSETS or {}).items():
	_BEST_RED_OFFSETS[(mode, None, "ff0000")] = value


def _render_red_scan_tables(num_colors: int = 16, mode: str | None = None) -> str:
	if mode is None:
		mode = list(DEFAULT_WHEEL_MODE_ORDER)[0]
	spec = DEFAULT_WHEEL_SPECS.get(mode)
	if spec is None:
		raise ValueError(f"Unknown mode: {mode}")

	def rows_for_offsets(offsets: list) -> list:
		rows = []
		for offset in offsets:
			hues = _generate_hues_equal(num_colors, offset=offset)
			color_hex = _color_for_hue(hues[0], spec, mode, m_override=spec.m_max)
			rows.append((offset, color_hex, _redness_score(color_hex)))
		return rows

	coarse_step = 5.0
	fine_step = 1.0
	micro_step = 0.2

	coarse_offsets = [i for i in range(0, 360, int(coarse_step))]
	coarse_rows = rows_for_offsets(coarse_offsets)
	coarse_ranked = sorted(coarse_rows, key=lambda x: x[2])
	best_coarse = coarse_ranked[0][0]

	fine_offsets = [best_coarse + d for d in range(-int(coarse_step), int(coarse_step) + 1, int(fine_step))]
	fine_offsets = [o % 360 for o in fine_offsets]
	fine_rows = rows_for_offsets(fine_offsets)
	fine_ranked = sorted(fine_rows, key=lambda x: x[2])
	fine_top = [row[0] for row in fine_ranked[:3]]

	micro_offsets = []
	step_count = int(round(1.0 / micro_step))
	for base in fine_top:
		for i in range(-step_count, step_count + 1):
			micro_offsets.append((base + i * micro_step) % 360.0)
	micro_offsets = sorted(set(micro_offsets))
	micro_rows = rows_for_offsets(micro_offsets)
	micro_ranked = sorted(micro_rows, key=lambda x: x[2])

	parts = []
	parts.append("<h2>Step 5 (coarse)</h2><table><tr><th>Offset</th><th>Color</th><th>Hex</th><th>Sum</th><th>|G-B|/(G+B)</th><th>(G+B)/(2R)</th></tr>\n")
	for offset, color_hex, score in coarse_ranked:
		total = score[0]
		gb_balance = score[1]
		gb_over_2r = score[2]
		parts.append("<tr>")
		parts.append(f"<td>{offset:.1f}</td>")
		parts.append(_generate_table_td(color_hex, "000000", ""))
		parts.append(f"<td>{color_hex}</td>")
		parts.append(f"<td>{total:.3f}</td>")
		parts.append(f"<td>{gb_balance:.3f}</td>")
		parts.append(f"<td>{gb_over_2r:.3f}</td>")
		parts.append("</tr>\n")
	parts.append("</table>")

	parts.append("<h2>Step 1 (refine)</h2><table><tr><th>Offset</th><th>Color</th><th>Hex</th><th>Sum</th><th>|G-B|/(G+B)</th><th>(G+B)/(2R)</th></tr>\n")
	for offset, color_hex, score in fine_ranked:
		total = score[0]
		gb_balance = score[1]
		gb_over_2r = score[2]
		parts.append("<tr>")
		parts.append(f"<td>{offset:.1f}</td>")
		parts.append(_generate_table_td(color_hex, "000000", ""))
		parts.append(f"<td>{color_hex}</td>")
		parts.append(f"<td>{total:.3f}</td>")
		parts.append(f"<td>{gb_balance:.3f}</td>")
		parts.append(f"<td>{gb_over_2r:.3f}</td>")
		parts.append("</tr>\n")
	parts.append("</table>")

	parts.append("<h2>Step 0.2 (micro)</h2><table><tr><th>Offset</th><th>Color</th><th>Hex</th><th>Sum</th><th>|G-B|/(G+B)</th><th>(G+B)/(2R)</th></tr>\n")
	for offset, color_hex, score in micro_ranked:
		total = score[0]
		gb_balance = score[1]
		gb_over_2r = score[2]
		parts.append("<tr>")
		parts.append(f"<td>{offset:.1f}</td>")
		parts.append(_generate_table_td(color_hex, "000000", ""))
		parts.append(f"<td>{color_hex}</td>")
		parts.append(f"<td>{total:.3f}</td>")
		parts.append(f"<td>{gb_balance:.3f}</td>")
		parts.append(f"<td>{gb_over_2r:.3f}</td>")
		parts.append("</tr>\n")
	parts.append("</table>")

	return "".join(parts)


def _write_red_scan_html(filename: str, num_colors: int = 16, mode: str | None = None) -> None:
	if mode is None:
		mode = list(DEFAULT_WHEEL_MODE_ORDER)[0]
	with open(filename, "w") as f:
		f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Red Scan</title>"
				"<style>table {width: 100%; border-collapse: collapse; text-align: center;} "
				"th, td {padding: 8px; border: 1px solid black;} "
				"th {background-color: #333; color: white;} "
				"</style></head><body>")
		f.write(_render_red_scan_tables(num_colors=num_colors, mode=mode))
		f.write("</body></html>")

	print(f"Red scan table saved as {filename}")


def _write_red_scan_bundle_html(filename: str, num_colors: int = 16, modes: list | None = None) -> None:
	if modes is None:
		modes = list(DEFAULT_WHEEL_MODE_ORDER)

	with open(filename, "w") as f:
		f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Red Scan</title>"
				"<style>table {width: 100%; border-collapse: collapse; text-align: center;} "
				"th, td {padding: 8px; border: 1px solid black;} "
				"th {background-color: #333; color: white;} "
				"</style></head><body>")
		for mode in modes:
			f.write(f"<h1>{mode}</h1>")
			f.write(_render_red_scan_tables(num_colors=num_colors, mode=mode))
		f.write("</body></html>")

	print(f"Red scan bundle saved as {filename}")


def _best_red_offset(
	num_colors: int,
	mode: str,
	anchor_hex: str,
	wheel_specs: dict | None = None,
	coarse_step: float = 5.0,
	fine_step: float = 1.0,
	micro_step: float = 0.2,
	top_k: int = 3,
) -> float:
	specs = wheel_specs or DEFAULT_WHEEL_SPECS
	spec = specs.get(mode)
	if spec is None:
		raise ValueError(f"Unknown mode: {mode}")

	def score_offset(offset: float) -> tuple:
		hues = _generate_hues_equal(num_colors, offset=offset)
		color_hex = _color_for_hue(hues[0], spec, mode, m_override=spec.m_max)
		return _redness_score(color_hex)

	coarse_offsets = [i for i in range(0, 360, int(coarse_step))]
	coarse_ranked = sorted(((score_offset(o), o) for o in coarse_offsets), key=lambda x: x[0])
	best_coarse = coarse_ranked[0][1]

	fine_offsets = [best_coarse + d for d in range(-int(coarse_step), int(coarse_step) + 1, int(fine_step))]
	fine_ranked = sorted(((score_offset(o % 360), o % 360) for o in fine_offsets), key=lambda x: x[0])
	fine_top = [o for _s, o in fine_ranked[:top_k]]

	micro_offsets = []
	for base in fine_top:
		step_count = int(round(1.0 / micro_step))
		for i in range(-step_count, step_count + 1):
			micro_offsets.append((base + i * micro_step) % 360.0)

	micro_ranked = sorted(((score_offset(o), o) for o in micro_offsets), key=lambda x: x[0])
	return micro_ranked[0][1]


def _select_hues_for_anchor(num_colors: int, mode: str, anchor_hex: str, samples: int = 48, wheel_specs: dict | None = None) -> list:
	specs = wheel_specs or DEFAULT_WHEEL_SPECS
	spec = specs.get(mode)
	if spec is None:
		raise ValueError(f"Unknown mode: {mode}")

	anchor_key = anchor_hex or "ff0000"
	cache_key = (mode, num_colors, anchor_key)
	global_key = (mode, None, anchor_key)
	if cache_key not in _BEST_RED_OFFSETS:
		if anchor_key == "ff0000" and global_key in _BEST_RED_OFFSETS:
			_BEST_RED_OFFSETS[cache_key] = _BEST_RED_OFFSETS[global_key]
		else:
			_BEST_RED_OFFSETS[cache_key] = _best_red_offset(num_colors, mode, anchor_hex, wheel_specs=specs)

	best_offset = _BEST_RED_OFFSETS[cache_key]
	return _generate_hues_equal(num_colors, offset=best_offset)


def _generate_table_td(bg_hex_color: str, text_hex_color: str, text: str = "this is a test") -> str:
	td_cell = ''
	td_cell += f"<td style='background-color:#{bg_hex_color};'>"
	td_cell += f"<span style='color:#{text_hex_color};'>{text}</span></td>\n"
	return td_cell
