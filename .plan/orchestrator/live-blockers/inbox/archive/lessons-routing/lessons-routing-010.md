envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:44:02Z

# domain-narrow can empty references.domains, and the documented recovery call fails

- **Severity:** high — graded by the operator at this run (it was put to them as borderline medium/high)
- **Bundle:** `plan-marshall` (`phase-3-outline`, `tools-script-executor`)
- **Source lesson:** `2026-10-05-17-002`
- **Full body:** `lessons-routing/lessons-archive/filed-live-blockers/2026-10-05-17-002.md`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). The lesson is retired from the corpus.

## What the lesson says

Two coupled failures on cui-http PLAN-13 (PR #262):

1. Every deliverable declared `domain: documentation`, but the phase-3 domain-narrow dropped all
   four detected domains, leaving `references.domains` as `[]`. No domain skill resolves in any
   later phase until the list is restored by hand.
2. The documented recovery, `manage-references set-list --values ""`, exits 2 because the executor
   strips empty-string arguments; `--values=` works.

Proposed: domain-narrow keeps every domain a deliverable declares and never narrows to an empty set
while deliverables carry a domain; either keep empty argument values in the executor or document
`--values=` as the clearing form.

## Owner today

None found. It is not in `backlog.md`. Seen once, in a consumer repository.

## Asked of live-blockers

Verify at HEAD, then decide whether to stage it. Not re-checked in code at this run.
