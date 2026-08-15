# Run report — 190-frozen-manifest-diverges-from-live-config (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/frozen-manifest-live-config-82b59f`    **PR:** [#1236](https://github.com/cuioss/plan-marshall/pull/1236)    **Outcome:** completed

## Skills loaded

| Skill | Route | Notes |
|---|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` | First action of the run, before reading the plan. |
| `plan-marshall:ref-code-quality` | bundle path | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | bundle path | `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md` |

Conditional skills were loaded by surface: the plan touches Python production code, Python tests, `SKILL.md` / bundle structure, and workflow docs. No skill was unobtainable by either route.

## Split-guard evaluation (plan's ⚠ "Evaluate the split at outline")

The plan flagged its own weakest-cohesion risk and instructed: *"If the outline finds D4 does not belong beside D1–D3, drop it to its own trivial plan rather than carrying it."*

**Decision: D4 was CARRIED, not split.** The plan's framing is accurate — D1–D3 are one story (a frozen view going stale mid-run) and D4 is residue grouped by who filed it. The deciding factors against splitting:

1. **D5 binds D4 into this plan's test deliverable.** D5(c) — "an unchanged title token emits no repeated line" — is a test *of D4b*. Splitting D4 out would orphan a third of D5 or force D5 to split too.
2. **Each D4 item is single-digit-lines of behaviour change.** A separate branch, PR, and full bot-review cycle for ~25 lines of residue costs more than carrying them.
3. **D4a lands on a surface this plan already opens.** `finalize-step-simplify.md` is in `phase-6-finalize/`, the same skill D2 rewires at Step 1.5.

The split guard was evaluated rather than ignored; the outcome is recorded here because the plan asked for the evaluation, not for a particular answer.

## Deliverables

### D0 — GATE: re-ground all four defects against the implementing source

Mutated nothing. Each defect carries a verdict naming the file and symbol that settled it.

| # | Claim | Verdict | Settled by |
|---|---|---|---|
| 1 | A self-modifying plan's frozen manifest references steps that no longer exist, and nothing reconciles | **CONFIRMED live, with one half of the asserted absence REFUTED** | See below |
| 2 | The per-tree executor is not regenerated after a script-set-changing rebase | **CONFIRMED live** | `workflow-integration-git/scripts/git-workflow.py::cmd_worktree_rebase_to` — the success path read `pre_sha`/`post_sha` and returned; no executor call anywhere in the verb. Both finalize rebase sites route through it (`finalize-step-sync-baseline.md` order 3, `branch-cleanup.md` order 70). `integrate_into_main.py` docstring lines 26 and 525 explicitly disclaim regeneration; the only regeneration was the meta-project-only, post-merge, on-**main** `project:finalize-step-sync-plugin-cache` (order 85) — wrong tree and far too late. |
| 3 | The simplify prompt's scope boundary is file-level only | **CONFIRMED live** | `phase-6-finalize/standards/finalize-step-simplify.md` Step 3 dispatched prompt: `"never touch a file outside that list"` — a file-level bound, with changeset scope described only as "diff hunks vs base SHA". The doc's own § Scope semantics stated the line-level *intent*, but the intent never reached the prompt the agent actually receives. |
| 4 | The title-token line is emitted unconditionally | **CONFIRMED live** | `manage-status/scripts/_status_query.py::cmd_title_token`, the `set` branch — `log_entry(...)` fired immediately after `rmw_json(...)` with no comparison against the stored record. Asymmetric with the sibling `clear` branch in the same function, which was already gated on `if outcome['cleared']`. |

**Defect 1, stated precisely — the plan's own doubt was partly justified.** The plan asserted an absence ("nothing reconciles them") and instructed that an asserted absence be verified exactly as an asserted presence. It does not fully hold:

- **REFUTED:** *"Is the frozen manifest compared against live state at all?"* — Yes. `phase-6-finalize/SKILL.md` Step 1.5 ran `manage-execution-manifest validate-loadable`, implemented at `_manifest_validation.py::_check_step_loadable`. A comparison existed.
- **CONFIRMED:** the comparison was **one-directional** (built-in standards-file *presence* only — never the live `marshal.json` candidate set), and its handling on divergence was a **hard abort**, which is precisely the direction the originating report ruled out. Nothing detected the mirror direction (live config gained a step the frozen manifest misses). A repository-wide search for reconciliation in the manifest bundle found only `change_type` scope reconciliation, which is unrelated.

**None of the four was refuted outright.** The plan ⛔ ACTIVELY DOUBTED that all four remained live and expected at least one to have been closed by unrelated work. That expectation did **not** hold: all four were still live at HEAD. The only correction to the plan's premises is the partial refutation above — the "nothing compares" half of defect 1 was wrong, and correcting it materially improved D2 (see D1).

### D1 — GATE: establish what diverges and how it is handled today

Mutated nothing.

**Current behaviour (pre-change), named:** a hard abort. `phase-6-finalize/SKILL.md` Step 1.5 walked `manifest.phase_6.steps`, and on any `loadable: false` aborted finalize before Step 3 with the canonical actionable message. A sibling compose-time gate (`unresolvable_step`) covered the same direction at composition.

**Fail-direction, settled before the fix was written:** diff-and-backfill, per the originating report and the plan's out-of-scope entry ("Hard-failing on manifest divergence. Excluded per D1's reasoning unless D1 explicitly chooses it").

**The settled direction is a split, not a blanket softening** — and this is the substantive output of the D0 refutation above. Because a comparison already existed and had real value, replacing it wholesale would have lost a genuine guard. The two states it conflated are separated instead:

| Frozen step | Live candidate set | Verdict | Handling |
|---|---|---|---|
| unloadable | **absent** from it | `stale` | **Drop.** Live config agrees the step is gone, so the frozen view is merely behind a change this plan already made. This is the self-modifying-plan case that was being blocked. |
| unloadable | **still lists it** | `broken` | **Fail loud**, message unchanged. The doc was deleted without sweeping `marshal.json` — the original motivating failure. Reconciling it away would silently drop work the project still schedules. |

The hard fail was therefore **narrowed to the case it was written for**, not removed. Recorded in commit `2fd1db5`.

### D2 — reconcile the frozen manifest against live configuration at finalize entry

Commit `2fd1db5`.

- New `manage-execution-manifest reconcile [--apply]` (`manage-execution-manifest.py::cmd_reconcile`), implementing the D1 table. Without `--apply` it is a pure report; it never writes on the error path.
- `compose` now snapshots `phase_6.candidate_steps` — the boundary-normalized candidate list captured **before** any pre-filter or matrix row subtracts from it.
- `phase-6-finalize/SKILL.md` Step 1.5 reconciles **before** checking loadability; the ordering is load-bearing and pinned by a test.
- `required-steps.md` gains a "Reconciliation Contract" section ahead of the existing "Loadability Contract".

**Why the candidate snapshot is load-bearing.** Backfill cannot be "in live config but not in the manifest" — that set includes every step the decision matrix deliberately dropped, so backfilling it would silently defeat the composer. Only a candidate absent from the set *this manifest was composed from* is owed, because only such a step never faced the matrix. Where the diff is unavailable (a manifest frozen before the field existed, or unreadable live config) the verb reports `backfill_determinable: false` and backfills nothing rather than guessing.

**Fail-closed on unreadable live config:** with no live candidate set, "config dropped it" is indistinguishable from "config still wants it", so every unloadable step is classified `broken` — today's hard fail — rather than reconciled away on absent evidence.

**⭐ Self-exercisability trap — stated explicitly, as the plan requires.** This plan changes finalize-entry behaviour, and its own finalize (were it run under the plan-marshall lifecycle) would execute under the manifest frozen at its own outline — i.e. under the OLD behaviour. **A green finalize here is evidence of NOTHING for this deliverable.** This run compounds that: it executed in the standalone `doc/plans/` cloud lane, which never touches `.plan/` and never runs `phase-6-finalize` at all, so the finalize path was not exercised even once.

**Named observation point:** the first plan **composed after this change merges** and then reaches `phase-6-finalize` Step 1.5. Only that run exercises `reconcile` against a manifest composed by the updated `compose` (and therefore carrying `phase_6.candidate_steps`). Verification here rests entirely on the D5 tests, which drive `cmd_reconcile` directly.

### D3 — regenerate the per-tree executor after a rebase that changed the script set

Commit `2fd1db5`. `git-workflow.py`: new `_run_generate_executor` (subprocess seam) and `_refresh_worktree_executor` (decision), wired into `cmd_worktree_rebase_to`'s success path. Payload gains `executor_drift` / `executor_regenerated` / `executor_detail`.

Placed in the rebase verb rather than in either caller because **both** finalize rebase sites route through it, and the verb already computes whether commits were replayed.

Three bounds, each observable on the payload:

- **No replay → no probe.** The `clean` early return and a pre/post-SHA-equal rebase share one `_EXECUTOR_REFRESH_NOT_REPLAYED` constant.
- **Positive drift only.** The probe is `generate_executor drift`, which compares the executor's *embedded* mappings against live bundle state — a precise answer to "did the script set change?", not a guess from changed paths.
- **Indeterminate → regenerate nothing.** A tree with no vendored `marketplace/bundles` (every consumer project) cannot produce a meaningful verdict, and generating there can exit 0 having written nothing — replacing a working executor with an empty one. That is strictly worse than the stale map: a stale map fails one dispatch loudly and is repairable via `/marshall-steward`; an empty executor breaks every dispatch. The verdict is reported and acted on by nobody.

**Non-fatal by contract.** HEAD has already moved when the refresh runs, so converting a refresh failure into a rebase failure would make callers abort a rebase that worked.

**⛔ The standing do-not-duplicate was honoured.** The plugin-registry pin inversion (another epic's) was not touched. This change regenerates a *per-tree derived executor* after a *rebase*; it does not pin, resolve, or alter any plugin registry. Same failure family, different mechanism — kept separate deliberately.

### D4 — finalize prompt and log residue

Commit `4e0859b`. All three shipped; none was already-closed by D0.

- **Line-level simplify scope.** The dispatched prompt gains an explicit line-level clause under changeset scope, and § Scope semantics now names the file-vs-line boundary split as the thing `changeset` and `artifact` actually differ by.
- **Title-token repeat suppression.** `cmd_title_token`'s `set` branch decides `changed` inside the `rmw_json` critical section (same discipline the `clear` branch already used) and emits the INFO line only on a genuine change. `set_at` is excluded from the comparison by construction — it changes on every call, so including it would suppress nothing. **The write is never suppressed**, so the aged-token staleness predicate keeps seeing a live token across a long build. Published as `changed` on the return payload.
- **Bypass-before-dispatch rule promoted** into `ref-code-quality/standards/code-organization.md` § Guard Clauses, with the correctness argument (a bypass after its dispatch cannot undo a mutation, lock, remote call, consumed rate budget, or operator prompt) rather than only the efficiency one.

### D5 — tests, each verified to FAIL pre-fix

| Test | File | Pre-fix failure observed |
|---|---|---|
| (a) frozen manifest referencing a deleted step reconciles per D1's direction | `test/plan-marshall/manage-execution-manifest/test_reconcile.py` (15 tests) | `AttributeError: module has no attribute 'cmd_reconcile'` at collection |
| (b) a script-set rebase leaves a regenerated executor | `test/plan-marshall/workflow-integration-git/test_worktree_rebase_executor_refresh.py` (6 tests) | 6 failed — `AttributeError: ... has no attribute '_run_generate_executor'` |
| (c) an unchanged title token emits no repeated line | `test/plan-marshall/manage-status/test_title_token_repeat_suppression.py` (7 tests) | 6 failed, 1 passed — `KeyError: 'changed'` and no suppression behaviour |

The (c) run's one pre-existing pass is `test_suppressed_set_still_returns_the_record`, the "don't weaken the record" guard — correctly green before the change, since the fix must not alter that behaviour. Recording it rather than hiding it: a test file that goes 100% red is not automatically better evidence than one whose guard tests were already satisfied.

Each red was confirmed to fail **for the right reason** before the fix. An earlier (c) run failed on a fixture defect (`status.json not found`) rather than on behaviour; the fixture was corrected and the red re-observed before implementing.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **4 Python files changed**, so the gate fired:

- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py`

