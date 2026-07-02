#!/usr/bin/env bash
# dist_clean.sh - deep clean: wipe build artifacts, tool caches, and dependency
# installs to return the repo to a distribution-clean checkout.
#
# Front door: run this directly as ./devel/dist_clean.sh. This is the deep reset,
# used when preparing the repo for distribution or forcing a clean dependency
# reinstall. The lighter everyday build clean is devel/clean_build.sh (wired to
# `npm run clean`), which leaves node_modules intact.
#
# Keeps package-lock.json: it is committed and drives reproducible `npm ci`.
#
# Universal across repo types (python, typescript, rust). Patterns that do
# not exist in a given repo are silently skipped via `nullglob` + an
# existence check, so no false-positive output.
#
# After this runs you may need to reinstall language-specific dependencies
# before the usual gates work again:
#   typescript: npm install
#   python:     pip install -r pip_requirements.txt -r pip_requirements-dev.txt
#   rust:       cargo build (recompiles dependencies on next invocation)
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

# JS dependency installs (forces clean reinstall on next npm install). Keeps
# package-lock.json, which is committed and drives reproducible npm ci.
delete_if_exists node_modules

# JS/TS tool caches.
delete_if_exists .cache .eslintcache .prettiercache .nyc_output

# Test outputs (Playwright, coverage).
delete_if_exists test-results playwright-report blob-report coverage

# Python bytecode and tool caches (any depth).
delete_if_exists **/__pycache__ **/.pytest_cache **/.mypy_cache **/.ruff_cache

# Rust build outputs.
delete_if_exists target

if [ "${#DELETED[@]}" -eq 0 ]; then
	echo "Nothing to clean."
else
	echo "Cleaned ${#DELETED[@]} path(s):"
	for p in "${DELETED[@]}"; do
		echo "  $p"
	done
fi
