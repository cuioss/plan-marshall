# PLAN-PR-001: `wait-for-comments` counts rows instead of watching one row

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`pr wait-for-comments` decides a review arrived by comparing an unresolved-comment COUNT against a
baseline snapshot. PR-Agent re-reviews by EDITING its one persistent Guide comment in place and
posting nothing new, so the count never grows and the await can only time out. Since `#1054` and
`#1052` composed, every loop-back burns the full 600 s timeout and escalates to the operator even
when pr-agent reviewed correctly and on time. Make the await watch the observable pr-agent
actually moves — the timestamp on the row — for bots whose registry record already declares that
requirement, so a correct re-review is detected when it happens.

The correct pattern already exists one file over and the registry already declares the answer;
this plan is a convergence onto an existing in-repo contract, not a new mechanism.

## Provenance — this spec absorbed `truthful-signals` PLAN-116 Defect A

PLAN-116 (`review-detectors-check-the-wrong-observable`) was released to this epic on 2026-07-30 and
**split**; its Defect A is this plan. The material below is folded in from that spec and is NOT
re-derivable from the summary that accompanied the handover. Nothing of A remains there.

- **A ~23-minute await completed nothing** while pr-agent had in fact reviewed — its Guide
  `updated_at` was `09:10:26Z`. This is the measured instance behind the mechanism.
- **The live cost has a named cause in two merged PRs that compose badly**: `#1054` (`25b0c91c9`)
  made a loop-back post each REQUIRED bot's trigger comment AND await the result; `#1052`
  (`ef80c1c8d`) narrowed `required_bots` to `pr-agent` alone. ⇒ every loop-back posts `/review`,
  awaits via `wait-for-comments`, the count cannot grow, it burns the full
  `re_review_await_timeout_seconds` (600 s), hits `re_review_on_timeout: ask`, and escalates.
  **The detector is now blind to precisely the one bot it is the sole waiter for.** It does NOT
  deadlock — the `ask` fallback holds.
- ⛔ **This is a PORT, not an invention.** Two detectors exist where one was taught the lesson and
  the other was not. Do not invent new logic, and do not lengthen the timeout — this is a shape
  problem, not a duration problem, and it *presents* as a duration problem.
- **Sibling slices of the same split** (do not absorb them): PLAN-PR-002 (Defect B, org guard),
  PLAN-PR-005 (Defects C+E, participation credited from lossy views), PLAN-PR-006 (Defect D, canned
  no-op vs substantive review), PLAN-PR-007 (Defect F, `stale` vs `absent`).

## Deliverables

1. `cmd_pr_wait_for_comments`'s completion predicate detects a re-review for a bot declaring
   `participation_requires_update`, keying on observed movement of the LATER of `updated_at` /
   `created_at` rather than on count growth — converging on the pattern already implemented in
   `github_re_review.py`.
2. Count-growth detection is RETAINED for bots that append a new comment per review
   (`participation_requires_update: false` — CodeRabbit, Sourcery). This is a widening, not a
   replacement: replacing it would break the bots the current predicate serves correctly.
3. **A detector that cannot answer says so** (folded from PLAN-116 D3). An await that ends because
   its observable can never change must report THAT, not a timeout. ⭐ A timeout claims "we waited
   long enough"; this detector never could have succeeded — **and the two demand opposite operator
   responses.** This is the deliverable that makes the failure legible next time rather than merely
   absent.