(plus three new test files.)

**Result: `./pw verify` SUCCESS**, all three sub-steps clean. Run twice — once before the PR, and again after the verification-agent fixes:

```text
quality-gate:  ruff "All checks passed!", mypy "Success: no issues found in 399 source files",
               SPDX-header check passed, plugin-doctor issues[0]
test-compile:  mypy "Success: no issues found in 739 source files"
module-tests:  19693 passed, 14 skipped   (pre-fix run)
               19702 passed, 14 skipped   (post-fix run, commit 0eb85e6)
coverage: COMPLETE — checked over full scope
```

Both runs reported **0 failed**. This is the evidence against finding F15's claim of a pre-existing failure — see the verification table.

Read from the streamed tool output per the direct-`./pw` contract (no executor TOON log exists on this path). A per-commit `./pw quality-gate` also ran clean before commit `4e0859b`.

Two failures were caught by the gate and fixed before the commit landed — both recorded as findings below. Notably, **both were invisible to the narrower calls**: the `test-compile` errors are exactly the sub-step that neither `quality-gate` nor `module-tests` runs, which is why the lane contract insists on the full `verify`.

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | D0 re-grounding | The plan's claim "nothing compares the frozen manifest against live config" is half wrong: `validate-loadable` at Step 1.5 *was* such a comparison. | **Accepted as a correction to the plan's premise.** Materially changed D2's design — the fix narrows the existing guard instead of replacing it, preserving the fail-loud for the half-done sweep. |
| 2 | D0 re-grounding | The plan expected ≥1 of the four defects to be already closed by unrelated work. None was. | Recorded. No scope change; the doubt was warranted to hold but did not materialise. |
| 3 | `./pw verify` (quality-gate) | `mypy` union-attr error at `manage-execution-manifest.py:2792` — the backfill-determinable invariant was encoded in a `bool`, so `composed_candidates` could not be narrowed. | **Fixed.** Branch on the narrowing predicate (`isinstance(...) and ... is not None`) directly. mypy's complaint was legitimate, not a nuisance: the predicate is clearer than the bool. |
| 4 | `./pw verify` (test-compile) | `test_reconcile.py:80` — `Need type annotation for "data"`. | **Fixed** (`data: dict`). |
| 5 | `./pw verify` (test-compile) | `test_worktree_rebase_executor_refresh.py:127` — `Returning Any from function declared to return "dict"`. | **Fixed** (bind to an annotated local before returning). |
| 6 | `./pw verify` (module-tests) | `test_manifest_loadability_guard.py::test_skill_md_documents_step_1_5_manifest_loadability_check` failed — a narrative-contract test pins the exact Step 1.5 heading, which D2 renamed. | **Fixed by updating the pin, deliberately not by reverting the heading.** The step genuinely does more now. Two *new* pins were added rather than merely relaxing the old one: reconcile-before-loadability **ordering**, and the presence of `unreconcilable_step` (so a future edit cannot quietly drop the fail-loud half and leave prose reading "reconcile heals everything"). |
| 7 | Beyond-diff sweep | `prepare_execute.py`'s executor-lifecycle comment enumerated two production points; D3 adds a third, making the enumeration incomplete (not false). | **Fixed** — comment now enumerates all three. |
| 8 | Beyond-diff sweep | `manage-execution-manifest/SKILL.md` § "Manifest-on-Write Semantics" asserted the manifest is never re-resolved and never re-consults `marshal.json`; `reconcile` is a bounded exception. | **Fixed** — the section now names `reconcile` as the bounded exception and states precisely what it does *not* do (never re-runs the matrix, never re-adds a matrix-dropped candidate). |

