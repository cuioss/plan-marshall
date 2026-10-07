envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:42:45Z

# Candidate lesson: a plan that removes a polarity coercion introduced a new one at the call site it added

**Source record:** `pr-comment` finding `212b88`, resolution `fixed`, CodeRabbit inline (Major) at `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:643`, reviewed commit `56580bd9d`. Remediated by TASK-9 in `851e5396b`.

## The observation

The plan's entire premise is that an unproven observation must not be coerced into a definite state. Its new call site did exactly that. The item-5 read at `SKILL.md:632` and the instruction at `:643` were **binary**: pass `--not-triggered` when no `pull_request` run exists, omit it otherwise. An unreadable return — `status: error`, `status: unconfigured`, or a response omitting `has_pull_request_run` — fell into "omit it otherwise", which silently asserts *a run exists*. A silent required bot then resolved to `absent` (escalate) instead of being held open.

Two aggravating properties:

- It **neutered a deliberate fail-loud guard.** The provider verb returns a typed `unconfigured` status precisely so a caller cannot proceed on an unread observable. The binary call site converted that loud signal into a quiet false.
- The correct pattern was **already present in the same document.** `SKILL.md:674-701` carries a worked UNKNOWN branch for the `review_completeness check` call, and the sibling call site in `branch-cleanup.md:769` already routed an unconfigured-or-error `pull-request-runs` read to UNKNOWN. Only the newly added site lacked the branch. The fix reused the existing UNKNOWN handling; it invented nothing.

## The generalisable shape

**A plan that establishes a fail-closed discipline is not thereby compliant with it.** The discipline was written into the contract documents and into the classifier, and then a fresh call site added by the same change consumed a fallible read with a two-branch `if`. The author's attention was on the states being distinguished (`participated_stale`, `not_triggered`, `absent`) and not on the readability of the input that selects between them.

The tell is mechanical and cheap to check: **a boolean flag derived from a fallible read has three inputs and two branches.** Wherever a plan adds a call site of the form "pass the flag when X, omit it otherwise", ask what happens when X could not be determined. Here the answer was "omit", and omit meant "assert the positive".

Related, from the same review: finding `a582b1` raised the same class one level up — the barrier's validation rules were written as **enumerations of known-bad shapes** (`unconfigured`, `error`) rather than as **positive validations of the required shape**, so a `status: success` return that merely omitted `has_pull_request_run`, or carried a non-boolean there, fell through the enumeration into the same "omit the flag" default.

## Why it is routed here

The call site, the observable, and the discipline are all `review-apparatus` surface. The transferable rule — a new call site consuming a fallible read must branch three ways — is a candidate for wider promotion, which is the orchestrator's call, not the plan's.
