envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:08Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# The outline's test-pin list was a sample presented as an enumeration: 1 named, 12 real

An outline that repairs a documented string must also repair every test that pins the old string. This
outline enumerated **one** such pin. Twelve existed.

## Observed

Q-Gate finding `563f71` (5-execute, `test-failure`, resolution `fixed`):

> 11 tests pin the OLD defective `generate.py --target claude` prescription

`test/marketplace/targets/claude/test_content_drift.py` (lines 145, 215) and
`test/marketplace/targets/claude/test_equality_check.py` (lines 253, 284, 316 ×4, 340, 430 ×3) each
assert the old prescription text. The finding names the archetype itself:

> This is the atomic doc-fix-plus-test-pin pair the outline already anticipated — but it enumerated
> only ONE such pin (`test/finalize-step-deploy-target/test_deploy_target.py:87`) and MISSED these
> eleven. Record that under-enumeration explicitly: it is the *"a reviewer's list of call sites is a
> SAMPLE, not an enumeration"* archetype, and the D0 test-pin sweep that produced the single-pin
> figure was itself incomplete.

Prescribed remedy, verbatim: *"re-derive the test-pin population from source rather than from the
outline's list."*

## The same run demonstrates the correct shape twice

Both `stale_count_prose` findings in this run were resolved by **deleting** the count rather than
re-counting it:

- `d00d72`: the "exactly one file / one path exemption" clauses were deleted; the comment now defers
  to the sibling sweep's own `_EXCLUDED_PATHS` tuple as the authority on membership.
- `8cc109`: the eleven-site enumeration was deleted from a module docstring; the guard *"derives its
  scope by walking `_SCAN_ROOTS`, a list copied into prose is a second unmaintained count, and what
  the guard covers is what it publishes at runtime."*

And `6ff43a`'s resolution declined to add six duplicate path assertions precisely because
*"duplicating six path checks there would be a second, unmaintained enumeration of a set the
deliverable-4 guard already derives."*

## Rule

An outline's affected-file list for a *string-replacement* deliverable must be **derived by a content
sweep at outline time**, not assembled by hand and then presented as complete. The derivation is one
`architecture search --content` call whose clean-coverage fields (`files_scanned`, `unreadable`,
`truncated`, `elided`) establish whether the resulting count is a population or a lower bound. Where
the sweep cannot be run, the list must be labelled a sample in the outline, so the execute phase
knows to re-derive rather than to trust.
