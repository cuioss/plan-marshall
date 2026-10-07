# Gaps — 220-build-ledger-is-the-build-time-oracle

**Source:** verification.md (same directory)   **Open items:** 7

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
- **Why it matters:** the `build_share` cell asserts "0% of this plan's elapsed time was spent
  building" for a plan whose build time is unmeasurable — a fabricated ratio, unflagged and stamped
  `informational`. Every plan archived before the ledger existed reads this way. This is the precise
  defect class the plan was written to remove (a zero indistinguishable from an absence),
  reintroduced on the facet it added, and it contradicts two other cells of the *same emitted row*
  (`has_ledger: false`) and of the same block (`plans_without_ledger_ids`), so the block is
  internally inconsistent rather than merely terse.
  *(Adversarial-review correction: an earlier draft of this gap also claimed "the corpus view of
  build share is systematically dragged toward zero". That clause is **unsupported** — the emitter
  publishes no corpus-level build-share aggregate at all; `cross_sequence_build_minimality`'s
  `corpus` dict, `audit.py:4298-4321`, carries no share key. The defect is confined to the per-plan
  row cell.)*
- **Fix:** gate the share on the numerator's availability as well —
  `build_share = total_build_seconds / wall_clock_seconds if (has_ledger and wall_clock_seconds > 0) else None`
  (compute `has_ledger` before the share; it is already derived at `audit.py:4102`). Extend
  `checks/sequence-and-build-minimality.md` § "Build time vs plan wall-clock (share + the
  invariant)" (line 146) to state that the share is withheld when EITHER side is unavailable, and
  the `build_share` row in the column table (line 242) likewise. *Verified during adversarial
  review:* this exact edit applied to `audit.py` leaves all **640** tests under
  `test/plan-marshall/audit-archived-plan-retrospectives/` green, so nothing depends on the current
  behaviour — and no existing test goes red against the unfixed code, confirming the defect is
  unguarded.
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
  (rule 4, documented at `:455-464`) returns it for exit-0-with-unreadable-payload, deliberately and
  "never `success`".
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
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:59-70` (module docstring, the `sequence-and-build-minimality` bullet — the bullet ends at 70; 71 already opens `input-integrity`) and `audit.py:3786-3843` (the check's section comment — it ends at 3843; 3845 is already the unrelated `_SBM_DISPATCH_RE` comment)
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
  delete the `.plan/temp/` prototype sentence (`audit.py:3793-3795`), add a one-line pointer to the
  "The build-time ORACLE" block that already exists at `audit.py:3863-3866`, and add the two missing
  flags to the REDUNDANCY / ANTI-PATTERN FLAGS catalogue (`audit.py:3810-3843`).
  *Adversarial-review note:* the stale prose is confined to `audit.py`. A broadened sweep of the
  whole audit skill and the whole `plan-retrospective` bundle for `pyproject_build` returns only
  `audit.py:62` (the stale docstring), `audit.py:3934/3937` (`_sbm_is_build`'s intentional
  delta-baseline matcher), `audit.py:2567`/`:4651` (multi-build-system patterns), and two accurate
  historical mentions in `checks/sequence-and-build-minimality.md:36` and `:302` — so `SKILL.md:166`
  and the check document are genuinely reconciled and this gap is the sole holdout.
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
  `python3 .plan/execute-script.py default-bundle:audit-archived-plan-retrospectives:audit --check sequence-and-build-minimality`
  (notation and flag verified against `.plan/execute-script.py:198` and its registered `check`
  flag) — and record the emitted `corpus_build_seconds`, `corpus_build_seconds_log_derived`,
  `corpus_build_seconds_delta` and `plans_without_ledger` values in the report. If that corpus is
  still unavailable, amend the D1 bullet to state plainly that the delta could not be measured in
  this environment and name the command above as what would measure it.
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
  deferred it to the operator. It is still unadopted:
  `grep -c "CHECK_ERA\|era_stamp_fill" .claude/skills/cloud-plan-lane/SKILL.md` returns **0**.
  *(Adversarial-review correction: an earlier draft cited `grep -n "era" …` as "returns nothing".
  That is false — a bare `era` matches 112 lines of that file, inside words such as `ledgers`,
  `operations`, `generated` and `deliberately`. The substantive absence is of `CHECK_ERA` and
  `era_stamp_fill`, and only that narrower sweep supports the claim.)*
- **Why it matters:** the next lane run that touches an audit check can land a stale era stamp — or
  a literal `PR-PENDING` string — on `main`, poisoning the era model every archived-plan audit
  reads its rows against.
- **Fix:** add to `cloud-plan-lane`: "if the change alters an `audit-archived-plan-retrospectives`
  check's semantics, bump its `CHECK_ERA` entry (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
  the `CHECK_ERA` table) to the `PR-PENDING` sentinel while working, then resolve it by running
  `python3 .claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py run --pr-number {N} --worktree-path .`
  manually after create-pr, committed and pushed before the merge gate — the finalize step that
  normally does this does not fire in this lane." (Script path and argument spelling verified at
  `.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py:155-161`; the lock-step
  test mirror it also rewrites is `test_audit_check_era_model.py`.)
- **Done when:** `.claude/skills/cloud-plan-lane/SKILL.md` names `CHECK_ERA` and
  `era_stamp_fill.py` in its Step 4 or Step 8 obligations.
- **Module/topic:** `.claude/skills/cloud-plan-lane` — lane contract

## G6 — State the absent-is-not-zero rule in `plan-efficiency.md`, so §7 never renders a fabricated `total_build_seconds: 0`

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/plan-efficiency.md:16-36` — § "Build time is READ from the change-ledger, never re-derived here", and the `totals` TOON shape at `:74`
- **What is wrong:** the section carries exactly two truthfulness rules — suspect-zero and
  `killed`-is-separate — and omits the third one the sibling document already states. The
  `log_analysis` reference (`references/log-analysis.md:18-21`) says *"`build_count: 0` = no ledger
  rows = build time UNAVAILABLE (absent is not zero)"*, but `plan-efficiency.md` never repeats it,
  and the `totals` block it specifies carries `total_build_seconds` **without** `build_count` or
  `suspect_count`. A reader of report §7 therefore sees `total_build_seconds: 0` with no field in
  that section that distinguishes "no ledger rows, unmeasurable" from "no builds ran".
