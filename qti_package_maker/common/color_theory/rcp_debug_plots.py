#built-in libraries
import math

#pypi libraries
import colour
import colorsys
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

class RCPColorUtils:
   """
   RCP (RYB-Hue, Colorfulness, Perceived Brightness) Color Model.
   - Uses RYB for Hue to improve color mixing aesthetics.
   - Uses CIECAM02 Colorfulness for more perceptually accurate saturation.
   - Uses HSP Perceived Brightness for consistent luminance perception.
   """
   def __init__(self):
      # Define control points for RGB to RYB conversion
      rgb_hues = np.array([-90, 0, 30, 60, 120, 240, 270, 360, 390])
      ryb_hues = np.array([-60, 0, 60, 120, 180, 240, 300, 360, 420])
      self.rgb_to_ryb_interp = interpolate.PchipInterpolator(rgb_hues, ryb_hues, extrapolate=False)
      self.ryb_to_rgb_interp = interpolate.PchipInterpolator(ryb_hues, rgb_hues, extrapolate=False)

   def rgb_to_ryb_hue(self, rgb_hue_deg):
      """Convert an RGB color hue to its RYB hue equivalent."""
      return float(self.rgb_to_ryb_interp(rgb_hue_deg))

   def ryb_to_rgb_hue(self, ryb_hue_deg):
      """Convert an RYB hue back to its RGB hue equivalent."""
      return float(self.ryb_to_rgb_interp(ryb_hue_deg))

   @staticmethod
   def _validate_rgb(rgb):
      # **Step 1: Validate Input Format**
      if not isinstance(rgb, (list, tuple, np.ndarray)) or len(rgb) != 3:
         raise ValueError(f"Invalid RGB input: {rgb}. Expected a 3-element list/tuple/array.")

      # **Step 2: Ensure RGB is in [0,1] range**
      if any(c < 0 or c > 1 for c in rgb):
         raise ValueError(f"RGB values must be in [0,1] range, got: {rgb}")

   @staticmethod
   def _validate_hsl(hsl):
      # **Step 1: Validate Input Format**
      if not isinstance(hsl, (list, tuple, np.ndarray)) or len(hsl) != 3:
         raise ValueError(f"Invalid HSL input: {hsl}. Expected a 3-element list/tuple/array.")

      # **Step 2: Ensure RGB is in [0,1] range**
      if any(c < 0 or c > 1 for c in hsl):
         raise ValueError(f"HSL values must be in [0,1] range, got: {hsl}")

   def perceived_brightness(self, rgb):
      """Calculate perceived brightness using the HSP model."""
      self._validate_rgb(rgb)
      r, g, b = rgb
      brightness = math.sqrt(0.299 * (r ** 2) + 0.587 * (g ** 2) + 0.114 * (b ** 2))
      return brightness

   def colorfulness(self, rgb, fl=1.0):
      """
      Compute colorfulness (M) using the CIECAM02 model.

      - `rgb`: RGB color in [0,1] range.
      - `fl`: Luminance adaptation factor (default 1.0 for average surround).
      """
      self._validate_rgb(rgb)
      # Use sRGB colour space for conversion
      rgb_colourspace = colour.RGB_COLOURSPACES["sRGB"]

      # Convert RGB (0-1 range) to XYZ
      xyz = colour.RGB_to_XYZ(rgb, rgb_colourspace)

      # Convert xy chromaticity coordinates to full XYZ whitepoint
      source_xy = colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65']
      source_wp = colour.xy_to_XYZ(source_xy)  # Now (3,)
      target_wp = colour.xy_to_XYZ(source_xy)  # Now (3,)

      # Debug: Print fixed whitepoint shapes
      #print("Fixed Source Whitepoint (XYZ):", source_wp)
      #print("Fixed Target Whitepoint (XYZ):", target_wp)

      # Ensure both are (3,) shape
      if source_wp.shape != (3,) or target_wp.shape != (3,):
         raise ValueError(f"Whitepoints must be (3,)! Got {source_wp.shape} and {target_wp.shape}")

      # Apply chromatic adaptation
      xyz_adapted = colour.adaptation.chromatic_adaptation(
         xyz, source_wp, target_wp, transform="Bradford"
      )

      # Define standard CIECAM02 viewing conditions
      viewing_conditions = colour.VIEWING_CONDITIONS_CIECAM02["Average"]

      # Set `L_A` and `Y_b` values
      L_A = 64 / 5  # Adapting field luminance
      Y_b = 20.0  # Background relative luminance

      # Convert XYZ to CIECAM02 JCh
      JCh = colour.XYZ_to_CIECAM02(
         xyz_adapted,
         XYZ_w=target_wp,
         L_A=L_A,
         Y_b=Y_b,
         surround=viewing_conditions
      )

      # Extract chroma (C) and compute colorfulness (M)
      C = JCh.C  # Chroma
      M = C * (fl ** 0.25)  # Final Colorfulness calculation

      return M / 100.

   def rgb_to_hsl(self, rgb):
      self._validate_rgb(rgb)
      """Convert RGB (0-255) to HSL (Hue 0-360, Saturation 0-100, Lightness 0-100)."""
      r, g, b = rgb
      h, l, s = colorsys.rgb_to_hls(r, g, b)
      return (h, s, l)

   def hsl_to_rgb(self, hsl):
      """Convert HSL (Hue 0-360, Saturation 0-100, Lightness 0-100) to RGB (0-255)."""
      self._validate_hsl(hsl)
      h, s, l = hsl
      r, g, b = colorsys.hls_to_rgb(h, l, s)
      return r, g, b

   def set_colorfulness(self, rgb, wanted_cfn, step_size=0.5, max_iterations=120):
      """
      Adjust saturation of an RGB color to match a target colorfulness.
      - `rgb`: Input RGB color (0-1 range).
      - `wanted_cfn`: Target colorfulness (0-1 range).
      - `step_size`: Amount to adjust per step.
      - `max_iterations`: Maximum number of attempts to prevent infinite loops.
      Returns: RGB (0-1 range) with adjusted colorfulness.
      """
      self._validate_rgb(rgb)
      print(f"rgb = {rgb}")
      hsl = self.rgb_to_hsl(rgb)
      h, s, l = hsl
      self._validate_hsl(hsl)
      print(f"hsl = {hsl}")
      new_rgb = self.hsl_to_rgb(hsl)
      print(f"new_rgb = {new_rgb}")
      current_cfn = self.colorfulness(new_rgb)
      # prev_cfn tracking removed - was unused
      iteration = 0
      print(f"wanted colorfulness = {wanted_cfn:.2f}")
      while iteration < max_iterations:
         # Check if colorfulness is actually changing
         diff = (wanted_cfn - current_cfn)
         if abs(diff) < 0.005:
            break
         print(f"iteraton = {iteration+1}")
         print(f".. diff = {diff:.4f}")
         print(f".. colorfulness = {current_cfn:.2f}")
         print(f".. saturaturation = {s:4f}")
         # prev_cfn tracking removed - was unused
         # Adjust saturation while ensuring it stays within [0,1]
         new_s = s + step_size * diff
         if not (0 <= new_s <= 1):
            break
         s = new_s  # Update saturation
         # Convert back to RGB
         new_hsl = (hsl[0], new_s, hsl[2])
         self._validate_hsl(new_hsl)
         print(f"new_hsl = {new_hsl}")
         new_rgb = self.hsl_to_rgb(new_hsl)
         self._validate_rgb(new_rgb)
         current_cfn = self.colorfulness(new_rgb)
         s = new_s
         iteration += 1

      if iteration >= max_iterations:
         print(f"Max iterations reached. Final colorfulness: {current_cfn:.3f}, Wanted: {wanted_cfn:.3f}")

      # TODO: this function is incomplete - returns original HSL, not adjusted values
      return self.hsl_to_rgb(h, s, l)

   def set_perceived_brightness(self, rgb, wanted_pbr, step_size=0.001, max_iterations=100):
      """
      Adjust lightness of an RGB color to match a target perceived brightness.
      - Starts from the current lightness and increases or decreases it iteratively.
      """
      hsl = self.rgb_to_hsl(rgb)
      h, s, l = hsl
      current_pbr = self.perceived_brightness(rgb)
      max_iterations = 10
      iteration = 0

      # TODO: this function is incomplete - l is updated but hsl is not rebuilt
      while abs(current_pbr - wanted_pbr) > 0.02 and iteration < max_iterations:
         print(f"{current_pbr} - {wanted_pbr}")
         l = max(0, min(1, l + step_size * (wanted_pbr - current_pbr)))  # Keep within [0,1]
         hsl = (h, s, l)
         new_rgb = self.hsl_to_rgb(hsl)
         current_pbr = self.perceived_brightness(new_rgb)
         iteration += 1

      if iteration >= max_iterations:
         print(f"Max iterations reached. Final colorfulness: {current_pbr:.3f}, Wanted: {wanted_pbr:.3f}")

      return self.hsl_to_rgb(hsl)

