envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=code-intelligence-substrate
kind=finding
created=2026-10-03T11:30:23Z

# Finding: staged specs declare paths that no longer exist in this repository

## Sender

Plan `cross-repo-telemetry-archive-and-analyze` (kind: finding).

## What changed

The plan relocated the retrospective auditor and the era-stamp fill step out of the
`plan-marshall` repository into the `plan-marshall-telemetry` repository, and then removed
the originals here. These three path families no longer exist in `plan-marshall`:

- `.claude/skills/audit-archived-plan-retrospectives/**`
- `.claude/skills/finalize-step-era-stamp-fill/**`
- `test/plan-marshall/audit-archived-plan-retrospectives/**`

The finalize step `project:finalize-step-era-stamp-fill` is also de-registered from this
repository's `.plan/marshal.json` (`plan.phase-6-finalize.steps`).

## Affected staged specs

All three are staged with no running plan, so this message queues for the epic drain:

| Spec | Stale declaration |
|------|-------------------|
| `PLAN-CIS-050` | Still declares one or more of the removed paths listed above |
| `PLAN-CIS-052` | Still declares one or more of the removed paths listed above |
| `PLAN-CIS-054` | Still declares one or more of the removed paths listed above |

Each spec still names the removed paths as part of its declared surface. A plan started
from any of them unchanged would target files that are absent from this repository.

## New home

The `plan-marshall-telemetry` repository:

- `.claude/skills/audit-archived-plan-retrospectives/**` — the auditor skill and its `checks/`
  and `scripts/audit.py`
- `.claude/skills/era-stamp-fill/**` — the era-stamp fill skill (renamed from
  `finalize-step-era-stamp-fill`)
- `test/audit-archived-plan-retrospectives/**` — the auditor test suite
- `test/era-stamp-fill/test_era_stamp_fill.py` — the era-stamp fill test

## Requested handling

Re-ground `PLAN-CIS-050`, `PLAN-CIS-052` and `PLAN-CIS-054` against HEAD before any of them
is started: either re-point each stale declaration at the `plan-marshall-telemetry`
repository, or drop the declaration where the work no longer belongs in this repository.

The staged specs themselves were not edited by the sending plan.
