#!/usr/bin/env python3
"""
Ad-hoc CLI wrapper around qti_package_maker.common.package_integrity.

Runs the cross-reference integrity check against any package ZIP or already
extracted package directory (real LMS exports, probe kits under
output_probes/, or suspect ZIPs a user hands you), and prints the violations
plus a one-line summary. Useful outside the pytest suite, where the checker
is otherwise only wired into structure/roundtrip tests.
"""

# Standard Library
import argparse

# QTI Package Maker
from qti_package_maker.common import package_integrity


#============================================
def parse_args() -> argparse.Namespace:
	"""
	Parse command-line arguments.

	Returns:
		argparse.Namespace: Parsed arguments.
	"""
	parser = argparse.ArgumentParser(
		description="Check a QTI/Blackboard package ZIP or extracted directory "
		"for cross-reference integrity violations."
	)
	parser.add_argument(
		'-i', '--input', dest='input_path', required=True,
		help="Path to a package ZIP file or an already extracted package directory.",
	)
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	args = parse_args()
	violations = package_integrity.check_package(args.input_path)
	for violation in violations:
		print(violation)
	if violations:
		violation_count = len(violations)
		print(f"{violation_count} violation(s): {args.input_path}")
		raise RuntimeError(
			f"{violation_count} integrity violation(s) found in {args.input_path}")
	print(f"CLEAN: {args.input_path}")


#============================================
if __name__ == '__main__':
	main()
