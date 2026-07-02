# Engine authoring guide

This guide explains the required files, functions, and common patterns for adding a new
engine to `qti_package_maker`.

## What you are building

An engine is a format adapter that converts external files into internal assessment
items stored in an `ItemBank`, or exports those items back out to a format.

## Directory layout
- Create a new package under `qti_package_maker/engines/<engine_name>/`.
- Include at least `engine_class.py` and a writer module (usually `write_item.py`).
- Add `read_package.py` only if the engine can read.
- Add an empty `__init__.py` so the folder is importable.

| File | Required | When you need it | Typical contents |
| --- | --- | --- | --- |
| `engine_class.py` | Yes | Always | `EngineClass`, wiring, registration hooks |
| `write_item.py` | Usually | Any writer | per-item-type renderers |
| `read_package.py` | Only for readers | Any read and write engine | unpack, parse, build items |
| `__init__.py` | Yes | Always | package import, discovery |

Example layout:
```text
qti_package_maker/engines/<engine_name>/
	__init__.py
	engine_class.py
	write_item.py
	read_package.py
```

## Minimal working engine
Use this as a starting point for a write-only engine that supports `MC` and returns
`None` for other types.

Example `engine_class.py`:
```python
from qti_package_maker.engines import base_engine
from qti_package_maker.engines.<engine_name> import write_item


class EngineClass(base_engine.BaseEngine):
	def __init__(self, package_name: str, verbose: bool = False):
		super().__init__(package_name, verbose)
		self.write_item = write_item
		self.validate_write_item_module()

	def save_package(self, item_bank, outfile: str = None):
		item_bank.renumber_items()
		outfile = self.get_outfile_name("<engine_name>", "txt", outfile)
		assessment_items_tree = self.process_item_bank(item_bank)
		# write_item.MC must return a string for this example
		with open(outfile, "w") as f:
			for item_text in assessment_items_tree:
				f.write(item_text)
		return outfile
```

Example `write_item.py`:
```python
def MC(item_cls):
	return f"{item_cls.item_number}. {item_cls.question_text}\n"

def MA(item_cls):
	return None

def MATCH(item_cls):
	return None

def NUM(item_cls):
	return None

def FIB(item_cls):
	return None

def MULTI_FIB(item_cls):
	return None

def ORDER(item_cls):
	return None
```

Example input and output:
- Input: one `MC` item in the `ItemBank`
- Output: `get_outfile_name("<engine_name>", "txt")` creates `<engine_name>-<name>.txt`

## Read and write engine example
If the format supports reading, add `read_package.py` and implement a reader there.
Then call it from `EngineClass.read_items_from_file(...)`.
```python
from qti_package_maker.assessment_items import item_bank
from qti_package_maker.assessment_items import item_types

def read_items_from_file(input_file: str, allow_mixed: bool = False):
	new_bank = item_bank.ItemBank(allow_mixed)
	with open(input_file, "r") as f:
		for line in f:
			item_cls = read_MC(line)
			if item_cls:
				new_bank.add_item_cls(item_cls)
	return new_bank

def read_MC(line: str):
	question_text = line.strip()
	choices_list = ["A", "B"]
	answer_text = "A"
	return item_types.MC(question_text, choices_list, answer_text)
```

Example `engine_class.py` wrapper:
```python
def read_items_from_file(self, infile: str, allow_mixed: bool = False):
	return read_package.read_items_from_file(infile, allow_mixed=allow_mixed)
```

## Required functions

| Function | Required | Purpose | Inputs | Output | Common errors |
| --- | --- | --- | --- | --- | --- |
| `__init__` | Yes | load writer module, validate wiring | `package_name`, `verbose` | instance | wrong module path |
| `save_package` | Yes | write bundle or single file | `item_bank`, `outfile` | output path | wrong outfile name, non-determinism |
| `read_items_from_file` | No | read input and build ItemBank | `infile`, `allow_mixed` | `ItemBank` | mixed types rejected |

### engine_class.py
Implement `EngineClass` that subclasses `BaseEngine`. In this codebase, engines write
via `save_package()` and optionally read via `read_items_from_file()`.

Required methods:
- `__init__(self, package_name: str, verbose: bool = False)`
  - set `self.write_item` to your `write_item` module
  - call `self.validate_write_item_module()`
- `save_package(self, item_bank, outfile: str = None)`
  - render with `self.process_item_bank(item_bank)` (the single shared render
    loop); pass `item_transform_fn` / `post_render_fn` for media handling
    instead of re-implementing the loop (see "Media and image contract")
  - write outputs to a file (or ZIP) using `self.get_outfile_name(...)`
  - for bundle formats, write to a temp folder, zip the folder, then return the zip path
- `read_items_from_file(self, infile: str, allow_mixed: bool = False)`
  - only if the engine supports reading
  - call `read_package.read_items_from_file(...)` and return an `ItemBank`

The registry discovers engines by importing
`qti_package_maker.engines.<engine_name>.engine_class.EngineClass`.

