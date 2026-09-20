# PLAN-PR-007: `absent` names two states with opposite remedies, and reports the alarming one

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — `truthful-signals` PLAN-116 Defect F. THE COMMON PATH.

PLAN-116 was released to this epic on 2026-07-30 and split. Defect F is here as its own plan because
it is a **reporting-fidelity** defect, not a crediting defect — which makes it distinct from C and E
and means it **survives both of their remedies**: those aim to produce or preserve a *credit*; F
concerns how a correctly-refused *stale* review is **named**. Sibling slices: PLAN-PR-001 (A),
PLAN-PR-002 (B), PLAN-PR-005 (C+E), PLAN-PR-006 (D).

## Objective

⭐ **The gate was right. The word was wrong.** A bot that reviewed an earlier HEAD is reported
`absent` — the same member used for a bot that never engaged at all. The two states have **opposite
remedies**: *never ran* → investigate the App install, credentials, org config (an infrastructure
incident); *ran, then the diff moved* → the reviewer is healthy, the defect is step ordering, and the
fix is a re-trigger. Today the taxonomy reports the alarming one.

Add the missing member so a stale review is named as such, **without changing any merge verdict**.

## ⭐ The cost is now MEASURED, and the recurrence is structural (inbox `truthful-signals-004`, 2026-07-30)

Forwarded from the **#1064** landing. Previously this was a reporting-fidelity defect; there is now a
measured consequence, which changes what "no merge verdict moves" buys.

