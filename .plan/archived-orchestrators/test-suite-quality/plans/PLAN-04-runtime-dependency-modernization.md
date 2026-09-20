# PLAN-04 (superseded slug): Runtime & Dependency Modernization

epic: test-suite-quality
workstream: WS-02

> **This spec was SPLIT on 2026-07-22 and no longer names a queued plan.** It is retained as an
> audit record only — the queue in `status.json` is the machine authority.

## Where the content went

The original `PLAN-04-runtime-dependency-modernization` carried five deliverables that coupled a
zero-cost configuration change to a known-breaking dependency migration. The operator chose to split
them:

| Original deliverable | Now lives in |
|----------------------|--------------|
| 1. Lift the capped majors and pin | `PLAN-06-runtime-dependency-modernization.md` D1 |
| 2. Absorb the bump fallout | `PLAN-06` D2 |
| 3. Python-floor / CI-parity resolution | `PLAN-06` D3 |
| 4. Document the resolved runtime floor | `PLAN-06` D4 |
| 5. Enforcement gates (`filterwarnings`, `--strict-markers`, `--strict-config`) | `PLAN-04-enforcement-gates-and-measurement.md` D1–D3 |
| — (new) yardstick re-measurement | `PLAN-04-enforcement-gates-and-measurement.md` D4 |

The queue order is **PLAN-04 → PLAN-06 → PLAN-05**, which preserves the 2026-07-21 decision that the
PLAN-05 capstone measures on the final pinned toolchain.

## Why

The 2026-07-21 decision that kept the gates bundled here rested on *"`--strict-markers` would
immediately fail the tree PLAN-02 is about to rewrite"*. That blocker expired when PLAN-02 registered
the markers and PLAN-03 finished rewriting the tree. Meanwhile `pyproject.toml:18-38` records that the
bump target is known-breaking, so keeping the two coupled risked losing a provably-zero-cost change to
a migration that may not land. See the epic's Decisions section, entry dated 2026-07-22.
