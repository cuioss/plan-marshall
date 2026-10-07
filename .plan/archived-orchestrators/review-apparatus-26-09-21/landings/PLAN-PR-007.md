# Landing Analysis: PLAN-PR-007 — `absent` names two states with opposite remedies

epic: review-apparatus
workstream: WS-01
pr: 1118 — merged, squash `fddc4ec8b`

> Written by the `analyze` verb from the operator's pasted finalize report, after corroborating every
> material claim against ground truth. A pasted claim is a lead, never a fact.

## Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1118 merged | **CORROBORATED** | `ci pr view --pr-number 1118` → `state: merged`; `git log` → `fddc4ec8b` on main |
| Plan lifecycle complete | **CORROBORATED** | absent from `manage-status list` (the correct oracle); worktree removed |
| 5/5 deliverables, 21/21 finalize steps | **CORROBORATED as consistent** | commit body enumerates the same five; `--stat` shows 30 files, +3521/−116 |
| 11 inbox messages emitted | ⚠ **CORRECTED — there are 12** | `inbox list` → `count: 12` (1 `landing` + 11 `candidate-lesson`), all valid. The report undercounts by one. ⭐ A message written *after* the report was composed is exactly the batch-self-description defect `PLAN-PR-010` D3 exists to remove — **this landing is a fresh instance of it.** |
| Cache healthy at `0.1.1326` | **ACCEPTED, not re-derived** | Operator-reported; the three-consumer assertion is theirs. Not independently checked here. |

## What shipped

The failure taxonomy went from a five-member closure to **seven**: `participated_stale` (a bot whose
evidence matched a declared publish shape but failed the currency test) and `not_triggered` (no
`pull_request`-event workflow run exists at all — PR-wide, not per-bot). Both **block for a required
bot exactly as `absent` does**, so no merge verdict moved, and each carries a *distinct remedy*
(re-trigger the review / trigger the review at all). Precedence is explicit and reasoned: a refusal
outranks a stale publish; `participated_stale` outranks `in_progress`; `not_triggered` is evaluated
last so it can never override a positive per-bot observation.

## ⭐⭐ The plan's own verdict is the most valuable thing in this landing, and it is correct

> *"The pre-merge barrier blocked once, on this plan's own new `participated_stale` member firing
> against its own PR. Choosing the loop-back over an override is what produced CodeRabbit's review —
> 8 actionable comments including a Major where the plan violated its own fail-closed thesis at a call
> site it had just added."*

**A plan's new gate fired against the plan that authored it, and honouring it produced the review that
caught the plan violating its own thesis.** That is the strongest possible evidence for the member's
value, obtained at no design cost. ⛔ **Record the counterfactual precisely: an override was available
and would have been defensible** — the bot was refusing for reasons outside the repo's control, which
is the exact deadlock `PLAN-PR-008` D3 exists to sanction. Taking it would have merged a Major defect
in the plan's own new code behind a green barrier.

⇒ **This is the epic's first datum on the VALUE side of the override question**, and it belongs to
PLAN-PR-008's D3 escalation: the honest framing for the operator is no longer "pay latency to recover
findings that can never block", but "an override taken at the one observed opportunity would have
shipped a Major". Folded there.

## ⛔⛔ The known defect this landing DID NOT close, and the plan could not have known

Verified by symbol at `github_pr.py` § `_has_update_movement` (`:645-677`):

```
return bool(updated_at) and updated_at != created_at
```

**The currency test that decides `participated_stale` keys on COMMENT MUTATION — no commit SHA is
consulted anywhere.** So the member is honest about *what happened* while resting on the wrong
observable: a bot that reviewed commit N and later edits its comment for any reason still reads as
current for N+1. ⭐ `reviewed_commit_sha` is already stored and is simply not what the barrier reads.

⚠ **This plan's own spec predicted the trap** — it warned that "a detector keyed on diff CONTENT rather
than on HEAD IDENTITY would miss the content-identical rebase". What shipped is keyed on **neither**.
⇒ Owned by **PLAN-PR-013**, whose D3 was re-scoped against this at the 2026-08-08 queue audit: *re-key
the currency test onto HEAD identity*, not *add a comparison*. **Not a defect of this landing** — the
spec scoped naming, not anchoring — but it is why PR-013 remains the queue head.

## The five flagged items — three stand, one is re-attributed, one is re-framed

