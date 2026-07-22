---
name: search-markers
description: Domain-owned OpenRewrite marker detection for the java-cui domain — scans Java/Kotlin sources for cui-rewrite TODO markers, categorizes them by recipe, and fails the gate on any detected marker
user-invocable: false
mode: script-executor
---

# Search Markers (java-cui domain verb)

Detect OpenRewrite TODO markers left in source by the cui-rewrite recipes.

The cui marker format and the auto-suppressible recipe table describe recipes
**this bundle defines** (see `pm-dev-java-cui:recipe-cui-logging-enforce`), so
the detector is owned here rather than by the core build layer. Core reaches it
through the `marker-detect` domain verb this bundle declares via
`provides_domain_verb()`, and resolves the verb to `null` when the java-cui
domain is not active — a project without java-cui simply runs no marker gate.

## Enforcement

**Execution mode**: `script-executor` — drive the documented script and route on
its exit code and result TOON. No LLM judgement is involved in detection.

**Prohibited actions:**
- Do not invoke this skill directly as a workflow — core dispatches it through the resolved `marker-detect` domain verb.
- Do not invent script subcommands or flags — use only the surface in `## Canonical invocations` below.
- Do not hand-write a marker literal when testing this detector. The marker syntax is pinned by a provenance-bearing fixture copied verbatim from the upstream recipe project's checked-in test resources; derive every literal from that fixture.

**Constraints:**
- The marker syntax and this detector's `MARKER_PATTERN` must agree with the provenance fixture, never with recollection of the format.
- The exit-code contract below is the gate's machine-readable verdict and must not be weakened by category.

## Marker syntax

```text
/*~~(TODO: <message>)~~>*/
```

The closing delimiter is `)~~>*/` — the `~~` belongs to both delimiters,
because OpenRewrite's `SearchResult` printer wraps the description as
`~~(<description>)~~>`. A detector that terminates on `)>*/` silently matches
nothing against real recipe output.

## Categorization

Each detected marker is categorized by the recipe name parsed from its message:

| Category | Meaning |
|----------|---------|
| `auto_suppress` | The recipe has a known mechanical suppression. The marker carries a `suppression_comment` (`// cui-rewrite:disable <Recipe>`) and is counted in `auto_suppress_count` / `by_category.auto_suppress`. |
| `ask_user` | The recipe is not in the auto-suppressible table, so the marker needs a human decision. Counted in `ask_user_count` / `by_category.ask_user`. |

Categorization describes **how a marker can be silenced**, not whether it is
still present — see the exit-code contract.

## Exit-code contract

| Exit code | Condition |
|-----------|-----------|
| `0` | The scan succeeded and the source is marker-free (`total_markers == 0`) |
| `1` | Any marker was detected (`total_markers > 0`), **or** the scan itself failed (`status: error`, e.g. an unreadable `--source-dir`) |

`auto_suppress` is **not** an exemption from the non-zero exit: a source
carrying only auto-suppressible markers still fails the gate, because the
markers are still in the source. Callers that want to act only on markers
needing a human decision read `ask_user_count` from the payload — never from
the exit code. Because both the failure and the markers-found paths return `1`,
distinguish them by the payload's `status` field.

## Result payload

```toon
status: success
data:
  total_markers: 3
  files_affected: 2
  recipe_summary: {CuiLogRecordPatternRecipe: 2, SomeOtherRecipe: 1}
  auto_suppress_count: 2
  ask_user_count: 1
  by_category: {auto_suppress: [...], ask_user: [...]}
  markers: [{file, line, column, message, recipe, raw_marker, action, category, reason, suppression_comment}]
```

On a failed scan the payload is `status: error` with an `error` key
(`source_not_found`) and a human-readable `message`.

## Canonical invocations

The canonical argparse surface for the entry-point script this skill registers:
`search_markers.py`. The plugin-doctor analyzer reads this section as
source-of-truth for the `manage-invocation-invalid` and
`missing-canonical-block` rules. Consuming docs xref this section by name
instead of restating the command inline.

### search_markers — search

```bash
python3 .plan/execute-script.py pm-dev-java-cui:search-markers:search_markers search \
  [--source-dir SOURCE_DIR] [--extensions EXTENSIONS] [--skip-patterns SKIP_PATTERNS] [--format {toon,json}]
```

**Parameters**:
- `--source-dir` — Directory to search (default: `src`)
- `--extensions` — Comma-separated file extensions (default: `.java`)
- `--skip-patterns` — Comma-separated directory names to skip (default: `build,target,.gradle,node_modules`)
- `--format` — Output format, `toon` (default) or `json`

## Related

- `plan-marshall:extension-api/standards/ext-point-domain-verb.md` — the `marker-detect` domain-verb contract this skill implements the domain side of
- `pm-dev-java-cui:plan-marshall-plugin` — the bundle manifest whose `provides_domain_verb()` override declares this skill's notation
- `pm-dev-java-cui:recipe-cui-logging-enforce` — the recipe that defines `CuiLogRecordPatternRecipe`, one of the auto-suppressible recipes above
