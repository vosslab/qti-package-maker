# Troubleshooting

Symptom, cause, and fix for the errors a new user hits most. Image-related
errors come from the shared media layer in
`qti_package_maker/common/media_assets.py`.

## Install or import errors
- Ensure dependencies are installed: `pip install -r pip_requirements.txt`.
- If running scripts directly, use `source source_me.sh` to set `PYTHONPATH`.
- If engine discovery fails, verify the package is importable:
  `python3 -m qti_package_maker.engines.engine_registration`.

## BBQ parse issues
- BBQ files must be tab-delimited, have no header row, and contain one question per
  line.
- Blank lines or embedded newlines in questions will cause parsing errors.
- Use `--allow-mixed` (CLI) or `allow_mixed=True` (API) for mixed question types.

## Empty output or missing items
- If an output is empty, confirm the input file was read and yielded items.
- Try a small sample file and increase `--limit` to isolate a bad row.

## HTML tables in question text
- Tables are converted to plain text when possible.
- If you see `[TABLE]`, the HTML may be malformed; verify `<table>` tags are
  well-formed.

## HTML self-test styling
- The HTML self-test output uses inline styles and helper functions in
  `qti_package_maker/engines/html_selftest/html_functions.py`.
- For styling changes (including dark mode), update those helpers and regenerate output.

## Image file not found
- Symptom: `FileNotFoundError: image file not found for src '...'` naming the
  resolved path.
- Cause: an `<img src>` points at a local file that is missing under the bank's
  media base directory.
- Fix: place the file at the resolved path shown in the message, or correct the
  `src` to match the real filename.

## Image path escapes the base directory
- Symptom: `ValueError: path '...' escapes the base directory '...'`.
- Cause: an `<img src>` uses `../` (or an absolute path) that resolves outside
  the media base directory; traversal is rejected before any file read.
- Fix: keep image files inside the base directory and reference them with a
  relative path such as `images/foo.png`.

## Unsupported image extension
- Symptom: `ValueError: unsupported image type '.webp' for '...'`.
- Cause: only PNG, JPG, JPEG, and GIF are first-class; SVG is packaged with a
  warning; every other extension (for example `.webp`) fails loudly.
- Fix: convert the image to PNG, JPG, or GIF, then update the `<img src>`.

## Local image with no media base directory
- Symptom: `ValueError: cannot resolve local image '...' without a base
  directory`.
- Cause: a bank built programmatically references a local `<img src>` but never
  had its `media_base_dir` set, so there is nowhere to resolve the file from.
- Fix: set the base directory before packaging, for example
  `bank.media_base_dir = "/path/to/images"`, or register bytes with
  `bank.add_image(src, data_bytes)` (which creates a base directory for you).

## Merging banks with different base directories
- Symptom: `ValueError: cannot merge ItemBanks with different media_base_dir
  values.` naming both directories.
- Cause: each bank resolves its own `<img src>` against its own base directory,
  and a single merged bank cannot serve two different directories.
- Fix: point both banks at the same `media_base_dir` before merging, or merge
  only banks that share one directory (same-dir and one-sided merges are silent).

## Data URI image into a packaging engine
- Symptom: `MediaPolicyError: engine '...' cannot package a data URI image; ...
  Supply a file-backed <img src> instead.`
- Cause: file-writing engines (Canvas QTI, Blackboard QTI, Blackboard export
  zip) need a real file to embed; an inline `data:` URI carries no file.
- Fix: save the embedded image to a file and reference it with a normal
  `<img src="images/foo.png">`.

## SVG and external-URL warnings
- Symptom: printed warnings that an SVG was bundled with uncertain LMS support,
  or that an external image URL was kept verbatim and not bundled.
- Cause: these are warn-only by design. SVG packages but its LMS import is not
  guaranteed; `http(s)://` and protocol-relative URLs are never downloaded.
- Fix: no action needed to produce output. To silence the warnings, convert SVG
  to a raster format and download external images to local files.

## Blackboard Ultra shows `[image: name.ext]`
- Symptom: exported Ultra items contain `[image: name.ext]` text instead of the
  image.
- Cause: this is expected, not a bug. The Ultra engine uses the placeholder
  policy and drops `<img>` tags; packaged images await the Ultra media probe.
- Fix: none needed. Use Canvas QTI or Blackboard export zip when you need the
  image bundled into the package.

## Cleaning up reader extraction directories
- Readers that unzip a package (for example Blackboard export zip) extract into
  their own temp directory and own it, so images resolve during writing.
- Call `bank.cleanup()` when finished with a bank returned by such a reader to
  remove that extraction directory; it is idempotent and a no-op for banks that
  did not create their own directory.
</content>
</invoke>
