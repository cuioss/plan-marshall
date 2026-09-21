envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:54Z

# Carried-out finding 18f362 — CI payload cannot establish WHICH commit was verified: run head_sha and run age contradict each other

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `18f362` |
| type / severity | `triage` / `warning` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:tools-integration-ci` |
| file | `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

CI payload cannot establish WHICH commit was verified: run head_sha and run age contradict each other

## Detail (verbatim from the archived store)

At PR #1388 after pushing 13d2177f4..8148fed53, the ci abstraction returns two facts that cannot both be true. (1) ci checks wait returns run_id 33790703017 together with head_sha 8148fed537da... — the current local HEAD, exactly. (2) The same run reports elapsed_sec growing 2347 -> 2926 -> 3495 -> 3579 across four reads, i.e. a run created roughly 60 minutes ago, which predates 8148fed53 by a wide margin. A run cannot have started an hour before the commit it verifies. Either head_sha is the caller's local git rev-parse HEAD echoed back rather than the RUN's head sha (making it useless for attribution), or elapsed_sec measures something other than time since run creation. A consumer cannot tell which, so no consumer can establish from this payload which commit CI actually observed. COMPOUNDING OBSERVABLE: in that same run verify / verify is SKIPPED while verify / gate passes in 12s and verify / conclusion passes in 3s. Per .github/workflows/python-verify.yml the gate skips the heavy build when every changed path is non-building OR when the commit is already covered by an open PR run; the always-reporting conclusion job then reports green. This push changed Python source (target.py, _build_server_protocol.py, build_server.py, marshalld.py, _build_cli.py) plus six test modules, so a docs-only skip would be wrong, and an already-covered-by-PR skip would be pointing at the PR run for the SUPERSEDED commit 13d2177f4. Waiting 511s produced no new run id. IMPACT: the required check reports green while it is unestablished that any heavy build observed this HEAD — which is exactly the condition the pre-merge barrier trusts. Counterweight for this plan specifically: local verify IS green at this exact tree (23760 tests, compile+lint+test, freshness corroborated and covered), so the code is verified even though CI attribution is not. REMEDY CANDIDATES: have ci checks status / wait publish the RUN's head sha under a distinct key from the caller's local HEAD, and publish run created_at rather than a bare elapsed so age is checkable; a consumer could then refuse a green whose run head does not equal the PR head.
