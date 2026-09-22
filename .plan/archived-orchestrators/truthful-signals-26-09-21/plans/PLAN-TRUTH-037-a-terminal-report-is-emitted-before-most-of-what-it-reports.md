# PLAN-TRUTH-037: a terminal report is emitted before most of what it reports

## ✅✅ RETIRED UNCONDITIONALLY — 2026-08-03. STATUS `superseded`. DO NOT EMIT.

**PR #1080 merged as `e1ae38142`**, corroborated by `code-intelligence-substrate` first-party via
`git log`, **not from the implementing plan's report**. It landed **as scoped**: the
`POST-RUN REVIEW (post-merge, order > 70)` band exists, `post_run_review` is **derived per-step** (never
a list), and `default:lessons-capture` declares it at **`order: 991`** — **after `branch-cleanup` (70)**.

⇒ **The condition set below is discharged.** ⭐ **The insistence was worth it**: the retirement was held
against an *open* PR for a full day, and the sibling's answer confirms the qualifier was right to
demand — *a retirement executed against an open PR is a retirement against a hypothesis.*

⭐ **The cross-epic contract they flagged is now LIVE and it changes this orchestrator's timing**:
this epic now receives its inbox messages **AFTER the merge, not before**. That held on this very drain
(messages written 21:53Z, post-merge). ⚠ ⇒ **The write-direction defect this spec described is closed at
the source**, which is why no successor plan is needed on our side.

⛔ **What is NOT closed, and is tracked elsewhere — do not read this retirement as "the family is
fixed"**: the **upward-facing consumer** (`lessons-housekeeping` at `order: 4` consuming an artifact
produced at 990) survives in merged main, and the **metrics half** (`plan-retrospective` 995 reads
`metrics.md` before `record-metrics` 998 writes it) survives too. See `PLAN-TRUTH-044` D3 and
`PLAN-TRUTH-035`.

---

**Historical record below — retained for the evidence, not for execution.**

⛔⛔ **CONDITIONAL RETIRE — 2026-08-02. DO NOT EMIT.** `code-intelligence-substrate` answered the D0
boundary question: **`PLAN-CIS-028` covers BOTH directions**, and the write direction is explicit rather
than incidental. Their evidence, first-party: CIS-028's D1 names **both** `review-retrospective`
(order 50) **and `lessons-capture` (order 60)**, and its PR **#1080** introduces a
`POST-RUN REVIEW (post-merge, order > 70)` band plus a **derived `post_run_review: true` frontmatter
discriminator** (⭐ membership as a declared fact, never a list), with `workflow/lessons-capture.md`
modified in the same diff as a declared member.

⚠ **The condition is load-bearing**: this is corroborated against the **OPEN** PR #1080
(`mergeable: clean`, `review_decision: none`), **not a landing**. ⇒ **Retire this plan when #1080 lands;
if it lands materially re-scoped, RE-ASK — they will re-answer.** ⛔ A retirement executed against an
open PR is a retirement against a hypothesis.

⭐ **They flagged a contract with us regardless of the outcome**: moving `lessons-capture` **changes when
this orchestrator receives inbox messages**. That is being handled as a cross-epic contract, not as an
internal detail of theirs.

⚠ **One symptom this spec carries that CIS-028 must model, per `review-apparatus-015` item 1 (FOURTH
sighting): the retrospective is ordered wrong from BOTH sides.** `finalize-step-lessons-housekeeping`
needs the retrospective's OUTPUT and runs BEFORE it, while the retrospective needs the worktree and runs
AFTER its destruction. **A remedy that only moves it earlier breaks the first consumer; one that only
moves it later leaves the second.** Forwarded to them.


## ⚠ 2026-08-03 — a third instance was MIS-ATTRIBUTED to this plan; correcting it

`PLAN-TRUTH-010`'s landing message (21:09:09Z) said it *"shipped as PR #1081"*. **#1081 was CLOSED
unmerged**; the real landing was **#1082** at 21:47:23Z. I first recorded that as this plan's strongest
evidence — **a terminal report naming an identifier that was later invalidated.**

⛔ **Struck.** The cause was **`ci pr merge` returning `merged: true` and deleting the branch without
merging.** The landing message **faithfully reported the only signal available to it.** ⇒ **A remedy
that moves the emission later would NOT have prevented it.**

⭐ **The residual signal is real but weak**: a later emission would have had a *second chance* to observe
the truth. That is a benefit of terminal emission, not evidence of the defect. ⇒ **Keep n=2 measured
instances (13 min, 59 min); do NOT count this as a third.** Routed to `review-apparatus` as a
merge-verb defect.

