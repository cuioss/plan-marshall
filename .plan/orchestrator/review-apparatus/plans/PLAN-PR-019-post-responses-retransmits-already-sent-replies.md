# PLAN-PR-019: `post_responses` re-transmits already-sent replies, and reports the re-sends as work done

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — ⛔ THIRD recorded occurrence, and it had no owner until now

Drained 2026-08-03 from `truthful-signals-014`, filed there explicitly as a **recurrence, not a new item**.

| # | Where | When |
|---|---|---|
| 1 | consuming project, round-6 findings item 6 (original) | — |
| 2 | PLAN-31B | — |
| 3 | **PLAN-31C** — round 2 reported `count_responded: 7` for **3** newly-decided dispositions | 2026-08-01/02 |

⛔⛔ **Three plans, three rounds of evidence, one unfixed row — and it was carried as a recurrence line
under other findings each time, so it was never staged by anyone.** ⭐ **That is itself the finding**: a
defect recorded only as an appendix to other defects accumulates sightings without ever acquiring an owner.
This spec exists to end that.

## Objective

`github_pr post_responses` is not idempotent across rounds. On PLAN-31C round 2 it **re-transmitted all
four round-1 replies** alongside the 3 genuinely new ones and reported `count_responded: 7`.

**Two distinct defects, and the second is the one this epic cares about:**

1. **The re-transmission itself.** Duplicate replies land on the reviewer's threads — noise on a third
   party's surface, and on a rate-limited bot it is spend against a quota this epic is separately fighting
   to conserve (see PLAN-PR-006 § diff-size, PLAN-PR-008).
2. ⛔⛔ **The count is reported as work done.** `count_responded: 7` for 3 decisions is a **confident
   affirmative over an action that mostly did not need to happen** — a metric that overstates responsiveness
   by 133% on this instance. Any consumer reading it as "replies this round" is wrong, and the
   `review-retrospective` %-resolved figures are computed from this family of counts.

⭐ **The polarity is worth naming**: unlike most of this epic's findings, the *action* is harmless-ish and
the *signal* is the defect. **Do not scope this as "stop double-posting" and leave the count.**

## Deliverables

1. **D1 — GATE (mutates nothing): establish the idempotency key that SHOULD exist, and whether one does.**
   Determine what `post_responses` uses to decide a disposition still needs transmitting, and why a
   round-1 reply re-qualifies in round 2. ⚠ **Verify-at-outline: an asserted absence.** ⛔ **Derive every
   consumer of the returned count** before changing its meaning — the standing rule that a list of call
   sites is a SAMPLE has bitten this epic twice.
2. **D2 — transmission is idempotent per (thread, disposition).** A reply already posted for an unchanged
   disposition is not re-sent. ⚠ **A disposition that genuinely CHANGED between rounds must still be
   transmitted** — the fix is a key, not a suppression.
3. **D3 — the count reports what it names.** Distinguish newly-transmitted from already-satisfied.
   ⛔ **Do not silently redefine the existing field** — D1's consumer derivation decides whether to narrow
   it or add a sibling; a narrowed field with unmigrated consumers moves the defect rather than fixing it.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) The PLAN-31C shape: 4 round-1 replies + 3 new
   dispositions in round 2 transmits **3** and reports **3**. (b) A disposition that changed between rounds
   **is** re-transmitted. (c) The consumer population D1 derives is non-empty-asserted and every member is
   covered — copy `test/_shared/_dispatch_roster.py`.

## Claim Labels

- OBSERVED (filer, first-party across three plans): the re-transmission and the `count_responded: 7` for 3
  dispositions. ⚠ **Re-derived by nobody here**, and the round-6/round-7 evidence comes from a consuming
  project at bundle **0.1.1276**, which predates our tree. ⛔ **Re-ground before scoping** — and check
  whether any of the three sightings postdates a change to this surface.
- ⚠ HYPOTHESIS: that all three sightings share one root cause. **Three occurrences of one symptom are not
  three occurrences of one bug** — D1 confirms or splits them.
- ⚠ UNKNOWN: whether duplicate replies materially affect bot rate-limit consumption. Relevant to severity,
  not to correctness. **Do not block the fix on measuring it.**

## Expected Surface

⛔ **Added 2026-08-08 — this spec was staged WITHOUT one, so the `next` verb's disjointness admission
test had nothing to read.**

- **OBSERVED** (orchestrator-verified at HEAD, 2026-08-08):
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  § `cmd_post_responses` (`:1333`) and the `_RESPONDABLE_RESOLUTIONS` selection loop.
  ⚠ **The file was modified by `#1118`** (+90 lines, participation plumbing) — a different function, but
  re-ground the line numbers.
- **HYPOTHESIS** (verify-at-outline): the consumer set of `count_responded`, including
  `finalize-step-review-retrospective`'s %-resolved computation. D1 DERIVES it.