Findings 3–8 are recorded **per instance**, not bundled.

**Self-assessment on finding #7.** The beyond-diff sweep I ran found the `prepare_execute.py` executor enumeration but **missed its sibling** in `tools-script-executor/SKILL.md` — the identical defect class, one directory away. The verification agent caught it (F6). Recorded because it is the honest reading: my sweep was partial, and the independent pass is what closed it. Four further stale restatements (F1, F2, F3, F9, F12) were likewise mine to have found.

_Verification sub-agent findings: see § "Verification sub-agent" below._

## Verification sub-agent

Dispatched read-only (`general-purpose`) before PR creation, against `plan.md`'s requirements and `git diff origin/main...HEAD`, with an explicit instruction to sweep beyond the diff by consumer kind including `*.py` fixtures.

**Round 1 verdict:** D0 PASS, D1 PASS, D2 PASS-with-findings, D3 PASS-with-gaps, D4 PASS (3/3), D5 PASS, out-of-scope CLEAN (plugin-registry pin inversion verified untouched). 15 findings, recorded per instance below. Round 2 was dispatched after the fixes, because a verification pass that found a defect has not finished.

The agent independently re-grounded all four D0 defects against the `origin/main` blobs rather than trusting the report — a check I want recorded, since D0's whole value is that its verdicts are re-derivable.

