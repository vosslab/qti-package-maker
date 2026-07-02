# bb_export_slice.zip fixture

Trimmed, real-shape slice of a Blackboard Learn Classic "Original" course
export, kept as a committed durable fixture because its proprietary
multi-file layout (not any single value inside it) is the behavior under
test. Per the image-support plan's fixture policy, this is the only
committed durable artifact for the plan; everything else is built inline in
`tmp_path`. See `docs/active_plans/active/image_support_plan.md`, the
reader-capture image work and the write->read roundtrip integration coverage
(matrix row 9).

Stored as a single ZIP, `tests/fixtures/bb_export_slice.zip`, with
`imsmanifest.xml` at the ZIP root -- the same layout a real Blackboard
Original export ZIP has, and the shape the `blackboard_export_zip` reader's
real-world input takes. Consuming tests either pass the ZIP path directly to
`read_package.read_items_from_file()` / `package_integrity.check_package()`
(both accept a ZIP path), or open it with `zipfile.ZipFile` to read
individual entries.

## Source

`SAMPLES/blackboard_learn_classic-bb_export/` (untracked sample export,
2026-07-01), a real "MC test" / "HOTSPOT image" question pool exported from
Blackboard Learn Classic.

## Questions kept

Two items from the pool `res00002.dat`, selected because together they
exercise both confirmed image mechanisms:

- **"MC test"** (`bbmd_asi_object_id` = `_23221280_1`): a multiple-choice
  item whose question stem and all four choices each carry one embedded
  image. This is the typical multi-image csfiles case (5 images in one
  item).
- **"HOTSPOT image"** (`bbmd_asi_object_id` = `_23221297_1`): a hotspot item
  whose question stem carries one embedded csfiles image AND whose response
  area references a second image via `<matapplication>`. This item alone
  demonstrates both mechanisms together.

## Image mechanisms preserved

- **csfiles mechanism**: pool item HTML contains
  `src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-<n>_1"` tokens.
  Each token resolves to a binary at
  `csfiles/home_dir/__xid-<n>_1.jpg` plus an LOM sidecar
  `csfiles/home_dir/__xid-<n>_1.jpg.xml` (recovers the original filename,
  e.g. `image-1.jpg`), cross-referenced by a `res00005.dat`
  `<cms_resource_link>` entry whose `parentId` matches the item's
  `bbmd_asi_object_id` and whose `resourceId` matches the xid. The
  `imsmanifest.xml` does NOT declare these files (implicit bundling, as in
  the real export).
- **hotspot mechanism**: the "HOTSPOT image" item's response area wires a
  `<matapplication uri="1eee67ddd3bf4b03ae0a9d03c55cf48d/image-30.jpg">`
  element to the file at
  `res00002/1eee67ddd3bf4b03ae0a9d03c55cf48d/image-30.jpg`, which IS tracked
  in `imsmanifest.xml` as a bb-namespace `<file href="...">` child of the
  `res00002` resource.

xids referenced: 23446236 (question image), 23446237-23446240 (four choice
images) for "MC test"; 23446440 (question image) for "HOTSPOT image", plus
the hotspot file `image-30.jpg`.

## What was trimmed from the real export

- `res00002.dat` (pool): every `<item>` except "MC test" and "HOTSPOT image"
  was removed from `<section>`; the `<assessment>`/`<assessmentmetadata>`/
  `<rubric>`/`<presentation_material>`/`<sectionmetadata>` wrapper elements
  are kept verbatim from the source.
- `res00005.dat` (CSResourceLinks): kept only the 6 `<cms_resource_link>`
  entries whose `parentId` is `_23221280_1` or `_23221297_1` (28 -> 6
  entries). Re-serializing through lxml also flattened the original
  `<![CDATA[...]]>` text nodes to plain text; the recovered string values are
  unchanged, only the wire-level CDATA wrapping was lost.
- `imsmanifest.xml`: kept only the `res00002` and `res00005` `<resource>`
  entries (dropped `res00001` course settings, `res00003` assessment
  creation settings, `res00004` rubrics, `res00006` standards alignments,
  `res00007` rubric association -- none of which affect image capture).
  Root-level `.bb-log-info`, `.bb-package-info`, `.bb-package-sig` files were
  also dropped (package-level metadata, not read by the image mechanisms).
- Image binaries: every JPEG was recompressed and downsized (ImageMagick
  `-resize 80x80 -quality 60`) to keep the slice well under the size budget;
  each source photo was hundreds of KB, the shrunk versions are under 1.4 KB
  each. They remain valid JPEGs (verified with `file`); only the pixel
  content changed, not the mechanism (filenames, xids, tokens, and manifest
  wiring are all preserved exactly).
- LOM sidecar XML files (`__xid-<n>_1.jpg.xml`) are copied byte-for-byte
  from the source export, unmodified.

## Size

`bb_export_slice.zip` is 12K (`du -sh tests/fixtures/bb_export_slice.zip`),
down from 76K as a loose 18-file tree.
