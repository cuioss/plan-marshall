envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:27Z

component=plan-marshall:phase-6-finalize
category=improvement

Relayed from Token-Sheriff PLAN-07 (PR #715 / `8f3b8aee`). Three process observations from one run, bundled because they share a shape: **a non-answer must not be read as an answer.** A reviewer's detail, a poll timeout, and a harness-killed build each produce something that looks like a verdict and is not one. The bundling is the relaying orchestrator's judgement — split them if you disagree.

## A — accept a reviewer's intent, verify its detail

# Candidate lesson (process observation): accept a reviewer's intent, verify its detail

Source: process observation from plan `test-signal-and-assertion-integrity`, PR #715,
CodeRabbit review.

## Observation

CodeRabbit proposed adding an AsciiDoc cross-reference using the anchor
`#signal-integrity`. The real anchor in the target document is `[[_signal_integrity]]`.
The suggestion was applied with its detail corrected. Applied verbatim it would have
produced a cross-reference that RENDERS as a link and resolves to nothing.

## Proposed rule

A review suggestion carries two separable things: the intent (add the cross-reference —
correct and worth applying) and the concrete detail (the anchor spelling — wrong). Accept
the first, verify the second against the target before applying. Reviewer-suggested
identifiers, anchors, paths, and flag names are exactly the class an LLM reviewer produces
plausibly and without checking, and the failure is silent at the point of application: a
broken AsciiDoc xref does not fail a build, it renders as a link.

Verify any identifier a suggestion introduces against the artefact it names.

## Why it belongs to this epic

Same theme in a new place: the rendered link CLAIMS to point at a section and does not.
Nothing in the build or the review reports on that gap.

---

## B — a poll timeout is a no-verdict, not a failure

# Candidate lesson (process observation): a poll timeout is a no-verdict, not a failure

Source: process observation from plan `test-signal-and-assertion-integrity`, CI polling on
PR #715.

## Observation

Three CI polls returned `deadline_exceeded`. Each was read as "no verdict yet", not as
"the check failed". The pending set then drained 3 -> 1 -> 0 across subsequent polls and
every check came back green.

Filing a `ci_failure` finding on any of those three returns would have recorded a failure
that never happened — and, downstream, would have blocked a merge on a fabricated red and
sent the run hunting a defect with no cause.

## Proposed rule

Distinguish "the check reported a failing verdict" from "the read did not complete". They
are different facts and only the first is a defect signal. A timeout, a deadline, a
network error, and an unreadable log are all absence-of-observation; converting any of
them into a negative verdict manufactures evidence.

The same discipline that makes a measured zero require a measurement (see the
`tests_population` candidate in this stream) applies to verdicts: the honest value for an
unread check is UNKNOWN, and unknown means poll again, not fail.

## Why it belongs to this epic

Directly the epic's theme with the sign flipped: instead of a green that establishes
nothing, this is a red that would have been recorded over nothing observed.

---

## C — a harness-killed build is re-attachable, not restartable

# Candidate lesson (process observation): a harness-killed build is re-attachable, not re-runnable

Source: process observation from plan `test-signal-and-assertion-integrity`, whole-tree
build routed through marshalld.

## Observation

A whole-tree build was killed by harness memory pressure. Because it had been submitted
through marshalld, re-attaching with the build_server `wait` verb recovered a build that
was still running SERVER-SIDE at 477s elapsed, and it went on to complete.

A blind re-run would have discarded that in-flight work, paid the full ~24-minute cost
again, and violated the do-not-blind-retry rule for a killed outcome.

## Proposed rule

The client being killed says nothing about the server-side job. "My reader died" and "the
work failed" are different facts, and a killed CLIENT is an absence-of-observation, not a
failed build — so the correct next move is to re-attach and read the outcome, never to
re-submit.

Concretely, on a killed build-wrapper call: establish the job's actual state via the build
server before deciding anything. Blind retry is both wasteful and, when the two runs
interleave, capable of corrupting shared build state.

## Why it belongs to this epic

Same discrimination as the CI `deadline_exceeded` candidate in this stream: a lost read is
not a verdict. Recorded here because the recovery path is specific and easy to miss under
time pressure — the instinct on a killed build is to re-run it.
