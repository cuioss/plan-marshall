# Verification — 302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains

**Verified against:** commit `b3abd112`   **Landed as:** PR #1215, commit `5a5446d3` (squash)   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding list is distinguishable from a check that examined nothing.

**Read in full:** `plan.md`, `report-01.md`; the landed squash diff (`git show --stat 5a5446d3`, 22 files, +1343/-53) and the per-file diffs for `_manifest_core.py`, `test_config_defaults.py`, `inbox-envelope.md`.

**Opened at HEAD, by symbol:**

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` (whole file, 245 lines)
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (whole file, 112 lines)
- `_orchestrator_inbox.py` §§ `LANDING_REQUIRED_KEYS`, `_LANDING_FENCE_RE`, `parse_landing_facts`, `check_landing_completeness`, `cmd_inbox_landing_check`, `classify_source_id`
- `manage-execution-manifest.py` §§ `_TERMINAL_EMISSION_STEP`, `_read_plan_source_id`, `_apply_terminal_emission_orchestration_gate`, the pre-filter-7 call site (~line 2074), the compose-result projection (~line 2551), `_log_dropped_records`
- `phase-6-finalize/SKILL.md` §§ "Dispatched workflows vs inline steps", "Built-in Step Dispatch Table", Step 3 items 4b.a0 / 4b.b
- `phase-6-finalize/standards/dispatch-inline-split.md` (whole rosters), `output-template.md` §§ renderer/snapshot, `record-metrics.md` (frontmatter + § Structured facts), `branch-cleanup.md` frontmatter, `create-pr.md` frontmatter, `workflow/lessons-capture.md`, `standards/lessons-integration.md`, `standards/finalize-step-preference-emitter.md`
- `extension-api/standards/ext-point-finalize-step.md` §§ "Structured step facts", "`work_performed`", "Declared obligations", "Current Implementations"
- `extension-api/standards/finalize-step-order-bands.md` § "The bands"
- `plan-orchestrator/workflow/analyze.md` § Step 4 + the `inbox_scan` output block; `plan-orchestrator/SKILL.md` § `inbox landing-check`; `standards/inbox-envelope.md`
- `manage-execution-manifest/SKILL.md` § compose output contract; `standards/decision-rules.md` § Outputs
- `manage-status/SKILL.md` § "Structured step facts"
- Tests: `test_landing_completeness.py`, `test_terminal_emission_gate.py`, `test_dispatch_roster_closure.py`, `test_finalize_orchestration_routing.py::TestDefaultPhase6StepsMatchesDiscovery`, `test_subtraction_visibility_population.py`, `test_step_records_facts_contract.py`

**Commands run:**

- `uv run python -m pytest test/plan-marshall/plan-orchestrator/test_landing_completeness.py test/plan-marshall/manage-execution-manifest/test_terminal_emission_gate.py test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py -o addopts="" -q` → **82 passed**
- `uv run python -m pytest test/plan-marshall/phase-6-finalize -o addopts="" -q` → **752 passed**
- `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_step_records_facts_contract.py test/plan-marshall/manage-execution-manifest/test_subtraction_visibility_population.py -o addopts="" -q` → **64 passed**
- `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps` → **26 discovered steps**, `default:emit-landing` at order 1000, `default:archive-plan` at 1100

**Functions EXECUTED on real input** (not read):

- `check_landing_completeness` on a landing carrying `schema=landing-facts/1` and any single other required key degraded to `n/a` (tried `total_tokens`, and `steps`+`deliverables_total`) → returned `(True, [])`. **Correction (adversarial review):** an earlier draft of this line said the same of a landing whose *eight* values are all `n/a`; re-executed, that input returns `(False, ['schema'])`, because the schema branch fail-closes first. See G1.
- `check_landing_completeness` on an indented fence → `(False, [all 8 keys])` (fail-closed); on the pre-fix prose-only landing → `(False, [all 8 keys])` (re-executed during adversarial review — the D5 guard bites without needing a mutation).
- `classify_source_id('')` → `SourceIdClassification(orchestrated=False, …, detection='not_orchestrator_pointer')`.
- The `.plan/marshal.json` registry `plan.phase-6-finalize.steps` → **25 keys, `emit-landing` absent** (vs 26 discovered).

**Mutation check (highest-risk guard, D5).** Snapshotted `_orchestrator_inbox.py` to the scratchpad after `git diff --quiet` returned 0 (file unmodified by any concurrent agent), then rewrote the no-block branch of `check_landing_completeness` from `return False, list(LANDING_REQUIRED_KEYS)` to `return True, []` — the exact vacuous-guard shape the plan exists to prevent. `test_landing_completeness.py` went **RED**: `TestSeenToFailOnPreFixLanding::test_pre_fix_prose_landing_is_reported_incomplete` and `TestLandingCheckCli::test_prose_landing_reports_incomplete_end_to_end` both failed (2 failed, 11 passed). Restored from the saved bytes; `git diff --quiet` returned 0 again. **The D5 guard is non-vacuous for the prose-only case.**

No file in the repository was modified except the two written by this verification.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: re-derive the seam, confirm 300's slot | all four facts read by symbol and recorded | yes | yes | yes | yes | `finalize-step-order-bands.md:41-42` (Terminal emission 1000–1099; Terminus 1100); `ext-point-finalize-step.md:86-87` (∃/∀ guards); `output-template.md:5,88,129` (renders from `display_detail`); `_orchestrator_inbox.classify_source_id` is a pure classifier — executed, returns `not_orchestrator_pointer` for `''` |
| D1 | Dedicated terminal step in 300's slot | emission is the last thing before the archive step | yes | yes | yes | **partial** | `standards/emit-landing.md:7` `order: 1000`; `archive-plan.md:7` `order: 1100`; `list-finalize-steps` shows nothing between; `lessons-capture.md:84` emits no landing; SKILL.md:178 dispatch row. **But** `dispatch-inline-split.md` carries no classification row (G5) and `.plan/marshal.json` never registered the step (G7) |
| D2 | Step exists ONLY under an orchestrator | non-orchestrated compose drops it as an observable compose-time decision | yes | yes | yes | **partial** | `manage-execution-manifest.py:932-993` `_apply_terminal_emission_orchestration_gate`; call site line 2079; result field line 2551; `test_terminal_emission_gate.py` (**5** tests — 3 at function level, 2 through `cmd_compose`, incl. the positive control; count re-derived with `pytest --collect-only`) passes. **But** `terminal_emission_dropped` is absent from both compose output contracts (G6) |
| D3 | Derive the report↔inbox delta, both directions, classified | set difference derived, every item classified | yes | yes | **partial** | **partial** | `landing-payload-spec.md:39-50` (delta + reverse direction), `:58-66` (seven-finding control, #4 and #7 NARRATIVE-ONLY), `:28-32` (empirical sample stated unreachable). **But** the delta's MECHANISABLE rows are not covered by the required-key set the same doc defines (G2), and two keys' Source column names facts that do not exist (G3) |
| D4 | Terminal emission carries the facts, machine-readable | emission carries typed facts, not prose | yes | **partial** | **partial** | **no** | `emit-landing.md:176-189` (fenced `landing-facts`); `record-metrics.md:15-18` + `:139-141` (three `--fact` flags wired, `records_facts` declared); `test_step_records_facts_contract.py` green. **But** `pr`/`merge_state` have no typed producer (G3), per-step typed facts are OPTIONAL (G2), and the step declares no `work_performed` despite a no-work `done` branch (G4) |
| D5 | Drain-completeness check, seen to FAIL on a known-incomplete input; state whether the paste is retired | check exists, fails on pre-fix input, report states retirement | yes | yes | **partial** | **partial** | `_orchestrator_inbox.py:859-889` + `cmd_inbox_landing_check:1752`; `orchestrator.py:2719-2732`; `analyze.md:96-110,206,225`; `test_landing_completeness.py::TestSeenToFailOnPreFixLanding` passes and goes RED under mutation. **But** a landing with any single non-`schema` required key degraded to `n/a` reports `complete: true` (G1), so "complete" does not mean what `analyze.md:106` says it means |

### D1 — not a clean pass

The step itself is correct: `standards/emit-landing.md` declares `order: 1000`, `mutates_source: false`, `post_run_review: true`, `default_on: true`, `implements: …ext-point-finalize-step`, and discovery places it between `finalize-step-print-phase-breakdown` (999) and `archive-plan` (1100) with nothing in between. `lessons-capture` was not relocated — it stays at 991 and keeps its candidate-lesson stream; only the landing left it, and the now-purposeless zero-signal orchestration carve-out is gone from `lessons-capture.md:35,84,247`, `SKILL.md:766,848`, and the pinned description in `test_config_defaults.py`.

Two wiring sites are incomplete. `phase-6-finalize/standards/dispatch-inline-split.md` declares itself "the single source of truth for which of the default + project finalize steps dispatch … and which run inline" and carries a Closure invariant ("never both and never neither") — and it has no row for `default:emit-landing` in either roster. `SKILL.md:178` calls it inline in a parenthetical; the authority does not say so at all. The guard that should have caught this, `test_dispatch_roster_closure.py::test_every_registered_step_is_classified_exactly_once`, derives its population from `.plan/marshal.json` → `plan.phase-6-finalize.steps` (`_registered_steps`, line 213-217), which carries 25 keys and does not include `emit-landing` — so the omission is invisible to it. See G5, G7.

### D2 — not a clean pass

The gate is correct and its test is not vacuous (it carries the positive control: an orchestrated `request.md` KEEPS the step, both at function level and through `cmd_compose`). Failure modes all fail toward exclusion — missing/unreadable `request.md`, `source_id: none`, an unrecognised pointer, and even an `ImportError` on the detector all drop the step with a named reason. The drop's *reason* rides the `[STATUS]` decision-log line (`_log_dropped_records` → `format_dropped_record`), while the compose result carries only the step id — the same split every other narrowing site uses, so this is convention, not a defect.

What is missing is the documentation of the new observable: `terminal_emission_dropped` appears in neither `manage-execution-manifest/SKILL.md`'s compose-result TOON example (lines 130-163) nor `standards/decision-rules.md` § Outputs (lines 71-82), whose bullet list enumerates every other narrowing site's field. See G6.

### D3 — not a clean pass

The delta is derived in both directions and the seven-finding control is present and classified; `TestPayloadSpecDoc` pins the classification of #4 and #7 as NARRATIVE-ONLY. The defect is internal coherence. The delta table (`landing-payload-spec.md:43`) routes "Per-step outcome + `display_detail` … in composed order" as "`steps` (per-step `{step,outcome}` + typed `facts`)", and line 45 routes "Repository end-state" as "folds into `steps` (`branch-cleanup` facts)". The required-key table then defines `steps` (line 88) as "Comma-joined `{step}:{outcome}`" — no `display_detail`, no facts — and relegates per-step typed facts and `total_wall_seconds` to the OPTIONAL list (line 90-91), explicitly stating "their absence is not incompleteness". Three MECHANISABLE delta rows are therefore not guaranteed by any required key. See G2.

### D4 — not a clean pass

The routing half that landed is real: `record-metrics` now declares `records_facts: [total_tokens, total_wall_seconds, any_phase_missing_end_time]` and wires all three at its single `--outcome done` call site, satisfying the ∃/∀ contract (`test_step_records_facts_contract.py` green).

The rest is not routing. Of the eight required keys, `pr` and `merge_state` have **no typed producer at all**: `create-pr.md` declares no `records_facts` (frontmatter lines 1-15), and `branch-cleanup.md` declares `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` — no `merge_state`. `emit-landing.md:158-162` accordingly instructs deriving both from the step records' "`facts` / `outcome` / `display_detail`", i.e. from prose. The payload spec's Source column (lines 83-84) nonetheless names "`create-pr` / CI" and "`branch-cleanup` facts". See G3.

Separately, `emit-landing.md`'s frontmatter declares no `records_facts`, while its Error Handling table (line 236) has an `--outcome done` branch reachable when `orchestrator inbox write` FAILED — precisely the conditional trigger in `ext-point-finalize-step.md` ("A step MUST declare `work_performed` when at least one of its `--outcome done` branches is reachable without the step having performed its characteristic work"). The conformance suite only checks the converse direction (every step *declaring* `work_performed` carries it on every done branch), so nothing catches it. See G4.

### D5 — not a clean pass

The check exists, is CLI-reachable, is wired into `analyze.md`'s drain with an Open-Defect disposition and a `landings_incomplete` counter, and is genuinely seen to fail on the pre-fix prose-only control (confirmed by mutation). The gap is the sanctioned degraded path: `emit-landing.md:176` and the Error Handling table both instruct writing `n/a` for any field that could not be read, and `check_landing_completeness` tests only `if not facts.get(key)` — so `n/a` counts as present for every key except `schema`, which the preceding schema branch fail-closes. Executed: a landing carrying a valid `schema` and `total_tokens=n/a` returns `(True, [])`; so does one with `steps=n/a` and `deliverables_total=n/a`. `analyze.md:106` then draws the conclusion "the landing transmitted its whole mechanisable delta … a subsequent operator paste yields nothing new from that plan" over a landing that transmitted nothing. See G1.

## Report accuracy

Re-derived every figure and named symbol in `report-01.md` at HEAD. Findings:

**Contradicted.**

1. **Residue bullet 2** — *"A meta-project marshal.json re-seed is owed … `.plan/marshal.json` is under the `.plan/` tree the cloud lane does not touch … This is a local-developer re-seed concern (kin to the deferred `/sync-plugin-cache`), not a code debt."* `.plan/marshal.json` is **git-tracked**: `.gitignore` line 45 ignores `.plan/*` and line 46 negates it (`!.plan/marshal.json`); `git ls-files .plan/` lists it; `git log --oneline -- .plan/marshal.json` shows **36 commits touching it, 17 of them `chore(steward)`** (an earlier draft of this line said "five" — corrected during adversarial review; the count does not change the conclusion). It is present in a fresh clone and in CI. It is not a machine-local artifact, and the consequence is not cosmetic: the registry carries 25 steps without `emit-landing`, so (a) this repository's own orchestrated plans still emit no landing, and (b) `test_dispatch_roster_closure.py` — which reads exactly that file as its population — cannot see the step, which is why the missing `dispatch-inline-split.md` row passed CI. See G5, G7.

2. **D5, "the mechanisable delta is now drained as facts, so a paste stops yielding the mechanisable findings."** Not established. Of the six MECHANISABLE rows the plan's own delta table derives, three (per-step typed facts, repository end-state, wall-clock) are carried only by OPTIONAL keys the completeness check does not require, and two required keys (`pr`, `merge_state`) are re-derived from `display_detail` prose rather than from the facts map. See G2, G3.

3. **D4, "consuming the existing typed facts map … rather than prose — a ROUTING fix."** True for `total_tokens` / `total_wall_seconds` / `any_phase_missing_end_time` only. `pr` and `merge_state` are parsed out of prose because no step records them as facts. See G3.

**Not resolvable.** Every deliverable section cites `Commit 249a2d7` (and D5 adds "plus the gate-reshape follow-up commit"). `git cat-file -t 249a2d7` → *"Not a valid object name"*. The PR was squash-merged as `5a5446d3` and the branch is gone, so the pre-squash shas are unreachable from this clone. This is normal for a squash merge, not a contradiction — recorded so a later reader does not chase them.

**Confirmed accurate** (re-derived, not assumed):

- D0.1 — band 1000–1099 declared, `archive-plan` at 1100, last reporting step `finalize-step-print-phase-breakdown` at 999 / `record-metrics` at 998. All four read at HEAD.
- D0.2 — the ∃-direction ("No orphan declaration") and ∀-direction ("No undeclared record") guards exist verbatim in `ext-point-finalize-step.md`, and the conformance test asserts "these two and no third scope".
- D0.3 — `output-template.md` renders from `display_detail`; the snapshot reads `{step_name: {outcome, display_detail}}` and discards `facts`.
- D0.4 — `classify_source_id` is a pure classifier over `request.md`'s persisted `source_id`; `_read_plan_source_id` reads that same field via `parse_document_sections`; no second detector and no new persisted field exist (grep across the tree finds exactly one classifier).
- D1 — "ext-point Current Implementations table (25→26)": counted 26 rows at HEAD; `list-finalize-steps` returns `count: 26`.
- D1 — "the item-4b.a0 orchestration-verdict consumer list (three→four steps)": `SKILL.md:770` says "currently **four** steps" and names all four; `lessons-integration.md:50` keeps the lesson write-site set at three and reconciles the fourth explicitly.
- D2 — "not added to the `DEFAULT_PHASE_6_STEPS` CSV fallback": confirmed, with the reason documented in the tuple comment; `TestDefaultPhase6StepsMatchesDiscovery` asserts containment (not equality), so the omission is legitimate rather than a drift the test tolerates by accident.
- D2 — "registered in `test_subtraction_visibility_population.py`": `_run_terminal_emission_gate` present at line 303-309 and reached by the derived-population sweep; 64 tests pass.
- Findings list — all five sub-agent findings are resolved in today's tree: `test_config_defaults.py` carries the new pinned string; `SKILL.md` item 4b, `lessons-capture.md` Branch C, and the `test_finalize_orchestration_routing.py` comment all describe the removed carve-out as removed; `SKILL.md:770` says "four", not "All three consumers".

## Out-of-scope compliance

Clean. The landed diff (22 files) stays inside the declared Expected surface. Specifically:

- **The ordering space (plan 300's territory)** was not touched: `finalize-step-order-bands.md` is not in the diff, no step other than the new one gained or changed an `order`, `archive-plan.md` is untouched, and no consumer-repository declaration was renumbered.
- **The totals' sampling point** was not changed — `record-metrics` gained three `--fact` flags over values it already computed; no sampling logic moved.
- **The retrospective's unconditional session rebind (Problem C)** was not touched: `plan-retrospective` appears nowhere in the diff, so the plan's "record it if a change here touches it" obligation did not fire, exactly as the report states.
- Two files outside the literal Expected-surface list were edited — `phase-6-finalize/standards/lessons-integration.md` and `standards/finalize-step-preference-emitter.md` — both only to retract their now-false "this branch emits no landing / the write-site set is N" statements. That is the emission move's necessary consequence, not undeclared collateral.

## Residue carried forward

| report-01.md residue item | Status in today's tree |
|---|---|
| No end-to-end integration test executes `emit-landing`'s inline body through the discovery seed | **Partly closed, and the original framing was wrong.** `test_landing_completeness.py::TestLandingCheckCli` already drives a spec-shaped payload through the real `orchestrator inbox write --kind landing` and `landing-check` subprocesses in both the complete and the prose-only direction. What genuinely cannot be tested is the LLM-executed body itself. The residual, actionable half — nothing binds the constant to the two prose restatements of the required-key set — is what G8 now names; see gaps.md § Refuted. |
| A meta-project `marshal.json` re-seed is owed | **Still open, and mis-characterised.** The registry has 25 keys (re-derived by parsing `.plan/marshal.json` at HEAD), `emit-landing` absent. The file is git-tracked, not machine-local — see Report accuracy 1. Raised as G7. |
| Problem C (retrospective's unconditional session rebind) | **Still open by design** — out of scope for this plan, untouched by the diff. Not raised as a gap here. |
| Plan/CI note: the plan text says "archive path at 1000"; 300 moved `archive-plan` to 1100 | **Accurate and settled.** The band doc and `archive-plan.md` both say 1100; the emission took 1000. The plan file is a frozen input and correctly was not amended. |

## What could NOT be verified

- **The full-suite figures** "19526 passed, 14 skipped" and the quality-gate counts ("mypy 396 files clean"). Not re-run — a full `./pw verify` is out of proportion to this check. The targeted subsets that cover the plan's own surface were run and are green (898 tests across four modules/dirs).
- **Everything about PR #1215 itself**: CI green on head `9045558`, `mergeable_state: clean`, the three reviewers' verdicts, the "coverage 1 of 3" disclosure, and the rate-limit bodies quoted in § Reviewer participation. No PR surface was consulted.
- **Commit `249a2d7`** and the "gate-reshape follow-up commit" — unreachable from this clone (squash merge, branch deleted).
- **The runtime behaviour of `emit-landing`**. Its body is LLM-executed markdown with no executable entry point, so "the emission carries typed facts" is verified as a *specification* (the doc, the spec, and the validator agree on the fenced-block shape) and never as an *execution*. The claims about `n/a` degradation (G1) were verified against the validator by execution, not against a real emission.
- **The seven report-only findings and the cross-repository corroboration.** The archived plans, run reports, and drained messages live under `.plan/` (git-ignored beyond `marshal.json` and `project-architecture/`) and outside this repository. The plan itself labels both HYPOTHESIS and unreachable; the payload spec repeats that the empirical sample was not taken. Nothing here confirms or refutes them.
- **Whether the operator paste actually stops yielding new material** — the plan names the operator as the oracle for D5, and that oracle is not consultable from the tree.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every gap G1–G8 and every deliverable row, plus every re-derivable figure in this document.

*Files opened at HEAD:* `_orchestrator_inbox.py` §§ `LANDING_FACTS_FENCE`/`LANDING_FACTS_SCHEMA`/`LANDING_REQUIRED_KEYS` (801-820), `parse_landing_facts`, `check_landing_completeness` (859-887), `cmd_inbox_landing_check` (1752); `manage-execution-manifest.py` §§ `_TERMINAL_EMISSION_STEP` (898), `_read_plan_source_id` (901), `_apply_terminal_emission_orchestration_gate` (932-993), call site 2077-2087, result projection 2551, `DEFAULT_PHASE_6_STEPS` (`_manifest_core.py:280-309`); `emit-landing.md` (whole, 244 lines); `landing-payload-spec.md` (whole, 111 lines); `dispatch-inline-split.md` (whole, both rosters); `branch-cleanup.md` frontmatter; `workflow/create-pr.md` frontmatter; `record-metrics.md` frontmatter + `:131-144`; `ext-point-finalize-step.md` §§ `records_facts` (46), ∃/∀ guards (86-87), `work_performed` (91-98), Declared obligations (107-119), Current Implementations (225-255); `finalize-step-order-bands.md` § The bands (35-42); `output-template.md` §§ 5/88/122/129/220; `phase-6-finalize/SKILL.md` 178/766/770/772/796/848/883; `lessons-capture.md` 35/84/239/247; `analyze.md` 95/96-110/206/225; `plan-orchestrator/SKILL.md` 195/313-327; `inbox-envelope.md` 84/97/151-152; `test_landing_completeness.py` (whole); `test_dispatch_roster_closure.py` `_registered_steps` (213-218) + `test_every_registered_step_is_classified_exactly_once` (475-494); `test_terminal_emission_gate.py`; `test_step_records_facts_contract.py` header + test list; `.gitignore:45-47`.

*Commands run:* `git show --stat --name-only 5a5446d3` (22 files, +1343/-53 — re-derived); `git cat-file -t 249a2d7` (still not a valid object); `git log --oneline -- .plan/marshal.json` (36 commits, 17 `chore(steward)`); `git ls-files .plan/`; `manage-config list-finalize-steps` (26 steps, `emit-landing` 1000, `archive-plan` 1100, nothing between); the three pytest subsets (82 / 752 / 64 — all re-derived exactly); `pytest --collect-only` on `test_terminal_emission_gate.py` (**5**, not 6); tree-wide `grep -rn terminal_emission_dropped marketplace/` (4 hits, all `.py`); tree-wide sweep for a second orchestration detector (`classify_source_id`, `cmd_inbox_detect`, `is_orchestrated`, `orchestrator inbox detect`) — one classifier, one verb, confirming D0.4 with a broader pattern than the original.

*Functions executed on real input* (`uv run python`, importing `_orchestrator_inbox` directly): `check_landing_completeness` on (a) the all-`n/a` block, (b) a valid-schema block with only `total_tokens=n/a`, (c) a valid-schema block with `steps=n/a`+`deliverables_total=n/a`, (d) the pre-fix prose-only body; `classify_source_id('')`. `.plan/marshal.json` parsed and its `plan.phase-6-finalize.steps` key set enumerated (25 keys, listed).

**Not re-checked.** No mutation was applied (the original document's D5 mutation was superseded by direct execution of the same branch, which is stronger evidence and touches no file). The full suite, the quality-gate figures, PR #1215's own surface, commit `249a2d7`, the seven report-only findings, the cross-repository corroboration, and the operator oracle remain unverified for the reasons already stated in § "What could NOT be verified". Deliverable D0's four sub-facts were re-derived; D3's seven-finding control table was read but its *classification* of items #1, #2, #3, #5, #6 as MECHANISABLE was not independently re-argued.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | All-`n/a` landing returns `(True, [])`; severity `high` | **re-written, severity upheld** | Executed: all-`n/a` returns `(False, ['schema'])` — the schema branch fail-closes first. But `schema=landing-facts/1` + `total_tokens=n/a` → `(True, [])`, and `steps=n/a`+`deliverables_total=n/a` → `(True, [])`. The defect is real and *easier* to reach than claimed (one failed read suffices). `Where` corrected 887→886; `schema` removed from the Fix's sentinel list as already-handled; `analyze.md:105`→`106`. |
| G2 | Required-key set does not cover the MECHANISABLE delta | **upheld** | `landing-payload-spec.md` lines 43/45 (delta "Routed as") vs 88/90-91 (required `steps` = outcomes only; per-step facts and `total_wall_seconds` OPTIONAL, "absence is not incompleteness") read verbatim. Line refs correct; `analyze.md:105`→`106`. |
| G3 | `pr`/`merge_state` have no typed producer | **upheld, mitigation added** | `create-pr.md` frontmatter (lines 1-15) carries no `records_facts` and no `--fact` appears anywhere in the file; `branch-cleanup.md:12-16` declares `action`/`upstream_commit_count`/`merge_mechanism`/`work_performed`. Line ref corrected 11-15→12-16. Severity held at `medium` — `analyze.md:95` requires both to be corroborated against git and the CI abstraction before the landing report is written, so the operational blast radius is doc-level. |
| G4 | `emit-landing` must declare `work_performed` | **upheld** | `ext-point-finalize-step.md:95` states the conditional trigger; `emit-landing.md:236` is a `--outcome done` branch reachable with the inbox write failed (Step 0's non-orchestrated guard uses `--outcome skipped`, so it is not a second instance). `test_step_records_facts_contract.py` header enumerates checks (6)/(7) as *"every step **declaring** `work_performed`…"* — no trigger-direction check exists. `ext-point-finalize-step.md` has no Declared-obligations row for `default:emit-landing`. |
| G5 | `default:emit-landing` in neither roster | **upheld** | `grep emit-landing dispatch-inline-split.md` → no match. Roster location corrected to heading 36 / rows 40-52. The document's Closure invariant is scoped to `marshal.json`'s registry, which does not yet carry the step — so the invariant is *not* violated today; G5's own text already says the violation arrives with G7, which is accurate. |
| G6 | `terminal_emission_dropped` undocumented | **upheld, broadened** | Tree-wide sweep (broader than the two cited documents): the identifier appears in **no `.md` file anywhere in `marketplace/`** — only at `manage-execution-manifest.py` 2079/2081/2085/2551. `decision-rules.md` § Outputs bullets re-located to 72-80 (lead-in 70). |
| G7 | `.plan/marshal.json` is git-tracked and lacks the step | **upheld, figure corrected** | `.gitignore:45-46` (`.plan/*` then `!.plan/marshal.json`); `git ls-files .plan/` lists it; registry parsed → 25 keys, `emit-landing` absent, while discovery returns 26. "five `chore(steward)` commits" → **17** (of 36). Added: `test_every_registered_step_is_classified_exactly_once` asserts `classified == registered` in both directions, so G5 and G7 must land in one change. |
| G8 | "No test drives the landing end to end" | **refuted and re-written** | `test_landing_completeness.py::TestLandingCheckCli::test_facts_landing_reports_complete_end_to_end` already writes a spec-shaped payload through the real `orchestrator inbox write --kind landing` subprocess and asserts `landing-check` → `complete: true`; the prose-only negative and the missing-key negative also exist. The prescribed fix was already shipped. G8 is re-scoped to the surviving clause — nothing derives the fixture's key population from `LANDING_REQUIRED_KEYS`, and nothing binds the constant to its two prose restatements. Full refutation recorded in gaps.md § Refuted. |
| G9 | — (new) | **added, `medium`** | `_orchestrator_inbox.py:808-810` claims the required-key set "is NOT re-listed in prose elsewhere — the spec doc points here". `landing-payload-spec.md:79-88` tabulates all eight; `emit-landing.md:176` enumerates all eight. It also contradicts `landing-payload-spec.md:8-10`, which declares that document the tie-breaker. A false source-of-truth claim on the constant that is supposedly the source of truth. |
| Verdict | `implemented-with-gaps` | **upheld** | Every deliverable D0–D5 is implemented and reachable; none is absent. D4 is the weakest (2 of 8 required keys re-derived from prose) but the emission, the typed block, the schema gate and the validator all exist and are exercised. No row supports `partially-implemented`. |
| Method figures | 82 / 752 / 64 passed; 26 discovered steps; 22 files +1343/-53; `249a2d7` unreachable | **upheld** | All re-run or re-derived at HEAD; every figure matches. |
| D0.4 | "grep across the tree finds exactly one classifier" | **upheld under a broader sweep** | Re-swept with four patterns instead of one (`classify_source_id`, `cmd_inbox_detect`, `is_orchestrated`, `orchestrated.*=.*source_id`): one classifier at `_orchestrator_inbox.py:752`, one CLI verb at `:1731`, one consumer at `manage-execution-manifest.py:981`. |
| D0.3 | Report renders from `display_detail`, discards `facts` | **upheld** | `output-template.md:5` ("pure assembler … each step authors its own one-line `display_detail`"), `:88`, `:122`, `:129` (snapshot is `{step_name: {outcome, display_detail}}` — `facts` absent). |

**Documents corrected.**

*gaps.md* — G1's What-is-wrong and Fix rewritten around the executed result (`schema` is already fail-closed; the reachable door is any other degraded key) and `Where` corrected 887→886; G2's `analyze.md` refs 105→106; G3 gains the drain-corroboration mitigation that holds its severity at `medium` and its `branch-cleanup.md` ref corrected to 12-16; G5's roster location corrected to 36/40-52; G6 gains the tree-wide sweep result and corrected `decision-rules.md` refs; G7's "five" corrected to 17 and gains the both-directions coupling with G5; **G8 rewritten** from a refuted premise to the surviving one; **G9 added**; a `## Refuted during adversarial review` section records the original G8 framing and the original G1 probe error in full. Open items 8 → 9.

*verification.md* — the executed-function bullet corrected (the all-`n/a` probe result was wrong); D2's test count 6 → 5; `analyze.md:105` → `106` in two places; the gate's line range 932-995 → 932-993; the `chore(steward)` count five → 17; the D5 narrative's `n/a` framing corrected; the two residue-table rows updated. The headline verdict is unchanged.

**Residual doubt — what a third reviewer should look at first.**

1. **G4's blast radius is probably understated.** `emit-landing.md:236` marks `done` when the inbox write *failed*. That failed run's landing never reaches the epic, and `analyze.md:225` counts `landings_incomplete` only over messages that *exist* — a landing that was never written is invisible to the drain-completeness check entirely. The whole D5 chain ("queue empty ⇒ nothing outstanding") may therefore have a second hole that no gap here names: an epic with zero queued landings is indistinguishable from an epic whose plans all failed to emit. Check whether `analyze.md` reconciles the set of *shipped* plans against the set of *landings seen*.
2. **`required-steps.md` § Steps does not list `emit-landing`.** `output-template.md:220` makes a missing record for a *required* step a `[FAILED]` condition. `finalize-step-print-phase-breakdown` is likewise absent, so there may be a deliberate optional-step convention — but if `emit-landing` is meant to be unconditional under an orchestrator, its absence from that list means a silently-skipped emission never reddens the report. Not raised as a gap because the convention could not be established from the tree.
3. **D3's MECHANISABLE classification of control items #2 and #6** ("producer-gap … routable AS SOON AS the producing step records those as `--fact`") was read but not re-argued. A classification that depends on a change nobody has scheduled is arguably NARRATIVE-ONLY today, which would move the delta and therefore G2's remedy.
