envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:54:24Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern
title=Documenting that a property is unenforced is not a fix - honesty is not enforcement

# Documenting that a property is unenforced is not a fix - honesty is not enforcement

## Observation

A `mutates_source: false` finalize step's empty-tree property rested entirely on the **frontmatter declaration**, with nothing at runtime observing whether the step actually left the tree clean. The remediation shipped in PLAN-CIS-028 was to rewrite **three doc sites** to be honest about that: to say plainly that the property was declared, not enforced.

CodeRabbit's response was direct: **honesty is not the fix.** An accurate description of an unenforced invariant is still an unenforced invariant. That review became TASK-021 — a runtime tracked-file check that actually observes the property for post-run-review steps.

## Rule

When a review or self-review surfaces "this property is declared but nothing checks it":

- **The default remediation is the check, not the prose.** Adding a runtime observer is the fix; describing the gap accurately is at best a stopgap and at worst launders the gap into a documented feature.
- **Honest documentation of a gap is only acceptable when paired with the enforcement**, or with an explicit, tracked decision not to enforce (with the reason). A doc-only change that closes the finding is a false close.
- Watch for the tell: a diff whose entire content is *rewriting descriptions of behaviour* in response to a finding about *missing behaviour*. That shape is the defending-documentation / vacuous-authority archetype, now at n>=6 across the epics.
- A declaration in frontmatter, a manifest, or a contract table is an **assertion by the author**, not a guarantee by the system. Every load-bearing declaration needs a producer that observes it or a consumer that rejects a violation.

## Impact

Applies to every declarative frontmatter fact that carries operational weight — `mutates_source`, `post_run_review`, `head_dependent`, `default_on`, `presets`, `execution_tier` — and to the broader class of contract-source declarations across the marketplace. The concrete enforcement landed as TASK-021 (runtime tracked-file check for post-run-review steps) in PR #1080.
