# The Two-Signal OpenRewrite Detection Model

The java-cui domain surfaces OpenRewrite recipe findings through **two
complementary signals**, each owned in `pm-dev-java-cui` by the
ownership-of-format principle: the format each signal parses describes recipes
this bundle's domain governs, so the detector lives here rather than in the core
build layer. The two signals **complement, never replace, one another** — they
observe findings at different points in the recipe lifecycle and have distinct,
non-overlapping coverage boundaries. Neither is a substitute for the other.

## Signal A — tree-scan (`pm-dev-java-cui:search-markers`)

Scans Java/Kotlin **source files** for the in-source
`/*~~(TODO: …)~~>*/` markers OpenRewrite's `SearchResult` printer persists into
the source tree. Reached from core through the `marker-detect` domain verb.

- **What it sees**: markers that a recipe **wrote into the source** and that are
  still present on disk — persisted findings, independent of any particular
  build run. It can gate a source tree at any time, even with no build log.
- **Coverage boundary**: it sees only what was **persisted into source**. It has
  no per-run log context — it cannot distinguish a newly-detected finding from a
  pre-existing one, cannot see findings the recipe reported to the log but did
  not persist as a source marker, and sees nothing about whether `rewrite:run`
  actually executed.

## Signal B — log-parse (`pm-dev-java-cui:parse-rewrite-log`)

Parses the cui-open-rewrite **#118 structured WARN lines** from the Maven
**build log**, extracting `(path, line, column, recipe, message)` per finding and
classifying each as newly-detected vs pre-existing. Reached from core
`build-maven` through the `rewrite-log-parse` domain verb.

- **What it sees**: **every per-run finding** the recipe emitted this run —
  including the **pre-existing** findings that #118 surfaces (`CUI_REWRITE-101`),
  which Signal A cannot distinguish — together with the exact recipe and message
  per finding, and the newly-detected-vs-pre-existing classification.
- **Coverage boundary**: it sees a finding **only when `rewrite:run` actually
  executed** and emitted the WARN line into the captured log. A build that
  failed before `rewrite:run` (e.g. a compile error) produces no log-parse
  signal — which the consumer reports fail-closed as `not_observed`, never a
  false "clean" (see [ADR-009]). It sees only what the build **logged this run**,
  not what is persisted in source across runs.

## Why both, and why they never collapse into one

The two coverage boundaries are complementary, not redundant:

| Aspect | Signal A (tree-scan) | Signal B (log-parse) |
|--------|----------------------|----------------------|
| Source of truth | in-source markers on disk | #118 WARN lines in the build log |
| Sees pre-existing findings distinctly | no | yes (`CUI_REWRITE-101`) |
| Needs a build run | no — scans source any time | yes — only when `rewrite:run` executed |
| Survives across runs | yes (persisted in source) | no (per-run log only) |
| Reached via domain verb | `marker-detect` | `rewrite-log-parse` |

A source marker Signal A finds may never appear in a given run's log (the recipe
did not re-report it); a per-run finding Signal B reads may never be persisted as
a source marker. Collapsing them into one detector would lose exactly the
findings the other uniquely covers. They are therefore two independent signals,
each owned in `pm-dev-java-cui`, that a consumer reads **together** for full
coverage.

## Suppression-marker scope

The `// cui-rewrite:disable <Recipe>` marker named in the Categorization table of
[`../SKILL.md`](../SKILL.md) is **scoped to the CUI recipes this bundle defines**.
It silences the named CUI recipe and nothing else. In particular it does **not**
stop `AutoFormat`, the upstream formatting recipe that runs outside this bundle's
recipe set and is not addressable by any local marker.

The consequence is a coverage boundary, not a configuration detail: a formatting
conflict originating in `AutoFormat` — an indentation this pipeline applies and
`AutoFormat` rewrites back — **survives every local marker**, because no local
marker reaches the recipe producing it. Adding another marker, or widening an
existing one, changes nothing about it.

**No local remedy for that conflict exists.** The only lever that acts on it is
the upstream `AutoFormat` recipe itself — its own configuration, or its removal
from the recipe list that runs. The honest statement about the local surface is
that it has none, so a reader looking for a local workaround should stop looking
rather than keep widening a marker that cannot reach the cause.

## No fixed point to report

A rewrite pipeline whose own output is an input to its next run has **no fixed
point to report**. "Formatted" is a statement about the pass that just ran: it
says that pass finished and applied what it had to apply. It says nothing about
whether a further pass over the same tree would apply anything more. Convergence
— a pass that changes nothing — is a different property, and no single pass can
observe it.

This is a property of the pipeline itself, and it holds regardless of which
recipes are configured or how cleanly any one of them reports. Two consequences
follow for anything that consumes a rewrite report:

- A clean report is **one pass's** verdict. It is not evidence that the tree has
  stopped changing, and it must not be read as one.
- Convergence is established only by observation across passes — a pass whose
  output equals its input. Nothing inside a single run's report substitutes for
  that observation.

This bounds a different thing from the two signals' coverage boundaries above:
those bound what each signal *sees* within one run, while this bounds what any
single run's clean report can *mean*.

## Related

- `../SKILL.md` — Signal A, the tree-scan marker detector this standard documents alongside.
- `pm-dev-java-cui:parse-rewrite-log` — Signal B, the log-line finding parser.
- `plan-marshall:extension-api/standards/ext-point-domain-verb.md` — the `marker-detect` and `rewrite-log-parse` domain verbs the two signals are reached through.

[ADR-009]: the fail-closed "absence-of-evidence is a distinct third state, never a vacuous positive" principle the log-parse consumer applies via its `not_observed` verdict.
