envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=finding
created=2026-09-23T18:55:59Z

## Post-merge request: run `migrate-layout` over every epic ledger

Plan `ledger-decomposition-and-row-vocabulary` splits each epic ledger into per-concern files: a header-only `status.json`, `resume_anchor.md`, one `queue/{PLAN-ID}.json` per queue row, and the generated, git-tracked `queue-view.md`. From the moment it lands, every orchestrator verb that reads the queue or the anchor refuses a ledger still in the monolithic layout with `legacy_layout`. `status.json` still carrying `plans[]` or `resume_anchor` is the symptom of an unmigrated ledger. There is no read-fallback.

Per the Ledger Write-Boundary this plan migrates no existing ledger itself. After the PR lands on main, please:

1. Enumerate the population with `orchestrator corpus epics`, covering both the active and the archived partitions.
2. Run `orchestrator migrate-layout --slug {slug}` for every slug it returns. The verb resolves an archived epic too, and a second run reports `already_migrated: true`.
3. Commit the migrated ledgers together with the `queue-view.md` each migration writes. Each migration also strips the two GENERATED marker blocks from `epic.md` and leaves every hand-written byte in place.

One refusal to watch for: `migrate-layout` writes nothing and returns `unmigratable_rows` when a `plans[]` entry cannot become a row file. That happens when the entry is not an object, or when its id falls outside the plan-id grammar. A letter-suffixed id such as `PLAN-XX-025B` is outside that grammar. Each rejected entry is named with its index and reason. Such a ledger needs an operator decision on the row id before it can be migrated. Until that decision is made the ledger stays refused.