| # | Finding | Severity | Disposition |
|---|---|---|---|
| F4 | `reconcile` emitted `decision.log` lines **outside** the `--apply` guard: a dry run both mutated a file the verb promises not to touch and wrote an audit record asserting a subtraction that never happened. Compounded by the test module globally stubbing `_emit_decision_log` to a no-op, making emission unobservable to any test. | **Behavioural — real bug in new code** | **FIXED** (`0eb85e6`). Emission moved inside the guard; the stub now *records* instead of discarding, and dry-run silence + apply-time emission are both pinned by new tests. |
| F7 | `executor_regenerated: True` was derived from `gen_rc == 0` alone. The generator can exit 0 having written nothing when marketplace anchoring lands nowhere — exactly the case `prepare_execute._executor_landed` exists for. D3's done-when is phrased as an on-disk outcome. | **Behavioural** | **FIXED** (`0eb85e6`). Added `_worktree_executor_path` / `_executor_landed`; the verdict now comes from disk. Two new tests. |
| F10 | The title-token change-gate compared the **raw** stored field. A record already aged past the staleness threshold "reads as absent" to every consumer, so re-asserting it reported `changed: false` and stayed silent about a token the renderers had stopped honouring. | **Behavioural** | **FIXED** (`0eb85e6`). Comparison now goes through `read_title_token` (staleness-aware). New test. |
| F11 | `reconcile` compared raw frozen ids against a boundary-normalized live set, so a hand-edited `default:`-prefixed id (a path `SKILL.md` sanctions) could be dropped as stale though live config still lists it — and symmetrically backfilled as a duplicate. | **Behavioural** | **FIXED** (`0eb85e6`). Both comparisons canonicalize; the original id is still what is written back. Two new tests. |
| F5 | My new prose asserted "**BOTH** finalize rebase sites route through `worktree-rebase-to`" in three places. There are **three** — `automatic-review` (order 30) dispatches it on its refusal-recovery path. The wrong population was the stated *rationale* for the placement. | **Wrong claim** | **FIXED** (`0eb85e6`). All three now assert the invariant ("EVERY finalize rebase routes through this one verb") with an illustrative rather than closed roster, so a new caller cannot falsify it. The placement decision was correct — arguably more so with three callers. |
| F1 | `manifest-schema.md` — the canonical schema block omits `phase_6.candidate_steps` (while `SKILL.md`'s table was updated: two schema statements disagreeing), and § Validation named only `validate-loadable`. | Stale restatement | **FIXED** (`0eb85e6`). |
| F2 | `phase-6-finalize/SKILL.md:341` "reads the manifest **verbatim** … **not from `marshal.json`**" contradicted Step 1.5 thirteen lines below it. | Stale restatement | **FIXED** (`0eb85e6`) — the bounded exception is now named at the point of the claim. |
| F3 | `manage-execution-manifest/SKILL.md` item 2 of the numbered contract read false in isolation (the carve-out sat two paragraphs later with no pointer), and line 414 wrongly lumped `reconcile` in with the persisted-file-only readers. | Stale restatement | **FIXED** (`0eb85e6`). |
| F6 | `tools-script-executor/SKILL.md:276-281` enumerates when a worktree-bound executor is regenerated — the **same defect class** this run had already fixed in `prepare_execute.py` (report finding #7), in a sibling file the sweep missed. | Stale restatement | **FIXED** (`0eb85e6`). |
| F9 | `status-lifecycle.md:72` "**both verbs emit** a `[MANAGE-STATUS]` work-log line" made false by D4b. | Stale restatement | **FIXED** (`0eb85e6`). |
| F12 | `branch-cleanup.md` documents the `worktree-rebase-to` parse step-by-step but said nothing about the three new payload fields it now receives. | Stale restatement | **FIXED** (`0eb85e6`). |
| F8 | Every test replaced `_run_generate_executor` wholesale, so nothing pinned the verb names, `--marketplace-root`, the cwd pin, or `drift_status`. The agent verified all of them manually and they are correct today — but a rename would go green. | Coverage gap | **FIXED** (`0eb85e6`). Added `TestSubprocessSeamShape`: captures the real argv + cwd, and asserts the live `generate_executor.py` still exposes each name. |
| F13 | Illustrative-only restatements (the SKILL.md TOON example, module docstring, frontmatter description) that already omitted verbs before this change. | INFO | **REJECTED — no action.** The agent itself classified these as not newly falsified; the example block already omits `step_params`, so it is evidently illustrative rather than normative. Changing them would imply a completeness they never claimed. |
| F14 | Run report's Step 9 sections were unfilled and the file untracked at review time. | Process | **REJECTED as a defect — expected mid-flight.** The lane contract fixes those sections to Step 8 condition 3, immediately before the merge gate. Recorded because the observation is fair; the file was committed in `2a1f763` shortly after the agent read it. |
| F15 | Claimed pre-existing failure of `test_branch_cleanup_merge_queue_routing.py::…[gitlab:merge-queue]` at HEAD, contradicting this report's clean-run claim. | Factual challenge | **NOT REPRODUCIBLE.** Re-ran standalone: **23 passed**. Two consecutive full `./pw verify` runs reported SUCCESS with **0 failed** (19693, then 19702). The agent's own runs were concurrent with this session's edits, which is the likeliest explanation. Re-check requested in round 2. The report's clean-run claim stands on the two full-gate runs, not on assertion. |

Findings F1–F15 are recorded **per instance**, not bundled. Two were rejected with reasons stated; one is a factual challenge resolved against the agent, with the counter-evidence named rather than merely asserted.

### Round 2 (after `0eb85e6`)

**All twelve fixes confirmed resolved**, each re-derived from the files rather than from the commit message — the agent checked `read_title_token`'s actual signature against what `_apply_set` passes, and proved the F5 invariant by establishing that `git rebase` appears exactly once in the whole bundle tree (`git-workflow.py`, inside `cmd_worktree_rebase_to`), so "every finalize rebase routes through this one verb" is true rather than merely restated.

**F15 withdrawn, with a root cause.** The pushback was correct, and the reason is worth keeping: the agent's environment runs Python 3.11, and the guard predicate under test scans `tokenize` **NAME** tokens. Before PEP 701 an f-string is a single `STRING` token, so the interpolated identifier the guard looks for does not exist; from 3.12 it tokenizes normally. `pyproject.toml` sets `requires-python >= 3.12` and pins `UV_PYTHON = "3.12"`, so `./pw verify` was always running the supported interpreter. **Residue, informational and pre-existing in an untouched file:** that predicate is silently interpreter-version-sensitive and would go vacuous-then-red if the floor ever moved below 3.12.

Three new findings, all introduced by the round-1 fixes — i.e. all mine:

| # | Finding | Severity | Disposition |
|---|---|---|---|
| N1 | The round-1 schema doc asserted `steps ⊆ candidate_steps` as an invariant. It is not: `_apply_ceremony_finalize_selection` force-inserts a gate's canonical step on `always` with **no candidate-membership check**, and two of the four gate steps are absent from `DEFAULT_PHASE_6_STEPS`, so the violation is reachable on the CSV/default fallback. The same overstatement was encoded in my test assertion, which passes only because the default gates are `auto`. | **False invariant in new prose** | **FIXED** (`c81aee6`). The relation is now stated as normal-but-not-invariant with the exception named; the test states the condition it actually holds under and warns against generalizing. `reconcile` is genuinely unaffected — a forced-in step is in the frozen list so backfill excludes it, and the stale/broken partition never reads `candidate_steps`. |
| N2 | A test I added in round 1 called `read_text()` **before** its `is_file()` guard, so the actionable message was unreachable — a bypass placed after the dispatch it guards, which is *verbatim* the anti-pattern D4c promotes into `ref-code-quality`. | **Self-inconsistency** | **FIXED** (`c81aee6`). Guard reordered, with a comment naming the rule it was violating. Shipping a rule and breaking it in the same change is the part worth recording. |
| N3 | The round-1 F7 fix **duplicated** `_executor_landed` / `_worktree_executor_path` into a second file in the same scripts directory, with two independently-drifting `PLAN_DIR_NAME` sources — a direct hit on `code-organization.md` § Duplication. | **Duplication I introduced** | **FIXED** (`c81aee6`). Extracted to a shared `_executor_slot.py` both entrypoints import. The repo's `_cmd_*.py` counter-convention ("duplicate private helpers to keep modules independent") was weighed and found not to apply: it governs helpers private to ONE module, whereas these are a definition two executor-producing paths must **agree** on. |
| N4 | `_emitted_for`'s docstring promised a reset mechanism that does not exist. | Minor | **FIXED** (`c81aee6`). |

### Round 3 (after `c81aee6`) — final confirmation

N1–N4 all confirmed resolved. The N3 extraction — the only fix touching a well-tested file outside the plan's scope — was checked specifically and found clean:

- **No dangling references.** A repo-wide sweep found zero references to either deleted definition; the alias rebinding preserves monkeypatch behaviour, which is why `test_prepare_execute.py`'s five direct `prepare_execute._executor_landed(...)` calls read unchanged.
- **`PLAN_DIR_NAME` equivalence verified, not assumed.** Both sources are the identical `os.environ.get('PLAN_DIR_NAME', '.plan')` expression, and **no test monkeypatches the attribute** on either module — every test that varies it uses `monkeypatch.setenv`, which both readers observe identically.
- **Executor discovery checked against the discovery code and empirically.** The glob path skips `_`-prefixed files, and an authoritative inventory scan returned **147 notations, zero containing `:_`**. `_executor_slot.py` adds no notation, so **no executor regeneration is owed by this change**.
- **Basename uniqueness** holds across all bundles — the property that actually matters, since the executor puts every skill's `scripts/` dir on `PYTHONPATH`.

**No `SHIM(A|B)` marker owed.** The convention scopes the marker to a read path accommodating a persisted shape an older version wrote; a re-export alias is not that, and all three required fields (owner, version floor, removal trigger) would be unfillable. The detector's indicator set was checked directly — "historical" is not among them, so the module comment cannot trip `shim_unmarked`.

**No new stale restatements.** One readability nit was raised and **fixed** (`e0d7c4a`): the N1 asymmetry sentences had been inserted between `candidate_steps` and the "It exists solely for…" sentence, stranding the pronoun from its antecedent. Reordered so the purpose statement follows the definition and the asymmetry becomes its own paragraph.

**Final deliverable verdicts: D0–D5 all PASS.** Out-of-scope list clean across all three rounds — no registry-pin work, no emission arm, no boundary-ledger arithmetic.

The agent could not run `./pw verify` itself (it needs the 3.12 toolchain), so the build gate in this report is the authority for the full gate; its own evidence is 5826 tests across the affected bundles plus direct reading.

## Reviewer participation

Expected reviewer population **derived from configuration** — the `author_login` of each registry doc under `marketplace/bundles/plan-marshall/skills/automatic-review/standards/`:

| Registry doc | `author_login` |
|---|---|
| `coderabbit.md` | `coderabbitai` |
| `sourcery.md` | `sourcery-ai` |
| `pr-agent.md` | `cuioss-review-bot` |

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | _pending_ | |
| `sourcery-ai` | _pending_ | |
| `cuioss-review-bot` | _pending_ | |

Coverage: _pending_. Shortfall disclosure: _pending_.

This PR does **not** carry `skip-bot-review`: the diff changes `*.py` and `marketplace/bundles/**`, and a skill is reviewed as code.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a token counter to the running agent.
- **Wall-clock:** approximately 1h05m of agent-driven work (first commit `33f025d` at 10:24 UTC, `2fd1db5` at 11:03 UTC, plus the pre-PR verification and report). Source: git commit timestamps on this branch.
- **Population:** this single Claude Code cloud session's activity. ⛔ **NOT comparable to a plan-marshall `metrics.toon` total**, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. A single interactive cloud session does not share that boundary, and no conversion between the two exists — so no equivalent figure is offered rather than presenting a number that implies parity.

## Contract check (Step 9)

_Completed at Step 8 condition 3 — see below._

## What have we learned (Step 9)

_See below._

## Residue

- **D2's observation point is owed and unmet by construction** (see D2). The first plan composed after this merges and reaching `phase-6-finalize` Step 1.5 is the real test. Whoever runs it should confirm `reconcile` emits `candidate_source: marshal.json` and `backfill_determinable: true` — a `false` there on a freshly-composed manifest would mean `compose` failed to write `phase_6.candidate_steps`.
- **A cloud run neither performs nor owes a `/sync-plugin-cache`** (lane contract § Scope and precedence). This change edits `marketplace/bundles/`, so a local developer's cache is stale until they sync; that is a local concern, not a debt this run tracks.
- **`reconcile` is not yet called from anywhere except `phase-6-finalize` Step 1.5.** Phase 5 has the same frozen-view exposure for `phase_5.verification_steps`, and no equivalent snapshot/reconcile exists there. Deliberately out of scope for this plan — the plan's D2 is phase-6-scoped — but it is the natural next arm if the divergence shows up in phase 5.
