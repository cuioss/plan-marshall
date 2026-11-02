envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T10:27:00Z

# The weakened_test check reads moved, renamed and deliberately removed tests as lost assertions, and re-raises them as blocking at every head

Severity: **high** (graded at the 2026-11-02 sweep: it needs an operator close in every review round, which blocks unattended finalize).
Bundle: `plan-marshall` (`phase-6-finalize` review_support, `_review_support_integrity.py`; `manage-findings` qgate dedup).

## Sources (API-Sheriff epic api-sheriff-0-2-0)

- `lessons-routing-008`: plan-v02-05-response-hygiene, PR cuioss/API-Sheriff#526
- `api-sheriff-api-sheriff-0-2-0-036`: plan-v02-42-validator-auth-oidc-rules, PR #502
- `api-sheriff-api-sheriff-0-2-0-048`, `-049`: plan-v02-43-validator-reserved-header-topology-rules, PR #505
- `api-sheriff-api-sheriff-0-2-0-062`, `-063`: plan-v02-27-test-simplification, PR #520
- `api-sheriff-api-sheriff-0-2-0-071`: plan-v02-51-lane-conditional-guards, PR #538

Bodies verbatim in `lessons-routing/inbox/archive/{sender}/`.

## Observation

Five plans, five PRs.

1. A git-mv test move or split produces blocking `weakened_test` rows for each old path in both reviews, in every round. In #502, 139 methods and 257 assertions were unchanged; in #505 the assertion lines went from 130 to 136.
2. Planned duplicate removals whose assertions had been carried into the surviving tests read the same way (8 of 11 rows in #520).
3. An assertion that is on origin/main but absent from the branch is reported as removed when main moved after the merge base (#526).
4. The rows stay blocking after the verifier refutes them with evidence. An operator acceptance is bound to its head, so every fix commit re-opens them: #505 operator closes at three heads; #520 reobserved_count 4; #538 a deliberate removal accepted at the first prompt came back at every later head and once made the verifier refuse an otherwise supported grading.
5. The two dedup paths disagree. Through `qgate add`, an identical re-observation folds silently into the resolved record (`--reopen` does nothing, `loop-back close --accept` sees no pending row); the review path re-raises it as new and blocking.

## Ground truth (c431a8193)

- `_review_support_integrity.py:75`: the changed set is `git diff --name-only --no-renames {base}...HEAD` — rename detection is off.
- `:81-84`: the pre-image is read at `{base_ref}:{path}` (the base tip), while the changed set is relative to the merge base, so upstream assertions added after the branch point count as removed (the #526 case).
- A deleted (moved) test file counts every assertion as gone; counting is per path, with no total across the files the assertions moved to.
- PLAN-LB-75 (parked, medium) D3 touches the same file but widens detection; it does not address moves, dedups or carry-forward.
- The carry-forward across heads and the qgate fold rest on the senders' Q-Gate records; not re-run here.

## What to consider

- Diff with rename/copy detection and compare assertion totals across the changed test set; report a loss only when the total drops or a named test disappears from every file. Read the pre-image at the merge base.
- Let the outline declare a planned dedup or removal, and have the check honour it.
- Key an operator acceptance or a verifier refutation to the removed-test identity, not to the head; re-open only when the removed set changes.
- Make `qgate add` and the review path give one visible outcome for an identical re-observation of a resolved blocking finding; `--reopen` must work or fail loudly.
