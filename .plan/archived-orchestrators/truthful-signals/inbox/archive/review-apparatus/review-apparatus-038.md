envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-13T20:56:49Z

# Five non-charter items from `plan-pr-046`'s landing (PR #1477)

Transferred from `review-apparatus` on 2026-09-13, drained from that epic's inbox as
`plan-pr-046-002` … `-006`. ⭐ **Routed here by the standing three-way rule**: none is PR/review
subject matter, so the PR test does not claim them. They are `plan-retrospective`,
`phase-6-finalize` and agent-behaviour items — and the first three are the *measurement-honesty*
theme this epic owns. All five are first-party to that plan's own finalize on PR #1477 (merged
`77cb2e251b348ce3e840ac1e565f5426f2d587de`).

⚠ **Leads, not instructions.** Each is the sending plan's own observation; the mechanisms below were
not re-derived in this checkout.

## 1. A post-merge empty base-ref diff is graded FAIL over no evidence

`plan-marshall:plan-retrospective`, category bug, confidence high.

`check-manifest-consistency` graded `branch_cleanup_changes` as **fail** because the plan's diff
against `origin/main` was empty — which is the *normal* state at finalize order 995, since the plan is
already merged by then. ⛔ The aspect reported `diff_available: true` while grading, so the verdict
reads as a checked negative rather than as an unobservable one.

⭐ The evidence was reachable: the sibling `check-outline-vs-shipped` resolved **31 realized paths**
through the shared resolver **in the same run**. ⇒ The remedy is not "grade it pass" — it is
`indeterminate` with the reason, or use the resolver the sibling already uses.

## 2. `permission-prompt-analysis` returns an empty list from a channel that cannot carry prompts

`plan-marshall:plan-retrospective`, category bug, confidence high.

The aspect reaches only the **reduced** transcript, whose reduction keeps operator turns and gate
decisions *by construction* (5 of 1810 messages on this run). A permission prompt is neither, so the
channel cannot carry the subject.

⭐ **That run recorded `coverage: not_evaluated` rather than letting the empty list read as a clean
zero — which is the correct behaviour and is why this is a design item, not an incident.** The open
question is whether the aspect should read an unreduced channel or be retired; publishing
`not_evaluated` forever is a third option and is honest, but it means the aspect never answers.

## 3. Give `pre-submission-self-review` a computed convergence signal

`plan-marshall:phase-6-finalize`, category improvement, confidence high.

On PR #1477 the step fired **7 times with 6 loop-backs**, and nothing in the loop computed whether it
was converging. ⛔ `done` is not convergence — the epic's own recorded rule — and a loop with no
convergence signal cannot distinguish "found a new class of defect" from "re-finding the same one".
Finalize was 48.5% of a 6.77M-token run, more than execute.

## 4. Re-derive the declared footprint when finalize edits widen it

`plan-marshall:phase-6-finalize`, category improvement, confidence medium.

10 undeclared files were modified (threshold 5), all during finalize as self-review rounds reached
contract docs and build files. ⛔ **This is the third consecutive landing in `review-apparatus` whose
realized footprint exceeded its declaration**, and on PR #1473 the undeclared half silently discharged
another plan's staged deliverable. `reconcile-scope` already detects the drift; **nothing in finalize
calls it.** Every `affected_files`-derived finalize step under-scopes whenever scope moves during
execute.

## 5. Verb-paraphrase remains the dominant argparse rejection despite the recurrence checklist

`plan-marshall:persona-plan-marshall-agent`, category anti-pattern, confidence medium.

The agent keeps inventing a plausible verb instead of reading the declared one, and the existing
recurrence checklist has not moved the rate. ⚠ Confidence is the sender's own *medium* — the claim
that the checklist is ineffective needs the rejection population behind it before anyone acts on it.
