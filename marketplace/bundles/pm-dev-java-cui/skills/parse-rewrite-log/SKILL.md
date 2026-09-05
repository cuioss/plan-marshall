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
This parser complements, never replaces, the tree-scan detector. How far the
local `cui-rewrite:disable` marker reaches — and what no local marker reaches,
whichever signal surfaced it — is stated once in
[`../search-markers/standards/marker-detection.md` § Suppression-marker scope](../search-markers/standards/marker-detection.md#suppression-marker-scope).

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

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `parse_rewrite_log` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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
`parse_rewrite_log.py`. The plugin-doctor `missing-canonical-block` rule checks
that this section is PRESENT, matching its heading only — the body is never
read; `manage-invocation-invalid` derives its accept-set from a live `--help`
walk rather than from this section. Consuming docs xref this section by name
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
