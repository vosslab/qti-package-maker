# HTML to image

Convert Blackboard Ultra-stripped table-cell drawings (and, when present, RDKit
JavaScript canvases) into packaged PNGs. This is the Playwright path for this
repository: the pip `playwright` package and Chromium, not npm.

## When to use it

Blackboard Ultra strips presentational table styles and does not run item
JavaScript. Gels, restriction maps, and agglutination wells become empty boxes
unless they are screenshots first. Pass `--html-to-image` on any ZIP packaging
engine: `-1` (`canvas_qti_v1_2`), `-2` (`blackboard_qti_v2_1`), or `-B`
(`blackboard_export_zip`). The flag is off by default.

## Playwright (tables)

Table conversion always uses pip Playwright. After `pip install -r
pip_requirements.txt`:

```sh
playwright install chromium
```

That downloads Chromium for the Python package. Do not use `npx playwright
install` or `devel/setup_playwright.sh` (removed). `TableRenderer` holds one
browser for a whole bank convert.

CLI evidence: `source source_me.sh && python3 tests/e2e/e2e_html_to_image.py`.

## RDKit (canvases only)

RDKit is an extra, listed in [pip_extras.txt](../pip_extras.txt). Table-only
banks never import it. If an item contains an RDKit `<canvas>` plus a following
script with `RDKitModule`, convert loads RDKit then. Missing RDKit raises
`ImportError` at that point:

```sh
pip install rdkit
```

or `pip install qti-package-maker[rdkit]` when using the package extras.

## Commands

```sh
bbq_converter.py -i bbq-demo-questions.txt -1 -2 -B --html-to-image
```

From Python:

```python
bank.save_package(
	"blackboard_export_zip",
	engine_options={"html_to_image": True},
)
```

Ordinary data tables and `padding: 0 2px` labels stay HTML. See
[USAGE.md](USAGE.md), [COOKBOOK.md](COOKBOOK.md), and
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).
