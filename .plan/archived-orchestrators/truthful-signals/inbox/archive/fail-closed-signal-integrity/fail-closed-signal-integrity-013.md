envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T22:07:46Z

component=project:finalize-step-lessons-housekeeping
category=bug
bundle=plan-marshall

# A `completely-covered` retirement verdict was justified by a worked example that contradicts its own clause

The evidence standard for retiring a lesson is currently "the rule is codified somewhere". It
needs to be "the codification is correct", because this run produced a retirement justified by a
demonstration that mishandles the very ambiguity cited as its coverage.

## The sequence, from this plan's own decision log

**13:43:31Z, decision `71fe82`** — housekeeping classifies lesson `2026-07-11-15-001`
(*detect-and-warn inferred a clean pass from absence-of-change, not an affirmative success
signal*) as **completely-covered**, reasoning:

> the rule … is now codified as error-handling.md Fail-Closed Classification (d), **whose worked
> contrast covers the succeeded-idempotently vs never-ran ambiguity the lesson names**. No residue
> outside that clause. Disposition remove.

**20:04:48Z, decision `ce09fb`**, acting on CodeRabbit comment `c9176b` on PR #1081:

> Clause (d) of error-handling.md states absence-of-change is not evidence of success and then its
> GOOD example branches on `outcome.applied`, a change flag, so a successful idempotent no-op
> routes to `markUnresolved`. **The GOOD example demonstrates the anti-pattern its own clause
> forbids.** … a lesson was retired against a demonstration that mishandles the ambiguity cited as
> its own coverage justification.

A second defect of the same class was found in the same pass: clause (f)'s GOOD-example comment
claims a short readback while the code only compares list sizes — the term misnames the mechanism.

## Why this is more than one bad call

Three independent controls were between the lesson and its retirement and none of them fired:

1. The housekeeping classifier itself read clause (d) and pronounced it covering.
2. `pre-submission-self-review` ran **five passes** over text this plan authored, at a recorded
   709,472 tokens, and did not flag it.
3. `plugin-doctor quality-gate` ran clean over the same file.

It was caught by a free external reviewer, in one pass, after the PR was open. And the lesson
survived only by accident: `restore-from-plan` was independently broken (inbox 002), so the
`remove` disposition could not be applied. Had the restore worked, a load-bearing lesson would
have been deleted on the strength of a worked example that contradicts itself.

**Safety by unrelated bug is not a control.**

## Solution

1. A `completely-covered` verdict must cite the codified clause **and** state, in one sentence,
   the concrete input on which the clause's own worked example produces the correct verdict. If
   that sentence cannot be written, the verdict is `partially-covered` at best.
2. Retirement must be a two-key operation: classification and deletion must not both derive from
   the same read of the same text by the same pass.
3. Codified worked examples are the highest-leverage text in the corpus — a wrong example
   propagates into every future retirement decision that cites it. They deserve a dedicated
   check: does the GOOD example actually satisfy the clause it illustrates? Both defects here
   (clause (d) and clause (f)) are that check, absent.