⛔ **The discipline that failed was mine**: an explanation that fits an observation is not the
explanation that produced it.

## ⭐ FOLDED 2026-08-03 — the READ direction recurred, and it is now MEASURED

From the same run (`-012`), the read-direction defect this plan's § *Same root cause* predicts, with a
number attached: `check-artifact-consistency` emitted

```text
affected_files_recall, fail, "Recall 0% below 70% threshold"   (declared 18, found 0)
```

**All 18 files are in merge commit `b713fe4b9`. Real recall is 100%.** The aspect derives the footprint
live from the plan's worktree, which `branch-cleanup` removed two steps earlier — **and an empty
footprint was rendered as a GRADED FAILURE rather than an unavailable measurement.**

⭐⭐ **This is the exact inversion of a false green and it is just as bad**: the coverage aspect put a
`fail` on a plan that achieved **full** declared coverage.

### ⛔ 2026-08-03 — THIS INSTANCE IS PRE-FIX. Correcting my own forwarding.

I forwarded it to `PLAN-CIS-028` as evidence that *"re-ordering is not enough, the reader must also fail
closed"*. **They answered that the obligation already exists, and they are right.**

✅ **Verified first-party** (`git log --first-parent origin/main`): **`b713fe4b9` (#1082) sits BELOW
`e1ae38142` (#1080)** ⇒ **#1082 merged FIRST**, so the `check-artifact-consistency` that graded
`recall 0%` was the **pre-fix reader**. On merged main today it carries a `FOOTPRINT_UNRESOLVED`
sentinel and a named `footprint_resolved` predicate, with an explicit warning that `not footprint` is
**not** equivalent — an unresolvable footprint yields `inconclusive`, never a graded `fail`.

⛔ **I did not check the merge ORDER before drawing an "it survives in main" conclusion from a
post-merge observation.** That is the same class of error as the `#1081` mis-attribution earlier in this
same drain — **an artifact observed after a fix is not an artifact produced after a fix.**

✅ **What survives**: my *framing* — *a graded `fail` on an absent input is the exact inversion of a
false green* — was kept by them as sharper than the one in the fix. ⇒ **The framing was worth
forwarding; the "still open" claim was not.**

⇒ **Genuinely still open is only the CAPTURE side** (`branch-cleanup`/`push` persists the realized
footprint — *capture, don't derive*), which is **`PLAN-CIS-034` D4**, theirs. ⛔ **`base..HEAD` stays
out of the chain — measured at 4.6× over-count on #1079, because sibling landings contaminate any such
range.**

epic: truthful-signals
workstream: WS-01

## Objective

The `kind: landing` inbox message is the epic's **summary of record** for a plan. It is written by
`lessons-capture` at **index 7 of 12** in `DEFAULT_PHASE_6_STEPS`. The merge is index 9. Metrics,
archive, retrospective, cache-sync and the operator report all follow.

⇒ The landing message is the **first** artifact a plan produces about itself and is consumed as the
**last word**. It cannot carry the merge SHA, the merge status, the token totals, the archive path, or
the retrospective's findings — essentially all of its own substance.

**Filed by `review-apparatus` (`-013`), then AMENDED by the same sender (`-014`) after an operator
correction.** ⛔ **Scope from `-014`, not `-013`** — `-013` proposed "emit it after the merge", which is
still wrong: the merge is only step 9 of a longer tail.

## The rule, in one line

> **A terminal report must be a terminal action.** If an artifact is defined as "what this run
> concluded", every step that can change the conclusion must already have run. Emitting it earlier does
> not make it early — it makes it **a forecast presented as a record**.

## OBSERVED evidence

- **Ordering**: `_manifest_core.py:249-262` — `lessons-capture` index 7, `branch-cleanup` index 9.
- **Unconditional emission**: `lessons-capture.md:233` — *"the `kind: landing` message is
  unconditional"*; `:91` is the write call. **One emission point, and it is pre-merge.**
- **Measured gap, n=2, and the SPREAD is the finding**: #1070 landing 19:05:08Z → merge 19:18:00Z
  (**13 min**); #1077 landing 11:40:51Z → merge 12:39:52Z (**59 min**). ⛔ **4.5× variance across two
  consecutive plans** — this is not a narrow race, and any remedy assuming a small window is
  mis-specified.
- **Message-stream bracket**: #1077's `-002..-007` written 11:41–11:43 (pre-merge), `-008..-018` written
  **13:17–13:22** (post-merge). ⭐ **Eleven of eighteen messages — the majority, and the substantive
  half — postdate the "landing" by ~1h36m.**
- **The other direction**: #1078's landing said "merging" at 12:57:49Z; the PR was still open at filing.

## ⭐ Same root cause as the read-direction defect

| Direction | Instance | Symptom |
|---|---|---|
| **read** | `plan-retrospective` (17) reads a worktree `branch-cleanup` (16) deleted | confident **wrong FAIL** — `affected_files_recall: 0%` when true recall was 100% |
| **write** | `lessons-capture` (7) reports an outcome `branch-cleanup` (9) produces | confident **unverifiable claim** |

⇒ Ordering is chosen by *"what logically concludes the plan"* rather than *"what each step needs to
already exist / not yet be destroyed"*. **One ordering defect, two directions.**

## ⛔⛔ BLOCKING PRECONDITION — a sibling plan may already own the read direction

`code-intelligence-substrate` has **`PLAN-CIS-028` (`post-run-steps-ordered-before-their-evidence`)
RUNNING**. By its name it works the **read** direction of this same family.

⛔ **D0 MUST resolve the boundary with CIS-028 before any implementation.** A question has been routed
to that epic's inbox. ⚠ **Do not infer its scope from its slug** — that is precisely the inference
discipline this epic exists to enforce; `review-apparatus` explicitly declined to guess and so must we.
**If CIS-028 covers both directions, this plan is absorbed and retired.**

## Deliverables

1. **D0 — GATE: resolve the CIS-028 boundary** (above), then derive the per-step
   **reads-from / writes-to** dependency the ordering must satisfy. ⛔ Population derived from the
   manifest, not sampled.
2. **D1 — the landing message becomes a terminal action**, anchored on the plan's **terminal state**,
   not on the merge. ⛔ **Do NOT simply move `lessons-capture` later** — the worktree is gone by then,
   which is exactly how the read-direction defect broke. Prefer splitting the kinds
   (`submitted` early with what is known, `landing` at terminus).
3. **D2 — a message may not assert an outcome it cannot observe.** ⚠ `merge_status: unknown` is a
   correct answer; omitting the field and writing "merging now" in prose is not.
4. **D3 — the completion oracle.** ⭐ `review-apparatus` reproduced the defect while filing it: it
   replaced the landing message with `ci pr view`, confirmed #1078 merged, marked the plan shipped —
   **and was still wrong**, because `manage-status list` showed the plan `in_progress` at `6-finalize`.
   ⇒ **Neither the message nor the PR state is the oracle; the plan's own terminal status is.**
   Discriminator confirmed by contrast: #1077 is *absent* from `manage-status list` because it reached
   `archive-plan`. **A plan is complete when it leaves the active status list, not when its PR merges.**
5. **D4 — a derived test.** Assert the emission index of the `kind: landing` write is greater than the
   index of every step named in the landing template's own fields. Verified to FAIL pre-fix.

## Claim Labels

- **OBSERVED (by the filer, source-confirmed with line references)**: ordering, the unconditional-
  emission text, both measured gaps, the message-stream bracket, the merged-but-`in_progress` state.
- ⚠ **NOT INDEPENDENTLY RE-DERIVED by this orchestrator** — the line references and timestamps are the
  filer's. They are precise and internally consistent, and one of them (#1077's message bracket) is
  corroborated by our own inbox. **Re-read `_manifest_core.py:249-262` and `lessons-capture.md:233` at
  D0 before scoping** — *a corrective is a hypothesis until the named site is read.*
- **HYPOTHESIS**: `CIS-028` does not cover the write direction. ⛔ **Explicitly unverified by design.**

## Expected Surface

- **HYPOTHESIS**: `manage-execution-manifest/scripts/_manifest_core.py` — `DEFAULT_PHASE_6_STEPS`
- **HYPOTHESIS**: `phase-6-finalize/workflow/lessons-capture.md` — the emission point
- **HYPOTHESIS**: `marshall-orchestrator/standards/inbox-envelope.md` — if a new kind is added

## Dependencies and Sequencing

- ⛔ **BLOCKED on the CIS-028 boundary answer** (routed; D0 gates on it).
- ⚠ **Absorbs `review-apparatus`'s staged `PLAN-PR-010`** (`landing-message-carries-the-outcome-post-
  merge`), handed over at operator instruction and **not started by them**.
- ⚠ Adjacent to `PLAN-TRUTH-032` (inbox protocol / quiescence signal) — **032's termination signal and
  this plan's terminal-report anchor are the same question from two ends. Strong candidate to merge;
  evaluate at D0.**
- ⛔ Epic is **AT CAP (`parallelization_scope` = 1)**.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-037-a-terminal-report-is-emitted-before-most-of-what-it-reports.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
and the sole sanctioned write mechanism are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