- **OBSERVED**: tests under `test/plan-marshall/workflow-integration-github/**`.

## ⭐⭐ D1's asserted absence is now CORROBORATED first-party — 2026-08-08

The spec's central claim was labelled an asserted absence owed verification. The orchestrator read
`cmd_post_responses` at HEAD and **confirms it**:

- The verb selects **every** `pr-comment` finding whose `resolution` is in `_RESPONDABLE_RESOLUTIONS`
  and whose `pr_number` matches the PR being responded to. There is **no transmitted/acknowledged
  marker anywhere in the selection predicate** — nothing records that a disposition was already sent,
  so a round-1 reply re-qualifies in round 2 exactly as the PLAN-31C evidence describes.
- ⭐ **The verb is already careful in a NEIGHBOURING dimension, which sharpens the finding rather than
  softening it.** Its `pr_number` gate exists precisely because a plan-scoped store would otherwise
  **misdeliver** another PR's dispositions "while the return still reports `count_untransmitted: 0` — a
  confidently green report for a partly-misdelivered action" (its own docstring). ⇒ **The author already
  reasoned about a confidently-green count over a wrong row set, and closed the cross-PR case while
  leaving the cross-ROUND case open.** The missing key is not an oversight of the concept; it is the
  same concept not carried to the second axis.
- ⇒ **D1's absence question is SETTLED; D1's remaining job is the CONSUMER derivation**, which is
  untouched by this check and still owed. Do not re-litigate whether the key is missing — derive who
  reads the count before D3 changes its meaning.

## ⭐⭐ THE REFERENCE IMPLEMENTATION ALREADY EXISTS IN-TREE — relocated from the epic ledger 2026-08-08

⛔ **This diagnosis was sitting in `epic.md` § Open Defects marked "no owning plan", six days after this
plan was staged to own it.** Relocated here because the spec is the authority and a defect write-up
duplicated in the ledger is the source-of-truth-duplication archetype. **It is the most actionable
content this plan carries — do not re-derive any of it.**

**The root cause, and the documented rationale is INVERTED.** `verification-feedback.md` Step 8 claims
*"already-responded findings are terminal and no longer pending"*. But `_RESPONDABLE_RESOLUTIONS` **is**
the terminal set — terminal is the **selection** criterion, not an exclusion criterion. ⇒ **A finding
becoming terminal is what makes it eligible, and it then stays eligible forever.** The doc reads as if a
guard exists; the code has no prior-transmission term at all.

⭐⭐ **The sibling provider already gets this right, and it is the model to copy:**

| Element | `workflow-integration-sonar/scripts/sonar.py` | `workflow-integration-github/scripts/github_pr.py` |
|---|---|---|
| imports `mark_finding_responded` | ✅ `:718` | ❌ none |
| skips on `finding.get('responded')` | ✅ `:748-749` | ❌ none |
| sets the marker after sending | ✅ `:764` | ❌ none |

⛔⛔ **A naive `grep responded` finds hits in BOTH files and suggests parity.** GitHub's `responded`
occurrences are a **local output accumulator of the same name** — not a persisted per-finding marker.
⭐ **The discriminator is `mark_finding_responded` / `finding.get('responded')`, never the bare word.**
This is a same-name-different-thing trap, and it is exactly why the defect survived three sightings.

**Corrective (adopt as D2/D3's shape):** add a per-finding `responded` marker mirroring Sonar; the
predicate becomes `terminal AND NOT responded`; ⛔ **set the marker in the SAME unit of work that sends
the reply** — a marker written in a later step reintroduces the gap it closes.

**Prior sightings and their honest weight:** 9 duplicated thread replies (plan-marshall), 11 threads
(API-Sheriff `#138`), and the PLAN-31C `count_responded: 7` for 3. ⚠ **PR `#1071` escaped only because
the store held exactly ONE finding — n=1 masked it, which is not evidence of safety.** ⛔ **Three
observations are not a rate; do not derive one.**

⛔ **If this widens, name the POPULATION**: every external-transmit verb needs auditing for a
prior-transmission term, and that sweep **crosses both providers** (GitHub and Sonar, and GitLab if it
transmits). D1's consumer derivation and this population question are different derivations — do both or
say which was skipped.

## Dependencies and Sequencing

- ⚠ Touches `workflow-integration-github/scripts/github_pr.py`, which **PLAN-PR-001 (shipped), PLAN-PR-005
  and PLAN-PR-013 also claim.** ⛔ **Sequence, never pair.** The functional boundary looks disjoint
  (`post_responses` vs `fetch_findings` vs the participation comparison) but that boundary is **unverified**
  — confirm at D1.
- Adjacent to `finalize-step-review-retrospective`, which consumes response counts (shared with
  PLAN-PR-006's absorbed retrospective item). **Coordinate; do not ship two vocabularies for one count.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-019-post-responses-retransmits-already-sent-replies.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
