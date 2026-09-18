# Usage

qti_package_maker converts Blackboard Question Upload (BBQ) text files into QTI
packages and other exports. Use it two ways: the installed `bbq_converter.py`
command (the source checkout is [tools/bbq_converter.py](../tools/bbq_converter.py)),
or the `package_interface.QTIPackageInterface` library API. Both drive the same
engines, so any format in [docs/ENGINES.md](ENGINES.md) is reachable from either path.

## Quick start (command line)

Install the package, create a small BBQ input file, then convert it. Input files
must match the `bbq-<name>-questions.txt` naming pattern; `<name>` becomes the
content name used in the output filenames.

```sh
python3 -m pip install qti-package-maker
printf 'MC\tWhat color is a clear sky?\tblue\tcorrect\tgreen\tincorrect\n' > bbq-demo-questions.txt
bbq_converter.py -i bbq-demo-questions.txt -1 -r -s
```

That writes three files into the current directory: `qti12-demo.zip` (Canvas QTI
v1.2), `human-demo.html` (readable review), and `selftest-demo.html` (self-contained
quiz). Fields in the BBQ line are tab-delimited; see [docs/FORMATS.md](FORMATS.md).

## Quick start (library API)

```python
from qti_package_maker import package_interface

qti_packer = package_interface.QTIPackageInterface("bio101", allow_mixed=True)
qti_packer.add_item("MC", ("What color is a clear sky?", ["blue", "green", "red"], "blue"))
qti_packer.add_item("MA", ("Which are primes?", ["2", "3", "4", "6"], ["2", "3"]))
qti_packer.save_package("canvas_qti_v1_2", "bio101.zip")
```

`add_item` takes an item type and a tuple; mixing item types in one bank needs
`allow_mixed=True`. To convert an existing BBQ file instead of building items by
hand, call `qti_packer.read_package("bbq-demo-questions.txt", "bbq_text")` before
`save_package`. For Blackboard table-cell drawings, pass
`engine_options={"html_to_image": True}` to `save_package` on
`blackboard_qti_v2_1` or `blackboard_export_zip`.

## CLI

```sh
bbq_converter.py -h
```

- `-i`, `--input`: path to the BBQ text file (required).
- `-o`, `--output`: output filename; works only with a single format.
- `-n`, `--limit`: limit the number of input items (random subset).
- `-f`, `--format`: pick one or more output engines (repeatable).
- `-a`, `--all`: enable all CLI output formats.
- `--allow-mixed`: allow mixed question types in one run.
- `--html-to-image`: convert table-cell drawings and RDKit canvases to PNGs
  before packaging (off by default; `blackboard_qti_v2_1` and
  `blackboard_export_zip` only).
- `-q`, `--quiet` / `-v`, `--verbose`: control logging (verbose by default).

Format shortcuts: `-1` Canvas QTI v1.2, `-2` Blackboard QTI 2.1, `-r`
human-readable, `-b` BBQ text upload, `-s` HTML self-test, `-A` Moodle Aiken,
`-B` Blackboard pool export ZIP. `--html-to-image` is applied only to `-2` and
`-B`; other selected formats in the same run are written without conversion.
The `exam_yaml`, `okla_chrst_bqgen`, and `text2qti` engines are reachable only
through the library API and `save_package(engine_name)`.
## Images

BBQ questions may embed a relative image reference such as
`<img src="images/figure.png" alt="..."/>`. How each engine handles that image
depends on its media policy:

- Packaging engines (`canvas_qti_v1_2`, `blackboard_qti_v2_1`,
  `blackboard_export_zip`) copy the image bytes into the output ZIP and rewrite
  the reference so the image travels with the package.
- `html_selftest` inlines each image as a base64 `data:` URI, so the single HTML
  file has no external references.
- Reference and placeholder engines keep a warned `<img>` reference or substitute
  `[image: name.ext]` text.

See the per-engine media table in [docs/ENGINES.md](ENGINES.md) for exact behavior.

Table-cell drawings and RDKit JavaScript canvases lose their meaning in
Blackboard Ultra, which strips presentational attributes and does not run
item JavaScript. Pass `--html-to-image` (or `html_to_image=True` on
`blackboard_qti_v2_1` / `blackboard_export_zip`) to replace those fragments
with packaged PNGs. The flag is off by default; without it, packaged item HTML
is the input HTML.

## Examples

```sh
bbq_converter.py -i bbq-demo-questions.txt -f canvas_qti_v1_2 -f human_readable
```

```sh
bbq_converter.py -i bbq-demo-questions.txt -o my_quiz.zip -1
```

```sh
python3 -m qti_package_maker.engines.engine_registration
```

The last command prints the engine table with read/write and media-policy columns.

## Media LMS probe kits

The `devel/build_*_probe.py` scripts build small image-import probe ZIPs for
manual LMS testing (Canvas gate A, Blackboard Original gate B, Blackboard Ultra
gate D). Each defaults to writing under `output_probes/<name>/`; pass `-o` to
choose another directory.

```sh
python3 devel/build_canvas_media_probe.py -o output_probes/canvas
```

See [docs/MEDIA_LMS_PROBES.md](MEDIA_LMS_PROBES.md) for import steps and the
results table.

## Inputs and outputs

- Inputs: tab-delimited BBQ text files named `bbq-<name>-questions.txt`; see
  [docs/FORMATS.md](FORMATS.md).
- Outputs: engine-specific artifacts written to the current working directory,
  named by content name (for example `qti12-<name>.zip`); see
  [docs/ENGINES.md](ENGINES.md).

## Known gaps

- Confirm whether any non-BBQ input formats are supported by the CLI beyond BBQ text.
- Verify output-filename prefixes for every engine against the current writers.