### write_item.py
Write one function per supported item type. Common names:
- `MC`, `MA`, `MATCH`, `NUM`, `FIB`, `MULTI_FIB`, `ORDER`

Each function receives a fully validated item class and returns:
- a string (for text-based outputs), or
- an XML element (for QTI engines), or
- `None` if the type is unsupported for this engine.

Keep output stable and deterministic to avoid flaky tests.
Use `None` for unsupported types, and raise only when the type is supported but invalid.

### read_package.py
If your engine reads input, implement:
- `read_items_from_file(input_file: str, allow_mixed: bool = False) -> ItemBank`
- helper readers such as `read_MC`, `read_NUM`, etc.

Return an `ItemBank` and use `add_item_cls` to preserve CRCs and metadata.

## Registration and discovery
Engines are auto-registered by scanning `qti_package_maker/engines/`.
To be discoverable:
- the folder must be a package (`__init__.py`)
- it must contain `engine_class.py` with `EngineClass`
- the folder name is the engine name shown in tables

You do not need to edit `engine_registration.py`.

To verify discovery, run:
```sh
python3 -m qti_package_maker.engines.engine_registration
```

## Tips and conventions
- Use tabs for indentation in Python files. See [PYTHON_STYLE.md](PYTHON_STYLE.md).
- Keep lines around 100 characters.
- Use `BaseEngine.get_outfile_name(...)` to standardize output naming.
- Call `ItemBank.renumber_items()` before writing to keep item numbers stable.
- Reuse helpers from `qti_package_maker/common/` and existing engines.
- For HTML or XML outputs, keep formatting stable to simplify tests.
- When a format cannot support an item type, return `None` in the writer.
- Rule of thumb: keep format-specific parsing and rendering in the engine, and put
  shared helpers in `qti_package_maker/common/`.

## Media and image contract

Every engine declares a `media_policy` class attribute and routes referenced
images through the shared layer in `qti_package_maker/common/media_assets.py`.
Do not write a private image scanner, regex, or policy branch in an engine.
See the per-engine behavior table in [ENGINES.md](ENGINES.md).

### media_policy values

Set one of these four values on your `EngineClass` (the `BaseEngine` default is
`media_assets.POLICY_REFERENCE_WARN`):

| Value | Use when |
| --- | --- |
| `media_assets.POLICY_PACKAGE` | The format can carry image bytes (a ZIP, or HTML with inlined data URIs). |
| `media_assets.POLICY_REFERENCE_WARN` | The format keeps a working `<img>`/link reference the user supplies the file for. |
| `media_assets.POLICY_PLACEHOLDER_WARN` | The format has no image channel; substitute a readable `[image: name.ext]` placeholder. |
| `media_assets.POLICY_FAIL` | Any referenced image must raise `MediaPolicyError`. |

### Applying the policy

- Collect an item's images with `item_bank.collect_assets()`, then read the
  per-item list from `collected_assets.item_dependencies[item_cls.item_crc16]`.
- Call `media_assets.apply_media_policy(self.media_policy, item_assets,
  self.name, item_cls.item_crc16)` once per item. It returns a
  `MediaPolicyDecision` with a `warnings` list and a `placeholders` map, and it
  is the single warning channel: print each warning rather than emitting your
  own. The external, data-uri, and SVG cautions all come from here, so every
  engine surfaces them identically.
- Rewrite `<img src>` only on writer output, never on the bank's stored item.
  Use `media_assets.rewrite_item_media(item_cls, src_map_fn)` (deep-copies then
  rewrites) or `media_assets.rewrite_html_srcs(html, src_map_fn)` for a single
  string. A file-packaging engine that must reject data URIs calls
  `media_assets.raise_on_data_uri_assets(item_assets, self.name,
  item_cls.item_crc16)`.

### Injecting media into the shared render loop

`BaseEngine.process_item_bank` is the one render loop for every engine: it
iterates the bank, resolves each item's write function, warns and skips unknown
types, and drops `None` renders. Do not copy this loop into your engine to slip
in a media step. Instead pass one of its two optional hooks:

- `item_transform_fn(item_cls) -> item_cls` runs BEFORE the write function and
  returns the item to render (usually a rewritten deep copy). Use it for src
  rewrites (`media_assets.rewrite_item_media`) and clone-before-render
  placeholder or description substitution.
- `post_render_fn(item_cls, item_engine_data) -> item_engine_data` runs AFTER
  the write function on the rendered output, keyed on the ORIGINAL item. Use it
  only when the substitution must happen on already-rendered text (for example
  a plain-text format that has no image markup channel).

