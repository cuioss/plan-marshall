envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:22Z

component=plan-marshall:execute-task
category=bug
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# assert_test_identifiers cannot report that it could not look

## Context

TASK-008 added `test_autonomy_defaults_documented.py` (496 lines). Its
module-testing verification could not confirm via `assert_test_identifiers` that
the new tests had executed. The run recorded the outcome at `09:28:42Z`:

> "assert_test_identifiers is uninformative against this build log: a pre-existing
> test in the same module also reports missing, so the log carries no per-test
> nodeids. New-test execution evidenced instead by (a) the module source executing
> under a real interpreter and deriving 25 census rows, (b) a green 20382-test
> plan-marshall run with the module present (an import/collection failure would be
> red), and (c) a mutation control proving the census parity fails when a Default
> cell disagrees."

The engineering there is sound — a positive control was run, and three
independent substitute evidences were gathered. What is missing is a contract
that permits it. `execute-task/SKILL.md` step 6 defines exactly two outcomes:
`passed: true` → mark the task done; `passed: false` → **do NOT mark the task
done**, mark it `requires_attention`. The task was marked done. There is no
documented third branch, so the correct engineering move had to be taken outside
the contract and narrated into a log line.

## Root cause

`passed: false` conflates two states that mean opposite things:

- **The tests were silently skipped** — the log lists tests, and these are not
  among them. This is the exact condition the guardrail exists to catch.
- **The log lists no tests at all** — the assertion could not look. Nothing was
  measured, so nothing failed.

The helper has every input needed to tell them apart: `assert_identifiers_in_log`
reads the whole log into `lines` before matching. A log carrying zero
nodeid-shaped tokens is directly observable, and a positive control is exactly
the check the run performed by hand.

This is the could-not-look-vs-measured-zero discriminator the codebase mandates
everywhere else — `findings_store_state`, `plans_root_state`,
`comparison: inconclusive`, `not_evaluated`, `unmeasured`, `evaluated_population`.
The guardrail is missing the discriminator its own project standard requires.

## Proposed action

1. Give `DiffResult` a third state. Emit `status: indeterminate` (or
   `measurable: false` alongside `passed`) when the log carries no
   nodeid-shaped token at all, and publish the population the helper scanned —
   the same `evaluated_population` shape the retrospective's own aspects use.
2. Add the branch to `execute-task/SKILL.md` step 6: on indeterminate, the task
   is neither auto-done nor `requires_attention` — it requires named substitute
   evidence, recorded in the return value, before it may be marked done.
3. Close a latent contract mismatch in the same pair of documents:
   `assert_test_identifiers.py`'s docstring says identifiers are
   `module::class::test` (three-part), while `execute-task/SKILL.md:301`
   instructs collecting `{rel_path}::{test_function}` (two-part). Pytest emits
   `path.py::TestClass::test_fn` for a class-scoped test, and the matcher
   anchors both sides, so a two-part identifier for a class-scoped test can
   never match. It did not bite here — this plan's new tests are module-level
   functions — but it is a live mismatch that would present as exactly the same
   uninformative-assertion symptom.

## Evidence

- work.log `09:28:42Z` `[VERIFY]` line, quoted above.
- `assert_test_identifiers.py:164-199` — the whole log is read before matching,
  so the nodeid-free case is observable at the point the verdict is formed.
- `execute-task/SKILL.md:309-316` — the two-branch contract.
- `execute-task/SKILL.md:301` vs `assert_test_identifiers.py:9` — two-part vs
  three-part identifier form.

## Evidence limit — the stated cause is not the provable one

The run's stated cause ("the log carries no per-test nodeids") is contradicted by
the evidence that survives, and the proposal above deliberately does not rest on
it. Every `module-tests` log still present in this plan's `build-results/` carries
full `test/path.py::TestClass::test_fn` nodeids — 40,483 occurrences in the
`python-2026-09-06-191112.log` run. The small logs in that directory that carry
none are `quality-gate` (18 KB) and `test-compile` (60 KB) logs, not module-tests.
The 09-07 logs the failing assertion actually read lived in the worktree, which
`default:branch-cleanup` removed, so which log was passed to `--log` is now
unverifiable. A plausible alternative cause — the wrong build log was passed — is
consistent with the surviving evidence and is not excluded.

That uncertainty does not weaken the finding, and is the reason it is worth
filing: whichever cause held, the helper reported an absence it had not measured,
and the contract had no state in which to say so.