def hue_to_rgb(hue_deg, rcp, target_cfn=0.20, target_pbr=0.75):
   """
   Convert a hue in degrees to an RGB color and adjust for colorfulness and perceived brightness.

   - `hue_deg`: Hue in degrees (0-360)
   - `rcp`: An instance of RCPColorUtils
   - `target_cfn`: Target colorfulness (default 80)
   - `target_pbr`: Target perceived brightness (default 60)

   Returns an adjusted RGB color in (0-255) format.
   """
   h = hue_deg / 360.0  # Convert hue to [0,1] range for colorsys
   r, g, b = colorsys.hls_to_rgb(h, 0.5, 1)  # Generate base color with full saturation, mid-lightness
   rgb = (r, g, b)  # Keep in 0-1 range

   # Adjust colorfulness
   adjusted_rgb = rcp.set_colorfulness(rgb, target_cfn)

   # Adjust perceived brightness
   final_rgb = rcp.set_perceived_brightness(adjusted_rgb, target_pbr)

   return final_rgb

def generate_color_circle(hue_function, rcp, title, num_colors=12):
   """Generate and display a color wheel based on a given hue conversion function."""
   fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
   angles = np.linspace(0, 2 * np.pi, num_colors, endpoint=False)

   for i, angle in enumerate(angles):
      hue_deg = i * (360 / num_colors)
      converted_hue = hue_function(hue_deg)
      color = hue_to_rgb(converted_hue, rcp)
      ax.bar(angle, 1, width=2*np.pi/num_colors, color=np.array(color) / 255, edgecolor="black", linewidth=0.1)
   ax.set_xticks([])
   ax.set_yticks([])
   ax.set_frame_on(False)
   ax.set_title(title)
   plt.show()

if __name__ == '__main__':
   # Instantiate RCPColorUtils
   rcp = RCPColorUtils()

   # Generate and display RGB color circle
   generate_color_circle(lambda h: h, rcp, "RGB Color Circle")

   # Generate and display RYB color circle
   generate_color_circle(rcp.ryb_to_rgb_hue, rcp, "RYB Color Circle")

def test_colorfulness(rcp):
    test_colors = {
        "Black": (0, 0, 0),
        "White": (1, 1, 1),
        "Gray": (0.5, 0.5, 0.5),
        "Red": (1, 0, 0),
        "Green": (0, 1, 0),
        "Blue": (0, 0, 1),
        "Yellow": (1, 1, 0),
        "Cyan": (0, 1, 1),
        "Magenta": (1, 0, 1),
        "Orange": (1, 0.5, 0),
        "Purple": (0.5, 0, 1)
    }

    print("\n== Testing Colorfulness Computation ==\n")
    for name, rgb in test_colors.items():
        cfn = rcp.colorfulness(rgb)
        print(f"{name:<10}: {cfn:.2f}")

# Run the test
if __name__ == "__main__x":
    rcp = RCPColorUtils()
    test_colorfulness(rcp)

