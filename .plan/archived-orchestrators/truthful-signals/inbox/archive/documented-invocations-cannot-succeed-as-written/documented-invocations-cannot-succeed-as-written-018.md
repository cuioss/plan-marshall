envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:19Z

component=plan-marshall:phase-6-finalize
category=improvement

# Unattended mode was armed mid-run and nothing records whether it was ever disarmed

The run's defining conversational event was the mid-flight arming of unattended mode. The transcript
records the arming. It records no un-arming, and no artifact establishes the end-of-run state.

## Observed

From this run's `chat_history_analysis` aspect (severity `warning`, and NOT among the eight
candidate-lessons the retrospective routed):

> Unattended mode was armed mid-run and the transcript records the arming but not any un-arming.
> Whether the two plan-local `automatic-review` overrides were restored before the run ended is not
> recoverable from the retained turns, and this retrospective did not verify it.

Everything after that point — the 6-finalize → 5-execute loop-back, the re-fired settle band, and the
merge-queue landing — ran without an operator gate. The composed manifest shows the resulting posture:
`final_merge_without_asking: true`, `pre_merge_comment_barrier: fail_into_loopback`,
`re_review_on_timeout: proceed`, `admin_merge_on_stuck_state: false`.

The aspect correctly notes the knobs live on the **manifest snapshot** — the prescribed per-run
location for finalize knobs — rather than in a tracked configuration file, which is the right design.
That is exactly why the residual state is hard to see after the fact: the snapshot is per-run, and
nothing carries an arming record forward.

## Why the retrospective cannot close this

The chat reduction is signal-selective (9 of 977 turns retained). An un-arming performed without
producing a retained turn would not survive into the population. So the aspect reports *not
recoverable*, correctly — and *not recoverable* is indistinguishable from *never happened* to every
downstream reader.

## Rule

Arming unattended mode should be a **recorded, structured act with a scope**, not a conversational
one:

- Record the arming as a step fact or a plan-state field (`unattended_armed_at`, the overridden knob
  set, and the intended scope), so the residual posture is derivable from plan state rather than from
  a transcript that is sampled before anyone reads it.
- Make the finalize run report the posture it actually ran under, in the run's own artifacts. A
  reader should be able to answer "did this plan merge unattended, and were the overrides
  plan-scoped?" without reconstructing it from chat.

A confident "the overrides were plan-local, so nothing leaked" is precisely the claim this run cannot
substantiate — and the epic's own theme is a confident signal that hides its caveat.
