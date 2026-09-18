# This file is vendored. Local changes can and will be overwritten by propagation.

"""Console and subprocess helpers for the PyPI publishing command."""

# Standard Library
import subprocess

# PIP3 modules
import rich.console


CONSOLE = rich.console.Console(highlight=False)
ERROR_CONSOLE = rich.console.Console(stderr=True, highlight=False)

#============================================

def print_step(message: str) -> None:
	"""Print a step header in cyan.

	Args:
		message: The step message to print.
	"""
	CONSOLE.print(message, style="bold cyan", highlight=False, markup=False)

#============================================

def print_info(message: str) -> None:
	"""Print a normal info message.

	Args:
		message: The info message to print.
	"""
	CONSOLE.print(message, highlight=False, markup=False)

#============================================

def print_warning(message: str) -> None:
	"""Print a warning message in yellow.

	Args:
		message: The warning message to print.
	"""
	CONSOLE.print(message, style="yellow", highlight=False, markup=False)

#============================================

def print_error(message: str) -> None:
	"""Print an error message in red to stderr.

	Args:
		message: The error message to print.
	"""
	ERROR_CONSOLE.print(message, style="bold red", highlight=False, markup=False)

#============================================

def fail(message: str) -> None:
	"""Print an error and exit.

	Args:
		message: The error message to print.

	Raises:
		RuntimeError: Always, after printing the error.
	"""
	print_error(message)
	raise RuntimeError(message)

#============================================

def run_command(args: list[str], cwd: str, capture: bool) -> subprocess.CompletedProcess:
	"""Run a command and fail on error.

	Args:
		args: Command arguments.
		cwd: Working directory.
		capture: Whether to capture output.

	Returns:
		The completed process.
	"""
	result = subprocess.run(
		args,
		cwd=cwd,
		text=True,
		capture_output=capture,
	)
	if result.returncode != 0:
		command_text = " ".join(args)
		fail(f"Command failed: {command_text}")
	return result
#============================================

def run_command_allow_fail(args: list[str], cwd: str, capture: bool) -> subprocess.CompletedProcess:
	"""Run a command and return the result, even if it fails.

	Args:
		args: Command arguments.
		cwd: Working directory.
		capture: Whether to capture output.

	Returns:
		The completed process.
	"""
	result = subprocess.run(
		args,
		cwd=cwd,
		text=True,
		capture_output=capture,
	)
	return result

#============================================

def run_command_to_log(
	args: list[str],
	cwd: str,
	log_path: str,
) -> subprocess.CompletedProcess:
	"""Run a command and write its output to a log file.

	Args:
		args (list[str]): Command arguments.
		cwd (str): Working directory.
		log_path (str): File receiving command output.

	Returns:
		subprocess.CompletedProcess: Completed command result.

	Raises:
		RuntimeError: When the command fails.
	"""
	with open(log_path, "a") as handle:
		handle.write(f"$ {' '.join(args)}\n")
		handle.flush()
		result = subprocess.run(
			args,
			cwd=cwd,
			text=True,
			stdout=handle,
			stderr=handle,
		)
	if result.returncode != 0:
		command_text = " ".join(args)
		fail(f"Command failed (see {log_path}): {command_text}")
	return result

#============================================
