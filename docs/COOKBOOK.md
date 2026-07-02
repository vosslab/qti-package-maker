# Cookbook

Multi-step recipes that go beyond the single-command usage in
[USAGE.md](USAGE.md). The command-line tool `tools/bbq_converter.py` only reads
BBQ text input, so any recipe that reads a different format, converts between
formats, or handles images uses the Python interface in
`qti_package_maker/package_interface.py`.

Load the repo environment first so imports resolve without an install:

```sh
source source_me.sh
```

## The Python interface in one minute

`QTIPackageInterface` holds one `ItemBank` and moves items between formats:

- `read_package(input_file, engine_name)` reads a file with a reader engine and
  merges its items into the bank.
- `add_item(item_type, item_tuple)` adds a single item directly.
- `save_package(engine_name, outfile=None)` writes the bank with a writer
  engine and returns the output path.

Which engines can read and which can write is listed in
[ENGINES.md](ENGINES.md). Reader engines include `blackboard_export_zip`,
`bbq_text_upload`, `okla_chrst_bqgen`, and `text2qti`.

## Convert a Blackboard pool export into other formats

The command-line tool cannot read a Blackboard pool export ZIP, but the
`blackboard_export_zip` engine can. Read the export, then write any format you
like. Real exports usually mix question types, so pass `allow_mixed=True`:

```python
from qti_package_maker import package_interface

packer = package_interface.QTIPackageInterface(
	"my_pool", verbose=True, allow_mixed=True)

# read a Blackboard Learn (Original) pool export ZIP
packer.read_package("blackboard_learn_classic-bb_export.zip", "blackboard_export_zip")

# write a human-readable review copy and a Canvas import package
packer.save_package("human_readable", "my_pool_review.txt")
packer.save_package("canvas_qti_v1_2", "my_pool_canvas.zip")
```

The reader skips question types it does not understand (for example Ordering or
Hot Spot from a Blackboard export) and prints a warning naming each skipped
item, so the item count you write may be smaller than the source pool.

## Pick a target engine that covers your item types

Writer engines handle unsupported item types in one of two ways, and the
difference matters when you convert a mixed bank:

- Most writers return `None` for an unsupported type, so the item is silently
  skipped (for example Canvas QTI v1.2 skips fill-in-the-blank).
- Some writers raise `NotImplementedError` instead. `text2qti` raises on
  `MATCH`, `MULTI_FIB`, and `ORDER`, so converting a bank that contains any of
  those to `text2qti` stops with an error rather than skipping.

Two safe strategies:

- Convert to an engine that covers every type in your source. `human_readable`
  supports all item types and is a good review target.
- Or trim the bank to the types your target supports before writing. Inspect
  what you have first:

```python
packer.summarize_item_bank()
print(packer.get_available_item_types())
```

The full support matrix is the "Assessment item types" table in
[ENGINES.md](ENGINES.md).

## Embed a self-test quiz in an MkDocs site

The `html_selftest` engine writes a single self-contained HTML file with any
referenced images inlined as base64 `data:` URIs, so the file has zero external
references. That makes it safe to drop into an
[mkdocs-material](https://squidfunk.github.io/mkdocs-material/) site at any
navigation depth, because there are no relative asset paths to break.

Generate the self-test:

```python
from qti_package_maker import package_interface

packer = package_interface.QTIPackageInterface("chapter1", verbose=True)
packer.read_package("bbq-chapter1-questions.txt", "bbq_text_upload")
packer.save_package("html_selftest", "docs/quizzes/chapter1_selftest.html")
```

Then include it from a Markdown page with the
`mkdocs-include-markdown-plugin`, or link to it directly from the nav. Because
the HTML is self-contained, no `extra_css` or asset wiring is required.

## Author questions with images

Item content keeps the author's plain `<img src="images/foo.jpg" alt="...">`;
there is no special asset scheme to learn. What happens to a referenced image
on export depends on the engine's `media_policy`:

- Packaging engines (`canvas_qti_v1_2`, `blackboard_qti_v2_1`,
  `blackboard_export_zip`, `html_selftest`) copy the image bytes into the
  output.
- Reference engines (`text2qti`, `bbq_text_upload`, `exam_yaml`,
  `human_readable`) keep a reference and warn you to supply the file.
- Placeholder engines (`moodle_aiken`, `okla_chrst_bqgen`) replace each
  `<img>` with a readable `[image: name.ext]` placeholder and warn.

Local `<img src>` paths resolve against the bank's media base directory. When
you build a bank in Python and reference local images, point the bank at the
folder that holds them:

```python
packer.item_bank.set_media_base_dir("path/to/image/folder")
```

PNG, JPEG, and GIF are first-class raster types. SVG is packaged but warned;
other extensions raise. External URLs and data URIs are never bundled by a
packaging engine. The per-engine behavior table and the full policy contract
are in [ENGINES.md](ENGINES.md) and [ENGINE_AUTHORING.md](ENGINE_AUTHORING.md).

## References

- [USAGE.md](USAGE.md) command-line usage and flags
- [ENGINES.md](ENGINES.md) engine capabilities and media behavior
- [FORMATS.md](FORMATS.md) BBQ input format
- [DEVELOPMENT.md](DEVELOPMENT.md) setup, tests, and adding an engine
