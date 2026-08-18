# Run report — 510-finalize-step-contract-ordering-and-refire-currency (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/step-contract-ordering-refire-cjlzup`    **PR:** _pending_    **Outcome:** _in progress_

> **Verification loop exit:** _pending_

## Skills loaded

Loaded by path from the bundle source (the `plan-marshall` plugin is not installed in this session,
so `Skill: {bundle}:{skill}` notation was not used):

| Skill | Path | Why |
|---|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` | always |
| `pm-plugin-development:plugin-script-architecture` | `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md` | always |
| `plan-marshall:ref-workflow-architecture` | `.../ref-workflow-architecture/SKILL.md` | workflow docs, dispatch topology (D5) |
| `plan-marshall:persona-implementer` | `.../persona-implementer/SKILL.md` | production code (D2.2, D4.3, D8) |
| `pm-dev-python:python-core` | `marketplace/bundles/pm-dev-python/skills/python-core/SKILL.md` | Python production code |
| `pm-dev-python:pytest-testing` | `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` | Python tests (D2, D3) |
| `pm-plugin-development:plugin-architecture` | `.../plugin-architecture/SKILL.md` | `SKILL.md` / bundle structure |
| `pm-documents:ref-asciidoc` | `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md` | `.adoc` documentation (D4) |

Every skill named was obtainable by the bundle path; none was unavailable by both routes.

## Populations (D1)

All four populations were **re-derived during this run**. No number below is carried over from the
plan file. Derivation scripts were written to the session temp dir (never the repository).

### (a) The `ext-point-finalize-step` implementor set — **26 implementors**

Derived from the `implements:` frontmatter across the four surfaces
`extension_discovery.find_implementors` scans (phase-6-finalize `workflow/` then `standards/` with
`workflow/` precedence on a bare-name collision; every bundle's `skills/*/SKILL.md` except
`phase-6-finalize`; project-local `.claude/skills/finalize-step-*/SKILL.md`). The stock
`_IMPLEMENTOR_FRONTMATTER_KEYS` tuple does **not** carry the eight keys D1 asks for, so the
derivation re-implements the same scan surfaces with the wider key set:

```bash
python3 $TMPDIR/derive_pop_a.py .     # mirrors find_implementors' four surfaces
```

| order | step id | source | `mutates_source` | `head_dependent` | `post_run_review` | `records_facts` | `requires_prompt_fields` | `verdict_inputs` | `reads` | `destroys` |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | `default:finalize-step-sync-baseline` | built-in | true | — | — | `action`, `upstream_commit_count`, `work_performed` | — | — | — | — |
| 4 | `project:finalize-step-lessons-housekeeping` | project | true | true | — | — | — | — | — | — |
| 5 | `default:pre-push-quality-gate` | built-in | false | true | — | — | — | — | — | — |
| 6 | `project:finalize-step-plugin-doctor` | project | — | true | — | — | — | — | — | — |
| 7 | `default:pre-submission-self-review` | built-in | false | true | — | — | `candidates` | — | — | — |
| 8 | `default:finalize-step-simplify` | built-in | true | true | — | — | — | — | — | — |
| 9 | `default:finalize-step-security-audit` | built-in | true | true | — | — | — | — | — | — |
| 10 | `default:architecture-refresh` | built-in | — | — | — | — | — | — | — | — |
| 11 | `default:push` | built-in | false | — | — | — | — | — | — | — |
| 20 | `default:create-pr` | built-in | false | — | — | — | — | — | — | — |
| 21 | `project:finalize-step-era-stamp-fill` | project | true | true | — | — | — | 3 globs | — | — |
| 22 | `default:ci-verify` | built-in | false | true | — | — | — | — | — | — |
| 30 | `plan-marshall:automatic-review` | built-in | true | true | — | — | — | — | — | — |
| 40 | `default:sonar-roundtrip` | built-in | true | true | — | `count_status`, `new_code_issue_count`, `issues_fetched`, `work_performed` | — | — | — | — |
| 62 | `default:adr-propose` | built-in | — | — | — | — | — | — | — | — |
| 70 | `default:branch-cleanup` | built-in | false | — | — | `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` | — | — | — | `worktree` |
| 81 | `project:finalize-step-deploy-target` | project | false | — | — | — | — | — | — | — |
| 85 | `project:finalize-step-sync-plugin-cache` | project | false | — | — | — | — | — | — | — |
| 990 | `project:finalize-step-review-retrospective` | project | false | true | true | — | — | — | — | — |
| 991 | `default:lessons-capture` | built-in | false | — | true | — | — | — | — | — |
| 992 | `default:finalize-step-preference-emitter` | built-in | false | — | true | — | — | — | — | — |
| 995 | `plan-marshall:plan-retrospective` | bundle-optional | false | — | true | — | — | — | — | — |
| 998 | `default:record-metrics` | built-in | false | — | true | `total_tokens`, `total_wall_seconds`, `any_phase_missing_end_time` | — | — | — | — |
| 999 | `default:finalize-step-print-phase-breakdown` | built-in | false | — | true | — | — | — | — | — |
| 1000 | `default:emit-landing` | built-in | false | — | true | — | — | — | — | — |
| 1100 | `default:archive-plan` | built-in | false | — | — | — | — | — | — | `plan-directory` |

A dash means the key is **absent** from the frontmatter, not that it is declared false.

Facts this run depends on, read off the table:

- **`reads:` is declared by zero implementors** — D7.1's asserted absence, re-verified.
- **`destroys:` is declared by exactly two** — `default:branch-cleanup` → `[worktree]`,
  `default:archive-plan` → `[plan-directory]` — D2.5's two anchors, re-verified as present.
- **`create-pr` (20) → `era-stamp-fill` (21) → `ci-verify` (22)** — D2.1's adjacency holds today.
- **`mutates_source: true` AND `order > default:pre-push-quality-gate.order` (5)** resolves to
  `default:finalize-step-simplify` (8), `default:finalize-step-security-audit` (9),
  `project:finalize-step-era-stamp-fill` (21), `plan-marshall:automatic-review` (30),
  `default:sonar-roundtrip` (40) — D8 / 230-G1's correct membership.
- `default:lessons-capture` declares `mutates_source: false` — the wrong example 230/G1 names.

### (b) The hand-written `[DISPATCH]` emission population — **11 blocks in 7 files**

```bash
python3 $TMPDIR/derive_pop_b.py .     # manage-logging `work` call carrying [DISPATCH]
```

Both D1 exclusions applied: `ref-workflow-architecture/standards/dispatch-logging.md` (which quotes
the shape in order to forbid it) is excluded by construction, and the dispatch-site / doc-echo split
is decided by whether the file carries a **fenced, executable** `effort resolve-target` command
block, not by the string appearing in prose.

**Dispatch sites — 9 blocks in 5 files:**

| File | Blocks (line) |
|---|---|
| `plan-marshall/workflow/planning-outline.md` | 110, 144, 429, 482 |
| `plan-marshall/workflow/planning.md` | 284, 324 |
| `phase-3-outline/standards/outline-workflow-detail.md` | 215 |
| `phase-6-finalize/workflow/pre-submission-self-review.md` | 202 |
| `workflow-pr-doctor/SKILL.md` | 36 |

**Doc-echoes — 2 blocks in 2 files:** `phase-6-finalize/workflow/lessons-capture.md` (64),
`phase-6-finalize/workflow/adr-propose.md` (49). Neither carries an `effort resolve-target` call,
confirming 280's adversarial-review correction that the "add `--workflow` to the resolve" instruction
is uncarryable for them.

### (c) The per-implementor input-table `Required` row population — **1 row outside the contract**

```bash
python3 $TMPDIR/derive_pop_c.py . pop_a.json   # header-parsed Required column, never a fixed index
```

Across the 26 implementor docs, tables carrying a `Required` column yield 9 rows, of which **3** sit
in a table whose first header cell is `Prompt-body field` (the repository-wide convention header —
11 docs tree-wide use it verbatim) and **6** sit in `plan-retrospective`'s CLI `| Parameter |
Required |` table, which is not a prompt-body-field table. Scoped to prompt-body-field tables, the
rows whose key falls outside the generic contract set
(`name`/`plan_id`/`skills`/`workflow`/`instructions`/`WORKTREE`) are exactly one:

| Step | Key | Required |
|---|---|---|
| `default:pre-submission-self-review` | `candidates` | Yes |

**Sizing fact for D3:** only **2 of the 26** implementors carry a `prompt: |` block of their own
(`default:pre-submission-self-review`, `default:finalize-step-simplify`) — so **24 of 26** have none,
and the `∀`-direction of `test_step_prompt_fields_contract.py` is vacuous for those 24.

### (d) The `from _dispatch_roster import` importer set — **9 modules**

```bash
grep -rn "^from _dispatch_roster import" test/ | sed 's/:.*//' | sort -u
```

Six under `test/plan-marshall/phase-6-finalize/` and **three outside it**:
`test/plan-marshall/manage-lessons/test_lesson_store_resolution_population.py`,
`test/plan-marshall/phase-5-execute/test_execute_phase_markers.py`,
`test/plan-marshall/ref-workflow-architecture/test_citations_only_conformance.py`.

**040/G3 closed:** `040-inert-thinking-directives-in-dispatched-docs/report-01.md` § D2 asserted the
module's "sole consumers are the phase-6-finalize tests". That clause is replaced with the derived
importer set. The paragraph's conclusion — that the module is a Markdown-section/roster-row parser,
not the execution-context workflow roster — is independently correct and is left unchanged.

**HALT gate:** (a) and (c) were both derivable, so the plan proceeds.

## Deliverables

_in progress_

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
