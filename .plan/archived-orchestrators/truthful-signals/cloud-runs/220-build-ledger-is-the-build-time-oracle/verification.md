# Verification — 220-build-ledger-is-the-build-time-oracle

**Verified against:** commit `ac06e4fc`   **Landed as:** PR #1224, commit `8620ab0b`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full; extracted D0–D4, the Done-when conditions, the
  out-of-scope list, the Expected surface, the nine claim labels, and the Verification section.
- Located the landed commit: `git log --oneline --all --grep '#1224'` → `8620ab0b`
  (12 files, +1319/−141). Read `git show --numstat 8620ab0b` and the full diff of
  `SKILL.md`, `checks/sequence-and-build-minimality.md`, and the three `plan-retrospective`
  reference docs.
- Opened at HEAD: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
  (lines 3785–4275 the whole re-based check, 6391–6510 the emitter, 350–412 `CHECK_ERA`,
  9159–9176 the `run_checks` wiring, 8485–8560 the cross-check-synthesis consumer, 55–72 the
  module docstring), `checks/sequence-and-build-minimality.md`, `SKILL.md`,
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`
  (120–200, 1650–1700), `retro_sections.py`, `references/{plan-efficiency,log-analysis,report-structure}.md`,
  `plan-retrospective/SKILL.md:120–140` and `:185`.
- Cross-checked the producer side (the STOP CONDITION): `manage-change-ledger/scripts/_ledger_core.py`
  (`build_record`, `BUILD_STATUSES`, `resolve_ledger_path`, `read_entries`),
  `tools-file-ops/scripts/file_ops.py` (`now_utc_iso`, `get_tracked_config_dir`), and
  `tools-script-executor/templates/execute-script.py.template`
  (`_BUILD_CLASS_PREFIXES`, `_is_build_class_notation`, `_derive_build_status`).
- Re-derived counts: `len(CHECK_NAMES)` parsed by `ast.literal_eval` → **24** (matches the
  "twenty-four" stated in `SKILL.md:3` and `audit.py:3`).
- Executed code rather than reading it:
  - `summarize_build_ledger('p')` run against a staged three-row ledger
    (`success`/`unknown`/`killed`, one zero duration) →
    `{'total_build_seconds': 150.0, 'build_count': 3, 'suspect_count': 1, 'pass': 1,
    'error': 0, 'timeout': 0, 'killed': 1}`, and `summarize_build_ledger('nope')` → all-zero.
  - `_sequence_build_minimality_plan` + `emit_sequence_build_minimality_block` run against a
    plan with **metrics present and no ledger rows** → row
    `pre-ledger,,0,0,False,0,…,500,0%,…,informational`.
- Ran tests: `uv run python -m pytest test/plan-marshall/audit-archived-plan-retrospectives/
  test_audit_check_sequence_and_build_minimality_ledger_facets.py
  test/plan-marshall/plan-retrospective/test_analyze_logs.py -o addopts="" -q` → **121 passed**;
  whole audit test directory → **640 passed**.
- **Mutation-checked three guards** (file bytes saved to scratchpad first, restored by byte copy;
  final `md5sum` matches the pre-mutation `c6368ab5177c02e03698b11f97cc9980`):
  1. invariant tolerance `+ 1.0` → `+ 100000.0` ⇒ `test_build_time_exceeds_wallclock_is_flagged`
     **RED**.
  2. `killed` folded into `error` in the status tally ⇒
     `test_status_ratio_counts_all_four_with_killed_separate` and
     `test_status_ratio_visibly_separate_in_emitted_block` **RED**.
  3. `_sbm_ledger_duration` `return value if value > 0 else None` → `return value` ⇒ **no test
     failed**. This is not a vacuous test: for an exactly-zero duration the mutation is
     behaviourally equivalent (adding 0.0 to the sum and to `max()` changes neither), and the
     suspect classification that the test does assert comes from `_sbm_classify_build`. The
     guard's only distinct effect is on a *negative* duration, which no test covers.
- `git log --oneline 8620ab0b..HEAD -- <paths>` to separate later supersession from gaps: 14
  later commits touch these files; none reverted or re-based any symbol this plan added.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| STOP | Ledger carries a structured duration + mandatory plan id for every build system | checked before anything else | yes | yes | yes | yes | `_ledger_core.py:135` `build_record` (`duration_seconds: float \| None`, `plan_id: str` required, `status` over `BUILD_STATUSES` = `_ledger_core.py:81`); `execute-script.py.template:314` `_BUILD_CLASS_PREFIXES` (the four prefixes at `:315-318`, `build-pyproject/​maven/​gradle/​npm`) + `_is_build_class_notation` at `:334` |
| D0 | GATE: facet inventory + wall-clock denominator recorded | both recorded | yes | yes | yes | yes | report-01.md § D0; pre-fix citations re-derived exact at `8620ab0b^`: `_sbm_is_build` line **3461**, `_sequence_build_minimality_plan` line **3514** |
| D1 | Re-base build-duration classification onto the ledger | durations from the ledger for every build system and phase; report quantifies the delta | yes | partly | yes | **no** | `audit.py:3898` `_load_build_ledger_index`, `:3919` `_sbm_ledger_duration`, `:4101-4122` the ledger loop; delta fields `corpus_build_seconds{,_log_derived,_delta}` at `:6461-6463`. **No number was ever produced** (see below) |
| D2a | Build time vs overall wall-clock | facet computes | yes | yes | **no** | yes | `audit.py:4130-4139` `wall_clock_seconds` / `build_share`; withheld guard covers only the denominator — see G1 |
| D2b | Passing vs failing ratio, `killed` separate | computes, `killed` counted separately, invariant fires on a violating fixture | yes | partly | yes | **no** | `audit.py:4105`/`:4109-4110` status tally, `:6459` `corpus_build_killed` line + the `killed` row column at `:6492`, `:4211` invariant. Mutation 1 and 2 both went RED. **Re-severitied by adversarial review:** the per-plan ROW omits `status_unknown`, so a single plan's `pass+error+timeout+killed` need not reconcile against its `builds` — the check doc claims it is "counted per plan". See G7 |
| D3 | Total build time on the plan's own reporting surface | aggregate appears on the surface D0 named | yes | partly | yes | **no** | `analyze-logs.py:154` `summarize_build_ledger`, `:1661-1667` `build_time` in the `log_analysis` fragment; `references/plan-efficiency.md:74` `totals.total_build_seconds`; `report-structure.md:19` §7. Unknown-status builds fall out of the ratio — see G2. **Added by adversarial review:** `plan-efficiency.md` carries the suspect-zero and `killed`-separate rules but NOT the absent-is-not-zero rule, so §7 renders a bare `total_build_seconds: 0` for a plan with no ledger rows — see G6 |
| D4 | Tests (a)–(d) each red pre-fix + doc reconciliation, no stale count | all four pass, each seen red first, no stale count remains | yes | yes | yes | **no** | `test_audit_check_sequence_and_build_minimality_ledger_facets.py` (11 tests: a=`test_status_ratio_counts_all_four_with_killed_separate`, b=`test_build_time_exceeds_wallclock_is_flagged` + negative control, c=`test_non_pyproject_build_appears_in_totals`, d=`test_wallclock_denominator_derivation_is_non_empty`); `TestBuildTimeFromLedger` (6 tests). `len(CHECK_NAMES)==24` ✓, `CHECK_ERA["sequence-and-build-minimality"] == "#1224"` at `audit.py:407` with the lock-step mirror at `test_audit_check_era_model.py:82`. Stale prose remains inside `audit.py` — see G3 |

### D1 — the delta was never quantified

`plan.md` D1's Done-when is explicit: *"the report **quantifies the delta** against the old
log-derived totals … 'We now see more' without a number is a claim; the delta is the evidence."*
The code emits `corpus_build_seconds`, `corpus_build_seconds_log_derived` and
`corpus_build_seconds_delta` (`audit.py:6461-6463`), and the delta is unit-tested
(`test_ledger_delta_over_ledger_bearing_population` asserts 240 / 40 / 200 on a synthetic
corpus). But **no real delta figure exists anywhere** — not in `report-01.md`, not in the PR
body. The plan asked for the number; it got the mechanism that would produce one.

This clone confirms the number was not obtainable: `.plan/` contains only
`execute-script.py`, `local/`, `marshal.json`, `project-architecture/`, `temp/` — there is no
`.plan/work/change-ledger.jsonl` and no `.plan/local/archived-plans/`. So the constraint was
real, but `report-01.md` never says so; it asserts the delta was "quantified".

### D2a — the withholding guard covers the denominator only

`audit.py:4137-4139`:

```python
build_share = (
    total_build_seconds / wall_clock_seconds if wall_clock_seconds > 0 else None
)
```

`total_build_seconds` is 0 for a plan with **no ledger rows** — the check's own document calls
that state "UNAVAILABLE (absent is not zero) … read that as 'unmeasurable', never 'no builds'"
(`checks/sequence-and-build-minimality.md` § "Build time comes from the change-ledger"). The
guard tests only the denominator, so a pre-ledger plan whose `metrics.toon` is present divides a
*missing* numerator by a real denominator and renders a measurement. Executed:

```
has_ledger False builds 0 wall 500 share 0.0
  pre-ledger,,0,0,False,0,0,0,0,0,0,0,0,0,0,0,0,500,0%,0,0,0,0,,smt=0;…,,,informational
