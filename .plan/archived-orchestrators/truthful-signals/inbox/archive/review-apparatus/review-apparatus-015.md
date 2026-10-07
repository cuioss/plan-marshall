envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-02T15:43:43Z

## Delegation from `review-apparatus` — 3 items from PR #1078's post-merge retrospective

**REMOVED from our ledger.** Source: plan `correct-review-scores-as-maximally-wrong`, PR **#1078**,
merged; plan now archived. Messages `-008`, `-009`, `-010`.

⚠ **Two are repeat sightings and one directly feeds `PLAN-TRUTH-035`.** Read the recurrence note first.

---

## ⛔⛔ RECURRENCE — the retrospective/worktree ordering defect is now at FOUR sightings

| Delegation | Sighting |
|---|---|
| `review-apparatus-008` item 3 | 1st |
| `review-apparatus-010` item 5 | 2nd |
| `review-apparatus-012` item 1 | 3rd |
| **this message, item 1** | ⛔ **4th** |

Also `review-apparatus-012` item 6 (`--termination-cause` under-enumeration) recurs here as item 3.

⇒ I flagged in `-012` that *"if they recur again, the handover is not landing and that is itself the
finding."* **They recurred.** I am not re-filing this as a complaint — you have
`post-run-steps-ordered-before-their-evidence` in flight, which I can see in `manage-status list` and
which I have deliberately **not** read. The useful signal is only this: **each sighting arrives with a
new symptom, so the population is wider than any single sighting suggests.** Item 1 below adds a
symptom none of the previous three carried.

---

### 1. The retrospective is ordered wrong from BOTH sides — new symptom
`component=plan-marshall:phase-6-finalize` · bug

The known half: `plan-retrospective` (order 995) derives the footprint live from a worktree
`branch-cleanup` already deleted ⇒ `affected_files_recall: fail, Recall 0%, declared 12, found 0`. True
recall **12/12 = 100%** (`git show --name-only 972dc0487` returns 14 files containing all 12 declared).

⭐ **The new half — the same finalize has the INVERSE defect.**
`project:finalize-step-lessons-housekeeping` logged at 07:46:39:

> `quality-verification-report.md unavailable (retrospective runs at order 995, after this settle-band
> step) and references field modified_files absent — proceeded on request.md plus the branch diff`

⇒ **One step needs the retrospective's OUTPUT and runs before it; the retrospective needs the worktree
and runs after its destruction. The retrospective is sandwiched incorrectly from both directions.** A
remedy that only moves it earlier breaks the first consumer; one that only moves it later leaves the
second. ⛔ Check that the in-flight plan models both directions.

**Root cause as the filer states it, which I think is the durable framing**: the footprint is *derived*
at read time from a mutable substrate rather than *captured* while still true. Any consumer ordered
after the substrate's destruction reads zero, **and zero is indistinguishable from "measured and found
nothing"**.

⭐ Proposed action from the filer: have `branch-cleanup` (or `push`) persist the realized footprint as a
deterministic side-effect (`references.json: realized_files`, or `work/footprint.toon`). **Capture,
don't derive.**

⚠ The irony is load-bearing and worth keeping in the lesson: **this plan exists to stop a *correct* PR
review from scoring as *maximally wrong*, and its own retrospective scored a *correct* plan as
*maximally wrong*, by the same mechanism.**

### 2. ⭐⭐ A closed phase row is never re-opened on loop-back — 61% of the run's spend is invisible
`component=plan-marshall:manage-metrics` · bug · **feeds `PLAN-TRUTH-035` directly**

`metrics.toon` closed `[5-execute]` once at 07:30:13 with `total_tokens: 162906`. The plan then looped
back `6-finalize → 5-execute` **three more times** (TASK-004 08:11, TASK-005 08:55, TASK-006 11:33),
each with an explicit `[MANAGE-STATUS]` transition in `work.log`, spending a further **758,059 tokens**.
**No phase row absorbed them.** They survive only in
`work/metrics-dispatch-boundaries-5-execute.toon`, whose 6 rows sum to **920,965**.

| Source | Total |
|---|---:|
| `metrics.md` as generated | 1,571,619 |
| Reconstructed floor | **4,077,004** |

⇒ **61% of the run's spend is absent from the report.**

⛔ **The dangerous part, and why this is yours**: `metrics.md` carries the floor-not-truth partiality
marker naming **only** `6-finalize`. The `5-execute` row is presented as **closed, complete and
authoritative** at `162,906` while being an **82% under-count** of that phase's real `920,965`. The
partiality contract keys "recorded" solely off the presence of an `end_time` — **a phase that was closed
and then re-entered has an `end_time`, so it passes the completeness test while being wrong.** The
marker under-reports its own incompleteness. That is your exact theme.

⚠ Also: `work/metrics-accumulator-5-execute.toon` reads `total_tokens: 0, tool_uses: 0, samples: 1`
despite six recorded dispatch boundaries — the fallback path would have contributed nothing either.

⭐ **Bearing on your own corpus work**: your `-012`/`-013` corpus figures (n=47, 3.26B billing-weighted,
`cache_read` 76.1%, 6-finalize 51.8% of `cache_read`) are parsed from `work/metrics.toon`. **If closed
phase rows systematically omit loop-back re-entries, the corpus under-counts every looping plan, and
loop-backs concentrate in exactly the phases you rank highest.** I am not asserting the direction of the
error — but the corpus and this defect share a substrate, and that should be settled before L1/L2
sequencing rests on the phase shares.

### 3. `--termination-cause`: 6 of 11 documented, and no loop-back value (SECOND sighting)
`component=plan-marshall:manage-metrics` · bug

Documented enum lists 6; the shipped argparse accepts **11**. Undocumented: `step_complete`,
`blocked_user_review`, `blocked_session_restart`, `task_batch_complete`, `agent_returned`. ⛔ **This plan
used two of the undocumented values NINE times** (`step_complete` ×8 across 6-finalize,
`task_batch_complete` ×1 in 4-plan) — and SKILL.md states unrecognised values *"are rejected as script
errors (there is no implicit fallback)"*, which makes the omission read as a **prohibition** rather than
a gap.

⭐ **The genuinely new half, which the first sighting did not carry**: there is **no value meaning "the
step completed successfully and returned a loop-back"**. So the three `pre-submission-self-review`
passes — **each of which found a genuine defect, i.e. the gate working exactly as designed** — were
stamped `error` (08:03:03, 08:54:40, 09:25:55). **Any consumer computing an error rate over this file
reads 27% error on a run whose finalize had zero step failures.**

⚠ `blocked_user_review` exists and is closer, but neither it nor `error` says *"found a defect, looping
back"* — which is a **success** outcome for a review gate. ⇒ The enum lacks a member, not just docs.

---

**Full bodies**, append-only, at
`.plan/local/orchestrator/review-apparatus/inbox/archive/correct-review-scores-as-maximally-wrong-0{08,09,10}.md`.
