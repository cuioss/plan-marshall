---
name: parse-rewrite-log
description: Domain-owned OpenRewrite log-line finding parser for the java-cui domain — parses the #118 structured WARN lines from the Maven build log, extracting path/line/column/recipe/message per finding and classifying each as newly-detected vs pre-existing
user-invocable: false
mode: script-executor
---

# Parse Rewrite Log (java-cui domain verb)

Parse the structured per-run WARN lines that `cui-open-rewrite` #118 emits into
the Maven build log, extracting one structured finding per line.

This is **Signal B** of the two complementary OpenRewrite signals — the
log-parse sibling of `pm-dev-java-cui:search-markers` (Signal A, tree-scan). The
two-signal model, each signal's coverage boundary, and their complementary
(never-replacing) relationship are documented in
[`../search-markers/standards/marker-detection.md`](../search-markers/standards/marker-detection.md).
This parser complements, never replaces, the tree-scan detector.

The #118 WARN-line format describes log lines emitted by recipes this bundle's
domain governs, so the parser is owned here rather than by the core build layer.
Core `build-maven` reaches it through the `rewrite-log-parse` domain verb this
bundle declares via `provides_domain_verb()`, and resolves the verb to `null`
when the java-cui domain is not active — a project without java-cui simply runs
no log-parse signal.

## Enforcement

**Execution mode**: `script-executor` — drive the documented script and route on
its exit code and result TOON. No LLM judgement is involved in parsing.

**Prohibited actions:**
- Do not invoke this skill directly as a workflow — core dispatches it through the resolved `rewrite-log-parse` domain verb.
- Do not invent script subcommands or flags — use only the surface in `## Canonical invocations` below.
- Do not hand-write a WARN literal when testing this parser. The line format is pinned by a provenance-bearing corpus captured verbatim from the upstream recipe project's own source; derive every literal from that corpus.

**Constraints:**
- The line format and this parser's `FINDING_PATTERN` must agree with the provenance corpus, never with recollection of the format.
- A change to the upstream #118 WARN shape (template wording, identifier, or prefix) that the corpus no longer matches must fail the format-drift regression test rather than silently disabling the parser.

## WARN-line format

The recipe emits two WARN `LogRecord` templates per finding (from
`RecipeLogMessages.java`), rendered by cui-java-tools' `LogRecordModel.format`
with the `"%s-%s".formatted(prefix, identifier)` header and the `": "`
after-prefix separator:

```text
CUI_REWRITE-100: Finding detected at <path>:<line>:<column> by <recipe>: <message>
CUI_REWRITE-101: Finding pre-existing at <path>:<line>:<column> by <recipe>: <message>
```

The five fields are the source file path, line, column, recipe display name, and
the marker/task message. The identifier is the authoritative classification
signal:

| Identifier | Classification | Template verb |
|------------|----------------|---------------|
| `100` | `newly_detected` | `Finding detected at …` |
| `101` | `pre_existing` | `Finding pre-existing at …` |

Only the `CUI_REWRITE-<id>: ` application prefix is part of the recipe-emitted
string; the surrounding log layout (JUL formatter / Maven / OpenRewrite console)
prepends any timestamp / level tag / logger name / thread. The parser therefore
matches the prefix as a **substring anywhere in the line** (never anchored at
line-start) and captures the message field **greedily to end-of-line**, because
the message can itself contain `": "` (e.g. `TODO: Throw specific not RuntimeException`).

## Exit-code contract

| Exit code | Condition |
|-----------|-----------|
| `0` | The parse succeeded and the log carried no finding (`total_findings == 0`) |
| `1` | Any finding was parsed (`total_findings > 0`), **or** the parse itself failed (`status: error`, e.g. an unreadable `--log-file`) |

Because both the failure and the findings-parsed paths return `1`, distinguish
them by the payload's `status` field. A `0` exit means only "no finding in this
log text" — it is **not** a "clean run" verdict. The reached-`rewrite:run` /
not-reached / domain-inactive distinction (the fail-closed `not_observed` state,
ADR-009) is `build-maven`'s responsibility, not this parser's.

## Result payload

```toon
status: success
data:
  total_findings: 3
  newly_detected_count: 2
  pre_existing_count: 1
  findings: [{path, line, column, recipe, message, identifier, classification, raw_line}]
```

On a failed parse the payload is `status: error` with an `error` key
(`log_not_found` / `log_unreadable`) and a human-readable `message`.

## Canonical invocations

The canonical argparse surface for the entry-point script this skill registers:
`parse_rewrite_log.py`. The plugin-doctor analyzer reads this section as
source-of-truth for the `manage-invocation-invalid` and
`missing-canonical-block` rules. Consuming docs xref this section by name
instead of restating the command inline.

### parse_rewrite_log — parse

```bash
python3 .plan/execute-script.py pm-dev-java-cui:parse-rewrite-log:parse_rewrite_log parse \
  --log-file LOG_FILE [--format {toon,json}]
```

**Parameters**:
- `--log-file` — Path to the build-log file to parse (required)
- `--format` — Output format, `toon` (default) or `json`

## Related

- `../search-markers/standards/marker-detection.md` — the two-signal OpenRewrite model this parser is Signal B of
- `pm-dev-java-cui:search-markers` — Signal A (tree-scan); this parser is its log-parse sibling, complementary and never a replacement
- `plan-marshall:extension-api/standards/ext-point-domain-verb.md` — the `rewrite-log-parse` domain-verb contract this skill implements the domain side of
- `pm-dev-java-cui:plan-marshall-plugin` — the bundle manifest whose `provides_domain_verb()` override declares this skill's notation