Build the hook with `functools.partial` to bind per-bank state (the collected
assets, an output `media/` dir, a copied-name set) and keep the hook a plain
`item_cls`- or output-keyed callable. `moodle_aiken` and `okla_chrst_bqgen` use
`post_render_fn`; `human_readable`, `canvas_qti_v1_2`, and
`blackboard_export_zip` use `item_transform_fn`. Engines that also collect side
data (Canvas's packaged assets) compute it in `save_package` around the loop, so
the transform stays a pure per-item function.

When you build a per-item `{in_content_src: writer_output_src}` map, wrap it with
`media_assets.make_src_map_fn(src_map)` rather than hand-rolling a lookup
closure; hand the result to `rewrite_item_media`.

### Two authoring traps

1. If your engine has a pretty-print or sanitize step that strips HTML tags,
   substitute placeholders on a cloned item BEFORE rendering, not after. A
   post-render substitution has nothing to match because the tags are already
   gone. Clone with `item_cls.copy()`, rewrite its HTML-bearing fields (use
   `get_supporting_field_names()` to find them), then render the clone; leave
   the bank's item untouched. The `human_readable` engine follows this
   clone-before-render pattern because its pretty-printer strips all tags.
2. Use the shared `media_assets.IMG_TAG_PATTERN` and
   `media_assets.SRC_ATTR_PATTERN` when you must match `<img>` or `src=` in
   text. Never copy a private regex: a bare `src` pattern also matches
   `data-src=`/`lazy-src=` and silently rewrites the wrong attribute.
   `SRC_ATTR_PATTERN` uses a negative lookbehind so only a real `src=`
   attribute matches.

## Item type mapping
Use these item fields when parsing or writing. Attribute names are illustrative; confirm
exact names in the item type classes.

| Item type | write_item.py function | Minimum required fields | Sample attributes |
| --- | --- | --- | --- |
| `MC` | `MC(item_cls)` | prompt, choices, correct | `item_cls.question_text`, `item_cls.choices_list`, `item_cls.answer_text` |
| `MA` | `MA(item_cls)` | prompt, choices, correct set | `item_cls.question_text`, `item_cls.choices_list`, `item_cls.answers_list` |
| `NUM` | `NUM(item_cls)` | prompt, answer, tolerance | `item_cls.question_text`, `item_cls.answer_float`, `item_cls.tolerance_float` |
| `FIB` | `FIB(item_cls)` | prompt, answers | `item_cls.question_text`, `item_cls.answers_list` |
| `MATCH` | `MATCH(item_cls)` | prompt, pairs | `item_cls.question_text`, `item_cls.prompts_list`, `item_cls.choices_list` |
| `MULTI_FIB` | `MULTI_FIB(item_cls)` | prompt, answer map | `item_cls.question_text`, `item_cls.answer_map` |
| `ORDER` | `ORDER(item_cls)` | prompt, sequence | `item_cls.question_text`, `item_cls.ordered_answers_list` |

## Output artifacts

| Output style | What `save_package()` writes | Typical formats | Gotcha |
| --- | --- | --- | --- |
| Single file | one file at outfile | text, HTML, XML | encoding and newline stability |
| Bundle | folder then zip | QTI packages | temp paths leaking into content |
| Multi-file, no zip | folder tree | dev or debug engines | test harness expecting zip |

## Testing checklist
- Add or update smoke tests in `tests/` (see `tests/test_all_engines.py`).
- For writer-only engines, add output checks in `tests/integration/test_engine_outputs.py`.
- If reading is supported, add roundtrip tests in `tests/integration/test_reader_roundtrip.py`.
- Update capability tables in [README.md](../README.md).
- Document changes in [CHANGELOG.md](CHANGELOG.md).

Target notes:
- `tests/test_all_engines.py` is the fast smoke test across all engines.
- `tests/integration/test_engine_outputs.py` checks structural validity of outputs.
- `tests/integration/test_reader_roundtrip.py` checks read then write roundtrips.

## Package cross-reference integrity

A new packaging engine's output should pass the shared cross-reference
integrity check in `qti_package_maker/common/package_integrity.py`. Structure
and roundtrip tests do not catch a schema-plausible package with dangling
identifiers (for example a `correctResponse` id that no choice declares, a
manifest dependency pointing at nothing, or a Blackboard export whose resource
link `parentId` names an item the pool never emitted). Call
`package_integrity.check_package(zip_or_dir)` on your saved package; an empty
return means clean. The check dispatches by package shape rather than engine
name, so add a parametrized case to
`tests/integration/test_package_cross_references.py` and assert no violations.

| Goal | Command | Notes |
| --- | --- | --- |
| Run all engine tests | `pytest -q tests/test_all_engines.py` | baseline smoke |
| Run only this engine | `pytest -q -k <engine_name>` | fastest loop |
| Debug a single case | `pytest -q -k <test_name> -vv` | show captured logs |
| Run roundtrip tests | `pytest -q -k roundtrip` | matches `tests/integration/test_reader_roundtrip.py` |

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Engine not discovered | missing `__init__.py` or wrong import path | add `__init__.py`, verify discovery command |
| Crash on write | forgot `validate_write_item_module()` | call validator early in `__init__` |
| Flaky tests | non-deterministic ordering or whitespace | sort items and stabilize output |
| Reader rejects file | mixed types but `allow_mixed` ignored | plumb `allow_mixed` through read path |
| CRC or metadata lost | not using `add_item_cls` | rebuild `ItemBank` with `add_item_cls` |

## References
- [DEVELOPMENT.md](DEVELOPMENT.md)
- `qti_package_maker/engines/template_class/`