- **Why it matters:** §7 Plan Efficiency is the surface D0 explicitly named for D3
  (`report-01.md` § "D3 surface — D0 DECISION"), and the aspect is **LLM-composed**, not
  script-emitted (`plan-retrospective/SKILL.md:185` — aspect 4 is "(LLM on metrics.md + logs)"), so
  the reference document *is* the whole contract for what §7 prints. Every plan archived before the
  ledger existed renders a zero on the plan's own reporting surface — the same
  absence-rendered-as-measurement defect G1 names on the audit surface, on the other of the two
  surfaces this plan touched.
- **Fix:** add a third bullet to the "Two truthfulness rules ride with it" list in
  `references/plan-efficiency.md` (renaming it to three): **"Absent is not zero.** When the
  `build_time` block reports `build_count: 0` the plan carries no `kind=build` ledger rows and
  `total_build_seconds` is UNAVAILABLE, not zero — render it as `unavailable` and say so; never
  print `0`." Annotate the `totals` TOON line at `:74` with
  `# 'unavailable' when log_analysis.build_time.build_count == 0`.
- **Done when:** `references/plan-efficiency.md` contains the string `build_count` together with the
  absent-is-not-zero rule in its build-time section, and the `totals.total_build_seconds` line
  carries the `unavailable` rendering note.
- **Module/topic:** `plan-marshall:plan-retrospective` — `references/plan-efficiency.md`

