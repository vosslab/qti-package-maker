# Standard Library
import math
import random

# Pip3 Library
import colorsys

# QTI Package Maker
# none allowed here!!

#====================================================================
dark_color_wheel = {
	'red': 'b30000',
	'orange': 'b34100',
	'brown': '663300',
	'gold': 'b37100',
	'yellow': '999900',
	'olive green': '465927',
	'lime green': '4d9900',
	'green': '008000',
	'teal': '008066',
	'cyan': '008080',
	'sky blue': '076cab',
	'blue': '002db3',
	'navy': '004080',
	'purple': '690f8a',
	'magenta': '800055',
	'pink': '99004d'
}

light_color_wheel = {
	'red': 'ffcccc',
	'orange': 'ffd9cc',
	'brown': 'ffe6cc',
	'gold': 'ffebcc',
	'yellow': 'ffffcc',
	'olive green': 'eaefdc',
	'lime green': 'd9ffcc',
	'green': 'ccffcc',
	'teal': 'ccffe6',
	'cyan': 'ccffff',
	'sky blue': 'ccf2ff',
	'blue': 'ccd9ff',
	'navy': 'ccccff',
	'purple': 'e6ccff',
	'magenta': 'ffccf2',
	'pink': 'ffccff'
}

extra_light_color_wheel = {
	'red': 'ffe6e6',
	'orange': 'ffece6',
	'brown': 'fff3e6',
	'gold': 'fff9e5',
	'yellow': 'ffffe6',
	'olive green': 'f5f7ee',
	'lime green': 'ecffe6',
	'green': 'e6ffe6',
	'teal': 'e6fff3',
	'cyan': 'e6ffff',
	'sky blue': 'e6f9ff',
	'blue': 'e6ecff',
	'navy': 'e6e6ff',
	'purple': 'f3e6ff',
	'magenta': 'ffe6f9',
	'pink': 'ffe6ff'
}

#====================================================================
def get_indices_for_color_wheel(num_colors: int, color_wheel_length: int) -> list:
	"""
	Selects `num_colors` indices from a circular list of `color_wheel_length` items while ensuring
	that the selected indices are evenly spaced or satisfy other constraints depending on edge cases.

	Args:
		num_colors (int): The number of colors (indices) to select.
		color_wheel_length (int): The total length of the color wheel.

	Returns:
		list[int]: A sorted list of selected indices satisfying the constraints.

	Raises:
		ValueError: If `num_colors` is too large to satisfy the minimum distance requirement
		or if further indices cannot be selected under the constraints.

	Notes:
		- If `num_colors` exceeds `color_wheel_length`, the indices wrap around to repeat.
		- If `num_colors` is greater than half of `color_wheel_length`, random selection is used.
		- For smaller cases, a minimum spacing (`min_distance`) is enforced to distribute indices evenly.
		- The `color_wheel_length` is treated as circular, so wrap-around is handled.
	"""

	# Edge Case 1: If the number of colors exceeds the length of the color wheel
	# Wrap around by repeating indices in a circular fashion
	if num_colors > color_wheel_length:
		selected_indices = [i % color_wheel_length for i in range(num_colors)]
		return selected_indices

	# Edge Case 2: If there are many colors relative to the color wheel length
	# Use random selection without enforcing `min_distance` because spacing constraints aren't realistic
	if num_colors > color_wheel_length // 2 - 1:
		all_indices = list(range(color_wheel_length))
		random.shuffle(all_indices)  # Shuffle to randomize the selection
		selected_indices = all_indices[:num_colors]
		return sorted(selected_indices)

	# General Case: Calculate minimum spacing between indices
	# Ensure indices are approximately evenly distributed around the color wheel
	min_distance = int(math.floor(color_wheel_length / (num_colors + 1)))

	# Check if the desired number of colors can be selected given the `min_distance`
	if num_colors > color_wheel_length // min_distance:
		raise ValueError("num_colors too large to satisfy min_distance requirement")

	# Initialize an empty list for selected indices and create a list of all available indices
	selected_indices = []  # Stores the final selected indices
	available_indices = list(range(color_wheel_length))  # Indices that can still be selected

	# Select the required number of indices (`num_colors`)
	for _ in range(num_colors):
		# If no indices are available, raise an error
		if len(available_indices) == 0:
			raise ValueError("Cannot select further colors within min_distance constraints")

		# Randomly choose an index from the available indices
		index = random.choice(available_indices)

		# Add the chosen index to the list of selected indices
		selected_indices.append(index)

		# Remove indices too close to the chosen index
		# The range includes indices `min_distance` away in both directions (wrap-around accounted for)
		for offset in range(-min_distance + 1, min_distance):
			idx_to_remove = (index + offset) % color_wheel_length  # Handle circular wrap-around
			if idx_to_remove in available_indices:
				available_indices.remove(idx_to_remove)

	# Sort the selected indices for consistency
	selected_indices = sorted(selected_indices)

	# Check if the selected indices actually meet the `min_distance` constraint
	# If not, raise an error as a safety check
	if num_colors > 1 and min_difference(selected_indices) < min_distance:
		raise ValueError(f'min_difference {min_difference(selected_indices)} < min_distance {min_distance}')

	return selected_indices

