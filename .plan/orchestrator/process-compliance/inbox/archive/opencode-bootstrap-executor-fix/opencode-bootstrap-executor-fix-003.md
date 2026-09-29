envelope_version=1
sender_type=plan
sender_id=opencode-bootstrap-executor-fix
epic=process-compliance
kind=finding
created=2026-09-29T05:36:17Z

# 003 — Local verification green on a tree the CI checkout cannot have

**Plan:** opencode-bootstrap-executor-fix
**Phase:** 6-finalize (pre-push-quality-gate → ci-verify)
**Severity:** error

## What happened

`pre-push-quality-gate` reported the whole-tree `module-tests` arm green —
28,361 tests, exit 0 — and the freshness gate then permitted the push on the
strength of that evidence. CI failed on the identical SHA, twice, on two
separate workflow runs.

The cause was untracked generated state in the worktree. Earlier in the plan I
ran `./pw generate --target opencode`, which left a `target/` directory behind
(`target/` is gitignored). A test added by this plan,
`test_target_tree_foundational_skill_freshness.py`, asserts over the generated
target trees and refuses to read an empty population as a clean sweep. Locally
the population existed; on a clean CI checkout it does not, so the test was
unconditionally red there and locally meaningless.

The green I reported was therefore **not evidence about the tree I pushed**.

## The process failure

Not the test — the test behaved correctly, and its refusal is what exposed this.
The failure is that I accepted a green build as verification without establishing
that the machine's working state matched a clean checkout of the same commit.

The pre-push gate has no check for this, and nothing in the plan's own contract
required one. That is the gap worth closing: a gate that can be satisfied by
untracked local state is a gate that can certify a commit nobody else can build.

## Contributing factors

1. The plan runs in a **long-lived worktree** reused across the whole
   finalize phase, so generated artifacts accumulate and are never cleaned
   between steps.
2. `build-pyproject clean` does not remove generated target trees, so the
   documented cleanup verb would not have reset the state anyway.
3. The pre-push gate and the freshness gate both keyed on the same contaminated
   evidence, so agreeing with each other read as corroboration. Two gates
   reading one input are not two witnesses.

## Remedy applied

- The tree is regenerated per-CI before verify (`.github/workflows/python-verify.yml`
  `pre-verify-goals: generate`), so CI now populates the population the guard needs.
- Local re-verification was redone in CI's order: `./pw generate --target all --output target`
  then the module tests. Green, 23,618 tests in the plan-marshall module.

## Owed

- A pre-push gate check that refuses a green verdict whose worktree carries
  untracked generated state under a path a tracked test scans. Until that exists,
  any pre-push evidence produced in a reused worktree is suspect.
- The generalisation, which the retrospective should carry: a guard was checked
  for having a population (this fix) and separately for having the *right*
  population (the still-open flat-root coverage finding). A guard over an empty
  set and a guard over the wrong set are the same failure wearing different
  clothes, and this plan produced one of each.
