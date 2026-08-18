# Verification — 020-a-foreign-task-reports-done-with-no-pr-anywhere

**Landed as:** PR #1151, squash commit `9c679c99`
**Verdict:** verified-with-gaps

The three deliverables all landed and all survive in the tree. The verb, the predicate, the column,
the gate and the archive-plan wiring exist as named, and the named tests exist and pass. But the gate
as built cannot reliably answer the question it was created to answer — it never names the branch it
classifies — and it clears the one state (`unpushed`) that most obviously has no PR. One load-bearing
factual claim in `report-01.md` (the single-seam finding under D0) is false against the tree that was
current when it was written.

## Method

Read in full: `plan.md`, `report-01.md`.

Landed diff: `git show --stat 9c679c99`, plus `git show 9c679c99 -- <path>` for `ci_base.py`,
`github_ops.py`, `manage-solution-outline.py`, `foreign_pr_gate.py`, the two doc files.

Ground truth read at `HEAD` = `61a43e53` on branch `claude/review-apparatus-analysis-mcf8md`:

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py` (whole file)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md` lines 1–80
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` §
  "PR landing-state", `run_cli`
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` (router)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  lines 650–840, `github_ops.py` registration block
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py`
  (`is_foreign_path`, `_extract_affected_files`, `deliverable_write_set`) and
  `manage-solution-outline.py` (`_annotate_foreign`, `cmd_list_deliverables`, `_lookup_deliverable`)
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` `cmd_update`,
  `_cmd_step.py`, `_tasks_core.py` (`normalize_step_path`, `validate_steps_are_file_paths`)
- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`
  `normalize_to_repo_relative`
- the three test files, plus `test/plan-marshall/tools-integration-ci/test_ci_base.py` doc-parity block

Post-landing history per file: `git log --oneline 9c679c99..HEAD -- <path>` over every file in the
landed stat, plus `git log --oneline -S"mutation_scope" -- <two paths>`.

Searches run (each cited where it backs an absence):

- `grep -rn "landing-state\|landing_state\|LANDING_STATES" marketplace/ --include=*.py --include=*.md`
- `grep -rn "foreign_pr_gate"` across the repo (excluding `.git` and `doc/plans`)
- `grep -rn "foreign" marketplace/bundles/plan-marshall/skills/{manage-metrics,plan-retrospective,manage-execution-manifest}/`
- `grep -rn "foreign" marketplace/bundles/plan-marshall/skills/manage-solution-outline/**/*.md`
- `grep -rni "PR not yet opened" marketplace/ doc/` and `git grep -ni "not yet opened" 9c679c99^ -- marketplace/`
- `grep -rn "'status'\] = " marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py`
- `grep -rn "Sub-verbs" marketplace/bundles/plan-marshall/skills/tools-integration-ci/`
- `Grep _PR_ROW|pr \(\?P<verb>` over `test/`
- `Grep _resolve_landing_state|_list_deliverables|_resolve_repo_root` over `test/`
- `grep -rln "API-Sheriff" doc/ marketplace/`

Tests run (not the full build):

```
.venv/bin/pytest test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py \
  test/plan-marshall/workflow-integration-github/test_pr_landing_state.py \
  test/plan-marshall/manage-solution-outline/test_foreign_deliverable_column.py -o addopts="" -q
→ 56 passed in 8.62s
```

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | The report states the discriminator, where it is read, and the derivation method — or states none exists and the plan stops | Discriminator exists (outside-project-root path); completion seam single, at `_tasks_crud.py::cmd_update`; no halt | Discriminator claim CONFIRMED and correct. Single-seam claim FALSE: `_cmd_step.py:73` also writes `task['status'] = 'done'`, and did so at `9c679c99^` | met, on partly false evidence |
| D1 | The verb exists with a test per return value, and a plan with a `pushed_no_pr` foreign deliverable is refused at archive, proven by a test that fails before the change | `ci_base.derive_landing_state` + `LANDING_STATES`; `_github_pr.cmd_pr_landing_state` registered as `('pr','landing-state')`; `foreign_pr_gate.check`; wired into `archive-plan.md`; tests per state asserted against the declared set | All symbols exist at HEAD; tests exist and pass; the gate returns `blocked`. But the gate never passes `--branch`, and the refusal is proven only at the `check()` function, never at the archive step | met literally, defective in substance |
| D2 | A gate reads a structured signal rather than the artifact prose, and the coverage column distinguishes the two populations | `is_foreign_path`; `_annotate_foreign` stamps `foreign` per entry + roll-up; the gate consumes it | `is_foreign_path` at `_plan_parsing.py:63`, `_annotate_foreign` at `manage-solution-outline.py:505`, consumed by the gate. No coverage-ratio consumer reads `foreign`; the flag is absent from `read --deliverable-number` / `get-deliverable` | partially met |

### D0 — the halt gate

**The discriminator claim is correct.**
`file_ops.normalize_to_repo_relative` (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py:339`)
strips the repo-root prefix only under `if path.startswith(repo_root + '/')` (line 363) and otherwise
falls through to `return path` (line 366) — an outside-root absolute path survives verbatim.
`_tasks_core.normalize_step_path` (line 223) is a pure delegate to it.
`validate_steps_are_file_paths` (`_tasks_core.py:180`) admits any string with a `/` or a source
extension, so an outside-root absolute target is not rejected.
`_extract_affected_files` in `_plan_parsing.py` captures each path with `.strip()` only — verbatim,
as claimed; at `9c679c99^` it sat at lines 277–303 exactly as the report cites. **CONFIRMED.**

