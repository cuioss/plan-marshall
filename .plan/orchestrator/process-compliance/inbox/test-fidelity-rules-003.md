envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=process-compliance
kind=finding
created=2026-09-19T10:25:27Z

# PLAN-180 D9 staged: basetemp relocation blast radius (evidence, not a half-move)

## Claim

Relocating pytest's basetemp and `TEST_FIXTURE_BASE` out of `.plan/temp/` (lesson
2026-09-03-02-005, option 1) is a whole-tree contract-value change, not a
single-deliverable edit. It was deliberately NOT folded into carve-1.

## Measured entrenchment (HEAD at run time)

- Producer: `build.py` sets `PYTEST_BASETEMP_ROOT = Path('.plan/temp/pytest-basetemp')`
  with per-session subdirectories (cited verbatim in worktree tests).
- Contract test pins the path: `test/default/test_build_verify.py:169-170` asserts
  `--basetemp` points under `.plan/temp/pytest-basetemp/`.
- Consumer prose: dozens of test docstrings/comments reason about the repo-local
  basetemp (git-resolution fallbacks, worktree anchoring, `Edit(.plan/**)`
  permission coverage for `TEST_FIXTURE_BASE` at `test/conftest.py:41`).
- Written guidance conflict is real: the repo hard rule directs ALL agent scratch
  to `.plan/temp/`, the exact parent the suite prunes and writes into.

## Why staging is the compliant move

Per the Enumerate-Consumers rule, a contract-value change must discover and
update every consumer in the SAME atomic change. A partial relocation (move the
producer, miss one consumer) reds the suite in exactly the way the rule exists
to prevent, and the failure signature (thousands of setup errors) misdirects
diagnosis. The consumer set spans build config, conftest, the basetemp-root
constant, the prune helper, the contract test, and every test whose isolation
reasoning assumes repo-local ancestry. That is a dedicated plan with its own
census run, not a ninth deliverable in a shared turn.

## Request

Stage D9 as carve-4: its own plan with (1) two-pronged consumer enumeration
(symbol + literal `.plan/temp/pytest-basetemp` and `TEST_FIXTURE_BASE`), (2) the
atomic move to the dedicated path, (3) a full whole-tree census green before
merge, (4) the fast-failing guard the lesson asks for (scratch files in the
pytest temp root reported intelligibly). Optionally pair with the D3-style
mechanism test so documented temp-root behaviour and configured values cannot
drift again.
