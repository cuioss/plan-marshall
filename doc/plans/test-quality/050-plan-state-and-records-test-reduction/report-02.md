# Run report — 050-plan-state-and-records-test-reduction (run 02)

**Date (UTC):** 2026-08-16 **Branch:** `claude/test-quality-plan-execution-evap45` **PR:** _(§ Reviewer participation)_ **Outcome:** completed

This run does **not** execute the plan's deliverables. It closes the findings run 01 recorded as
**"recorded, not fixed"**, on operator instruction ("fix all the findings"). The plan's own residue —
D2's remaining builders, D3's missing fixture modules, D4's over-budget modules, D5's parametrization
— is untouched and stays in run 01's § Residue. Scope is stated here so the two are not conflated:
**a finding is a defect this plan surfaced; residue is deliverable scope it did not reach.**

## Skills loaded

Run 01 recorded skipping Step 1 and reported it as a deviation. This run loads them, which is the
correction.

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) |
| `plan-marshall:ref-code-quality` | bundle path — always-load |
| `pm-plugin-development:plugin-script-architecture` | bundle path — always-load |
| `pm-dev-python:pytest-testing` | bundle path — conditional: Python tests |
| `pm-dev-python:python-core` | bundle path — conditional: Python production code (the doctor rule) |

Every skill resolved by bundle path; none was unobtainable.

## Deliverables — the seven findings

### #13 — rule 7 cannot tell a named value from a cited record — **FIXED** (`d210db0`)

The `test-docstring-historical-prose` rule scoped itself to docstrings and comments, on the reasoning
that the same textual shapes appear far more often as string-literal test data. That discriminator is
right and **insufficient**: prose has to name values as well as cite records. A docstring stating the
id a generator returns, or a comment naming the task file a command creates, states the contract under
test and cites nothing.

Shape cannot separate the two. **Formatting can**: an identifier named as a value is written in an
inline literal; a citation appears bare in the narrative. Rule 7 now skips a match inside a backtick
span or a quoted string, which gives the rule a convention it can teach — **backtick the value you
name**.

The exemption is **per occurrence, not per segment**, so backticking one identifier cannot launder the
rest of a sentence. Three tests pin the new behaviour, including that mixed case; all 18 pre-existing
rule-7 tests still pass unchanged, because every one of them cites a **bare** id in narrative position.

**The 24 → 0 drop, split honestly by cause** — re-derived, not recalled:

| Measurement | `test-docstring-historical-prose` over the ten plan-state directories |
|---|---|
| `origin/main`, rule as shipped | **24** |
| `origin/main` corpus, **new rule** | **16** |
| this branch (new rule + corpus) | **0** |

So **the rule change alone clears 8; the remaining 16 came from editing the corpus** — backticking
14 task ids that prose names as values, and rewriting 2 genuine citations. Stating that split rather
than claiming the rule did the work: the convention is the fix, and the corpus now follows it. A
reader who assumed the rule alone took 24 to 0 would over-credit it.

**A live instance of the defect, found during the fix.** The docstring explaining the new discriminator
used a real-shaped lesson id as its example, and the sibling `no-lesson-id-in-skill-prose` rule — which
governs `marketplace/bundles/**` and does **not** carry this exemption — flagged it. The example is now
a shape placeholder, which documents the rule better anyway. **Recorded, not fixed:** that sibling rule
has the same false-positive class over bundle prose. It was left alone because bundle prose rarely needs
to name a lesson id as a value, so the case for widening the exemption there is unproven — and this run
had no evidence for it beyond one self-inflicted instance.

### #28 — `detect_outcome_for_diffed_tasks` name versus selector — **NOT a production defect; test fixed** (`d210db0`)

Run 01 recorded this as a *possible production defect* it could not resolve, because doing so required
reading a `marketplace/bundles/**` file the plan forbids editing. Read this run:
`analyze-logs.py:866` already documents the behaviour at its definition site — the per-task SHA range
is not persisted anywhere stable, so `status: done` is a **deliberately over-inclusive proxy** and the
LLM rule applies the diff guard downstream.