```

`build_share` reads `0%` — "this plan spent none of its elapsed time building" — with severity
`informational` and no flag. That is a fabricated zero of exactly the class this plan was written
to eliminate, on the one facet it added.

### D3 — the per-plan surface does not account for every build

`summarize_build_ledger` (`analyze-logs.py:173`) tracks `unknown` in `status_counts` but omits it
from the returned block (`:189-197`), so `pass + error + timeout + killed` can be strictly less
than `build_count` with nothing naming the remainder. Executed against a staged ledger:
`build_count: 3` with `pass 1, error 0, timeout 0, killed 1`. `unknown` is a reachable status —
`_derive_build_status` in the executor template returns it for exit-0-with-unreadable-payload
("**Never `success`**"). The audit side received exactly this fix during the run (the pre-PR
sub-agent's Finding 1: `corpus_build_status_unknown` + the reconciliation identity in the check
doc + `test_status_unknown_reconciles_corpus_build_count`); the retrospective side did not.

### D4 — reconciliation stopped at the check documents

`SKILL.md:166`, `checks/sequence-and-build-minimality.md` and the three `plan-retrospective`
reference docs were reconciled. `audit.py`'s own prose was not: the module docstring bullet
(`audit.py:59-70` — corrected from `59-72` during adversarial review; line 71 already opens the
`input-integrity` bullet) still describes the check as classifying "every `pyproject_build run` by
duration", never names the ledger, and lists only the seven pre-existing flags; the section
comment (`audit.py:3786-3843` — corrected from `3788-3845`; line 3845 is the unrelated
`_SBM_DISPATCH_RE` comment) still cites the `.plan/temp/sequence_analysis.py` +
`.plan/temp/build_minimality.py` prototype prose that this same commit **deleted** from the check
document, and its flag catalogue likewise omits `suspect_build_duration` and
`build_exceeds_wallclock`. A broadened sweep confirms the residue is confined to `audit.py`:
`grep -rn pyproject_build` over the whole audit skill and the whole `plan-retrospective` bundle
returns only `audit.py:62` (this defect), `audit.py:3934`/`:3937` (`_sbm_is_build`'s intentional
delta-baseline matcher), `audit.py:2567`/`:4651` (multi-build-system patterns), and two accurate
historical mentions in the check document (`:36`, `:302`).

## Report accuracy

Re-derived at the moment of stating:

- **"the stated check count stays twenty-four — verified `len(CHECK_NAMES) == 24`"** — confirmed
  by parsing the literal: 24. `SKILL.md:3` and `audit.py:3` both say "twenty-four". ✔
- **"`CHECK_ERA[...]` bumped to the `PR-PENDING` sentinel … resolved by running `era_stamp_fill.py`
  manually … so it never lands on `main` as `PR-PENDING`"** — `audit.py:407` reads `"#1224"`, and
  `test_audit_check_era_model.py:82` asserts the same. ✔
- **D0's pre-fix line citations** — `_sbm_is_build` at 3461 and
  `_sequence_build_minimality_plan(inputs)` (one positional arg) at 3514, verified against
  `8620ab0b^`. ✔
- **"`check_metrics` already flags `agent_duration_seconds > duration_seconds + 1.0` per phase"** —
  `audit.py:1757-1760` (`if wall > 0 and worked > wall + 1.0`). ✔ The new invariant copies the
  same `+1.0` shape.
- **"`parse_metrics_toon` returns `[]` when absent, and `check_metrics` reports
  `incomplete_recording: true`"** — `audit.py:1707-1715`. ✔
- **"Archived plan dirs are named `{YYYY-MM-DD}-{plan_id}` … `manage-status/_cmd_lifecycle.py:490`"** —
  the symbol is right, the line is now **492** (`archive_name = f'{date_prefix}-{args.plan_id}'`).
  Line drift from later commits, not a false claim.
- **"`parse_metrics_toon` line 877"** — now 912; it was 886 at the landed commit. Same drift class.
- **CONTRADICTED — "D1 … quantified: the block reports `corpus_build_seconds` … and their
  `corpus_build_seconds_delta`"**. Naming the fields that *would* carry a delta is not
  quantifying one. No delta figure is stated anywhere in the report or the PR body, and the run
  had no ledger and no archived corpus to derive one from. The report should have disclosed the
  impossibility instead of claiming the result.
- **Tests named**: `TestSequenceBuildMinimalityLedgerFacets` and `TestBuildTimeFromLedger` both
  exist and pass. The audit-side class has since moved from `test_audit_checks.py` into
  `test_audit_check_sequence_and_build_minimality_ledger_facets.py` (commit `88894aef`,
  "decompose the audit-checks monolith") — supersession, not a report error.
- **"the sub-agent … rejected `plan-retrospective/SKILL.md:131` with reason"** — checked: line 131
  is Step 2.5's `metrics.md` token-accumulator reconciliation. The stated rationale holds.
- **Build figures ("16457 passed", mypy "398 source files", "test-compile 588 files")** — not
  re-derivable here; a local full `./pw verify` was out of proportion for this check. Not
  contradicted, not confirmed.

## Out-of-scope compliance

Clean. The landed diff (`git show --numstat 8620ab0b`) touches 12 paths: the audit skill
(`SKILL.md`, one check doc, `audit.py`), the `plan-retrospective` bundle (three reference docs +
`analyze-logs.py`), three test files, and the plan's own directory (the `220-….md` → `220-…/plan.md`
rename plus `report-01.md`). **No producer file is touched** — no build script, no executor
template, no wrapper, no ledger writer — which is the split the plan declared. The wrapper
ceiling disagreement was recorded and not fixed, as instructed. `checks/metrics.md` was read for
the precedent and left unmodified, as D0 required. No undeclared collateral change.

## Residue carried forward

| report-01.md residue | Status in today's tree |
|---|---|
| Landing delegated (auto-merge armed, `verify / gate` in progress) | **Closed** — `8620ab0b` is on `main`. |
| Notify the sibling epic that measures our own runs | **Not verifiable from the tree** — no channel exists in-repo; nothing records the notification either way. |
| Local `/sync-plugin-cache` owed for the `plan-retrospective` bundle edit | **Not verifiable / not owed by the run** — `target/` and `~/.claude/` are outside the repo, and the lane explicitly neither performs nor owes it. |
| Contract-change proposal: add a `CHECK_ERA` / `era_stamp_fill.py` note to `cloud-plan-lane` | **Still open** — `grep -c "CHECK_ERA\|era_stamp_fill" .claude/skills/cloud-plan-lane/SKILL.md` returns **0**. Correctly deferred to the operator, and still unadopted. *(Adversarial-review correction: the original wording claimed the file "contains no occurrence of `era`". That is false — a bare `era` matches **112** lines, inside `ledgers`, `operations`, `generated`, `deliberately`. Only the narrower sweep supports the claim.)* |

## What could NOT be verified

- **The real corpus delta (D1's evidence).** This clone has no `.plan/work/change-ledger.jsonl`
  and no `.plan/local/archived-plans/`, so `corpus_build_seconds_delta` cannot be computed
  against a real corpus by anyone reading this tree. Only the synthetic-fixture delta (240 vs 40)
  is demonstrable.
- **The 411 s / `duration_seconds = 0` incident** — the plan itself labels it REPORTED-by-another-epic
  and not reproducible from this clone. Confirmed unreproducible; the suspect-zero rule that
  answers it is verified independently.
- **The run's build figures** (16457 tests, 398/588 mypy file counts) — not re-derived.
- **Whether the `plan_efficiency` LLM aspect actually writes `totals.total_build_seconds`.** That
  aspect is LLM-composed from `references/plan-efficiency.md`; the deterministic half (the
  `build_time` block in the `log_analysis` fragment, rendered verbatim in report §4 by
  `retro_sections.SECTION_SPEC`) is verified, the LLM half is instruction-only and cannot be
  verified from the tree.
- **Whether an `unknown`-status build has ever actually been written to a real ledger.** The code
  path that produces one is verified reachable (`_derive_build_status` rule 4); no real ledger is
  present to sample.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Working tree at `f816f85c`; `ac06e4fc` (this document's stated base) confirmed an
ancestor of HEAD, and `git log ac06e4fc..HEAD` over the audit skill, the `plan-retrospective`
bundle and `cloud-plan-lane` returns **no** commits, so every re-derivation below is directly
comparable to the original.

*Re-derived figures (all confirmed exact):* the landed diff `git show --numstat 8620ab0b` — **12
files, +1319/−141** (summed by hand from the numstat); `len(CHECK_NAMES)` parsed by
`ast.literal_eval` → **24**, and `ls checks/` → **24** documents; `SKILL.md:3` and `audit.py:3`
both read "twenty-four"; `CHECK_ERA["sequence-and-build-minimality"] == "#1224"` at `audit.py:407`
with the mirror at `test_audit_check_era_model.py:82`; pre-fix citations at `8620ab0b^` —
`_sbm_is_build` **3461**, `_sequence_build_minimality_plan` **3514**; `_cmd_lifecycle.py:492`
`archive_name`; `parse_metrics_toon` **912** today / **886** at the landed commit;
`audit.py:1711` `incomplete_recording` (inside the cited 1707-1715) and `audit.py:1759`
`worked > wall + 1.0` (inside the cited 1757-1760); `plan-retrospective/SKILL.md:131` is Step 2.5's
`metrics.md` reconciliation, and `:185` confirms aspect 4 is LLM-composed; test totals **121** and
**640** re-run and reproduced; `8620ab0b` confirmed an ancestor of `main`.

*Code executed (not read):* `_sequence_build_minimality_plan` + `cross_sequence_build_minimality` +
`emit_sequence_build_minimality_block` against (a) a metrics-present / no-ledger plan → `share 0.0`
and the emitted `0%` cell, and (b) a `success`/`unknown`/`killed` ledger → `builds 3` with statuses
summing to 2 and `'status_unknown'` absent from the row header;
`summarize_build_ledger('p')` and `('nope')` against a staged three-row ledger, reproducing this
document's stated dicts byte-for-byte.

*Mutation applied and restored:* `git diff --quiet -- audit.py` checked clean first; bytes copied to
scratchpad; the G1 fix (`has_ledger and wall_clock_seconds > 0`) applied; full audit suite re-run →
**640 passed**, i.e. no existing test guards the current behaviour and none conflicts with the fix.
Restored by byte copy; `md5sum` back to `c6368ab5177c02e03698b11f97cc9980` and
`git diff --quiet` clean.

*Not re-checked:* the run's build figures (16457 tests, 398/588 mypy file counts) — still not
re-derived; whether the `plan_efficiency` LLM aspect emits what its reference instructs; whether an
`unknown`-status build has ever reached a real ledger; the 411 s / `duration_seconds = 0` incident;
the qualitative reviewer-participation table in `report-01.md`; every check other than
`sequence-and-build-minimality`.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `build_share` guards only the denominator; a no-ledger plan renders `0%` | **upheld, rationale rewritten** (severity `high` stands — a shipped false signal on the facet the plan added) | Executed: `has_ledger False builds 0 wall 500 share 0.0`; emitted row `pre-ledger,…,False,0,…,500,0%,…,informational`. Code at `audit.py:4137-4139`, `has_ledger` at `:4102` — both citations exact. **Refuted clause:** "the corpus view of build share is systematically dragged toward zero" — no corpus build-share aggregate exists (`corpus` dict at `:4298-4321`, emitted block at `:6435-6470`). Clause moved to gaps.md § Refuted. |
| G2 | `summarize_build_ledger` omits `status_unknown` from its returned block | **upheld** | Executed against a staged ledger → `{… 'build_count': 3, 'pass': 1, 'error': 0, 'timeout': 0, 'killed': 1}`. `status_keys` at `analyze-logs.py:173`, `return {` at `:189`, `def` at `:154`, `log-analysis.md` `build_time` block at `15-28` — every citation exact. `unknown` reachable: `_derive_build_status` rule 4 (`execute-script.py.template:455-464`), "Never `success`". |
| G3 | `audit.py` docstring + section comment still describe the pre-fix, pyproject-only check | **upheld, line ranges corrected** | Stale prose confirmed at `audit.py:62` and `:3794`. Ranges re-derived: bullet ends **3786-3843**, docstring bullet ends **59-70** (was `59-72` / `3788-3845`). Broadened `pyproject_build` sweep over the whole audit skill and the whole retrospective bundle finds no other stale statement, so the gap is correctly scoped and `SKILL.md:166` is genuinely reconciled. |
| G4 | `report-01.md` says the D1 delta was "quantified" but states no number | **upheld, Fix made concrete** | `grep "delta\|corpus_build_seconds"` over `report-01.md` returns only field names (`:59`, `:145-146`, `:172`) — no figure. `.plan/` here holds `execute-script.py`, `local/`, `marshal.json`, `project-architecture/`, `temp/`: no `work/change-ledger.jsonl`, no `local/archived-plans/`, so the non-derivability is real. Fix now names the exact executor notation, verified at `.plan/execute-script.py:198`. |
| G5 | `cloud-plan-lane` never names the `CHECK_ERA` obligation | **upheld, evidence corrected** | `grep -c "CHECK_ERA\|era_stamp_fill"` → **0**. **Refuted clause:** `grep -n "era"` "returns nothing" — it returns **112** lines. Fix now names the script path and argument spelling, verified at `era_stamp_fill.py:155-161`. |
| G6 | *(new)* `plan-efficiency.md` omits the absent-is-not-zero rule, so §7 renders `total_build_seconds: 0` for an unmeasurable plan | **added** | `plan-efficiency.md:26-36` lists exactly two truthfulness rules (suspect-zero, `killed`-separate) and never repeats `log-analysis.md:18-21`'s `build_count: 0` = UNAVAILABLE rule; the `totals` shape at `:74` carries neither `build_count` nor `suspect_count`. §7 is the surface `report-01.md` § "D3 surface — D0 DECISION" names, and the aspect is LLM-composed (`plan-retrospective/SKILL.md:185`), so the reference doc is the whole contract. |
| G7 | *(new)* the audit check's per-plan ROW omits `status_unknown`, so a single plan's statuses need not reconcile against its `builds` | **added** | Executed: row `unknown-status,,0,0,True,3,3,0,0,0,1,0,0,1,…` — `builds 3`, statuses 2; `'status_unknown' in <row header>` → `False`. Computed at `:4257`, summed at `:4315`, emitted only as `corpus_build_status_unknown` at `:6460`. `test_status_unknown_reconciles_corpus_build_count` asserts over `corpus` only. The check doc claims the field is "counted per plan" (`:139-141`) and its column table (`:229-249`) omits it. |
| Verdict | `implemented-with-gaps` | **upheld** | No deliverable is unimplemented — every row's "Implemented?" is `yes`, including D1's mechanism and D3's surface. The unmet obligations are a missing figure (D1), a fabricated ratio (D2a), two incomplete signals (D2b/D3) and unreconciled prose (D4). `partially-implemented` would require an absent deliverable; there is none. |
| Out-of-scope compliance | "Clean … 12 paths … no producer file touched" | **upheld** | `git show --numstat 8620ab0b` re-run: 12 paths, sums `+1319/−141` exactly. No build script, executor template, wrapper or ledger writer in the diff; `checks/metrics.md` untouched. |
| Supersession sweep | "14 later commits … none reverted or re-based any symbol this plan added" | **upheld** | Re-run with a broader instrument than a path log: `git log -S` over `summarize_build_ledger`, `_sbm_ledger_duration`, `_load_build_ledger_index`, `build_share`, `build_exceeds_wallclock`, `suspect_build_duration`, `corpus_build_seconds_delta`, `status_unknown`. The only code commit touching any of them is `88894aef` (test decomposition, already disclosed); `aeab5ab5` and `7cadb986` are false matches on the unrelated `build_shared`. |
| Mutation 3 reasoning | "`return value if value > 0 else None` → `return value` kills no test, and this is not vacuous" | **upheld** | Re-derived by reading the call site: for `dur = 0.0` the mutated return feeds `build_times.append(0.0)` — sum unchanged, `max()` unchanged — and `_sbm_classify_build` receives `0.0` on both paths, so `unknown` is stamped either way. `dur = None` short-circuits at the earlier `isinstance` branch, unaffected. Only a negative duration distinguishes them, and none is tested. The explanation holds. |

**Documents corrected.** *gaps.md:* open items 5 → **7**; G1's unsupported corpus-drag rationale
deleted and replaced with the internal-inconsistency argument plus the 640-test fix verification;
G2 given the precise `_derive_build_status` rule citation; G3's two line ranges corrected and the
broadened sweep recorded; G4's Fix given the real executor notation; G5's false `grep "era"`
evidence replaced and the script path added; **G6** and **G7** added; a
`## Refuted during adversarial review` section added recording the three refuted clauses.
*verification.md:* the non-existent symbol `_BUILD_CLASS_NOTATION_PREFIXES` replaced with the real
`_BUILD_CLASS_PREFIXES` (two occurrences) and the STOP row's citation made line-exact; **D2b
re-severitied** from a clean pass to `As documented? partly / Complete? no` (G7); **D3** moved to
`As documented? partly` (G6); the D4 section's two line ranges corrected and the broadened sweep
recorded; the residue table's false "no occurrence of `era`" claim replaced. Four further emitter
citations that did not re-derive were corrected: `corpus_build_seconds{,_log_derived,_delta}`
`:6462-6464` → **`:6461-6463`** (twice), `corpus_build_killed` `:6449-6453` → **`:6459`** plus the
`killed` row cell at `:6492`, and the status tally `:4106-4108` → **`:4105`/`:4109-4110`**.

**Residual doubt — what a third reviewer should look at first.**

1. **The §7-vs-§4 split for D3.** D0 named §7 Plan Efficiency as the D3 surface, but the only
   *deterministic* rendering of `total_build_seconds` is the §4 `log_analysis` fragment; §7's copy
   depends on an LLM following `plan-efficiency.md`. That is consistent with how every other §7
   total works, so it was not filed as a gap — but if this epic wants build time to be a *guaranteed*
   figure on the plan's own report, the mechanism is instruction-only and should be re-examined.
2. **The `build_unknown` / `status_unknown` name collision.** Two distinct `unknown` axes (suspect
   *duration* band vs unrecognized *status*) share a word in the emitted block, the check document
   and the row dict. The code maps them correctly (`audit.py:4252` vs `:4257`), and the check doc
   calls them "orthogonal" at `:143-145`, but the emitted row currently shows only one of them —
   fixing G7 puts both in the same row and makes the collision reader-facing.
3. **Ledger durability across archiving.** `_load_build_ledger_index` reads one non-plan-scoped,
   git-ignored `.plan/work/change-ledger.jsonl`. Nothing in this plan's surface guarantees that file
   still carries rows for a plan archived long ago; if it is ever rotated or truncated, previously
   measurable plans silently become `plans_without_ledger`. No evidence either way was obtainable
   from this clone.
