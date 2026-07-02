# Color Wheel Refactor Plan

## Goals
- Model color appearance using a true human vision model.
- Produce visually balanced color sets across multiple lightness categories.
- Eliminate perpetual hue specific tweaks and ad hoc corrections.
- Preserve randomness and current performance characteristics.
- Keep API shape stable, with CAM16 opt-in until the default is intentionally flipped.

## Constraints
- No deterministic seeding for regular use.
- No heavy validation or slow paths.
- Primary test remains visual inspection via `write_html_color_table`.
- Consistency and saturation are defined per wheel mode.
- sRGB is the final output gamut and a hard physical limit.

## Core Decision
Replace OKLCH based sampling with a color appearance model.
Adopt CAM16 with fixed viewing conditions.

This shifts the system from geometric color spacing to perceptual appearance control.

## Conceptual Model
Work in CAM16 appearance correlates, not abstract chroma.

Primary parameters:
- J: perceived lightness
- M: perceived colorfulness
- h: hue angle
Optional limiter:
- Q: perceived brightness

All constraints are expressed in J and M.

## Wheel Modes
Supported modes (current scope):
- very_dark
- dark
- light
- xlight

## Lightness Targets (J, starting points)
Tune visually.
- very_dark: J 25
- dark:      J 40
- light:     J 75
- xlight:    J 88 to 90

## Colorfulness Policy
Each mode defines:
- M_min
- M_max
- shared_M_quantile

Dark modes allow higher M and more variation.
Light modes constrain M tightly to avoid dominance.

## Viewing Conditions
Use fixed CAM16 viewing conditions.
- Surround: average
- White point: D65
- Adapting luminance: fixed constant (documented value)

## Dependencies (chosen)
- `colour-science` (CAM16 support; long-term maintenance and broad usage).

Keep the adapter thin so we can swap later if needed.

## Core Algorithm
1) Fix CAM16 viewing conditions once.
2) Choose N hues, equally spaced in hue angle.
3) Apply one hue layout strategy per run:
   - anchored red OR
   - global random offset OR
   - optimized offset
4) For each hue at target J:
   - Find max M that converts to valid sRGB (bisection search + cache).
5) Choose shared M using a low quantile of per hue maxima.
6) Assign per hue M within the allowed band.
7) Clamp by max M and optional brightness Q limit.
8) Convert CAM16 -> XYZ -> sRGB hex.

No hue specific logic.

## Gamut Handling
- Gamut fitting is required, not validation.
- Per hue max M is found by search.
- Shared M uses a low quantile, not minimum.
- Final clamp prevents dominance without dulling the wheel.

## WheelSpec (Appearance Policy)
Define one spec per mode.

Each spec contains:
- target_J
- M_min
- M_max
- shared_M_quantile
- allow_M_variation (small, mode dependent)
- brightness_Q_cap (optional)

All mechanics are shared.

## Visual Test Plan
- Use `write_html_color_table` with CAM16 output.
- Compare across modes and repeated random runs.
- Tune J and M bands only, avoid logic changes.

## Rollout Steps
1) Choose CAM16 dependency and define viewing conditions.
2) Implement CAM16 conversion and inverse path.
3) Implement per hue max M search with caching.
4) Keep CAM16 opt-in behind an explicit backend switch.
5) Tune J and M ranges by eye.
6) Flip CAM16 to default when stable; keep legacy explicitly available.

## Remaining Items
- Decide when to flip CAM16 to default and update legacy naming/API accordingly.
- Add a brightness Q cap path (optional) and tune if dominance appears in light modes.
- Keep J/M/Q range tests in place and adjust tolerances as the ranges evolve.
- Tighten up docs (README/tables) once the default flips.

## Working History (Challenges + Attempts)
- Initial OKLCH sampling with per-hue max chroma looked inconsistent; some hues were far more vivid
  than others due to sRGB gamut limits.
- Switched to shared chroma (minimum of per-hue maxima) to enforce evenness; this made the wheel
  consistent but noticeably dull.
- Anchored hue 1 to sRGB red by computing its OKLCH hue to avoid red drifting magenta.
- Added hue-offset optimization (maximize shared chroma) to improve overall saturation while keeping
  evenness; still observed muted saturation in some bands.
- Introduced a blend between uniform chroma and per-hue max chroma to increase saturation while
  retaining most of the evenness; added a gamma curve to suppress over-dominant hues (notably yellow).
- Added hue-specific balancing around yellow: boost dark yellows to prevent muddiness and damp
  light yellows so they do not overpower the rest of the palette.
- Adjusted lightness targets: added `very_dark`, lightened `dark`, kept `extra_light`, and raised `light`
  for a more luminous palette.
- Identified over-constraint tensions (uniform vs punch, anchor vs offset, min chroma rule) and
  planned a per-wheel policy split plus quantile shared chroma to improve stability.
- Proposed moving from OKLCH to CAM16 to constrain appearance in J/M/Q terms and avoid
  hue-specific hacks.

## Non-Goals
- No deterministic seeding in normal usage.
- No heavy input validation or strict automated pass/fail checks.
- No removal of print/debug statements.
