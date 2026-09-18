# Design decisions

<!-- VENDORED HEADER: START -->
Record each durable decision about how this code and repository are shaped, once it is settled, with
the reasoning a later reader needs. Guidance Neil Voss states belongs in
[HUMAN_GUIDANCE.md](HUMAN_GUIDANCE.md), dated history in `docs/CHANGELOG.md`, open discussion in
`docs/active_plans/decisions/`. [PROPAGATED HEADER - ENTRIES BELOW ARE YOURS]
<!-- VENDORED HEADER: END -->

Write each decision as a level-three heading with these four fields. `Owner` names the
authoritative code or contract document, rather than a person.

```markdown
### <decision title>

**Decision.** <the durable direction>

**Why.** <the reason it was chosen>

**Consequence.** <the constraint a future change preserves>

**Owner.** <the authoritative code or contract doc>
```

## Software design

## Dependencies

## Generated artifacts

### Graphify agent guidance lives in the propagated devel README

**Decision.** Document Graphify usage for downstream repositories in
[../devel/DEVEL_README.md](../devel/DEVEL_README.md), and do not run
`graphify claude install` or `graphify codex install`.

**Why.** A repository README is never shared between repositories, `AGENTS.md` arrives only when a
repository lacks one, and `docs/` files are replaced wholesale on sync, so a shared `docs/USAGE.md`
would overwrite each repository's own usage document. Files under `devel/` are shared by location.
The Graphify installers additionally write into `CLAUDE.md` and `AGENTS.md` and add a PreToolUse
hook, contending with how those two files are already maintained.

**Consequence.** Guidance that must reach every repository goes in `devel/DEVEL_README.md`.
Third-party tools do not write to `CLAUDE.md` or `AGENTS.md`.

**Owner.** [../devel/DEVEL_README.md](../devel/DEVEL_README.md)

### Rust test symbols leave the graph before clustering

**Decision.** In a Cargo repository, a fresh build extracts with `--no-cluster`, removes
`#[cfg(test)]` symbols from `graph.json`, then runs `cluster-only`. Graphify's own source is never
modified.

**Why.** Filtering at print time leaves the symbols in the graph, where they still distort
community detection, hub degree ranking, and connector spread. `cluster-only` re-clusters an
existing graph, which makes removing them before clustering possible without forking Graphify.
Spans are found with tree-sitter because a brace scan would have to reason about strings,
comments, and nested modules to be correct.

**Consequence.** The gate is `Cargo.toml`, so repositories without Rust run the original pipeline
unchanged. Pruning is limited to fresh builds: re-clustering renumbers communities, and a fresh
build is the only path that always relabels afterward, so stored labels cannot go stale.

**Owner.** [../devel/graphify_prune_tests.py](../devel/graphify_prune_tests.py)

### Graphify exposes recurring maintainer actions

**Decision.** The wrapper exposes automatic update, explicit fresh, context, and documentation
publication. `--svg` composes with fresh or update and also publishes an existing map by itself.
`--ollama` remains the one fresh-build fallback when the Claude allowance is exhausted.

**Why.** These are the maintainer's recurring tasks. Semantic extraction, global registration,
reflection, map-page generation, deep extraction, and forced shrinking add configuration without
serving the normal workflow.

**Consequence.** `--svg` writes both `docs/GRAPHIFY.md` and `docs/GRAPHIFY_map.svg`. Both are
recorded as non-shared because they describe the repository where they were generated.

**Owner.** [../devel/graphify_map_repo.py](../devel/graphify_map_repo.py)

### The committed graph figure is decorative

**Decision.** Generate the SVG directly from community membership and intercommunity edges. Show
at most the largest twelve communities, scale circles by membership, weight connecting lines, and
keep names and detail in Markdown rather than an SVG legend.

**Why.** Full Graphify exports grow with every symbol and embed font glyphs for labels that are not
readable at repository-map scale. A community-level figure preserves the important visual
relationships while Markdown provides accessible, searchable names and repository-derived prose.

**Consequence.** The figure conveys relative community scale and coupling rather than code-level
detail. Publication has no matplotlib, SVG-cleaning, or XML-parser dependency.

**Owner.** [../devel/graphify_docs_lib.py](../devel/graphify_docs_lib.py)

### Recent untracked Markdown links are temporary working-tree inputs

**Decision.** The Markdown link checker admits nonignored untracked regular files as sources and
targets only while their creation age is strictly less than 24 hours.

**Why.** Newly authored documentation often links to another new file before staging, while older,
ignored, missing, and outside-repository paths should continue to fail the GitHub-browsability gate.

**Consequence.** Git supplies candidates through `ls-files --others --exclude-standard`; one
captured current time classifies birth time, or ctime where birth time is unavailable.

**Owner.** [../tests/test_markdown_links.py](../tests/test_markdown_links.py)

### Graphify orientation filters test symbols instead of trusting the graph

**Decision.** `devel/graphify_context_lib.py` drops test scaffolding, repository-wide utility types,
and uninformative call targets before printing orientation.

**Why.** Graphify's Rust extractor indexes `#[cfg(test)] mod tests` contents as production symbols.
Those modules live inside `src/*.rs`, so no `.graphifyignore` rule can exclude them without also
dropping the production code in the same file. Separately, a symbol spanning most communities is a
utility type carrying no navigational information.

**Consequence.** This filter is presentational and remains the fallback, not the primary fix. A
Cargo repository now removes those symbols from the graph itself before clustering, so the filter
covers what pruning does not reach: incremental updates, and other languages whose inline test
conventions have no prune step.

**Owner.** [../devel/graphify_context_lib.py](../devel/graphify_context_lib.py)

### Graphify diagnostics and staleness checks stay advisory

**Decision.** Edge-fidelity diagnostics and the stale-map warning report findings and never fail a
build or suppress orientation.

**Why.** Graphify documents no reliable threshold for same-endpoint edge collapse, and repeated
endpoint pairs are legitimate in some codebases. Context mode exists to orient a reader, so a stale
map must still print in full.

**Consequence.** These checks print and continue. Context mode also reads the `needs_update` flag
file directly rather than shelling out, preserving its documented promise to print orientation
without running Graphify.

**Owner.** [../devel/graphify_map_repo.py](../devel/graphify_map_repo.py)