So the production code is correct and self-explaining. The defect is test-side: a reader of
`test_detect_outcome_for_diffed_tasks_regression` had no way to see why the selector says `done` when
the function and its `tasks_with_diff_no_outcome` key both say *diff*. The test docstring now states
the proxy. **No production change was needed, and none was made.**

### #29 — duplicate `plan_id` across two tests — **FIXED** (`d210db0`)

`test_mark_step_done.py` used `'mark-step-legacy-force'` in two tests. They are safe only while
`plan_context` grants each test a fresh root; if that isolation ever weakened, the second `cmd_create`
would collide and the failure would present as a canonicalization bug rather than a fixture-name
collision. The ids are now distinct.

### #35 / #36 — stale epic-brief references — **FIXED** (`d210db0`)

`doc/plans/test-quality/README.md` and `findings-test-corpus-review.md` both still described
`test_audit_checks.py` as a live ~8,700-line module. Run 01 deliberately left them, because the briefs
are read concurrently by plans `030`–`080` and editing them risked a collision the epic README itself
warns about. That risk has since resolved: **#1258 merged**, so the file genuinely no longer exists and
the briefs were simply wrong. Both now describe the outcome rather than the pre-split state.

### #38 — `test_audit.py` over budget, five checks unmapped — **FIXED** (`386066b`)

At 1,509 lines it was the last module in the directory over the 400-line budget, and it held the five
`SKILL.md` checks no filename mapped. Split into **15 modules**, all within budget.

**All 24 of 24 checks in the SKILL.md inventory now map to a module by filename**, up from 19. The five
that gained one:

| Check | Module |
|---|---|
| `dispatch-topology` | `test_audit_check_dispatch_topology.py` |
| `execution-context-manifest` | `test_audit_check_execution_context_manifest.py` |
| `finalize-flow-conformance` | `test_audit_check_finalize_flow_conformance.py` |
| `lane-lever-effectiveness` | `test_audit_check_lane_lever_effectiveness.py` |
| `merge-window-accounting` | `test_audit_check_merge_window_accounting.py` |

