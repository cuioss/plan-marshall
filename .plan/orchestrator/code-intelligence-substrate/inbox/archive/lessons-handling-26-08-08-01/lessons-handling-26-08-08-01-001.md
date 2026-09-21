envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T16:27:32Z

## Routed lessons cluster C03 — a freshness gate admits a tree whose tests never ran (4 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-CIS-017` (freshness-gate-cannot-distinguish-test-authored-evidence) —
an exact-surface match.
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Four active lessons, all on `pre-commit-verify-freshness` and the `kind=build` ledger rows it
reads. Together they say the gate accepts at least three kinds of evidence that are not a
verify run over the production tree.

| Lesson | The non-evidence the gate accepted |
|--------|-------------------------------------|
| 2026-07-26-20-002 | a `kind=build` ledger entry **written by the test suite** satisfies the production gate |
| 2026-07-27-08-002 | the gate returns fresh off a **quality-gate-only** run, admitting a tree whose tests never ran |
| 2026-07-29-18-004 | the gate accepts a **`--help` invocation** as evidence a verify observed the tree |
| 2026-07-28-19-007 | `arch-constraint`: markdown under `marketplace/bundles/**` **IS a build input** (tests parse SKILL.md bodies), so a doc-only freshness-neutrality exemption is unsafe in this repo |

### Why these belong together

`PLAN-CIS-017`'s title names one of the four (test-authored evidence). The other three are the
same defect class at different admission points: the gate's predicate is *"a build row exists"*
rather than *"a verify observed this tree"*, so anything that writes a row clears it. Three
independent producers of a clearing row — the test suite, a quality-gate-only run, a `--help`
probe — is a stronger statement than any one of them.

`2026-07-28-19-007` is the inverse-facing member and is worth carrying explicitly: it is an
`arch-constraint` that **forecloses a tempting remedy**. Any fix that narrows the gate by
exempting doc-only footprints is unsafe here, because markdown under `marketplace/bundles/**`
is parsed by tests and is therefore a real build input. A fix for the other three that reaches
for that exemption reintroduces this one.

`2026-07-27-00-002` (`kind=build` rows record exit_code 0 for timed-out builds, and `--help`
probes count as builds) is routed to `truthful-signals` in cluster C02 as a
build-outcome-truthfulness lesson, but it is the **same ledger rows** as this cluster's
`2026-07-29-18-004`. If your fix and theirs both touch `manage-change-ledger`, that is a
sequencing collision worth raising before either starts.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-CIS-017` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that all four admission paths are still open. Confirm/refute
  artifact: the `pre-commit-verify-freshness` handler in `manage-change-ledger` — specifically
  the predicate it applies to a candidate `kind=build` row.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
