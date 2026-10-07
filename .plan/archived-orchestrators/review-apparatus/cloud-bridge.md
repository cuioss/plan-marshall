# Cloud bridge — review-apparatus

Pointer document. The orchestrator reads this to find the cloud leg of its own queue.

| Artifact | Path | Tracked in git |
|---|---|---|
| The lifecycle rule (create / sync / collect) | `doc/plans/cloud-bridge.md` | yes |
| This epic's cloud plans (the tree IS the state) | `doc/plans/review-apparatus/` | yes |
| This epic's cloud plans | `doc/plans/review-apparatus/{cloud-plan}/` | yes |
| The run contract a cloud session follows | `.claude/skills/cloud-plan-lane/SKILL.md` | yes |
| This epic's orchestrator ledger | `.plan/local/orchestrator/review-apparatus/` | **no** |

The rule is NOT restated here — read `doc/plans/cloud-bridge.md`. This file exists so the
orchestrator can reach it from inside its own tree without knowing the repository layout.

## What this obliges the orchestrator to do

- **On create** — author the cloud plan from the orchestrator spec, carrying the claim labels across
  intact, and set the row to `authored`. The orchestrator spec is not deleted; it stays the source
  record.
- **On collect** — take each `implemented` row, corroborate it against merged PR state and the run
  report before recording anything, transition the orchestrator plan through the queue verb, then set
  the row to `ingested`. The transition and the row move together or not at all.
- **Never** write epic state into `doc/plans/`, and never expect a cloud session to have written
  anything into `.plan/local/orchestrator/review-apparatus/`. Git is the only shared medium.

## Standing caution

A ledger row is a **claim** about the cloud leg, written by a party that could observe it at the
time. It is corroborated at ingest, not trusted: an `implemented` row whose PR is not merged is
precisely the confident-clean-signal failure this project keeps finding, and it is checkable here by
construction.
