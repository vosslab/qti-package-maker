# HTML to image

Convert all HTML tables (and, when present, RDKit
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
install` or `devel/setup_playwright.sh` (removed). `TableRenderer` starts one
browser lazily on the first uncached table render, then reuses one page with
the bundled font CSS loaded once. Canvas-only and fully cached conversions
start no browser. The MathML helper uses the same lazy page.

CLI evidence: `source source_me.sh && python3 tests/e2e/e2e_html_to_image.py`.

Table screenshots use the bundled Atkinson Hyperlegible Next variable font for
regular text and Atkinson Hyperlegible Mono for table text that requests the
generic `monospace` family. The SIL Open Font License files ship with both
fonts. If a font file cannot be read, Chromium uses its generic `sans-serif`
or `monospace` fallback. This only changes rasterized table images; the
`--html-to-image` flag remains off by default.

## RDKit (canvases only)

RDKit is an extra, listed in [pip_extras.txt](../pip_extras.txt). Table-only
banks never import it. If an item contains an RDKit `<canvas>` plus a following
script with `RDKitModule`, convert loads RDKit then. Missing RDKit raises
`ImportError` at that point:

```sh
pip install rdkit
```

or `pip install qti-package-maker[rdkit]` when using the package extras.

The offline renderer reads the literal SMILES, canvas dimensions, legend,
`explicitMethyl`, atom and bond highlight arrays, and RGB highlight colour. It
also recognizes the `getPeptideBonds(mol)` helper emitted by `aminoacidlib`.
The parser accepts the current static bptools form: a literal SMILES, an empty
`mdetails` object, and literal option assignments. It never evaluates item
JavaScript or loads the CDN. Canvas dimensions are limited to 4096 pixels per
side; SMILES strings are limited to 4096 characters.
An unmatched canvas, a dynamic option, or an unsupported drawing option raises
an error instead of producing an empty or incomplete figure. The recognized
CDN loader and consumed drawing scripts are removed when the field is converted.

Canvases inside tables are rendered first and embedded as PNGs in the table
renderer input. The outermost table is then captured once, including its nested
tables and molecule images. These intermediate canvas PNGs are not packaged
separately; standalone canvases remain separate packaged images.

Each `QTIPackageInterface` shares a renderer- and content-keyed PNG cache across items and
output engines for its entire lifetime, including later `save_package` calls.
A three-format CLI run renders each distinct prepared table
and canvas once, while each package retains its existing image filenames and
owns its media directory. Direct engine callers may pass `html_to_image_cache`
to share a cache; direct `convert_bank` callers may pass `cache`. Omitted caches
remain local to one conversion. Changing a custom renderer callback uses separate
cached images; reusing the same callback object reuses its images. See
[ENGINES.md](ENGINES.md) for options and callback configuration. Shipped selectors parse each HTML field once and
replace canvases and tables on that tree; custom string finder callbacks remain
supported.

## MathML renderer helper

`TableRenderer.render_mathml_png()` is a small rendering helper used by
exam-formatting-tools when importing biochemistry questions. It accepts the
current Henderson-Hasselbalch generator's MathML elements, expands legacy
`mfenced` parentheses, and rejects unknown tags, attributes, or expression
shapes. It renders only the validated MathML fragment; it does not execute
item scripts or load external resources. This helper does not change the
`--html-to-image` package conversion path or its default behavior.

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

With `--html-to-image` (biology generators: `-I`), every HTML table becomes an
image, including unstyled data tables and labels. Nested tables are captured
inside their outer table's image. See
[USAGE.md](USAGE.md), [COOKBOOK.md](COOKBOOK.md), and
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).