## G7 — Emit `status_unknown` on the audit check's PER-PLAN row, not only in the corpus totals

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6471` (the `rows[N]{…}` header) and `:6473-6509` (the per-row cell loop) — `emit_sequence_build_minimality_block`
- **What is wrong:** `_sequence_build_minimality_plan` computes `build_status_unknown` per plan
  (`audit.py:4257`) and `cross_sequence_build_minimality` sums it into `corpus['status_unknown']`
  (`:4315`), which the emitter publishes as `corpus_build_status_unknown` (`:6460`). The **row** does
  not carry it: the emitted column list runs `…,build_unknown,pass,error,timeout,killed,…` with no
  `status_unknown` column, so per plan `pass + error + timeout + killed` can be strictly less than
  `builds` with nothing naming the remainder. Executed against a staged three-row ledger
  (`success` / `unknown` / `killed`): the row reads
  `unknown-status,,0,0,True,3,3,0,0,0,1,0,0,1,200,…` — `builds: 3`, statuses summing to 2 —
  and `'status_unknown' in <row header>` is `False`.
- **Why it matters:** this is the *same* defect the run's own pre-PR sub-agent found and fixed, but
  the fix landed only at corpus level. `checks/sequence-and-build-minimality.md:139-141` already
  claims the field is "counted per plan in `build_status_unknown`" and the column table at `:229-249`
  omits it entirely, so the check document over-promises what the row shows. The corpus identity
  `pass+error+timeout+killed+status_unknown == corpus_builds` holds, but a reader triaging a single
  flagged plan — the normal use of these rows — cannot reconcile that plan's own numbers, and the
  test that guards the identity (`test_status_unknown_reconciles_corpus_build_count`) asserts only
  over `corpus`, so nothing catches this.
- **Fix:** add `status_unknown` to the `rows[N]{…}` header string at `audit.py:6471` (between
  `killed` and `total_build_seconds`) and `r["build_status_unknown"]` to the matching cell list
  immediately after `r["build_killed"]` (`:6492`). Add the row to the column table in
  `checks/sequence-and-build-minimality.md` (after the
  `pass` / `error` / `timeout` / `killed` row at `:237`) and restate the identity there at row
  scope: `pass + error + timeout + killed + status_unknown == builds`.
- **Done when:** a test in
  `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_sequence_and_build_minimality_ledger_facets.py`
  stages one plan with an unrecognized build status, asserts `'status_unknown'` appears in the
  emitted `rows[…]{…}` header, and asserts
  `row['build_success'] + row['build_error'] + row['build_timeout'] + row['build_killed'] + row['build_status_unknown'] == row['builds']`
  — and that test fails against today's emitter.
- **Module/topic:** `audit-archived-plan-retrospectives` — `sequence-and-build-minimality`

## Refuted during adversarial review

No gap was refuted in full — all five original gaps (G1–G5) survived re-verification at the file,
symbol and execution level. Three **clauses inside them** were refuted and are recorded here rather
than silently dropped:

| Refuted clause | Gap | Evidence |
|---|---|---|
| "the corpus view of build share is systematically dragged toward zero by plans nobody measured" | G1 | There is no corpus-level build-share aggregate. `cross_sequence_build_minimality`'s `corpus` dict (`audit.py:4298-4321`) has no share key, and the emitted block (`audit.py:6435-6470`, reproduced by running the emitter) publishes none. The defect is confined to the per-plan `build_share` cell. Clause deleted; the gap stands on the cell alone. |
| "`grep -n \"era\" .claude/skills/cloud-plan-lane/SKILL.md` returns nothing" | G5 | `grep -c "era"` on that file returns **112** (matching `ledgers`, `operations`, `generated`, `deliberately`, …). `grep -c "CHECK_ERA\|era_stamp_fill"` returns **0**. Evidence replaced with the narrower sweep that actually supports the claim. |
| Line ranges `audit.py:59-72` (docstring bullet) and `audit.py:3788-3845` (section comment) | G3 | Re-derived: the docstring bullet ends at **70** (71 opens the `input-integrity` bullet) and the section comment ends at **3843** (3845 is the unrelated `_SBM_DISPATCH_RE` comment). Ranges corrected. |
