envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-22-01
epic=code-intelligence-substrate
kind=finding
created=2026-09-22T07:15:32Z

# Direct finding from lessons-handling-26-09-22-01

A live, unaddressed, already-diagnosed bug in a file this epic owns, surfaced independently by two
lessons in the corpus routed elsewhere for their process angle (`truthful-signals`,
`2026-09-21-08-002` and `2026-09-21-08-003`) — forwarding directly since it names your own file.

## The bug

`.plan/orchestrator/code-intelligence-substrate/cloud-runs/_audit/analyze.py` hardcodes:
- `REPO = pathlib.Path("/Users/oliver/git/plan-marshall")` — a developer-machine absolute path
- a `/private/tmp/claude-501/<session-uuid>/scratchpad/` write target
- the pre-relocation address `.plan/local/orchestrator/…` (stale since the `tracked-orchestrator-store-
  resolver` plan moved this tree to `.plan/orchestrator/…`)

Confirmed still present on `origin/main` as of 2026-09-21 (`git show origin/main:.plan/orchestrator/
code-intelligence-substrate/cloud-runs/_audit/analyze.py`).

## Provenance

- `cuioss-review-bot` independently flagged this on PR #1555 (Hardcoded Local Paths, guide item 3) —
  never resolved.
- The step that should have caught it (`automatic-review` on plan `tracked-orchestrator-store-resolver`)
  recorded `outcome: done` while `manage-findings list --resolution pending` still showed this finding
  pending — a prose-vs-ledger divergence, filed separately to `truthful-signals`.

## Proposed remedy (from the source lessons, not independently verified here)

Replace the hardcoded `REPO`/temp-dir literals with argv or environment resolution; audit its siblings
under `.plan/orchestrator/**/_audit/` and `.plan/orchestrator/review-apparatus/findings/**` for the same
pattern.