#====================================================================
def default_color_wheel(num_colors: int, color_wheel: dict = dark_color_wheel) -> list:
	color_wheel_length = len(color_wheel)
	print(f"num_colors = {num_colors}; color_wheel_length = {color_wheel_length}")
	selected_indices = get_indices_for_color_wheel(num_colors, color_wheel_length)

	# Select the colors based on the generated indices
	color_wheel_keys = list(color_wheel.keys())
	selected_keys = [color_wheel_keys[i] for i in selected_indices]
	selected_colors_rgb = [color_wheel[i] for i in selected_keys]
	return selected_colors_rgb

#====================================================================
def light_and_dark_color_wheel(num_colors: int, dark_color_wheel: dict = dark_color_wheel, light_color_wheel: dict = light_color_wheel) -> tuple:
	color_wheel_length = min(len(dark_color_wheel), len(light_color_wheel))
	selected_indices = get_indices_for_color_wheel(num_colors, color_wheel_length)

	# Select the colors based on the generated indices
	dark_color_wheel_keys = list(dark_color_wheel.keys())
	dark_selected_keys = [dark_color_wheel_keys[i] for i in selected_indices]
	dark_selected_colors_rgb = [dark_color_wheel[i] for i in dark_selected_keys]
	light_color_wheel_keys = list(light_color_wheel.keys())
	light_selected_keys = [light_color_wheel_keys[i] for i in selected_indices]
	light_selected_colors_rgb = [light_color_wheel[i] for i in light_selected_keys]
	return light_selected_colors_rgb, dark_selected_colors_rgb

#====================================================================
#====================================================================
#====================================================================
#====================================================================
def _generate_table_td(bg_hex_color: str, text_hex_color: str, text: str = "this is a test") -> str:
	"""
	Generates an HTML table cell (<td>) with the specified background and text color.
	"""
	td_cell = ''
	td_cell += f"<td style='background-color:#{bg_hex_color};'>"
	td_cell += f"<span style='color:#{text_hex_color};'>{text}</span></td>\n"
	return td_cell

