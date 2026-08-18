# Gaps — 220-build-ledger-is-the-build-time-oracle

**Source:** verification.md (same directory)   **Open items:** 5

## G1 — Withhold `build_share` when the NUMERATOR is unavailable, not only the denominator

- **Kind:** bug
- **Severity:** high
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:4137` — `_sequence_build_minimality_plan`, the `build_share` expression
- **What is wrong:** the withholding guard tests only `wall_clock_seconds > 0`. A plan with **no
  ledger rows** has `total_build_seconds = 0` by *absence*, and the check's own document says to
  read that as "UNAVAILABLE (absent is not zero) … never 'no builds'". When such a plan has a
  present `metrics.toon`, the share is computed anyway. Executed against a fixture with metrics
  present and no ledger rows: `has_ledger False builds 0 wall 500 share 0.0`, emitted row
  `pre-ledger,…,False,0,…,500,0%,…,informational`.
- **Why it matters:** the block asserts "0% of this plan's elapsed time was spent building" for a
  plan whose build time is unmeasurable — a fabricated ratio, unflagged and stamped
  `informational`. Every plan archived before the ledger existed reads this way, so the corpus
  view of build share is systematically dragged toward zero by plans nobody measured. This is the
  precise defect class the plan was written to remove (a zero indistinguishable from an absence),
  reintroduced on the facet it added.
- **Fix:** gate the share on the numerator's availability as well —
  `build_share = total_build_seconds / wall_clock_seconds if (has_ledger and wall_clock_seconds > 0) else None`
  (compute `has_ledger` before the share; it is already derived at `audit.py:4102`). Extend
  `checks/sequence-and-build-minimality.md` § "Build time vs plan wall-clock" to state that the
  share is withheld when EITHER side is unavailable.
- **Done when:** a test staging a plan with `metrics_phases` present and `ledger_builds=None`
  asserts `row['build_share'] is None` and that the emitted row cell reads `n/a`, and it fails
  against today's code.
- **Module/topic:** `audit-archived-plan-retrospectives` — `sequence-and-build-minimality`

## G2 — Emit `status_unknown` from the per-plan `build_time` block so the ratio accounts for every build

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:189` — `summarize_build_ledger` return dict
- **What is wrong:** `status_counts` is built over `('success','error','timeout','killed','unknown')`
  at line 173 and every unrecognized status is folded into `unknown`, but the returned block omits
  it, so `pass + error + timeout + killed` can be strictly less than `build_count` with nothing
  naming the remainder. Executed against a staged three-row ledger:
  `{'total_build_seconds': 150.0, 'build_count': 3, 'suspect_count': 1, 'pass': 1, 'error': 0,
  'timeout': 0, 'killed': 1}` — one build accounted for nowhere. `unknown` is reachable in
  production: `_derive_build_status` in
  `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:430`
  returns it for exit-0-with-unreadable-payload, deliberately and "never `success`".
- **Why it matters:** the identical defect was found and fixed on the cross-plan audit surface
  during this same run (`corpus_build_status_unknown` + the
  `pass+error+timeout+killed+status_unknown == corpus_builds` identity), leaving the two surfaces
  inconsistent. A reader of the per-plan retrospective sees a status ratio that silently omits a
  build, on exactly the exit-0-unreadable path where trust matters most.
