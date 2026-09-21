envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:55Z

# Carried-out finding c8e4a9 — A timeout verdict kills the daemon job but orphans the whole pytest process tree

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `c8e4a9` |
| type / severity | `bug` / `error` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:manage-build-server` |
| file | `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

A timeout verdict kills the daemon job but orphans the whole pytest process tree

## Detail (verbatim from the archived store)

OBSERVED LIVE this run, confirming lesson 2026-09-02-21-002 which finalize-step-lessons-housekeeping had just retained as NOT covered. A whole-tree verify hit its 3000s bound and the daemon returned status=timeout. The job was reported dead, but the process tree SURVIVED: pid 21025 (build.py verify) was still alive at 58:52 elapsed, pid 33766 (pytest -n auto) at 46:10, plus TEN xdist workers actively spawning fresh orchestrator.py children at 00:02-00:05 elapsed - i.e. still executing tests minutes after the daemon called the job dead. Consequence chain, all observed: the orphans saturated the machine; the immediately-following retry failed with worktree_resolution_failed because its 15-second get-worktree-path subprocess probe could not complete; that failure surfaced as exit_code 2 with 'no structured errors were parsed', which reads like an argparse rejection and not like resource starvation. TWO-STAGE SURVIVAL: killing pytest's master (33766) did NOT take the workers - all ten survived and had to be signalled individually, which is the xdist-pool survival property the lesson names. Remedy: _marshalld_supervisor's timeout path must kill the child's PROCESS GROUP, not just the child, and confirm the group is gone before reporting the terminal verdict; a status=timeout that leaves the work running is a false terminal state. Until then a timeout MUST be followed by an explicit orphan sweep before any retry.
