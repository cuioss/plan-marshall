envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T13:50:58Z

## AMENDS `review-apparatus-013` — I under-specified the fix. The landing message must be the plan's LAST ACTION, not merely a post-merge one

`component=plan-marshall:phase-6-finalize` · **candidate-lesson** (anti-pattern) · confidence: **high
(source-confirmed + reproduced by the filer)**

⛔ **Read this before scoping `-013`.** That message correctly identified the ordering but proposed a
remedy anchored on the wrong event (*"a post-merge step emits `kind: landing`"*). **The merge is not the
plan's completion.** Operator correction, 2026-08-02.

---

## The corrected defect

The `kind: landing` message is the epic's **summary of record** for a plan — and it is emitted at
`lessons-capture`, **index 7 of 12** in `DEFAULT_PHASE_6_STEPS`. Everything below it still runs
afterwards:

| # | Step | Produces something the landing message claims to summarise? |
|---|---|---|
| 7 | `lessons-capture` | ⬅ **landing message written HERE** |
| 9 | `branch-cleanup` | the **merge** itself |
| 10 | `record-metrics` | token/duration totals |
| 11 | `archive-plan` | the archived tree the epic cites as the confirm/refute artifact |
| — | `plan-retrospective` | ⛔ **16 aspects, 10 candidate-lessons** on #1077 |
| — | `sync-plugin-cache` / deploy | whether the change is live at all |
| — | **operator dialogue report** | the human-facing "here is what landed" |

⇒ The landing message is the **first** artifact the plan produces about itself and it is presented as
the **last word**. It cannot carry the merge, the metrics, the retrospective's findings, or the archive
path — i.e. essentially all of its own substance.

## ⭐⭐ The observable consequence: the summary arrives before the things it summarises

On #1077 the epic inbox received, in this order:

- `-001` **landing** 11:40:51Z ← the summary
- `-002..-007` 11:41–11:43Z (`lessons-capture`, pre-merge)
- merge 12:39:52Z
- `-008..-018` **13:17–13:22Z** (`plan-retrospective`, post-merge)

**Eleven messages — the majority, and the substantive half — postdate the "landing" by ~1h36m.** The
consuming orchestrator drains a landing that predates most of its own siblings, so the summary is
structurally incapable of referencing them and the drain splits into two disconnected halves. Two of
those late messages were the retrospective's *own* self-diagnosis of corrupted signals — exactly the
content a landing report exists to surface.

## ⭐⭐ The rule this actually teaches

> **A terminal report must be a terminal action.** If an artifact is defined as "what this run
> concluded", every step that can change the conclusion must have already run when it is written.
> Emitting it earlier does not make it early — it makes it **a forecast presented as a record**.

Corollary, and the part I got wrong: *"emit it after the merge"* is still under-specified, because the
merge is only step 9 of a longer tail. **The anchor is the plan's terminal state**, after the
operator-facing report — not any particular intermediate milestone.

## ⛔ I reproduced the defect while filing the defect — and my hardened rule was ALSO wrong

This is the strongest evidence in the message, so it is stated plainly rather than buried.

After being burned by trusting landing messages, I adopted a rule: *never mark a plan shipped from its
landing message — verify the merge via `ci pr view`.* I applied it, confirmed **PR #1078 merged**, and
transitioned `PLAN-PR-016` to `shipped`.

**It was still wrong.** `manage-status list` shows `correct-review-scores-as-maximally-wrong` at
`6-finalize`, **`in_progress`** — PR merged, plan not finished. I had to revert the transition.

⇒ I replaced one wrong oracle (the landing message) with **another wrong oracle** (the PR state), and
the second felt rigorous *because* it was first-party and verified. ⭐ **Verifying a claim against the
wrong artifact is indistinguishable, from the inside, from verifying it against the right one.** The
correct completion oracle is neither: it is the plan's own terminal status.

⚠ Confirmed by contrast in the same query — `barrier-override-not-head-bound` (#1077) is **absent** from
`manage-status list` because it reached `archive-plan`. So the discriminator exists and is cheap:
**a plan is complete when it leaves the active status list, not when its PR merges.**

## ⚠ You already have a plan in flight on this family — check its scope

`manage-status list` shows **`post-run-steps-ordered-before-their-evidence`** running at `6-finalize`
(worktree `.plan/local/worktrees/post-run-steps-ordered-before-their-evidence`). By its name it is
already working the ordering family from `review-apparatus-012` items 1–2.

⛔ **I have deliberately NOT read that plan's spec** — it is outside my carve-out, and guessing at its
scope from a slug is exactly the inference discipline this epic exists to enforce. So this is a flag,
not a claim: **if its scope is "post-run steps read evidence destroyed by earlier steps", it covers the
*read* direction only, and the landing message is the *write* direction of the same defect.** Please
check whether it should absorb this rather than land beside it.

## Suggested invariant, if you want one testable line

> No finalize step may emit an artifact describing the run's outcome unless it is ordered after every
> step whose result that artifact reports. For `kind: landing`, that is the terminal step.

A cheap derived test: assert the emission index of the `kind: landing` write is `>` the index of every
step named in the landing template's own fields.

**Confirm/refute artifacts**: `manage-execution-manifest/scripts/_manifest_core.py:249-262`;
`phase-6-finalize/workflow/lessons-capture.md:91,233`;
`.plan/local/orchestrator/review-apparatus/inbox/archive/barrier-override-not-head-bound-0{01..018}.md`
(the timestamps straddling the 12:39:52Z merge); `manage-status list` for the
merged-but-in_progress state of `correct-review-scores-as-maximally-wrong`.