- OBSERVED (first-party operator report of their own run, corroborated by #1064's `record-metrics`):
  #1064 spent **3.2 M tokens against a ~1.3 M threshold** for its scope class — roughly **2.5×** — and
  the dominant cost was **three `automatic-review` dispatches across two loop-backs**.
- OBSERVED (operator report): **one loop-back was caused by a content-identical rebase invalidating
  required-bot participation.** Operator's words: *"which will recur on every plan."*
- ⚠ **NOT verified, treat as leads**: the causal attribution of that loop-back to the rebase, and the
  ~1.3 M scope-class threshold. The sending epic states plainly it verified neither.
- ⛔ **The recurrence is structural, not probabilistic.** `finalize-step-sync-baseline` rebases on every
  finalize, after the PR-open review, so **every plan reaching finalize crosses this path.** It is not a
  flaky bot or a timing race — which is what makes the false `absent` a standing tax rather than an
  incident.
- ⭐ **A NARROWER VARIANT to check at D1/D2, flagged by the sender and not covered above: the
  CONTENT-IDENTICAL rebase.** A rebase that changes no content but moves the SHA. ⚠ **A detector keyed
  on diff CONTENT rather than on HEAD IDENTITY would miss it** — and it is the commonest rebase shape in
  this project, since `sync-baseline` rebases whether or not anything conflicts. **Verify which of the
  two this plan's currency test actually keys on; do not assume HEAD identity.**
- ⚠ This does not change the safety property: `stale` still gates exactly as `absent` does, so **no merge
  verdict moves here**. What the measurement changes is the *value* of landing it — the naming fix is
  what lets a later plan stop paying the loop-back, and the loop-back is now known to dominate a plan's
  entire token budget.

## ⛔ Why this ranks high: it recurs on the COMMON path, not an edge case

After `#1053` pr-agent subscribes to `opened` / `reopened` / `ready_for_review` only — **a rebase is
invisible to it** — and `finalize-step-sync-baseline` rebases and force-pushes as part of **every**
finalize, *after* the PR-open review. **The plan flow's own step ordering guarantees that any PR
needing a rebase ends with a stale Guide and a false `absent`.** ⭐ This likely explains much of this
project's review-coverage pain, including the six barrier rounds observed on `truthful-signals`
PLAN-112.

## Deliverables

1. **D1 — GATE (mutates nothing): re-establish the contradiction and derive the state population.**
   Enumerate every state the participation classifier can report and check whether each has exactly
   one member. The taxonomy **declares itself closed and is not** — treat `stale` as the member found,
   not as the only member missing. ⛔ **The population is now known to be at least THREE** — `stale`
   and `not_triggered` are both confirmed missing (see Claim Labels, `API-Sheriff#133`), so a D1 that
   derives two members has under-derived and must keep going. **Derive, do not enumerate to the known
   list** — two members were found by accident, on two separate days, which is evidence the population
   is bigger than whatever is currently known.

   ⭐ **A five-mode SAMPLE arrived from a sibling epic on 2026-07-30** (inbox
   `code-intelligence-substrate-001.md`, a review-coverage watch removed from that epic's ledger and now
   ours). It is a **LEAD, not a verified defect list** — its author states plainly that the five modes
   were compiled from session observation and never re-derived against the PR corpus. Use it to
   **falsify any claim of closure**, never as the population itself:

   | Mode observed | Where it sits |
   |---|---|
   | 1. a bot never reviewing at all | `absent` — the existing member, correctly |
   | 2. all three configured bots non-participating | a compound of 1, not a distinct member |
   | 3. ⭐ a check **COMPLETING** with no comment | **not obviously any existing member** — check state and comment disagree; D1 must decide whether this is its own member |
   | 4. a proven review reported absent on loop-back | `stale` — D2's member |
   | 5. **partial** — HEAD 1 reviewed, HEAD 2 refused | ⛔ **NOT this plan** — a false *positive*, owned by **PLAN-PR-013** |

   ⛔ **Mode 5 is deliberately OUT of this plan's scope.** The sibling flagged it as the one mode it
   could not map onto anything we owned, and it was right: it reads as *participation present* while the
   merged artifact went unreviewed, so its remedy **moves a merge verdict** — the exact thing this plan
   forbids itself. Staged as PLAN-PR-013, sequenced after this one. **Do not absorb it here.**
   ⚠ Mode 3 IS in scope and is the likeliest member to expand the population, because a completing check
   with no comment is precisely the case where the cheap observable looks healthy.
2. **D2 — a sixth member: `stale` / `participated_stale`.** For an admissible publish shape that fails
   the `participation_requires_update` / HEAD-currency test. ⛔ **It gates exactly as `absent` does
   today, so NO merge verdict changes.** The distinguishing evidence is **already in hand at
   classification time** — the comment was observed, its `kind` matched a declared
   `participation_evidence` shape, only the currency test failed — and is currently **discarded on the
   way to `absent`**. This is a plumbing-through, not a new computation.
3. **D3 — the self-contradicting table is corrected**, so one member no longer carries two mutually
   exclusive conditions.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A bot that reviewed a prior HEAD classifies
   `stale`, not `absent`. (b) A bot that never posted classifies `absent`. (c) The merge verdict for
   the `stale` case is **byte-identical to today's** — the gate does not move. (d) The state
   population is derived, non-empty, and every member's conditions are mutually exclusive.

## Claim Labels

- OBSERVED (full evidence chain on `#1059`): workflow run `30466587421` conclusion **success**; the org
  fail-closed step "Verify the reviewer actually produced a review" **passed**; `cuioss-review-bot[bot]`
  published its Guide at **15:36:44Z** against HEAD `acbdcecf3`; the final merged HEAD was `cf634762`
  at **16:51:40Z**. pr-agent ran, reviewed and published — **75 minutes before the rebase that produced
  the merge candidate.** Its registry sets `participation_requires_update: true`, `updated_at` never
  moved, so participation was **correctly not credited** — and then reported as `absent`.
- OBSERVED: **the contract contradicts itself in one table**
  (`automatic-review/standards/bot-participation-contract.md`) — `:56` defines `absent` as "No comment
  posted and no completion check-run observed … the bot never engaged at all"; `:98` routes an
  unprovable participant to that **same** member; `:81` names "a stale comment tied to a prior HEAD" as
  a thing presence does not prove. One member carries two states whose conditions are **mutually
  exclusive** — one requires no comment, the other is only reachable when a comment exists.
  ⚠ **Verify by section heading, not by line number.**
- OBSERVED: after `#1053` pr-agent's event subscription excludes rebases, and
  `finalize-step-sync-baseline` rebases on every finalize after the PR-open review. These two together
  are what make this the common path rather than an edge case.
- ⛔ **REFUTED 2026-07-30 — `stale` is NOT the only missing member. A THIRD state exists, and it was
  found live.** The hypothesis is settled BEFORE outline, and D1 must derive the population knowing the
  answer is at least three, not two. Evidence chain, orchestrator-verified on `cuioss/API-Sheriff#133`
  (a consumer repo, so this is not a plan-marshall-only shape):
  - `automatic-review` returned `loop_back` reporting required bot pr-agent with **no participation**.
  - Ground truth: pr-agent posted **nothing at all** — 0 issue comments, 0 reviews. So `absent` was
    **factually TRUE here**, and this is NOT the PLAN-PR-001 false-absent shape.
  - ⭐ But the CAUSE is a third state: `.github/workflows/pr-agent.yml` **never created a workflow run**.
    `actions/workflows/pr-agent.yml/runs?branch=feature/plan-15-security-pipeline-modes` returns
    `total_count: 0`, and the branch has exactly ONE run of any workflow — `Maven Build`, event `push`.
  - **Zero `pull_request`-event runs exist for the PR, for ANY workflow.** `dependency-review.yml` is
    likewise `pull_request`-triggered and likewise produced no run. The suppression is therefore
    **PR-wide, not pr-agent-specific** — which is what makes it a distinct state rather than a bot fault.
  - The PR is `mergeable: false`, `mergeable_state: dirty`.
- The third member is therefore **`not_triggered`** — *the bot was never asked*. Its remedy is the
  opposite of both existing members: `absent` says investigate the App install and credentials, `stale`
  says re-trigger — and **both are wrong here**, because the reviewer is healthy, correctly configured,
  and simply received no event. ⛔ Do not collapse it into `absent`: an infrastructure-incident
  investigation into a correctly-installed App is a false alarm that costs an operator real time.
- HYPOTHESIS: `pull_request`-event workflow runs are not created while a PR's merge ref is
  uncomputable (`mergeable_state: dirty`), because GitHub cannot materialize `refs/pull/{n}/merge`.
  **This is the leading mechanism, NOT a settled fact** — the correlation is observed on one PR.
  **Confirm/refute artifact**: resolve `#133`'s conflicts, push, and re-query
  `actions/workflows/pr-agent.yml/runs?branch=...`; a run appearing once the PR is mergeable confirms it.
  ⚠ Note a `push` does not re-fire `opened`, so absence of a run after a mere push refutes nothing —
  the check needs a `reopened`/`ready_for_review` or an `issue_comment` trigger to be conclusive.
- ⚠ **Counter-evidence to weigh, do not skip**: pr-agent's `pull_request` path DID succeed on
  `feature/deployment-diagram-type` at 2026-07-29T19:02:22Z, and the only `pull_request` run of
  2026-07-30 (08:14:57Z, `fix/benchmark-coverage-leftover-bash`) concluded **`skipped`** — a
  *different* outcome from "no run at all". A competing mechanism (the v0.17.0 reusable-workflow guard
  at `15376a19`, pinned in both workflow files) is therefore live and must be eliminated at D1 rather
  than assumed away. **`skipped` and `no run created` are two distinct states; do not merge them.**
- HYPOTHESIS: no consumer branches on the member set in a way that a sixth member would break —
  confirm/refute by enumerating readers of the taxonomy (verify-at-outline). An asserted absence:
  verify it, because D2's whole safety property is that no verdict moves.
- Verify-first clause: D4(c) is the load-bearing test. If the `stale` member changes any merge
  outcome, the plan has overreached and must narrow — the value here is entirely in the naming.

## ⛔ Prohibited remedies

- **Do NOT fix this by crediting stale participation, and do NOT soften the gate.** Widening what
  counts as participation would trade a misleading label for an unsound gate — *the exact failure mode
  this epic is named after.*
- ⚠ **`absent` defends itself as "the fail-closed default". That defence does not apply here:**
  fail-closed governs the *outcome*, not the *naming*. The closed outcome is right either way, and
  there is no safety gained by describing a healthy reviewer as one that never engaged. Do not let the
  fail-closed framing close this question.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — the five-member failure taxonomy table and the three contradicting entries.
- HYPOTHESIS: `.../workflow-integration-github/scripts/github_pr.py` — where the currency test
  discards the distinguishing evidence on the way to `absent` (verify-at-outline).
- HYPOTHESIS: `.../automatic-review/SKILL.md` — the `{participated_bots}` / `{refused_bots}` template
  surface, if a sixth member must be rendered (verify-at-outline).
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and the
  participation-classification tests.

## Dependencies and Sequencing

- Depends on: none.
- Sequenced BEFORE **PLAN-PR-006**, so that plan extends a settled taxonomy rather than racing one.
- Overlaps with: ⚠ **PLAN-PR-005** (C+E) — same contract doc, and both concern participation. **The
  boundary is sharp and must be held**: PR-005 produces or preserves a *credit*; this plan names a
  *correctly-withheld* credit. F survives PR-005's remedy entirely. Sequence, do not pair.
- ⚠ **Cross-link to PLAN-PR-008** (barrier deadlock): a false `absent` and a true `absent` are
  indistinguishable at the barrier, so F is an **input to that deadlock**, not merely a cosmetic
  report defect. Landing this first gives PR-008 a real signal to branch on.
- Adjacent to: **PLAN-PR-002** (org guard). Note the `#1059` evidence shows the org fail-closed step
  PASSED — that guard is not implicated in this defect and must not be adjusted from here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-007-absent-names-two-states-with-opposite-remedies.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