#====================================================================
def write_html_color_table(filename: str, num_colors: int | None = None) -> None:
	"""
	Generates an HTML table displaying various color combinations.
	"""
	# Determine the number of colors to use
	if num_colors is None or num_colors > len(dark_color_wheel):
		num_colors = len(dark_color_wheel)
	# Get color pairs using the color wheel function
	light_colors, dark_colors = light_and_dark_color_wheel(num_colors)
	# Convert dictionaries to ordered lists
	extra_light_colors = list(extra_light_color_wheel.values())
	light_colors = list(light_color_wheel.values())
	dark_colors = list(dark_color_wheel.values())
	color_names = list(dark_color_wheel.keys())  # Get color names
	# Start writing the HTML file
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
		# Generate table rows
		for i in range(num_colors):
			color_name = color_names[i].lower()
			dark_hex = dark_colors[i]
			light_hex = light_colors[i]
			extra_light_hex = extra_light_colors[i]
			shifted_dark_hex = dark_colors[(i + num_colors // 2) % num_colors]
			#shifted_light_hex = light_colors[(i + num_colors // 2) % num_colors]
			f.write("<tr>\n")
			# Column 1: Color name (white background, black text)
			f.write(_generate_table_td("ffffff", "000000", color_name))
			# Column 2: "this is a test" (white background, dark text)
			f.write(_generate_table_td("ffffff", dark_hex))
			# Column 3: "this is a test" (extra light background, dark text)
			f.write(_generate_table_td(extra_light_hex, dark_hex))
			# Column 4: "this is a test" (light background, black text)
			f.write(_generate_table_td(light_hex, "000000"))
			# Column 5: "this is a test" (extra light background, black text)
			f.write(_generate_table_td(extra_light_hex, "000000"))
			# Column 6: "this is a test" (dark background, white text)
			f.write(_generate_table_td(dark_hex, "ffffff"))
			# Column 7: "this is a test" (dark background, light text)
			f.write(_generate_table_td(dark_hex, light_hex))
			# Column 8: "this is a test" (dark background, shifted dark text)
			f.write(_generate_table_td(dark_hex, shifted_dark_hex))
			f.write("</tr>\n")
		# End the HTML document
		f.write("</table></body></html>")

	print(f"HTML color table saved as {filename}")

#====================================================================
def default_color_wheel_calc(num_colors: int = 4) -> list:
	degree_step = int(360 / float(num_colors))
	r,g,b = (255, 0, 0)
	color_wheel = make_color_wheel(r,g,b, degree_step)
	return color_wheel

#====================================================================
def make_color_wheel(r: int, g: int, b: int, degree_step: int = 40) -> list: # Assumption: r, g, b in [0, 255]
	# Convert to [0, 1]
	r, g, b = r/255., g/255., b/255.
	#print('rgb: {0:.2f}, {1:.2f}, {2:.2f}'.format(r, g, b))
	hue, l, s = colorsys.rgb_to_hls(r, g, b)     # RGB -> HLS
	#print('hsl: {0:.2f}, {1:.2f}, {2:.2f}'.format(hue, s, l))
	wheel = []
	for deg in range(0, 359, degree_step):
		#print('--')
		hue_i = (hue*360. + float(deg))/360.
		#print(hue_i, l, s)
		#print('hsl: {0:.2f}, {1:.2f}, {2:.2f}'.format(hue_i, s, l))
		ryb_percent_color = colorsys.hls_to_rgb(hue_i, l, s)
		#print(ryb_percent_color)
		#print('ryb: {0:.2f}, {1:.2f}, {2:.2f}'.format(
		#	ryb_percent_color[0], ryb_percent_color[1], ryb_percent_color[2],))
		rgb_percent_color = _ryb_to_rgb(*ryb_percent_color)
		#print('rgb: {0:.2f}, {1:.2f}, {2:.2f}'.format(
		#	rgb_percent_color[0], rgb_percent_color[1], rgb_percent_color[2],))
		### this does not work
		rgb_color = tuple(map(lambda x: int(round(x*255)), rgb_percent_color))
		### this is worse
		#rgb_color = tuple(map(lambda x: int(round(x*255)), ryb_percent_color))
		hexcolor = '%02x%02x%02x' % rgb_color
		wheel.append(hexcolor)
	return wheel

#====================================================================
def _cubic(t: float, a: float, b: float) -> float:
	if not (0 <= t <= 1):
		raise ValueError(f"Invalid t value: {t}. Must be between 0 and 1.")
	weight = t * t * (3 - 2*t)
	return a + weight * (b - a)

#====================================================================
def _ryb_to_rgb(r: float, y: float, b: float) -> tuple: # Assumption: r, y, b in [0, 1]
	# red
	x0, x1 = _cubic(b, 1.0, 0.163), _cubic(b, 1.0, 0.0)
	x2, x3 = _cubic(b, 1.0, 0.5), _cubic(b, 1.0, 0.2)
	y0, y1 = _cubic(y, x0, x1), _cubic(y, x2, x3)
	red = _cubic(r, y0, y1)
	# green
	x0, x1 = _cubic(b, 1.0, 0.373), _cubic(b, 1.0, 0.66)
	x2, x3 = _cubic(b, 0., 0.), _cubic(b, 0.5, 0.094)
	y0, y1 = _cubic(y, x0, x1), _cubic(y, x2, x3)
	green = _cubic(r, y0, y1)
	# blue
	x0, x1 = _cubic(b, 1.0, 0.6), _cubic(b, 0.0, 0.2)
	x2, x3 = _cubic(b, 0.0, 0.5), _cubic(b, 0.0, 0.0)
	y0, y1 = _cubic(y, x0, x1), _cubic(y, x2, x3)
	blue = _cubic(r, y0, y1)
	# return
	return (red, green, blue)

#====================================================================
def min_difference(numbers: list) -> int:
	"""
	Find the minimum difference between any two consecutive integers in a sorted list.
	"""
	if isinstance(numbers, tuple):
		numbers = list(numbers)
	# Sort the list in place
	numbers.sort()
	# Calculate differences using list comprehension
	differences = [numbers[i+1] - numbers[i] for i in range(len(numbers) - 1)]
	# Return the smallest difference
	return min(differences)

#====================================================================
def main() -> None:
	"""
	Main function to test the color wheel functions.
	"""

	# Define the number of colors to generate
	num_colors = random.randint(3, 8)  # Choose a random number of colors to test

	print(f"Testing with {num_colors} colors...\n")

	# Test the default dark color wheel selection
	print("Dark Color Wheel:")
	dark_colors = default_color_wheel(num_colors)
	print(dark_colors, "\n")

	# Test the light and dark color wheel selection
	print("Light and Dark Color Wheel:")
	light_colors, dark_colors = light_and_dark_color_wheel(num_colors)
	print("Light:", light_colors)
	print("Dark:", dark_colors, "\n")

	# Test the extra light color wheel
	print("Extra Light Color Wheel:")
	extra_light_colors, dark_colors = light_and_dark_color_wheel(num_colors, light_color_wheel=extra_light_color_wheel)
	print("Extra Light:", extra_light_colors)
	print("Dark:", dark_colors, "\n")

	# Test the generated color wheel based on calculation
	print("Generated Color Wheel Based on RGB Rotation:")
	generated_wheel = default_color_wheel_calc(num_colors)
	print(generated_wheel, "\n")

	# Test writing the HTML color table
	html_filename = "color_table.html"
	write_html_color_table(html_filename)

#====================================================================
if __name__ == "__main__":
	main()