`execution-context-manifest` is the one that needed reading rather than pattern-matching: its tests are
the step-owner-drift cluster, which the old section banner named ("execution-context-manifest
owner-drift") while the filename did not.

**Verified a pure move:** 82 test functions before, 82 after, none missing or added (AST inventory);
**555 collected items at `origin/main` and 555 after**, measured in a worktree rather than recalled.

⭐ **This split slices by LINE range between section banners, not by AST node range** — directly
applying run 01's own lesson. That run's decomposition sliced by node and silently dropped 162 column-0
comments including 8 rationale blocks, because **a leading comment belongs to no AST node**. Slicing by
line carries every comment along with the code it explains.

Three changes beyond the move, each a consequence of it:

- **The directory was loading `audit.py` twice**, under two `sys.modules` names — this module via
  `sys.path` + `import audit`, its sibling via `spec_from_file_location`. The new modules take the one
  loader in `_audit_fixtures.py`. Safe to consolidate: the module has **zero** `monkeypatch` calls and
  its only attribute reads are `audit.__doc__`, identical either way.
- **`_write_log` existed in two incompatible shapes** — a 2-arg single-line writer here, the 3-arg
  shared writer in `_audit_fixtures`. The local one is the shared one with a fixed filename, so it is
  gone rather than hoisted, and its call sites now name the log file they write, which is the part that
  matters because the name must match the glob.
- `minimal_corpus` is used by four of the new modules and moved to `_audit_fixtures.py`.

**A bonus catch the split surfaced:** the section banners cited deliverable ids and PR numbers
("Deliverable 2 (a): … (#849)"). Rule 7 never caught them — it matches `deliverable D<n>`, not
`Deliverable 2`, and `PR #<n>`, not a bare `#849`. Each banner is now a module docstring stating what
its check asserts in the present tense. **Recorded:** rule 7's `_PLAN_DELIVERABLE_ID_RE` and
`_PR_REFERENCE_RE` do not match these two spellings. Not widened here — widening a matcher without a
measured false-positive rate is how the rule acquired the problem #13 just fixed.

### #39 — commit message off-by-one — **NOT FIXABLE**

`984c257`'s message says the prose count went "66 to 25" where the tool said 24. Commit messages are
immutable history; run 01's report already carries the re-derived figure. Recorded, not actionable.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **32 files** of 35 changed. Python footprint
present, so the gate applies.

`./pw verify` → **`=== verify: SUCCESS ===`**, 20,325 passed, 14 skipped, whole tree.

Per-commit gates: both commits touch `*.py` and both were preceded by a clean direct
`./pw quality-gate`, read from the tools' own output (`ruff … All checks passed!`, `mypy … Success: no
issues found in 408 source files`, `SPDX-header check passed`) since the direct path emits no
structured log.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | This run, while fixing #13 | The new rule docstring's own lesson-id-shaped example tripped the sibling `no-lesson-id-in-skill-prose` rule — a live instance of the very false-positive class | **Fixed** — example replaced with a shape placeholder |
| 2 | This run, while fixing #13 | The sibling `no-lesson-id-in-skill-prose` rule has the same citation-vs-datum gap over `marketplace/bundles/**` | **Recorded, not fixed** — no measured false-positive rate there; widening on one self-inflicted instance is how #13 arose |
| 3 | This run, while fixing #38 | `test_audit.py` section banners cited deliverable ids and PR numbers that rule 7 does not match (`Deliverable 2`, bare `#849`) | **Fixed in the corpus** (banners became present-tense docstrings); **matcher gap recorded, not widened** |
| 4 | This run, while fixing #38 | The directory executed `audit.py` twice under two `sys.modules` names | **Fixed** — one loader for the directory |
| 5 | This run, while fixing #38 | Two incompatible `_write_log` helpers in one directory | **Fixed** — the near-duplicate is gone, not hoisted |
| 6 | This run, verifying #28 | Run 01 recorded a *possible production defect*; the production docstring already documents the proxy | **Rejected as a production defect, with reason** — fixed test-side instead |

_(Independent pre-PR verification findings are appended below.)_

## Reviewer participation

_(Completed at the merge gate.)_

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no per-session figure
  to the running agent, so no number is given rather than an estimated one.
- **Wall-clock:** not separately instrumented. The durable timestamps are the commit times on the
  branch and the PR's `created_at`.
- **Population:** one interactive Claude Code cloud session plus one dispatched verification
  sub-agent. ⛔ **Not comparable** to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. This
  session does not share that boundary and emits no `metrics.toon`.

## Contract check (Step 9)

_(Completed before the merge gate.)_

## What have we learned (Step 9)

_(Completed before the merge gate.)_

## Residue

**The plan's own deliverable residue is unchanged and still lives in run 01's § Residue** — D2's 15
remaining namespace builders, D3's five directories without a fixture module, D4's over-budget modules,
and D5's unstarted parametrization. This run closed findings, not deliverables.

One figure moved: `test-module-line-budget` over the slice is **58**, down from 59, because
`test_audit.py` was the module #38 split. Every other residue figure in run 01 stands.

Two items recorded here for a future plan, neither actionable within this run's scope:

- **`no-lesson-id-in-skill-prose` has rule 7's old gap.** The same citation-versus-datum confusion
  applies over `marketplace/bundles/**`. Fixing it needs a measured false-positive rate over bundle
  prose, which this run did not gather.
- **Rule 7's matchers miss two live spellings** — `Deliverable 2` (it requires `deliverable D<n>`) and
  a bare `#849` (it requires `PR #<n>`). Both appeared in this repository's own test prose. Widening
  the matchers is a change that needs its own false-positive measurement first.
