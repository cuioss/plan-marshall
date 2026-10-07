# Landing: PLAN-21 review-barrier-residuals

- **PR:** #957 (`275915c48 fix(finalize-review): bot-agnostic rate-limit filter, triage-aware completeness guard, retire gemini default`) — merged to main
- **Workstream:** WS-10 pipeline-integrity-hardening
- **Granularity:** full ship
- **Verified:** commit + `git show --stat` (10 files, +703/-56, 3 test files) corroborate the deliverables; enriched 2026-07-21 with the operator's finalize narrative (added D4, self-validation payoff, in-run events).

## Deliverable fidelity vs spec

The plan shipped **4 deliverables** (D1–D3 as staged + an operator-approved D4 scope expansion surfaced by the plan's own self-validation).

| Deliverable | Shipped | Verdict |
|-------------|---------|---------|
| D1 — bot-agnostic rate-limit/service-notice classifier | `_is_rate_limit_notice` (`_github_pr.py`/`github_pr.py`) replacing the CodeRabbit-only gate; author-ungated, two-part precision; `test_github_pr.py` (+245) | ✅ generalizes PLAN-10 #936 |
| D2 — triage-state-aware completeness guard | `triage_ran` param in `review_completeness.py`; pre-triage pending findings no longer loop back; `test_review_completeness.py` (+201) | ✅ |
| D3 — retire sunset Gemini from `enabled_bots` default | `gemini.md`, `manage-config` (+ `test_config_defaults.py`); registry entry KEPT so past gemini comments still classify | ✅ caveat honored |
| **D4 — settled/responded bot is accounted-for, not unfetched** (operator-approved expansion) | completeness guard now treats a bot that posted comments (even all-noise) OR whose review window closed as accounted-for, not as an unfetched incompleteness | ✅ closes the 4th defect |

## Self-validation payoff (acceptance evidence)

The plan's own finalize exercised the fix on itself — the spec's stated acceptance mode. **D1–D3 alone still manufactured a spurious loop-back**: all-noise bots resolved to "unfetched" → the completeness guard looped forever. That uncovered a genuine **4th barrier defect**; the operator chose "fix now" → D4. After D4 the completeness check returned `complete: true` with **zero loop-back**. The barrier stopped inventing phantom work — that IS the acceptance evidence.

## Notable in-run events (all resolved)

- **3 D3 misses the outline under-scoped**, caught by CI + self-review: a stale test assertion (→ fix task TASK-6) and two stale doc citations (reconciled inline).
- **Cache-sync latency vs re-dispatched review leaf:** the D4 `SKILL.md` change was not visible to a re-dispatched review leaf (plugin cache syncs late), so the operator ran the D4 completeness logic **inline as orchestrator**. → new lesson (a re-dispatched leaf cannot see an uncommitted/un-synced skill edit).
- **Too-tight adaptive build timeout:** a resolved envelope of 447s was run under a 190s adaptive timeout → one false `module-tests` timeout; re-ran with `--timeout 500`. → new lesson (a false timeout is an untruthful failure — same family as PLAN-24's truthful-status theme).

## Housekeeping / metrics

- Lessons `2026-07-13-21-001` (D1 source) + `2026-07-18-05-001` (D2 source) removed — now shipped.
- `target/claude` + on-main executor regenerated to v0.1.1167 (this run); main clean. (Superseded by #959's v0.1.1170.)
- Metrics: ~3.3M tokens; ~2h7m worked / 10h16m wall; 6/6 phases recorded.

## Reconciliation actions

- Queue: PLAN-21 → shipped, pr=957 (was reconciled from git evidence a step earlier; this enriches the record).
- **Post-D4 residual watch (kept OPEN):** completeness-guard should distinguish a *structurally-absent* bot from an *in-progress* one. Captured in #959's lessons-capture — and #959 ran with D4 already in main, so D4 did NOT subsume this facet. It is a genuine post-D4 refinement (n=1); candidate PLAN-21 follow-up, do not treat as resolved by D4.
- **Two new lessons** (cache-sync-vs-re-dispatched-leaf; adaptive-build-timeout-too-tight) recorded as WS-10 datapoints; the timeout one is adjacent to PLAN-24's truthful-status theme and PLAN-29's waiting/timeout neighborhood.
