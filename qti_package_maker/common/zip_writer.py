"""
Shared ZIP builder for every packaging engine.

The four ZIP-producing engines (Canvas QTI 1.2, Blackboard QTI 2.1, Blackboard
Ultra QTI 2.1, Blackboard pool export) each used to hand-roll the same
os.walk + zipfile + relpath loop, plus a bespoke empty-directory workaround.
This module owns that logic in one place so every engine assembles archives the
same deterministic way.

The core contract is a mapping from archive path to content:

	archive_map: dict[str, bytes | str]
		key   -- the path the entry takes inside the ZIP (POSIX, forward slashes)
		value -- either raw bytes (in-memory payload, e.g. a rendered image) OR a
		         string source path to an existing file on disk to copy in

	empty_dirs: list[str] | None
		explicit zero-byte directory markers (e.g. "csfiles/") that some LMS
		importers require; ZIP has no implicit empty-directory concept, so these
		are written as their own entries

Entries are written in sorted order so the archive layout is deterministic and
does not depend on filesystem walk order.
"""

# Standard Library
import os
import zipfile

# Pip3 Library

# QTI Package Maker
# none needed here


#============================================
def collect_directory(source_dir: str) -> dict:
	"""
	Build an archive map from every file under a directory tree.

	Walks source_dir and maps each file's path-relative-to-source_dir (the arcname
	it will take inside the ZIP) to its absolute source path on disk. Empty
	directories are not included; pass those to build_zip via empty_dirs.

	Args:
		source_dir: directory whose files become archive entries.

	Returns:
		dict mapping archive path -> absolute source file path.
	"""
	archive_map = {}
	# walk the tree; only files become archive entries (dirs carry no bytes)
	for root, _dirs, files in os.walk(source_dir):
		for file_name in files:
			full_path = os.path.join(root, file_name)
			# arcname is the path relative to the collected root, matching legacy behavior
			archive_path = os.path.relpath(full_path, source_dir)
			archive_map[archive_path] = full_path
	return archive_map


#============================================
def build_zip(zip_path: str, archive_map: dict, empty_dirs: list | None = None) -> str:
	"""
	Write a ZIP file from an archive map plus optional explicit empty directories.

	Each archive_map value is either raw bytes (written directly) or a string
	source path (copied from disk). Entries are emitted in sorted archive-path
	order for deterministic output. Empty-directory markers are appended as
	zero-byte entries, skipping any that already exist as a file entry.

	Args:
		zip_path: output path for the ZIP file.
		archive_map: mapping of archive path -> bytes payload or source file path.
		empty_dirs: directory-marker entries (e.g. "csfiles/") to add as zero-byte
			entries; None means no explicit empty directories.

	Returns:
		The zip_path that was written.

	Raises:
		TypeError: an archive_map value is neither bytes nor a source path string.
	"""
	with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
		# deterministic layout: write file entries in sorted archive-path order
		for archive_path in sorted(archive_map):
			value = archive_map[archive_path]
			# bytes payload is written directly into the archive
			if isinstance(value, (bytes, bytearray)):
				zip_file.writestr(archive_path, bytes(value))
			# a string value is a source path on disk to copy in under archive_path
			elif isinstance(value, str):
				zip_file.write(value, archive_path)
			else:
				raise TypeError(
					f"archive_map['{archive_path}'] must be bytes or a source path str, "
					f"got {type(value).__name__}"
				)
		# ZIP has no implicit empty directories; add each marker as a zero-byte entry
		if empty_dirs:
			for empty_dir in sorted(empty_dirs):
				# do not shadow a real file entry already written above
				if empty_dir not in archive_map:
					zip_file.writestr(empty_dir, "")
	return zip_path