4. **DERIVE the detector population** (folded from PLAN-116 D1, scoped to this plan's observable).
   Treat `cmd_pr_wait_for_comments` as a SAMPLE: enumerate every completion/participation detector
   reachable from the await path and classify each by the observable it checks — row count, row
   content, check state, timestamp movement. A fix that lands at one of N detectors while the
   contract claims all N is this project's most-repeated defect. The population must be derived and
   non-empty, and the derivation is a gate that mutates nothing.

   ⭐ **The derivation seam is NAMED, and it was handed over deliberately** (inbox
   `truthful-signals-003.md`, drained 2026-07-30): **enumerate every `poll_until` caller in
   `workflow-integration-github/scripts/`** and check each for the count-vs-baseline predicate shape.
   This question travelled here with PLAN-116 and **nothing in the sibling epic will answer it** — that
   epic states so explicitly and asks that it not be allowed to lapse alongside the now-moot boundary
   question that carried it. ⛔ **Do not let it lapse**: an unenumerated population is how a one-site fix
   ships against a three-site defect, which is the failure this epic has now hit **four** times.
   ⚠ `poll_until` is the seam the sibling named, not necessarily the complete one — a detector that
   polls without going through `poll_until` would be invisible to that enumeration alone, so treat the
   caller list as the starting set and state whether it is closed.

   ⛔⛔ **CORRECTED 2026-07-30 — the `poll_until` seam is DEMONSTRABLY INCOMPLETE, and the caution above
   was right for the wrong reason.** Two further sites were found the same day, and **neither is on the
   await path at all**, so a `poll_until`-caller enumeration would have missed both:

   | Site | Predicate | Verdict |
   |---|---|---|
   | `_github_pr.py` § `cmd_pr_wait_for_comments` | unresolved **row count** vs baseline | ⛔ broken — this plan |
   | `github_pr.py:486` § `_has_update_movement` | `(bot_kind, id)` **then** `updated_at != created_at` | ✅ **correct — the model** |
   | `github_pr.py:776` § `cmd_fetch_findings` "Pre-filter 5" | `(bot_kind, comment_id)` **alone** | ⛔ broken — PLAN-PR-005 |

   ⇒ **D4's population is NOT "detectors reachable from the await path." It is every site that decides
   whether a comment represents NEW INFORMATION.** Derive on *that* question. ⭐ The correct
   implementation now has **two** exemplars (`github_re_review.py:247-250` and
   `github_pr.py:486`), which strengthens this plan's PORT-not-invention framing rather than weakening it.
   ⚠ **Coordinate with PLAN-PR-005** — the third site is inside its declared function, and it owns that
   fix. ⛔ Do not fix it from here; derive the population, name the members, and let each plan port to its
   own site.
5. Tests covering both arms, including the in-place-edit case that the current predicate cannot
   pass, the mixed case (one append-per-review bot plus one edit-in-place bot on the same PR), and
   the unanswerable case reporting its own inapplicability rather than a timeout. **Each test
   verified to FAIL pre-fix.**

## Claim Labels

- OBSERVED: the predicate compares a count against a baseline — read at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  § `cmd_pr_wait_for_comments` → its inner `is_complete_fn`, which returns
  `int(data.get('unresolved', 0)) > baseline`. The surrounding result payload
  (`baseline_count` / `final_count` / `new_count`) is count-shaped throughout.
- OBSERVED: the correct pattern already exists in the repo — read at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`,
  whose docstring states a comment counts when "the LATER of its `updated_at` and `created_at` is
  strictly after" the trigger time, and which notes `created_at` stops advancing after the first
  review.
- OBSERVED: the registry already declares which bots need this — read at
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
  § `participation_requires_update` (accessor plus module-level function), with
  `automatic-review/standards/pr-agent.md` declaring `participation_requires_update: true`
  ("a re-review EDITS that same comment in place") and `coderabbit.md` / `sourcery.md` declaring
  `false` ("each review appends new comments; presence IS the movement").
- OBSERVED: the config-level cause is real and must NOT be treated as the fix site —
  `pr-agent-settings` sets `persistent_comment = true` AND `final_update_message = false`, so
  pr-agent edits one comment and posts nothing new, by design and correctly so.
- HYPOTHESIS: `fetch_pr_comments_data` returns per-comment `updated_at` / `created_at` fields to
  this call site, so the predicate can be widened without changing the fetch — confirm/refute at
  `workflow-integration-github/scripts/github_ops.py` § `fetch_pr_comments_data`
  (verify-at-outline). If refuted, the fetch shape is part of this plan's scope and the
  deliverable count grows by one.
- HYPOTHESIS: `cmd_pr_wait_for_comments` is the only await site with this defect — confirm/refute
  by enumerating every caller of `poll_until` in `workflow-integration-github/scripts/`
  (verify-at-outline). Treat this as a POPULATION question, not a spot check: a sibling await with
  the same predicate shape is in scope. This project's recurring defect is exactly a fix that
  lands at one of N call sites while a doc claims all N.
- Verify-first clause: re-derive the whole Expected Surface against HEAD by SYMBOL before scoping.
  Line numbers in this spec are navigational only and are expected to have moved.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  — `cmd_pr_wait_for_comments` and its inner `is_complete_fn` / `check_fn` (~line 679-744 at
  `d38b769ba`). **This is the whole production surface this plan claims in this file.**
- OBSERVED (read-only reference, not edited): `.../scripts/github_re_review.py` — the pattern to
  converge on.
- OBSERVED (read-only reference, not edited): `.../automatic-review/scripts/bot_registry.py`
  § `participation_requires_update`.
- HYPOTHESIS: `.../scripts/github_ops.py` § `fetch_pr_comments_data` — edited ONLY if the
  timestamp fields are not already returned (verify-at-outline).
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py` and
  `test_pr_wait_for_comments_rate_limited.py` — the existing await tests this plan extends.
- HYPOTHESIS: `.../automatic-review/standards/bot-participation-contract.md` — a doc-contract
  update if that standard describes the await predicate in count terms (verify-at-outline).

## Dependencies and Sequencing

- Depends on: none. Specifically NOT on `truthful-signals` PLAN-115 — that plan's surface is
  `tools-integration-ci` plan-less-PR correction, which this plan does not touch.
- Overlaps with: ✅ **The PLAN-116 collision is RESOLVED, not merely noted.** That plan was released
  to this epic on 2026-07-30 and its row in `truthful-signals` is `transferred` (verified against
  that epic's live queue, not from its handover prose). Its Defect A was absorbed here, so there is
  no longer a competing owner. The earlier "narrowed to avoid serialization" framing is superseded.
- Overlaps with: ⚠ **PLAN-PR-005** (Defects C+E) touches participation derivation in
  `github_pr.py` / `_github_pr.py` — the same FILE, a different function. Sequence, do not pair,
  until both surfaces are re-verified at outline.
- Adjacent to: `truthful-signals` PLAN-115 (`plan-less-pr-can-be-opened-but-never-corrected`,
  **launched**, retained there). Its surface is `tools-integration-ci` pr verbs — adjacent PR comment
  plumbing, not this predicate. That epic will report its landing here.
- Adjacent to: the pre-merge review barrier (`truthful-signals` PLAN-119, refusal deadlock). This
  plan makes the await return sooner on a genuine re-review; it does NOT touch what the barrier
  does when a bot refuses, and must not absorb that.
- Adjacent to: `pr-agent-settings/.pr_agent.toml`. ⛔ **PROHIBITED remedy** — do not "fix" this by
  re-enabling `final_update_message`. It was turned OFF precisely because plan-marshall filed that
  content-free update comment as a finding needing triage. The fix belongs in the detector.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-001-wait-for-comments-counts-rows.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