**The single-seam claim is false.** The report states: *"`done` is written in exactly one place:
`manage-tasks/scripts/_tasks_crud.py::cmd_update`"*. A second writer exists:

```
marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py:73
        task['status'] = 'failed' if has_failed else 'done'
```

`git show 9c679c99^:.../_cmd_step.py | grep -n "task\['status'\]"` returns line 73 with the same text,
so this was true when the report was written. That path — the per-step `manage-tasks step` verb — is
the one the phase-5 task runner drives; it is arguably *the* completion seam, and `cmd_update` is the
manual override. Search backing the absence of any third writer:
`grep -rn "'status'\] = " marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py` → exactly
four hits, of which two write `done`/`in_progress` in `_cmd_step.py` and one in `_tasks_crud.py`.
**CONFIRMED FALSE.**

The falsity does not by itself invalidate the no-halt verdict — the plan's halt condition was
"the distinction is not derivable at the point completion is recorded", and it *is* derivable at both
seams. But the plan's HYPOTHESIS claim-label ("done-ness is decided at a **single**, locatable seam")
was reported as confirmed when the tree says two.

**Consequence not recorded by the report:** neither seam was changed. `steps[].target` is never read
by anything this plan added — the gate reads deliverable `affected_files`, not task steps. A foreign
*task* still reaches `done` at the commit exactly as before; only the *plan* is stopped, at archive.
The report acknowledges this design choice when rejecting a CodeRabbit comment ("the archive gate is
the correct, and plan-specified, enforcement point"), and the plan's D1 body does specify the archive
position — so this is a deviation from the plan's Goal sentence, not from its D1 instruction.

**The re-derivation of the "PR not yet opened" lead is accurate.**
`grep -rni "PR not yet opened" marketplace/ doc/` (excluding this plan directory) → no hits, and
`git grep -ni "not yet opened" 9c679c99^ -- marketplace/` → no hits. The string was absent before the
change too. **CONFIRMED.**

### D1 — the verb and the gate

**The verb exists, at HEAD, unchanged since landing.**
`ci_base.py:817` `LANDING_STATES: tuple[str, ...] = ('merged', 'pr_open', 'pushed_no_pr', 'unpushed')`;
`derive_landing_state` at line 820. `git log --oneline 9c679c99..HEAD -- .../ci_base.py` → empty.

**The handler exists and is registered.**
`_github_pr.cmd_pr_landing_state` at line 726; `github_ops.py:1868` maps `('pr','landing-state')`;
the `--branch` subparser is added in `github_ops.main()`. The router-level `--project-dir` is consumed
before dispatch in `ci.py:127` (`extract_routing_args`) and installed via `set_default_cwd`, and
`ci_base.run_cli` line 725 (`effective_cwd = cwd if cwd is not None else _DEFAULT_CWD`) honours it —
so the plan's ⚠ note about verifying `--project-dir` against the router rather than the argparse table
was followed and is correct. **CONFIRMED.**

**The gate exists and fails closed on indeterminacy.** `foreign_pr_gate.check` returns `error` on an
unlistable outline, an unresolvable project root, an unresolvable foreign root, and a landing state
outside `LANDING_STATES` (`foreign_pr_gate.py:317–327`); `cmd_check` exits 1 on `error`.
`archive-plan.md:36–51` carries the wiring as the first section, with `blocked` and `error` both
spelled as STOP. **CONFIRMED.**

**The cold read is defensible.** `archive-plan.md:50` reads *"**STOP. Do NOT mark the step done and do
NOT archive.** … The condition is **blocking**, not advisory"*. Read cold, that is a prohibition.
The report's BLOCKING verdict is **ACCURATE**.

**Where D1 is defective — see Correctness review G1, G2, G3, G5.**

### D2 — the structured signal and the column

`is_foreign_path` at `_plan_parsing.py:63` is lexical (`os.path.normpath` + `os.path.commonpath`),
never `resolve()`, and returns True on the `ValueError` cross-root branch. Every trap the report names
is covered by a passing test in `test/plan-marshall/manage-solution-outline/test_foreign_deliverable_column.py:33–61`
including the sibling-prefix case `/repo-other` vs `/repo`. **CONFIRMED.**

`_annotate_foreign` at `manage-solution-outline.py:505` is called from `cmd_list_deliverables` at
line 495. At landing it stamped only `affected_files`; the three-field loop at line 538
(`for field in ('affected_files', 'mutation_scope', 'survey_scope')`) was added later by
`63943f55` (#1295) — see Completeness review.

The "gate reads a structured signal" half is met. The "coverage column distinguishes the two
populations" half is met only as *data availability*: `grep -rn "foreign"` over `manage-metrics/`,
`plan-retrospective/` and `manage-execution-manifest/` returns **no hits**, so no computed ratio
anywhere separates the populations. The pooling defect the plan cites as D2's motivation is
un-addressed in any consumer.

## Report-claim audit

| Claim in `report-01.md` | Verdict | Evidence |
|---|---|---|
| D0: "`done` is written in exactly one place: `_tasks_crud.py::cmd_update` (the `args.status == 'done'` branch, lines ~662–667)" | **FALSE** | `_cmd_step.py:73` writes `done` too, at `9c679c99^` as well. The cited lines are also not an `== 'done'` branch but an `is not None` + membership check (`_tasks_crud.py:662–667`) |
| D0: "No repository-target field exists in the task schema" | ACCURATE | `_tasks_core.TaskDict` and `standards/task-contract.md` carry no repository field; grep over `manage-tasks/scripts` finds none |
| D0: `normalize_to_repo_relative` returns an outside-root absolute path unchanged (`file_ops.py:339`, line 366) | ACCURATE | Read; `return path` is at line 366 |
| D0: `_extract_affected_files` (lines 277–303) captures paths verbatim | ACCURATE | Verified against `9c679c99^`, where the function sits at 277–303 and only `.strip()`s |
| D0: `validate_steps_are_file_paths` admits an outside-root absolute target | ACCURATE | `_tasks_core.py:185–195` |
| D0: the literal "PR not yet opened" does not exist in the bundle tree | ACCURATE | Two searches, on HEAD and on `9c679c99^`, both empty |
| D0: `ci.py` consumes `--project-dir` before provider dispatch | ACCURATE | `ci.py:127` |
| D0 caveat: coverage depends on foreign paths being authored absolute/`../`-escaping | ACCURATE and still true | `is_foreign_path` unchanged |
| D1: `ci_base.derive_landing_state` + `LANDING_STATES` exist | ACCURATE | `ci_base.py:817`, `:820` |
| D1: registered as `('pr','landing-state')` with a `--branch` subparser, github-only, gitlab untouched | ACCURATE | `github_ops.py:1834–1868`; no gitlab registration (grep) |
| D1: "Auth failure / unparseable output / gh-list failure all hard-error" | ACCURATE | `_github_pr.py:762`, `:781`, `:777` |
| D1: the gate "iterates the foreign deliverables (from `list-deliverables`' `foreign` column)" | ACCURATE | `foreign_pr_gate.py:186–222`, `:265` |
| D1: "resolves each foreign repository's landing state via `ci pr landing-state --project-dir {root}`" | ACCURATE but incomplete | `foreign_pr_gate.py:155–166`. The command as built carries **no** `--branch`, which the plan's D1 signature specified (`--project-dir P --branch B`). The report does not disclose the omission |
| D1: tests "each parametrized over `LANDING_STATES` so the population is asserted against the verb's own declared set" | ACCURATE | `test_pr_landing_state.py:52–68`; `set(_CASE_PER_STATE) == set(LANDING_STATES)` plus a produced-set equality and a non-vacuity guard |
| D1: "plus the archive-refusal test proving a `pushed_no_pr` foreign deliverable is `blocked`" | OVERSTATED | `test_foreign_pr_gate.py:71` proves `check()` returns `blocked`. Nothing proves *archive* is refused; the archive-plan wiring is prose and is exercised by no test (`grep -rn "foreign_pr_gate"` → one prose site, one docstring, two test references, all to the module) |
| D1: "All fail before the change (the verb/gate did not exist)" | ACCURATE (trivially) | The modules and symbols are new in `9c679c99`; import would fail |
| D1: gate "fails closed … an unresolvable project root … yield `status: error`" | ACCURATE but the guard is decorative | `foreign_pr_gate.py:261` resolves `project_root` and then never uses it for classification — classification happens inside the `list-deliverables` subprocess, which resolves its own root and has no flag to be told one |
| D2: `is_foreign_path` correct on every named trap | ACCURATE | Six passing predicate tests |
| D2: "`list-deliverables` now stamps `foreign` on each `affected_files` entry and a per-deliverable roll-up" | ACCURATE for the landed state | At landing only `affected_files` was stamped; `mutation_scope`/`survey_scope` were left unstamped until `63943f55` |
| D2: "the sole intended ripple; no other existing assertion changed" | ACCURATE | Only `test_manage_solution_outline.py` changed among pre-existing tests (7 lines in the stat) |
| Build gate: "`./pw verify plan-marshall`: green — 15848 passed, 1 skipped" vs Contract check step 5: "final green run 15859 passed" | INTERNALLY INCONSISTENT | Both figures appear in the same report as the green run. The story is reconcilable (pre- and post-fix-commit) but § Build gate presents 15848 as final |
| Findings: "diff confirmed clear of the landing-message site, the merge-lock/branch-cleanup surfaces, and any other repository" | ACCURATE | `git show --stat 9c679c99` touches 15 files, none of them `branch-cleanup.md`, any merge-lock script, or any other repo |
| Residue: the `cuioss/API-Sheriff` #185/#154 re-review remains owed | ACCURATE and still owed | `grep -rln "API-Sheriff" doc/ marketplace/` → only this plan's two files and `automatic-review/standards/pr-agent.md`, which grounds on PR **#103**, not #185/#154 |
| Reviewer participation table and the derivation from `automatic-review/standards/{bot_kind}.md` `author_login` | UNVERIFIABLE | PR comment bodies are not in the clone; the three standards docs do exist |
| Cost / wall-clock figures | UNVERIFIABLE | No in-repo substrate |

## Correctness review

**C1 — the gate never names the branch it classifies. CONFIRMED.**
`foreign_pr_gate.py:155–166` builds:

```python
cmd = [sys.executable, str(executor), _CI_NOTATION, '--project-dir', repo_root, 'pr', 'landing-state']
```

No `--branch`. The plan's D1 specified `ci pr landing-state --project-dir P --branch B`. With `--branch`
omitted, `_resolve_landing_branch` (`_github_pr.py:664`) falls back to `git rev-parse --abbrev-ref HEAD`
in the foreign checkout — i.e. whatever branch that working tree happens to be sitting on when finalize
runs, which is not necessarily the branch the foreign change was committed to. Two failure directions
follow from the code, both reasoned from the handler body rather than observed:

- the foreign checkout is on its pushed default branch: `gh pr list --head main --state all` normally
  returns no tip-matching PR, `git branch -r --contains main` is non-empty → `derive_landing_state([], True)`
  → `pushed_no_pr` → the gate **blocks a plan whose foreign work is finished**;
- the foreign checkout has been switched away from the work branch: the work branch is never examined
  at all.

**C2 — `unpushed` clears the gate, and the plan's Goal says it must not. CONFIRMED.**
`foreign_pr_gate.py:78` `BLOCKING_LANDING_STATE = 'pushed_no_pr'` is the only refusal, and
`test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py:101` locks it in:

```python
def test_unpushed_foreign_deliverable_clears():
    ...
    assert result['status'] == 'clear'
```

The plan's Goal is *"A foreign task cannot reach `done` while its change has no pull request."* An
`unpushed` foreign change has no pull request — it has not even reached a remote — yet it clears. The
plan's D1 body does say "refuse to archive while any is `pushed_no_pr`", so the implementation is
faithful to the instruction and unfaithful to the goal. A foreign change that was committed and never
pushed is the strictly worse case, and it is the one that passes.

**C3 — the gate's population ignores declared intent. CONFIRMED.**
`_foreign_paths_by_deliverable` (`foreign_pr_gate.py:186–222`) and `_annotate_foreign`
(`manage-solution-outline.py:505–547`) collect every entry with a truthy `foreign` flag, with no
reference to `entry['intent']`. `_extract_affected_files` explicitly returns
`{'path': str, 'intent': str | None}` (`_plan_parsing.py:447`), and the repository already owns the
authoritative write-set helper `_plan_parsing.deliverable_write_set` (line 455), whose docstring states
the rule: *"every `affected_files` **or** `mutation_scope` entry whose declared intent is not
`STEP_INTENT_READ`"*. The gate does not use it. A foreign path declared `(read)` — a file the plan
merely consults in another repository — therefore enters the blocking population, and the gate can
refuse to archive over a repository nothing was written to.

**C4 — the "fail closed on an unresolvable project root" guard cannot enforce what it claims.
CONFIRMED (mechanism) / PLAUSIBLE (impact).**
`check()` resolves `project_root` at line 261 and thereafter uses it only in the error message and in
the emitted payload. The classification that decides the population is performed by
`_annotate_foreign` inside the `list-deliverables` **subprocess**, which resolves its own root and,
on failure, deliberately fails **open** (stamps everything host, `manage-solution-outline.py:518–522`).
`list-deliverables` accepts only `--plan-id` — there is no flag by which the gate could impose the root
it resolved. The two agree only because the subprocess inherits the gate's cwd; nothing asserts that,
and nothing detects a divergence.

**C5 — relative foreign paths are resolved against two different bases. CONFIRMED.**
`is_foreign_path` joins a relative path onto `project_root` (`_plan_parsing.py:95`), while
`_resolve_repo_root` (`foreign_pr_gate.py:120–140`) does `os.path.dirname(path)` and `os.path.isdir()`
against the **process cwd**. A `../other-repo/src/Foo.java` entry is classified against the git toplevel
and then resolved against the cwd. Equal when the gate runs from the checkout root; divergent otherwise.

**C6 — `LANDING_STATES`' ordering comment is wrong. CONFIRMED.**
`ci_base.py:814`: *"#: The closed set of landing states, in refuse-most-first precedence order."*
The tuple is `('merged', 'pr_open', 'pushed_no_pr', 'unpushed')` — landed-first. The only refused
state, `pushed_no_pr`, is third. The comment describes the opposite of the data it annotates.

**C7 — no provider guard. CONFIRMED (code) / reasoned (impact).**
`landing-state` is registered only in `github_ops.main()`; `grep -rn "landing"` over the gitlab skill
returns nothing. On a GitLab-configured project the gate's subprocess hits an argparse rejection, so
`_resolve_landing_state` sees empty stdout, returns `status: error`, and the gate errors — fail-closed,
but with an unactionable message. `leaf-command-reference.md:34` documents "**GitHub provider only.**";
the gate does not read that and cannot say it.

**C8 — a `blocked` verdict exits 0 even when items are also unresolved.** `cmd_check` returns
`1 if result.get('status') == 'error' else 0`, and the precedence at `foreign_pr_gate.py:330–336` puts
`blocked` above `error`. A caller relying only on the exit code proceeds on a `blocked` result. The
`archive-plan.md` contract does instruct parsing `status`, so this is documented rather than latent —
noted, not filed as a gap.

## Completeness review

**Doc consumers of the new verb — three of five surfaces were not updated. CONFIRMED.**

| Surface | Updated? |
|---|---|
| `tools-integration-ci/standards/leaf-command-reference.md:34` | yes |
| `workflow-integration-github/SKILL.md:280` | yes |
| `tools-integration-ci/SKILL.md:310` — § Canonical invocations, `### pr` "Sub-verbs:" enumeration | **no** — the list runs `view … create` with no `landing-state` |
| `tools-integration-ci/standards/api-contract.md:136–148` — § "PR Operations" response-field table | **no** — every other `pr` read verb has a row naming its response fields; `landing-state`'s (`branch`, `tip_sha`, `pushed`, `pr_count`, `landing_state`, `landing_states`) are documented nowhere |
| `phase-6-finalize/SKILL.md:1813–1822` — § Scripts inventory, and § Canonical invocations | **no** — all seven other scripts in `phase-6-finalize/scripts/` have rows; `foreign_pr_gate.py` has none. `grep -rn "foreign" phase-6-finalize/` returns only `archive-plan.md` and unrelated `foreign-safe` lock prose |

No test catches this: `test/plan-marshall/tools-integration-ci/test_ci_base.py:1212` defines
`_CHECKS_ROW` and asserts doc parity for `checks` verbs only. `Grep _PR_ROW|pr \(\?P<verb>` over
`test/` → no matches.

**The `foreign` column is undocumented in its owning skill. CONFIRMED.**
`grep -rn "foreign"` over `manage-solution-outline/SKILL.md` and `manage-solution-outline/standards/*.md`
→ no hits. The worked output example at `manage-solution-outline/SKILL.md:410–414` still shows
`affected_files` as bare path strings, with neither `intent` nor `foreign` and no deliverable-level
roll-up.

**The flag is missing from the sibling read verbs. CONFIRMED.**
`_annotate_foreign` is called only from `cmd_list_deliverables` (`manage-solution-outline.py:495`).
`_lookup_deliverable` (line 550), which backs both `read --deliverable-number` and `get-deliverable`,
returns the same record type **without** the flags. `SKILL.md:175` states those two verbs return
"byte-identical output" to each other; it is now the `list-deliverables` record that diverges from both.

**No coverage ratio consumes the column. CONFIRMED.**
`grep -rn "foreign"` over `manage-metrics/`, `plan-retrospective/` and `manage-execution-manifest/`
→ no hits. `manage-metrics._count_affected_files` reads `references.json::affected_files`, a different
substrate entirely. D2's stated motivation — "every coverage ratio silently pools host paths with
foreign ones" — is therefore not closed by anything that landed.

**The survey-scope half of the declared surface was missed at landing, and has since been closed.**
`git show 9c679c99:.../manage-solution-outline.py` shows `_annotate_foreign` looping
`deliverable.get('affected_files', [])` only, and the landed `_foreign_paths_by_deliverable` reading
only `affected_files`. A survey-scope deliverable declares `Files to survey:` / `Files expected to
mutate:` *instead* of a flat list, so its whole surface was unstamped and invisible to the gate.
`git log --oneline -S"mutation_scope" -- <both paths>` → `63943f55` ("fix(qgate): check the declared set
for CLOSURE, not only for existence", #1295) added the three-field loops and the dedupe. **Closed by a
later plan; recorded here for the record, not filed as an open gap.**

**The gate's I/O seams are untested. CONFIRMED.**
`Grep _resolve_landing_state|_list_deliverables|_resolve_repo_root` over `test/` returns matches only
in unrelated modules (`audit-archived-plan-retrospectives`, `manage-architecture`,
`manage-solution-outline`'s own `cmd_list_deliverables`). Every gate test injects all three seams via
`_run(...)` (`test_foreign_pr_gate.py:38–63`). The omitted `--branch`, the `--project-dir` routing and
the TOON parse path are covered by nothing.

**Nothing enforces the gate.** `grep -rn "foreign_pr_gate"` across the repo returns four sites: the
prose invocation in `archive-plan.md:43`, the module's own docstring, and two test references. The
archive step is executed by an LLM dispatcher following a standards document. The plan's own D2 states
*"Prose that no gate reads must not be the record of a blocking condition"* — the gate's invocation is
itself exactly that.

## Out-of-scope compliance

**Clean.** `git show --stat 9c679c99` lists 15 files: the plan directory move plus `report-01.md`,
`manage-solution-outline` (2), `phase-6-finalize/scripts/foreign_pr_gate.py` and
`standards/archive-plan.md`, `tools-integration-ci` (2), `workflow-integration-github` (3), and four
test files.

- **Landing-message composition site** — untouched; no file in the stat belongs to it.
- **Merge-lock and branch-cleanup surfaces** — untouched; `branch-cleanup.md` and every `merge_lock`
  script are absent from the stat. The one `phase-6-finalize` standards file changed is
  `archive-plan.md`, which the plan explicitly nominates as the gate position.
- **Any change to another repository** — the diff is entirely inside this repo.
- The plan's "Expected surface" also named `manage-tasks/` and `phase-5-execute/`; neither was changed,
  correctly, since D0 was analysis-only and the D2 prose premise did not reproduce.

## Residue status

| Residue item recorded in `report-01.md` | Status today |
|---|---|
| Owed conditional check: re-review `cuioss/API-Sheriff` #185 or #154 with the shipped reviewer pack and compare against the recorded zero | **STILL OPEN.** `grep -rln "API-Sheriff" doc/ marketplace/` returns only this plan's `plan.md` and `report-01.md`, plus `automatic-review/standards/pr-agent.md`, which grounds on PR **#103** — a different PR, and a grounding record, not the owed re-review. No later plan in `doc/plans/review-apparatus/` mentions it (`grep -rln "API-Sheriff" doc/`). The obligation now lives only in one run report, which is the same "written and read by nothing" shape the plan was written to remove |
| The absolute-path authoring dependency of the foreign discriminator | **STILL OPEN.** `is_foreign_path` is unchanged since landing; a foreign change authored with bare relative paths still classifies as host. Correctly recorded as a coverage bound, not a defect |
| Merge blocked on the operator's CLA on PR #1151 | **CLOSED.** `9c679c99` is an ancestor of HEAD |
| In-house reviewer (`cuioss-review-bot`) re-trigger owed on the final head | **MOOT.** The PR merged; a pre-merge re-trigger is no longer possible |

## Summary

**Counts by severity:** 3 major, 6 minor, 0 blocker. One of the majors is a false report claim.

Everything the report says was built is in the tree, under the names it gives, and the named tests
exist and pass (56 tests, run directly). The plan's literal *Done when* clauses are all satisfiable
against the tree. What does not hold up is the substance behind two of them. The gate that D1 exists to
provide asks `ci pr landing-state` a question about *whichever branch the foreign checkout is sitting
on*, because it never passes the `--branch` the plan's own D1 signature specified — so it can both
refuse a plan whose foreign work is done and examine the wrong ref entirely; and it clears `unpushed`,
the state in which a foreign change most unambiguously has no pull request anywhere. D2's column is
real but consumed by exactly one caller, so the coverage-pooling defect it was justified by is
untouched, and the column is absent from the two sibling read verbs and from its own skill's docs.
The report's D0 finding that `done` is written in exactly one place is false — `_cmd_step.py:73` wrote
it then and writes it now — which matters because that finding is what the plan's single-seam
HYPOTHESIS was marked confirmed on. Finally, the enforcement point is a paragraph in a standards
document that no code calls, which is the precise failure shape the plan set out to remove.
