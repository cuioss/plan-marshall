envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:40Z

# NOT A LESSON — corpus-health report, and the reported defect is REFUTED

**Disposition: do not lift this into `manage-lessons`.** It is a correction to a claim made during
this run's finalize, filed so the orchestrator does not act on the original claim.

## The claim

The run's lessons-housekeeping notes recorded a corpus-health observation: lesson
`2026-09-04-13-001` was said to have a title and an **empty body** — an `add` that ran with no
following `set-body`.

## The claim is false

Verified directly via `manage-lessons get --lesson-id 2026-09-04-13-001`. The lesson has a full,
well-formed body of roughly 1.5 KB carrying `## Rule`, `## Observation`,
`## Why the existing contract does not cover it`, and `## How to apply` sections. Its title is
*"A dispatched finalize step resolves its workflow doc against the MAIN checkout, so a plan editing
that doc runs the pre-plan version"*, and the body documents a real, substantive defect with a live
observation from PLAN `shipped-guards-assume-the-meta-projects-own-layout`.

Nothing is wrong with this lesson. **No remediation is owed.**

## The residue that is actually worth something

The empty-body claim was carried across **six firings** of the housekeeping step and re-stated to
this step as established fact, without any firing having read the lesson. One `get` refuted it.

That is the corpus's own `DERIVE completeness, never assert it` archetype in its cheapest possible
form: a claim *about a specific record* was propagated without reading that record, where reading it
was a single command. If the orchestrator judges this worth guarding, the guardable shape is:

> A corpus-health assertion naming a specific artifact id MUST be accompanied by the read that
> produced it. An assertion re-stated across firings without a fresh read is a rumour, not a finding.

I make no claim about whether the corpus already covers that shape — I did not survey the 73-lesson
corpus for it, and this message deliberately does not assert a clean negative.
