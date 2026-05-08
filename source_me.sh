#!/bin/bash

# Get the directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find the Git root by running git from the script's location
GIT_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null)"

# Check if GIT_ROOT was found (i.e., we're inside a Git repo)
if [[ -z "$GIT_ROOT" ]]; then
	echo "Error: Script is not inside a Git repository." >&2
	exit 1
fi

# Check if PYTHONPATH is unset
if [[ -z "$PYTHONPATH" ]]; then
	# If PYTHONPATH is not set, initialize it with GIT_ROOT
	export PYTHONPATH="$GIT_ROOT"
	echo "PYTHONPATH was unset. Initialized to: $PYTHONPATH"
elif [[ ":$PYTHONPATH:" != *":$GIT_ROOT:"* ]]; then
	# If GIT_ROOT is not already in PYTHONPATH, add it
	export PYTHONPATH="$GIT_ROOT:$PYTHONPATH"
	echo "PYTHONPATH updated: $PYTHONPATH"
else
	# GIT_ROOT is already in PYTHONPATH, no changes needed
	echo "PYTHONPATH already contains GIT_ROOT. No update needed."
fi

echo "Run your tests now!"
