envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=truthful-signals
kind=finding
created=2026-09-07T17:56:39Z

# The scoped build gates cannot see what the whole-tree gate sees

Established twice, independently, by two agents during plan
`test-suite-anti-vacuity`. Both are cases of a green that means less than it
appears to — the epic's theme exactly.

## 1. `quality-gate` never reaches `test/**`

`quality-gate` scopes by **bundle**; `module-tests` scopes by **module path**.
The two take different scope vocabularies, and that difference is load-bearing
rather than cosmetic:

- `quality-gate plan-marshall/manage-metrics` → `Bundle not found`
- `quality-gate plan-marshall` → green, but it lints
  `marketplace/bundles/plan-marshall`, which contains **no test files**

So ruff and mypy over the test tree are reached only by the whole-tree gate. A
per-task `quality-gate` green is therefore not evidence that a test-file change
is lint-clean — and the per-task verification commands this project's tasks
carry name exactly that command.

## 2. `module-tests` reported green over a live ruff error

A task changing `test/pm-plugin-development/ext-self-review-plan-marshall/`
introduced an `I001` (un-sorted import block). `module-tests` for that path
returned **green** while the error was live; only the bundle-scoped `verify`
surfaced it.

Taken together with (1): for a test-only change, neither scoped gate reliably
covers lint. The whole-tree `verify` is doing more of the work than the task
verification commands imply, and a task that runs only its declared scoped
command can land a lint error believing it verified.

**Remedy shape**: either give `quality-gate` a test-tree-reaching scope
vocabulary, or state in the task-verification contract that scoped gates do not
cover `test/**` lint so the whole-tree gate is not treated as redundant.

## 3. The build wrapper's `log_file` is a daemon summary, not the pytest log

Hit independently by **three** tasks in this one run. The wrapper's returned
`log_file` points at a marshalld job-summary wrapper carrying no per-test
nodeids; the real pytest log is named by that file's own `log_file` field.

The consequence is a false negative in the workflow's own diff-assertion
helper: it returned `passed: false, found_count: 0, missing_count: N` against
the summary — including for an **untouched pre-existing test**, which is what
proved the log carries no nodeids at all rather than the tests being absent. An
implementer who trusts that result concludes their tests did not run.

Plan-store context: observed by TASK-011, TASK-019 and TASK-020 of
`test-suite-anti-vacuity`, each diagnosing it independently.
