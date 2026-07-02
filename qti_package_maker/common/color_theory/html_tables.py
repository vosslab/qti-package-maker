"""HTML output for manual color evaluation."""

# QTI Package Maker
from qti_package_maker.common.color_theory import rgb_color_name_match
from qti_package_maker.common.color_theory.cam16_utils import _cam16_ucs_radius, _gamut_margin, _srgb_hex_to_cam16_spec, _xyz_to_srgb, cam16_jmh_to_xyz
from qti_package_maker.common.color_theory.generator import _color_for_hue, _colors_for_hues, _m_for_target_ucs_r, _print_legacy_red_comparison, _shared_m_and_max_ms
from qti_package_maker.common.color_theory.red_scan import _select_hues_for_anchor
from qti_package_maker.common.color_theory.wheel_specs import DEFAULT_WHEEL_MODE_ORDER, DEFAULT_WHEEL_SPECS


def _generate_table_td(bg_hex_color: str, text_hex_color: str, text: str = "this is a test") -> str:
	td_cell = ''
	td_cell += f"<td style='background-color:#{bg_hex_color};'>"
	td_cell += f"<span style='color:#{text_hex_color};'>{text}</span></td>\n"
	return td_cell


def write_html_color_table(filename: str, num_colors: int = 16, modes: list | None = None) -> None:
	if modes is None:
		modes = list(DEFAULT_WHEEL_MODE_ORDER)

	if not modes:
		raise ValueError("No modes available for HTML color table")
	required = ["dark", "light", "xlight"]
	missing = [mode for mode in required if mode not in modes]
	if missing:
		raise ValueError(f"Legacy HTML table requires modes {required}; missing {missing}")
	dark_mode = "dark"
	light_mode = "light"
	extra_light_mode = "xlight"

	anchor_hex = "ff0000"
	hues = _select_hues_for_anchor(num_colors, dark_mode, anchor_hex, samples=48)

	dark_wheel = _colors_for_hues(hues, DEFAULT_WHEEL_SPECS[dark_mode], dark_mode)
	light_wheel = _colors_for_hues(hues, DEFAULT_WHEEL_SPECS[light_mode], light_mode)
	extra_light_wheel = _colors_for_hues(hues, DEFAULT_WHEEL_SPECS[extra_light_mode], extra_light_mode)
	dark_spec = DEFAULT_WHEEL_SPECS.get(dark_mode)
	light_spec = DEFAULT_WHEEL_SPECS.get(light_mode)
	extra_light_spec = DEFAULT_WHEEL_SPECS.get(extra_light_mode)
	if dark_spec is not None and dark_wheel and dark_spec.target_ucs_r is None:
		dark_wheel[0] = _color_for_hue(hues[0], dark_spec, dark_mode, m_override=dark_spec.m_max)
	if light_spec is not None and light_wheel and light_spec.target_ucs_r is None:
		light_wheel[0] = _color_for_hue(hues[0], light_spec, light_mode, m_override=light_spec.m_max)
	if extra_light_spec is not None and extra_light_wheel and extra_light_spec.target_ucs_r is None:
		extra_light_wheel[0] = _color_for_hue(hues[0], extra_light_spec, extra_light_mode, m_override=extra_light_spec.m_max)

	with open(filename, 'w') as f:
		f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Color Table</title>"
				"<style>table {width: 100%; border-collapse: collapse; text-align: center;} "
				"th, td {padding: 10px; border: 1px solid black;} "
				"th {background-color: #333; color: white;} "
				"</style></head><body>"
				"<table><tr>"
				"<th>Color Name</th>"
				"<th>White / Dark</th>"
				"<th>Extra Light / Dark</th>"
				"<th>Light / Black</th>"
				"<th>Extra Light / Black</th>"
				"<th>Dark / White</th>"
				"<th>Dark / Light</th>"
				"<th>Dark / Shift Dark</th>"
				"</tr>\n")

		for i in range(num_colors):
			f.write("<tr>\n")
			matched_name = rgb_color_name_match.hex_to_best_xkcd_name(dark_wheel[i])
			color_name = f"hue {i + 1} ({matched_name})"
			dark_hex = dark_wheel[i]
			light_hex = light_wheel[i]
			extra_light_hex = extra_light_wheel[i]
			shifted_dark_hex = dark_wheel[(i + num_colors // 2) % num_colors]

			f.write(_generate_table_td("ffffff", "000000", color_name))
			f.write(_generate_table_td("ffffff", dark_hex, "this is a test"))
			f.write(_generate_table_td(extra_light_hex, dark_hex, "this is a test"))
			f.write(_generate_table_td(light_hex, "000000", "this is a test"))
			f.write(_generate_table_td(extra_light_hex, "000000", "this is a test"))
			f.write(_generate_table_td(dark_hex, "ffffff", "this is a test"))
			f.write(_generate_table_td(dark_hex, light_hex, "this is a test"))
			f.write(_generate_table_td(dark_hex, shifted_dark_hex, "this is a test"))
			f.write("</tr>\n")

		f.write("</table></body></html>")

	print(f"HTML color table saved as {filename}")
	_print_legacy_red_comparison(
		dark_wheel[0],
		light_wheel[0],
		extra_light_wheel[0],
		labels=(dark_mode, light_mode, extra_light_mode),
	)


def write_html_color_table_cam16_debug(filename: str, num_colors: int = 16, modes: list | None = None, repeats: int = 1) -> None:
	if modes is None:
		modes = list(DEFAULT_WHEEL_MODE_ORDER)

	with open(filename, "w") as f:
		f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>CAM16 Debug</title>"
				"<style>"
				"table {width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 24px;} "
				"th, td {padding: 8px; border: 1px solid black;} "
				"th {background-color: #333; color: white;} "
				".swatch {height: 32px;}"
				"</style></head><body>")

		anchor_hex = "ff0000"
		for mode in modes:
			spec = DEFAULT_WHEEL_SPECS.get(mode)
			target_j = spec.target_j if spec else 0.0
			f.write(f"<h1>{mode} (target J {target_j:.1f})</h1>")
			if spec is not None:
				if spec.target_ucs_r is not None:
					f.write(f"<p>control=target_ucs_r r={spec.target_ucs_r:.2f}</p>")
				else:
					f.write(f"<p>control=shared_m_quantile q={spec.shared_m_quantile:.2f}</p>")
			for repeat in range(repeats):
				f.write(f"<h2>run {repeat + 1}</h2>")
				f.write("<table><tr><th>Hue</th><th>Swatch</th><th>Hex</th><th>XKCD Name</th><th>J</th><th>Q</th><th>UCS_r</th><th>target_ucs_r</th><th>ucs_r_err</th><th>m_target</th><th>m_final</th><th>clamp_reason</th><th>M_max_hue</th><th>M_util</th><th>gamut_margin</th></tr>\n")
				hues = _select_hues_for_anchor(num_colors, mode, anchor_hex, samples=48)
				_shared_m, max_ms = _shared_m_and_max_ms(hues, spec, mode)
				colors = _colors_for_hues(hues, spec, mode, apply_variation=False)
				if spec is not None and colors and spec.target_ucs_r is None:
					colors[0] = _color_for_hue(hues[0], spec, mode, m_override=spec.m_max)
				for i, (hex_value, max_m) in enumerate(zip(colors, max_ms)):
					cam = _srgb_hex_to_cam16_spec(hex_value)
					ucs_r = _cam16_ucs_radius(cam)
					XYZ = cam16_jmh_to_xyz(cam.J, cam.M, cam.h)
					rgb_linear = _xyz_to_srgb(XYZ, apply_encoding=False)
					gamut_margin = _gamut_margin(rgb_linear)
					m_util = cam.M / max_m if max_m > 0 else 0.0
					target_ucs_r = spec.target_ucs_r if spec is not None else None
					m_cap = max_m
					m_target = None
					clamp_reason = ""
					ucs_r_err = ""
					if target_ucs_r is not None:
						m_target = _m_for_target_ucs_r(spec.target_j, hues[i], target_ucs_r, m_cap)
						ucs_r_err = f"{ucs_r - target_ucs_r:.2f}"
						clamp_reason = "gamut_limit" if m_target >= (m_cap - 1e-6) else "none"
					matched_name = rgb_color_name_match.hex_to_best_xkcd_name(hex_value)
					f.write("<tr>")
					f.write(f"<td>{i + 1}</td>")
					f.write(f"<td class='swatch' style='background-color:#{hex_value};'></td>")
					f.write(f"<td>{hex_value}</td>")
					f.write(f"<td>{matched_name}</td>")
					f.write(f"<td>{cam.J:.2f}</td>")
					f.write(f"<td>{cam.Q:.2f}</td>")
					f.write(f"<td>{ucs_r:.2f}</td>")
					f.write(f"<td>{'' if target_ucs_r is None else f'{target_ucs_r:.2f}'}</td>")
					f.write(f"<td>{ucs_r_err}</td>")
					f.write(f"<td>{'' if m_target is None else f'{m_target:.2f}'}</td>")
					f.write(f"<td>{cam.M:.2f}</td>")
					f.write(f"<td>{clamp_reason}</td>")
					f.write(f"<td>{max_m:.2f}</td>")
					f.write(f"<td>{m_util:.3f}</td>")
					f.write(f"<td>{gamut_margin:.4f}</td>")
					f.write("</tr>\n")
				f.write("</table>")

		f.write("</body></html>")

	print(f"CAM16 debug table saved as {filename}")