**1. `enriched.json` dirty on main — REAL, but NOT this run's doing, and already owned elsewhere.**
⛔ **The attribution to "a post-merge step in this run" is REFUTED.** Both files
(`.plan/project-architecture/{default,plan-marshall}/enriched.json`) were **already modified at this
orchestrator session's start**, before PR-007's finalize ran — first-party from this session's own
opening git snapshot. The sibling epic independently recorded the same condition earlier today
("4 architecture hints, deliberately uncommitted"), and **`truthful-signals` PLAN-TRUTH-064 is already
staged to make the guard SEE them**. Current drift is +6/−2 across the two files, consistent with that
same set. ⇒ **Do not file a follow-up plan and do not revert.** Finding `763636` is a duplicate of an
owned item; the correct action is to route the *observation* to the owner, not to open work here.
⭐ The report's own reasoning about the guard is right and worth keeping: `post_run_source_guard`'s
predicate excludes `.plan/`, and these are tracked files inside it — a guard whose scope excludes the
place the writes land.

**2. Full restart owed — STANDS, and is now the blocking next action.** This session loaded skill
bodies from `0.1.1304`, which the finalize sync then orphan-marked. `/reload-plugins` does not re-seat
skill markdown. ⛔ **Nothing may be launched from this session.**

**3. `marshal.json` stale at `0.1.1304` vs installed `0.1.1326` — STANDS, advisory.** `/marshall-steward`
refreshes the provisioning stamps.

**4. The last two commits were never bot-reviewed — STANDS, and it is the sharpest item.** CodeRabbit
refuses to re-review already-reviewed commits; Sourcery is over its diff-character limit; pr-agent
returned contentless guides. **The barrier passed on `participated_but_empty` — participation, not
coverage.** The 14 fixes after CodeRabbit's one real review rest on CI and self-review alone.
⛔⛔ **This is the epic's thesis reproduced by the very plan that widened the taxonomy to state it**, and
it lands on three owners at once:
- `participated_but_empty` clearing a barrier over an unreviewed range → **PLAN-PR-006** (a zero that
  cannot be distinguished from a review) and **PLAN-PR-013** (the anchor).
- CodeRabbit's refusal permanently consuming the range it declined → already folded into
  **PLAN-PR-005** at the 08-08 drain; **this is its second first-party instance.**
- ⭐ The honest reading: **the widened taxonomy made the gap NAMEABLE and did not make it VISIBLE at
  this barrier.** Naming a state is not detecting it.

**5. The token figure understates the run — STANDS, and the structural cause is already known.**
6.9M is the dispatched-subagent population; the same window carries 9.9M inline main-context tokens and
a 65.1M billing-weighted total. ⛔ **Three different populations that must never be summed.** The
ordering cause — `record-metrics` runs *after* `plan-retrospective`, so the retrospective analyses a
total that does not yet include it — is `truthful-signals` **PLAN-TRUTH-066**'s subject
(*"the retrospective reads a record that is not yet written"*), already staged there. ⇒ **Not ours; do
not re-stage.** ⭐ Consistent with the standing rule that every per-phase figure is retired and every
published total must name its population.

## Reconciliation Actions

- [x] row `status` → `shipped` — `queue --transition PLAN-PR-007 --status shipped`
- [x] row `pr` = `1118` (stamped from PR state at the 08-08 audit, before this report arrived)
- [x] row `landing` = `landings/PLAN-PR-007.md`
- [x] row `plan_marshall_plan_id` = `absent-names-two-states-with-opposite-remedies`
- [x] epic.md queue row and START-HERE reconciled from status.json
- [x] Item 1 re-attributed to `truthful-signals` PLAN-TRUTH-064; item 5 to PLAN-TRUTH-066 — neither staged here
- [x] The override counterfactual folded into PLAN-PR-008 D3
- [ ] ⛔ **12 inbox messages queued and NOT drained by this analysis** (1 landing — this one — plus 11
      `candidate-lesson`). A separate `analyze` pass owns them.

## Parallelization consequence

None observed — the plan ran alone against `N=1`. ⚠ But the run consumed **7h27m wall-clock** for one
plan at the cap, and the barrier loop-back is what produced the value. **Do not read the duration as an
argument for raising `N`**: the sequencing constraint here is the merge mutex and the shared
participation-classifier surface, neither of which duration speaks to.
