envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:49:43Z

component=plan-marshall:tools-script-executor
category=anti-pattern
bundle=plan-marshall

# Stale per-worktree derived state reads as a source defect after a rebase

`project:finalize-step-plugin-doctor` reported 8
`ARGUMENT_NAMING_NOTATION_INVALID` findings on PLAN-TRUTH-087. All 8 pointed at
a skill that had arrived in the worktree FROM UPSTREAM during
`finalize-step-sync-baseline`'s rebase (5 upstream commits). The worktree's
generated executor predated that skill, so the notation the doctor resolved
against did not exist in the executor's mapping.

Regenerating the executor cleared all 8 findings with **zero source edits**.
Every one of the 8 was an artifact of per-tree derived state, not a defect in
the skill the finding named.

The general shape: a rebase moves SOURCE into the tree but does not move the
DERIVED state built from that source. Anything the tree derives per-worktree —
the generated executor, a resolved inventory, a cache — is silently
out-of-date with respect to the newly-arrived commits, and every gate that
reads the derived state attributes the mismatch to the source file it is
inspecting.

## Solution

When a structural-lint gate reports findings against a file the plan did not
touch, and that file arrived from upstream, **regenerate the derived state
before reading the findings as defects**. Concretely: after
`finalize-step-sync-baseline` reports `action: rebased` with a non-zero
`upstream_commit_count`, treat the worktree's generated executor as stale.

The diagnostic tell is cheap and reliable: the findings name a component the
plan's own diff never touches. That asymmetry — findings on untouched,
newly-arrived files — is the signature, and it distinguishes this class from a
real regression the plan introduced.

## Impact

Applies to every plan whose finalize rebases in upstream commits, which is most
of them under a busy main. Cost when missed is a full round of source edits
against files that were never wrong, plus the risk of "fixing" upstream code to
match a stale local mapping.
