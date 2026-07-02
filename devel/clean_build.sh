#!/usr/bin/env bash
# clean_build.sh - light clean: wipe build output, tool caches, and test
# artifacts while KEEPING dependency installs (node_modules, Rust target/) so no
# reinstall or full recompile is needed afterward.
#
# Front door: this is the everyday build cleaner, wired to `npm run clean` in
# TypeScript repos. Run directly as ./devel/clean_build.sh. For a deep reset that
# also removes node_modules and Rust target/ (a distribution-clean checkout), use
# devel/dist_clean.sh instead. Both keep the committed package-lock.json.
#
# Universal across repo types (python, typescript, rust). Patterns that do not
# exist in a given repo are silently skipped via `nullglob` + an existence
# check, so no false-positive output.
set -euo pipefail
shopt -s globstar nullglob
cd "$(git rev-parse --show-toplevel)"

DELETED=()

# delete_if_exists <path...>
# Removes each path that exists (file, dir, or symlink) and records it.
# Unmatched globs expand to nothing under nullglob, so missing entries
# silently no-op and are not reported.
delete_if_exists() {
	local p
	for p in "$@"; do
		if [ -e "$p" ] || [ -L "$p" ]; then
			rm -rf "$p"
			DELETED+=("$p")
		fi
	done
}

# Generic build outputs (any language).
delete_if_exists dist dist-single _site build out

# TypeScript / JS build artifacts and bundler metadata.
delete_if_exists _bundle.js meta.json stats.html
delete_if_exists **/*.tsbuildinfo

# JS/TS tool caches.
delete_if_exists .cache .eslintcache .prettiercache .nyc_output

# Test outputs (Playwright, coverage).
delete_if_exists test-results playwright-report blob-report coverage

# Python bytecode and tool caches (any depth).
delete_if_exists **/__pycache__ **/.pytest_cache **/.mypy_cache **/.ruff_cache

# Dependency installs (node_modules, Rust target/) and the committed
# package-lock.json are intentionally KEPT here. Use devel/dist_clean.sh for a
# full reset that also removes node_modules and target/.

if [ "${#DELETED[@]}" -eq 0 ]; then
	echo "Nothing to clean."
else
	echo "Cleaned ${#DELETED[@]} path(s):"
	for p in "${DELETED[@]}"; do
		echo "  $p"
	done
fi
