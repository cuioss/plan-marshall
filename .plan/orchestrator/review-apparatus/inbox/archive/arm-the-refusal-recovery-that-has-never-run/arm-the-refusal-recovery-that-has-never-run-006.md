envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:29:23Z

# Gates that read a document cannot catch a document that cannot be executed

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high

## Context

Q-Gate finding `ed9ef2` records that `pr-review-operations.md` Step 1 instructed the caller to "Capture the PR's title, body and head branch from the return", and promised that "nothing an operator or a reviewer wrote is lost" — while the live `ci pr view` return carried **no body field at all**. A caller following the document literally reaches Step 3 ("Write the captured body") holding nothing.

That defect survived, in order: 5 `pre-submission-self-review` rounds, a clean `project:finalize-step-plugin-doctor` gate (7 skills gated, 37 rules, 0 findings), and a CodeRabbit review. It was found by **executing** the close-and-reopen recovery on this plan's own PR #1431.

Separately in the same run, CodeRabbit found four Majors across three rounds that those same doc-reading gates and six whole-tree verifies all missed.

## Root cause

Every gate that missed it reads the document. The one that caught it ran the document. The gates are not individually weak — they are all the same *kind* of gate, so their agreement is one assertion repeated, not independent corroboration. A procedure that is internally consistent on the page is exactly what a reading gate certifies, and exactly what an unexecutable procedure looks like.

## Proposed action

When a plan's deliverable is an **executable procedure** (a documented command sequence a caller is expected to follow), execute it once end-to-end against a real target before the merge barrier, and record the execution as evidence. This run demonstrates both the cost of not doing so and the value of doing it: running D10's own recovery is what exposed `ed9ef2`, and the same execution transitively surfaced `4394cf` (the `issue view` envelope-forgery hazard).

Note the scoping this is not: it is not a proposal to execute every documented command in every plan. The trigger is narrow — the plan ships the procedure as its deliverable.

## Evidence

- qgate finding `ed9ef2` (severity error, fixed) — its own detail names the gap: "it went undetected through 5 self-review rounds, a clean plugin-doctor gate and a CodeRabbit review because every one of those reads the doc rather than EXECUTING it".
- qgate finding `4394cf` (severity error, fixed) — found transitively while fixing `ed9ef2`.
- `status.metadata.phase_steps`: `pre-submission-self-review` `firing_count: 5` with 4 prior loop-backs, all ending "self-review clean"; `project:finalize-step-plugin-doctor` "0 findings".
- review yield: 4 CodeRabbit Majors across 3 rounds, against 0 findings from the doc-reading gates on the same content.
