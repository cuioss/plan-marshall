# Landing Analysis: PLAN-LB-120 — the merge gate does not admit a step it could not see, and the push gate does not turn an unreadable build row into a pass

epic: live-blockers
workstream: WS-01
pr: #1923

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-120.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `b4430a0a6718b6341913b5b413fa2e9931ccf2a3`, a squash commit with ONE parent, `9bd6a39d2f07a657c9200e50cb148bd4277b5ac1` (the merge of PLAN-LB-108, read with git and named in the leaf prompt). Landing message `rb-lb-120-merge-and-push-gate-truth-fixes-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 13 files, +1056/−154 (`git show --stat b4430a0a6`). The lane reports 4 of 4 deliverables done, `self-review: budget-exhausted` (round 2 was dispatched AFTER the merge and left ten open items), a spec read from the ledger copy.

Surface against the spec's Expected Surface: inside it except two files the spec's deliverables ask for — the new `test_refire_waiver_readers.py` and `test_verification_feedback_producer_vocab.py` (D4). The hypothesis entries `extension_discovery.py` and `_cmd_pre_commit_verify_freshness.py` were touched, with a stated reason. No verb or flag was added (`git diff 9bd6a39d2 b4430a0a6 -G'add_parser|add_argument' --stat` is empty, leaf), so no executor regeneration is owed. The later merge `f84eb0e36` changed `_cmd_loop_back.py` and `manage-status/SKILL.md` but not this plan's lines.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the merge gate separates "declares no head-dependence" from "could not be found" | shipped; the recording half rests on prose | A stale record for a step discovery does not return takes the fallback with `POPULATION_ABSENT_REASON`, and an unreadable declared document is refused (`pre_merge_gate.py:350-354,395-434,553-556`, `_cmd_mark_step.py:228-269,285-315`, `extension_discovery.py:1026-1055`; leaf). `mark-step-done` keeps its contract (an absent step still gives `(False, None)`). The `record-merge` facts are declared (`branch-cleanup.md:20-22`, `:2227-2229`) but `record_merge` does not derive them from the payload, so they are written only if the agent follows `branch-cleanup.md:1662` (L1-4). |
| D2 — the push gate does not turn an unreadable row into a pass | shipped (inability branch); the cause of the Maven residue is mis-attributed (L3-1) | A whole-tree change certified only by an unreadable row is no longer an `UNDETERMINED` pass (`_freshness_crosscheck.py:1110-1152`, leaf). The documented `verify -Ppre-commit -pl core-api` row is decided at outline as an inability; `build-execution.md` was left alone (L1-6). |
| D3 — tests, bounds and fault reports state what they pin | shipped; the "bounded" clause is partly true | Discovery runs once per merge (`pre_merge_gate.py:536`). Neither in-process read has a time limit; the Done-when counts discoveries only (L1-8). |
| D4 — the documents state what the gate does | shipped | The new test enumerates the waiver readers over a `MARKETPLACE_ROOT` `**/*.py` sweep (leaf). |
| executor regeneration | not owed | The argparse diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit. It reported its tool deviations (a skill load, denied Grep and Glob, one `git log --name-only` in the ledger worktree to find the PLAN-LB-121 spec) and no write. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — the read crosses 13 files, with 10 narrative claims passed one by one, the last with the ten round-2 items as sub-items.
- **Verdict:** layer 1 findings (minor); layer 2 findings (minor, info); layer 3 findings (**two major**, minor, info). No blocker.
- **Orchestrator re-read:** L3-1 (`_row_refusal` order and `_scope_adequate`), the `parse_row_scope` docstring for L3-3, the head-binding loop for L3-4. Every other row is a lead the leaf checked and I did not re-read; L3-5 in particular rests on whether `_head_dependence_probe()` runs its scan eagerly, which I did not read.
- **Prompt check.** The 10 claims went into the prompt as separate items.
- **Not read by the leaf:** CI, review and quota facts; real `kind=build` ledger rows; `_ledger_core.py`; `_build_examined.py` (the vocabulary membership is taken from the tests and a module docstring); `verdict_currency.py:362`; `build-execution.md`; `_maven_cmd_discover.py`; the re-entry table.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at b4430a0a6) |
|---------|-------|---------|-----------------------------------|
| L1-4 (minor, leaf) | D1: `record-merge` records a fact for an unconsulted stamp or a fallback | met with deviation: the keys are declared, nothing derives them from the payload and nothing checks a key against `records_facts`; the test shows only that a fact passes through | `pre_merge_gate.py:1408-1520`; `branch-cleanup.md:20-22,1662,2227-2229` |
| L1-6 (minor, leaf) | D2: the documented `verify -Ppre-commit -pl core-api` row | met with deviation: decided as an inability; the documented call shape now gives `stale` for a whole-tree change (L3-3) | `_freshness_crosscheck.py:1110-1152` |
| L1-8 (minor, leaf) | D3: discovery and status read run bounded while the mutex is held | met with deviation: discovery once per merge, no time limit on either read | `pre_merge_gate.py:536` |
| L1-10 (minor, leaf) | Constraint: documentation states current behaviour | partly violated: new tests describe the old behaviour ("Swallowing it left…", "A silent None… was an empty admit", a banner "Treating that as a pass let…"); `LB-100` remains in the `test_lb55` `_merge` docstring (a site the spec did not enumerate) | test files named |
| L1-11 (info, leaf) | Constraints: waiver shape, `loop-back close`, re-entry table, override labels, exact-label check, `required_coverage` | kept; no relaxation found | no change to those symbols |
| L1-1 to L1-3, L1-5, L1-7, L1-9, L1-12 (info, leaf) | the remaining Done-when bullets | met | see the fidelity table |

**Layer 1 verdict:** findings — three minor deviations, one minor doc-standard breach, the rest met.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1 (with the caveat that the unreadable-document branch is reachable in practice only by a race or a stub, because discovery finds only a document that declares `implements`, `extension_discovery.py:1344,1411`), C2 (as worded; recording is prose-driven), C3 (the row's own flags cannot be told from the payload's for the RECORDED row only; real ledger rows were not read), C5, C6, C9.
- **C4 confirmed on the verdicts, wrong on the cause (re-read):** `verify -pl X -am` is NARROW/refused, and `package`/`test -pl X -am` are UNDETERMINED/pass. The lane says this is because the goals are outside the coverage vocabulary. It is the ORDER of the checks (L3-1).
- **C7 — the ten round-2 items, all real (leaf):** (1) `manage-tasks/SKILL.md:616` sits outside the indented table at 607-615; (2) `:482` the new token sits in the `scope_cross_check_reason` table although the coverage dimension keeps `build_scope_unreadable`; (3) `:583-587` the stale cause list; (4) test `:620-622` banner; (5) `test_lb55` `:83-88` and near `:292` still say "at HEAD"; (6) `branch-cleanup.md:845` states `override_options[]` unconditionally; (7) `_cmd_pre_commit_verify_freshness.py:125-127` and `SKILL.md:593-596` say `missing_analyses` "is what to run" although the new route returns an empty list — the consumer falls back to "Re-run a build whose canonical and scope cover this change" (`:511-513`), which is vague and can loop (L3-3); (8) pre-existing "used to"/"historically" wording at the four sites, not in the diff; (9) the `extension_discovery.py:1032-1034` docstring; (10) a test name split across a line break. Items 1 to 6 and 9 and 10 are documentation only; item 7 is a documentation error with a gate-behaviour edge.
- **C8 partly contradicted** (two files outside the OBSERVED list, both asked for by D4); **C10 unverifiable** (CI and review facts).

**Layer 2 verdict:** findings — one claim right on the verdict and wrong on the cause (C4), ten round-2 items confirmed (nine documentation, one with a behaviour edge); the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read) | `_freshness_crosscheck.py:743-755, 766-777` (and the candidate selection around `:979-989`, leaf) | A Maven consumer makes a whole-tree change; the only candidate row is a successful `run --command-args test -pl core-api -am` | `_row_refusal` returns `ROW_CANONICAL_UNKNOWN` (an inability) at `:746-748` BEFORE the scope check at `:751-755`. A row that provably narrows the run is therefore filed as an inability, and a candidate list of inabilities is `UNDETERMINED`, which passes. `_scope_adequate` is False for any scoped row on a whole-tree change whatever its canonical, so the narrowing is decidable without touching `required_coverage`. The lane's reason ("outside the vocabulary") is not what blocks the fix. A push gate that passes a whole-tree change on a `-pl X` row is the fail-open the plan exists to close, left open for the Maven goals `test` and `package`. | major |
| L3-2 (leaf; interaction) | `_freshness_crosscheck.py:746-748, 756-757` | A Maven `test` row that measured zero tests, with PLAN-LB-110's root canonicals (every Maven module-tests row is outside the vocabulary) | `ROW_TESTS_EXECUTED_ZERO` is checked AFTER the canonical, so a green zero-test Maven `test` run is never refuted by this gate. This answers PLAN-LB-121 D1's open question for this gate: it does not refuse the zero-test success. | major (lead; the interaction with the running PLAN-LB-121) |
| L3-3 (leaf; reading of `parse_row_scope` re-read) | `_freshness_crosscheck.py:644-652`; `_cmd_pre_commit_verify_freshness.py:503-513` | A whole-tree change whose only evidence is a real whole-tree `verify --timeout 900` or `verify --format json`, the documented shape (the lane itself re-ran builds with `--timeout 900`) | An unknown flag after the canonical makes the row unreadable (`parse_row_scope` docstring `:615-627` says so), and an unreadable row cannot certify a whole-tree change. The change is `stale`; the message carries the generic remedy, so an agent that repeats the same call shape gets `stale` again. Only `manage-tasks/SKILL.md:616` says to drop the trailing flag. A false refusal that can loop; flags placed before `--command-args` stay readable. | major |
| L3-4 (leaf; the loop re-read) | `pre_merge_gate.py:553-574, 586-592` | A stale `done` record for a step that is no longer discovered (renamed, an opt-in bundle step removed, a cwd with no resolvable project root) | The fallback refuses it. "Re-run those steps" cannot clear it and the message rules out merge authorization; the only way out, `loop-back close --waive-refire` at the candidate head, is not named in the refusal. This is the same refusal as before PLAN-LB-107. The fallback cannot admit a stale record (it sets `declared = True`, so only a waiver or a `preserved` classifier verdict admits). Stranding, not a fail-open. | minor |
| L3-5 (leaf; not re-read) | `pre_merge_gate.py:536, 607` | Any merge with a `phase_steps` map | The probe runs before the gate knows a record is stale, so every merge may pay a full scan of bundles, cache and project skills while holding the mutex with no time limit. Before, a merge with nothing stale did no scan. The classifier worst case is still N × 300 s. | minor (lead) |
| L3-6 (leaf) | `pre_merge_gate.py:1397-1405`; `branch-cleanup.md:1662` | A misspelled or missing head-binding fact; `head_binding_status_read_fault={fault text}` | `record-merge` accepts any key, so the misspelling passes silently; raw exception text with quotes or newlines goes into a shell argument. | minor |
| L3-7 (leaf) | `extension_discovery.py:1053-1055`; `_cmd_mark_step.py:719-736` | A head-dependent step whose document is unreadable when it is marked done | It can still be recorded `done` without a head (warning only). Pre-existing. | info |
| L3-8 (leaf) | `_freshness_crosscheck.py:174-177` | The row writer joins argv unquoted | The first D2 branch (executor flags told from the payload's) could be opened at the writer, `_ledger_core`, which is outside the plan's surface. This is the root of L3-3. | info |
| L3-9 (leaf) | `pre_merge_gate.py:234-277, 515` | `_read_plan_status` now returns a NamedTuple | Only the head-binding call site was checked. | info |

**Layer 3 verdict:** findings — three major (L3-1, L3-3, and L3-2 as a lead on the interaction with PLAN-LB-121), minor L3-4 to L3-6, the rest info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `bbdacaf1c` (five inline findings and two nitpicks; four fixed, one answered and accepted in-thread, both nitpicks applied, all threads resolved), refused on quota for `b6f673465` and the merged head `3312fedcc`, with the standing authorization applied; Sourcery (optional) refused on its budget. The self-review round 2 ran after the merge and left the ten items above. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `b4430a0a6` and its subject. The lane's process defect is its own: the confirming self-review round should have run before the PR.

## Residue and Watches

- Three major layer-3 findings and ten round-2 items want a fix plan; it is staged on the operator's word only. The surface is `_freshness_crosscheck.py` (check order, executor-flag handling), `_cmd_pre_commit_verify_freshness.py` and `manage-tasks/SKILL.md` (messages and tables), `pre_merge_gate.py` (the fallback message, the waiver hint, the eager probe) and `branch-cleanup.md`.
- Settle first at that plan's outline: whether moving the scope check before the canonical check changes any verdict the PLAN-LB-121 lane is relying on; whether the row writer can record the executor's own flags apart from the payload's (L3-8); and whether the probe at `pre_merge_gate.py:536` runs the scan eagerly (decides L3-5).
- **Interaction watch (the earlier watch, now answered):** PLAN-LB-120 D2's Maven build-row interaction with PLAN-LB-110 resolves to L3-1 and L3-2. PLAN-LB-121 (running) changes the Maven root canonicals; whatever it chooses for the `test` goal does not reach the push gate until L3-1 is fixed.
- The ten round-2 items are the lane's own and partly overlap the fix plan's D3-type text work; nine are documentation. They ride the fix plan.
- Owed outside this plan, operator-run: the harness sync. No executor regeneration.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (four shell file operations, one guard refusal) is its own account and is not re-read.
