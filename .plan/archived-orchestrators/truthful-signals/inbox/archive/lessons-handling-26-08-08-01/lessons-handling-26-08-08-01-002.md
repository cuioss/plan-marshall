envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:39Z

## Routed lessons cluster C02 — a build reports its own outcome falsely (10 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-027` (build-ledger-is-the-build-time-oracle).
**You decide**: fold, restage, split, or decline. Nothing was written into your tree.

### The cluster

Ten active lessons in which a build's reported outcome disagrees with what the build did. This
is your epic's founding theme applied to the one signal every gate downstream trusts.

**False green** — the build failed or did not run, and said otherwise:

| Lesson | Claim |
|--------|-------|
| 2026-07-22-12-003 | a routed build reported outer `status: success` while the **daemon child had failed**, because terminal status was classified from a wrapper exit code that is always 0 |
| 2026-07-27-00-002 | `kind=build` rows record **exit_code 0 for timed-out builds**, and `--help` probes count as builds |
| 2026-08-08-12-001 | a pytest **COLLECTION ERROR reports `failed=0` and `build_status=SUCCESS`** through the parse verb — an entire un-executed test file reads as green; only `exit_code` and the raw log dissent |
| 2026-06-16-23-001 | the JVM build-error classifier tags compilation errors and test failures as `[deprecation_warning]` |

**False red** — the build passed and said otherwise:

| Lesson | Claim |
|--------|-------|
| 2026-08-01-13-001 | a pytest run that **reached its own green summary** is still reported `status=timeout exit_code=-1` when the wrapper budget expires in teardown |
| 2026-07-27-00-001 | routed builds misreport their own outcome: `--timeout` silently discarded, duration zeroed, and a daemon wait-expiry reported as a hard failure **over a child that passed** |

**The measurement itself is wrong**:

| Lesson | Claim |
|--------|-------|
| 2026-08-02-15-006 | two timeout authorities disagreed and the kill reported `duration_seconds=0` |
| 2026-07-16-16-003 | `build-maven run` defaults to an adaptively-lowered subprocess timeout that **silently kills long builds**; the script-level `--timeout` binds, not the Bash timeout |
| 2026-07-07-10-001 | log-summary extractors must **anchor to the summary line** before reading counts, not count-scan the whole log |
| 2026-07-22-20-005 | dependency-bump fallout was enumerated on an **unverified interpreter**; read it from the build log header or the whole fallout set must be re-measured |

### Why both directions matter

Four false-greens and two false-reds is not two problems — it is one: **the outcome is derived
from the wrong observable** (a wrapper exit code that is always 0, a wall-clock budget that
outlives the summary, a count-scan that outruns the summary line). A fix that only closes the
false-green half leaves the false-red half, and a false red is what trains a reader to
disbelieve the gate.

`2026-08-08-12-001` is the newest (filed today) and the sharpest: `failed=0` and
`build_status=SUCCESS` over an entire file that never executed, with `exit_code` and the raw log
as the only dissenters. That is a **quorum of one honest signal against two lying ones**.

⚠ **Known collision.** `2026-07-27-00-002` is the same `manage-change-ledger` `kind=build` rows
as cluster C03, which I routed to `code-intelligence-substrate` for `PLAN-CIS-017`
(freshness-gate). If both plans touch that ledger, serialize them.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-027` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each misreport is still live. Confirm/refute
  artifacts: `build-server-client`'s terminal-status classification, and `build-pyproject`'s
  `parse` verb where `failed` is derived.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
