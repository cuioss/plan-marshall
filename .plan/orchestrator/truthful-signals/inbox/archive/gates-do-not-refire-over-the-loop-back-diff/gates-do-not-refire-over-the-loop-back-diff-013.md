envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:11:13Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# Plan-internal deliverable ids baked into shipped test identifiers (recorded by finalize-step-simplify, not actioned)

## Observation

`finalize-step-simplify` recorded — and did **not** action — **plan-internal deliverable ids baked into shipped test identifiers** in PLAN-TRUTH-001's test surface (PR #1073).

Test names carry identifiers such as the plan's own deliverable labels (`D5a` and siblings). Those labels are **plan-lifecycle artefacts**: they exist inside one plan's outline, they are meaningful only while that plan is in flight, and they are archived with it.

## Why it matters

1. **The referent evaporates.** Once the plan is archived, `D5a` names nothing a future reader can resolve. The test asserts a real property but announces itself in a private vocabulary that no longer has a dictionary.
2. **It misdirects triage.** A failing test named after a deliverable id sends the reader looking for a *plan*, not for the *behaviour* under test. The name actively costs time at exactly the moment names matter most.
3. **It leaks lifecycle scope into permanent surface.** Tests outlive plans by design; embedding plan-scoped identifiers in them inverts that relationship.

## Why this belongs to `truthful-signals`

A test name is a **claim about what is being verified**. A name that resolves to an archived plan id is a claim that cannot be checked — the reader sees a specific, confident identifier and has no way to discover that it points at nothing. It is the naming-layer analogue of the epic's theme: a confident signal whose caveat (that its referent is gone) is unrepresentable in the signal itself.

## Suggested shape of the fix

1. Rename the affected tests to describe the **behaviour or invariant** they pin, not the deliverable that commissioned them. The head-dependence derivation tests should be named for head-dependence, not for `D5a`.
2. Durable half: a lint/self-review candidate that flags **plan-scoped identifiers** (deliverable ids, plan ids, task numbers) appearing in shipped source or test identifiers. This class is mechanically detectable and currently has no detector.

## Not actioned

Recorded by `finalize-step-simplify` during PLAN-TRUTH-001's finalize; deliberately not actioned in-run. Handed to the epic.
