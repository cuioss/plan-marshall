envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:54Z

# Carried-out finding 1f0c43 — Script startup cost makes run_script subprocess budgets marginal under verify's parallel load

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `1f0c43` |
| type / severity | `improvement` / `warning` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:manage-architecture` |
| file | `test/conftest.py` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

Script startup cost makes run_script subprocess budgets marginal under verify's parallel load

## Detail (verbatim from the archived store)

Measured this run, on an otherwise-idle machine: architecture.py module --module my-module takes 17.9s wall on a COLD inventory cache (203 percent CPU - genuinely crawling, not blocked) and 6.4s warm. test_module_subcommand_accepts_canonical_module calls it through run_script with timeout=30. Under verify's -n auto load (10 xdist workers, each spawning its own subprocesses) that 6-18s baseline exceeded 30s and the test failed with subprocess.TimeoutExpired - one failure in 23744, in a test with no relationship to this plan's changes. Same class as the four plugin-doctor timeouts this plan already marked, and as the daemon's own 15s get-worktree-path probe budget which failed twice for the same reason. A CONTRIBUTING cause was found and removed: 75917 temp files / 783MB of pytest-basetemp residue from earlier killed runs had accumulated under .plan/temp, and every script startup walked it - the pre-cleanup measurement was 19.8s at 22 percent CPU (I/O-blocked), the post-cleanup one 17.9s at 203 percent CPU (compute-bound), so the residue was real overhead but not the whole story. The residual issue is that a cold architecture crawl costs ~18s and several subprocess budgets across the suite are sized as if script startup were cheap. Remedy options: warm the inventory once in a session fixture, raise the run_script default budget for architecture-invoking tests, or make the crawl incremental.
