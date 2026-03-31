#!/usr/bin/env python3

import os
import re
import argparse
import importlib.metadata

from qti_package_maker import package_interface

#=====================================================
def _check_version():
	repo_version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
	if not os.path.isfile(repo_version_file):
		return  # Not running from repo, skip check
	with open(repo_version_file, 'r') as f:
		repo_version = f.read().strip()
	try:
		installed_version = importlib.metadata.version("qti_package_maker")
	except importlib.metadata.PackageNotFoundError:
		return  # Not installed as a package, skip check
	# PEP 440 normalizes 26.03 to 26.3, so compare normalized forms
	from packaging.version import Version
	repo_normalized = str(Version(repo_version))
	installed_normalized = str(Version(installed_version))
	if repo_normalized != installed_normalized:
		print(f"VERSION MISMATCH: repo VERSION file says {repo_version}, "
			f"but imported qti_package_maker is {installed_version}")
		print("Run 'pip install -e .' from the repo root to sync.")
		raise SystemExit(1)

#=====================================================
def parse_args(format_shortcuts) -> argparse.Namespace:
	"""
	Parses command-line arguments.

	Returns:
		argparse.Namespace: Parsed command-line arguments.
	"""
	parser = argparse.ArgumentParser(description="Convert BBQ file to other formats.")
	parser.add_argument("-i", "--input", "--input_file", required=True,
			dest="input_file", help="Path to the input BBQ text file.")

	parser.add_argument("-o", "--output", "--output_file", required=False,
			dest="output_file", help="Path to the output file, only works with one output engine.")

	parser.add_argument("-n", "--limit", "--question_limit", type=int,
			dest="question_limit", help="Limit the number of input items.")

	verbose_group = parser.add_mutually_exclusive_group()
	verbose_group.add_argument("-q", "--quiet", dest="verbose", action="store_false", help="Disable verbose output")
	verbose_group.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Enable verbose output")
	verbose_group.set_defaults(verbose=True)

	# Boolean flag for allowing mixed question types
	parser.add_argument("--allow-mixed", dest="allow_mixed", help="Allow mixed question types",
			action="store_true", default=False)

	#============== Output Formats ==============

	# Generate the list of all formats from format_shortcuts
	# Extracts only format names
	all_formats = list(format_shortcuts.keys())

	# Allow multiple formats using --format with an explicit list
	parser.add_argument("-f", "--format", dest="output_format", type=str, action="append",
			choices=all_formats, help="Set output format (multiple allowed)")

	# Shortcut for selecting ALL formats
	parser.add_argument("-a", "--all", dest="all_formats", help="Enable all output formats",
			action="store_true")

	# Register format shortcut options
	for engine_name, (short_opt, short_name, desc_text) in format_shortcuts.items():
		parser.add_argument(short_opt, f"--{short_name}", f"--{engine_name}", dest="output_format",
				action="append_const", const=engine_name, help=desc_text)

	args = parser.parse_args()

	# If --all is set, override other selections and set all formats
	if args.all_formats:
		args.output_format = all_formats
	elif args.output_format:
		# Remove duplicates
		args.output_format = list(set(args.output_format))
	else:
		parser.error("At least one output format must be specified. Use -f, -a, or a shortcut.")

	if args.output_file and len(args.output_format) > 1:
		parser.error("The --output-file option can only be used with a single output format. "
			"Specify only one format with -f or remove -o.")

	return args

#=====================================================
def extract_core_name(bbq_file_name):
	# Regular expression to match the core part
	if '/' in bbq_file_name:
		bbq_file_basename = os.path.basename(bbq_file_name)
	else:
		bbq_file_basename = bbq_file_name
	match = re.search(r'^bbq-(.+?)-questions\.txt$', bbq_file_basename)
	if not match:
		raise ValueError(f"Filename '{bbq_file_name}' does not match expected pattern.")
	bbq_core_name = match.group(1)
	return bbq_core_name

#=====================================================
#=====================================================
def main():
	"""
	Main function to handle the script execution logic.
	"""
	_check_version()

	# Shortcuts for common formats (used for both -f and individual options)
	format_shortcuts = {
		'canvas_qti_v1_2':     ('-1', 'qti12', 	"Set output format to Canvas QTI v1.2"),
		'blackboard_qti_v2_1': ('-2', 'qti21', 	"Set output format to Blackboard QTI v2.1"),
		'human_readable':      ('-r', 'human', 	"Set output format to human-readable text"),
		'bbq_text_upload':     ('-b', 'bbq',   	"Set output format to (B)lack(B)oard (Q)uestions"),
		'html_selftest':       ('-s', 'selftest',	"Set output format to HTML self-test"),
		'moodle_aiken':        ('-A', 'aiken',	   "Set output format to MOODLE aiken"),
	}

	args = parse_args(format_shortcuts)
	# documentation website:
	# https://help.blackboard.com/Learn/Instructor/Original/Tests_Pools_Surveys/Orig_Reuse_Questions/Upload_Questions

	if not os.path.exists(args.input_file):
		raise FileNotFoundError(f"Error: Input file '{args.input_file}' not found.")

	# general format of input_file = "bbq-(content_name)-questions.txt"
	content_name = extract_core_name(args.input_file)
	if not content_name:
		print("Invalid input filename format")
		raise ValueError
	print(f"Content Name: {content_name}")

	qti_packer = package_interface.QTIPackageInterface(
			package_name=content_name,
			verbose=args.verbose,
			allow_mixed=args.allow_mixed
		)

	# Step 1: Read questions from the input file
	qti_packer.read_package(args.input_file, "bbq_text")

	# Step 2: Apply question limit if specified
	qti_packer.trim_item_bank(args.question_limit)

	count = 0
	if args.output_file:
		qti_packer.save_package(args.output_format[0], args.output_file)
		count += 1
	else:
		for engine_name in args.output_format:
			#format_data = format_shortcuts[engine_name]
			#short_name = format_data[1]
			try:
				qti_packer.save_package(engine_name)
				count += 1
			except NotImplementedError:
				pass
	print(f"DONE, saved {count} of {len(args.output_format)} output files")

#==============

if __name__ == "__main__":
	main()