- **Fix:** add `'status_unknown': status_counts['unknown']` to the returned dict; document the
  field and the `pass + error + timeout + killed + status_unknown == build_count` identity in
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md`'s
  `build_time` block (currently lines 15–28).
- **Done when:** a test in `test/plan-marshall/plan-retrospective/test_analyze_logs.py`
  (`TestBuildTimeFromLedger`) stages a build with an unrecognized status and asserts
  `bt['pass'] + bt['error'] + bt['timeout'] + bt['killed'] + bt['status_unknown'] == bt['build_count']`.
- **Module/topic:** `plan-marshall:plan-retrospective` — `analyze-logs`

## G3 — Reconcile `audit.py`'s own docstring and section comment to the ledger re-base

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:59-72` (module docstring, the `sequence-and-build-minimality` bullet) and `audit.py:3788-3845` (the check's section comment)
- **What is wrong:** the module docstring still says the check "classifies every `pyproject_build
  run` by duration" — verbatim the pre-fix, single-build-system claim the plan re-based away from
  — never mentions the change-ledger, and lists only the seven pre-existing anti-pattern flags.
  The section comment still opens with "Operationalizes the prototype deep-dives
  `.plan/temp/sequence_analysis.py` + `.plan/temp/build_minimality.py`", prose that **this same
  commit deleted** from `checks/sequence-and-build-minimality.md`, and its flag catalogue likewise
  omits `suspect_build_duration` and `build_exceeds_wallclock`.
- **Why it matters:** these are the first two things a maintainer reads before touching the check.
  Both now state the exact blindness the plan closed, contradicting the check document, the
  `SKILL.md` Surfaces cell, and the code twenty lines below them. D4 required reconciling the
  affected documentation; the sweep stopped at the `.md` files.
- **Fix:** in the module docstring bullet, replace "classifies every `pyproject_build run` by
  duration" with the ledger-derived description (build count / duration / status / bands from
  `.plan/work/change-ledger.jsonl`, every build system and every phase) and append
  `suspect_build_duration` and `build_exceeds_wallclock` to the flag list. In the section comment,
  delete the `.plan/temp/` prototype sentence, add a one-line pointer to the "The build-time
  ORACLE" block at `audit.py:3863`, and add the two missing flags to the
  REDUNDANCY / ANTI-PATTERN FLAGS catalogue.
- **Done when:** `grep -n "pyproject_build run" audit.py` returns only `_sbm_is_build`'s own
  delta-baseline comment, and `grep -n "\.plan/temp/build_minimality" audit.py` returns nothing.
- **Module/topic:** `audit-archived-plan-retrospectives` — `scripts/audit.py`

## G4 — Publish the D1 delta figure, or record that it is not derivable

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/220-build-ledger-is-the-build-time-oracle/report-01.md` — § Deliverables, the D1 bullet
- **What is wrong:** the bullet says the blindnesses were "named … and quantified", then lists the
  three emitted field names. Naming `corpus_build_seconds`, `corpus_build_seconds_log_derived` and
  `corpus_build_seconds_delta` is the mechanism, not the number. `plan.md` D1 is explicit: *"'We
  now see more' without a number is a claim; the delta is the evidence."* No delta figure appears
  in the report or the PR body. The clone confirms none was obtainable — `.plan/` here holds no
  `work/change-ledger.jsonl` and no `local/archived-plans/` — but the report never says so.
- **Why it matters:** D1's Done-when is unmet and reads as met. A later reader (or the
  retrospective auditor consuming this corpus) takes "quantified" at face value and never runs
  the measurement, so the re-base's central claim stays unevidenced.
- **Fix:** run the audit once on a machine that has `.plan/work/change-ledger.jsonl` and a
  populated `.plan/local/archived-plans/` —
  `python3 .plan/execute-script.py … audit --check sequence-and-build-minimality` — and record
  `corpus_build_seconds`, `corpus_build_seconds_log_derived`, `corpus_build_seconds_delta` and
  `plans_without_ledger` in the report. If that corpus is still unavailable, amend the D1 bullet
  to state plainly that the delta could not be measured in this environment and what would
  measure it.
- **Done when:** report-01.md's D1 bullet carries either the four figures with the population they
  were derived over, or an explicit non-derivability statement — and no longer uses the word
  "quantified" for the field list.
- **Module/topic:** `doc/plans/truthful-signals` — plan 220 run report

## G5 — Add the `CHECK_ERA` obligation to the `cloud-plan-lane` contract

- **Kind:** omission
- **Severity:** low
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md` — Step 4 or Step 8
- **What is wrong:** this run had to (a) recognize that changing an
  `audit-archived-plan-retrospectives` check's semantics obliges a `CHECK_ERA` bump and (b) resolve
  the `PR-PENDING` sentinel by hand, because `project:finalize-step-era-stamp-fill` does not fire
  in the `doc/plans/` lane. The run raised this as a contract-change proposal and correctly
  deferred it to the operator. It is still unadopted: `grep -n "era" .claude/skills/cloud-plan-lane/SKILL.md`
  returns nothing.
- **Why it matters:** the next lane run that touches an audit check can land a stale era stamp — or
  a literal `PR-PENDING` string — on `main`, poisoning the era model every archived-plan audit
  reads its rows against.
- **Fix:** add to `cloud-plan-lane`: "if the change alters an `audit-archived-plan-retrospectives`
  check's semantics, bump its `CHECK_ERA` entry to the `PR-PENDING` sentinel while working, then
  resolve it by running `era_stamp_fill.py run --pr-number {N} --worktree-path .` manually after
  create-pr, committed and pushed before the merge gate — the finalize step that normally does
  this does not fire in this lane."
- **Done when:** `.claude/skills/cloud-plan-lane/SKILL.md` names `CHECK_ERA` and
  `era_stamp_fill.py` in its Step 4 or Step 8 obligations.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — lane contract
