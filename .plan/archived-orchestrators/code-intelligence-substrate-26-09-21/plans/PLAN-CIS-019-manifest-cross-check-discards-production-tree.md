# PLAN-CIS-019: The manifest cross-check discards this project's own production tree, then reports `findings: 0`

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-30 from the PLAN-11 landing (#1063), inbox message
> `audit-report-path-ignores-plan-dir-010`, **absorbing the standing M3 vacuous-guard defect** that
> `epic.md` previously listed as a PLAN-CIS-016 candidate.

## Objective

`check-manifest-consistency.py` carries a private hardcoded prefix list declaring `.claude/` to be
"bookkeeping", while this project's own `build_map` classifies `.claude/skills/*.py` as **production**.
Two components hold contradictory classifications of the same path class, and the one that is wrong for
this repository silently wins: on a real plan the filter discarded **10 of 11 files** and every
downstream rule then evaluated a 1-file phantom footprint — reporting `passed: 2, failed: 0,
findings: 0`. Make the component consult the declared oracle instead of its own guess, and make any
rule whose input set was reduced say so in its verdict.

## Why this is ours, and why it is not PLAN-CIS-016

Routing: it changes **how the system knows what is production** and **how a detector derives its
population** — routing test 2, squarely ours; no PR/review surface, so test 1 does not fire.

⛔ **It is deliberately NOT folded into PLAN-CIS-016** (`auditor-detector-integrity`), which `epic.md`
records as sitting **at the six-deliverable split guard with an explicit "do not add to it"**. Staging
separately is the split-guard rule working as intended, not a duplication.

## Deliverables

1. **D1 — replace the private prefix list with a `build_map` lookup.** A path whose resolved role is
   `production` or `test` is implementation; only `config`/unclassified paths are bookkeeping.
   ⭐ `.plan/` may stay hardcoded — it is genuinely runtime state and appears in no `build_map`.
2. **D2 — a rule whose input set was reduced MUST report the reduction.** Surface `files_filtered`
   in the verdict, or downgrade the rule to `indeterminate`. ⛔ `passed: 2, findings: 0` must not be
   emittable when 91 % of the supplied footprint was discarded before evaluation.
3. **D3 — fix rule M3, the vacuous guard, in the same file.** M3 compares `steps != ['module-tests']`
   against the composer's actual `['verify:module-tests']`, so the predicate can never fire. ⚠ This
   was a standing unowned Open Defect in `epic.md`; it lands here because it is the same file and the
   same class (a detector that cannot detect).
4. **D4 — GATE: derive the population of private classification lists.** Enumerate other components
   carrying their own hardcoded notion of "is this path implementation" instead of querying
   `build_map`. ⚠ **Population-derived, not the one site this spec names** — standing rule 4. Report
   the count found separately from the number of components examined.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) An 11-file footprint under `.claude/skills/`
   survives the filter intact. (b) A rule fed a reduced input set reports the reduction rather than a
   bare `pass`. (c) M3 fires on a `['verify:module-tests']` step list.

Five deliverables — under the split guard, no split rationale owed. ⚠ If D4 finds a materially larger
population, **stage the sweep separately** rather than growing this plan.

## Claim Labels

- **OBSERVED** (first-party, quoted from the source): `check-manifest-consistency.py:49` defines
  `_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')` with the comment "Paths whose changes are
  bookkeeping side-effects of phase-6-finalize, not implementation work. Filtered before evaluating
  any rule."
- **OBSERVED** (first-party, measured on the plan): running the aspect with the realized footprint
  supplied explicitly yields `files_total: 11, files_filtered: 10, files_kept: 1`. The single survivor
  is `test/plan-marshall/.../test_audit_checks.py`; the discarded set includes
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, a ~7000-line production module
  that was the entire subject of the plan.
- **OBSERVED**: the run reported `passed: 2, failed: 0, findings: 0` on a footprint it never saw, and
  `branch_cleanup_changes` emitted `pass, branch-cleanup paired with 1 changed file(s)` — a vacuous
  pass.
- **HYPOTHESIS**: `build_map` classifies `.claude/skills/*.py` as `production, compile` **as quoted** —
  confirm/refute against the live `build_map` for this project (verify-at-outline). **Load-bearing**:
  D1's entire remedy is "consult the oracle", so the oracle's actual content must be read, not
  assumed.
- **HYPOTHESIS**: M1 (`docs_only_diff`), M2 (`early_terminate_diff`) and M3 (`tests_only_diff`) are all
  skipped as a *consequence* of the filter rather than for independent reasons — confirm/refute at the
  rule-evaluation site (verify-at-outline).
- **HYPOTHESIS** (inherited, previously unowned): M3's predicate is unreachable for the reason stated —
  confirm/refute at the M3 predicate symbol (verify-at-outline).
- **Verify-first clause**: settle the `build_map` content and the M3 predicate against the
  **implementing source** before scoping. ⚠ The pending `PLAN-35` oracle-consolidation position
  ("`build_map` is THE build/no-build oracle") is a *standing position*, not a verification — do not
  treat it as confirmation that the lookup API exists in the shape D1 needs.

## Expected Surface

- OBSERVED: `check-manifest-consistency.py` — `_BOOKKEEPING_PREFIXES` (line 49), the rule-evaluation
  path, and the M3 predicate
- ⛔⛔ **OBSERVED, ADDED 2026-08-08 — THERE IS A SECOND, IDENTICAL SITE THIS SPEC DID NOT NAME:**
  `check-routing-decisions.py:65` declares **`_BOOKKEEPING_PREFIXES = ('.plan/', '.claude/')`** — the
  same constant, same literal value, in the same bundle — consumed at `:275` by the same
  `startswith`-over-the-tuple predicate as `check-manifest-consistency.py:204`. ⇒ **The population is
  at least TWO, and this spec's OBSERVED surface named ONE.**
  - ⭐ **This is the epic's own "a named list is a SAMPLE, not an enumeration" archetype, found inside a
    spec written to fix a private-classification-list defect.** D4 already anticipates it (*"derive the
    population of private classification lists"*) — ⛔ **but D1 must not be scoped to the single named
    file**, or the fix ships against half the population and the guard in D5 passes over the half it
    changed. **Both sites move to the `build_map` lookup, or the deliverable states why one does not.**
  - ⚠ **Coordination with `PLAN-CIS-025`**: that plan owns `.claude/**` attribution, and `.claude/` is
    one of the two literals here. A change to how these predicates classify `.claude/` paths is visible
    to it. **Not a duplicate — different maps in different files — but re-check at outline.**
- HYPOTHESIS: the `build_map` lookup API the component must call (verify-at-outline; locate before
  scoping)
- HYPOTHESIS: `plan-retrospective` reference docs describing the cross-check's contract
  (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⛔ **PLAN-CIS-016** (`auditor-detector-integrity`) — adjacent detector work; the M3
  defect moved here from that plan's candidate list, so **do not re-add it there**. Sequence, never
  pair, if both reach the head together.
  ⛔ **PLAN-CIS-012 / PLAN-CIS-013** — both edit `plan-retrospective`. Same bundle: do not pair.
- Adjacent to: the pending `PLAN-35` oracle-consolidation work (`build_map` as THE oracle) — this plan
  is one *consumer* adopting the oracle and does not consolidate it; that stays untouched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-019-manifest-cross-check-discards-production-tree.md"
```

## Relation to the epic

Two archetypes at once: **source-of-truth duplication** (a private list mirroring a set defined
authoritatively elsewhere) and **confident-signal-hides-a-caveat** (`findings: 0` over 9 % of the real
input). ⭐ It is also the *same* archetype the audited plan #1063 was itself fixing — a hardcoded list
mirroring a set defined elsewhere — which is why the pattern is worth fixing at the oracle rather than
at the site.

## ⭐⭐ A VACUOUS `skip` ON THE INVOCATION ITS OWN SKILL.md DOCUMENTS — folded 2026-08-09 from inbox `self-review-resweeps-full-surface-every-round-007`

**OBSERVED first-party on PR #1126.** `plan-retrospective/SKILL.md` § Aspect 13 documents the
capture pattern with a **plan-relative** `--diff-file`:

```bash
check-routing-decisions run --plan-id {plan_id} --mode live --diff-file work/footprint.txt
```

Run verbatim it produces `"mis_prune:sonar-roundtrip",skip,no_code_delta,not_evaluated,no realized footprint`.
The **identical file** passed as an absolute path produces
`"mis_prune:sonar-roundtrip",fail,no_code_delta,predicate_evaluated,sonar-roundtrip skipped as no_code_delta but the realized footprint touched production code`.

**Same file, same content, same run.** The documented form silently degrades and reports `skip`;
the undocumented form finds a real mis-prune violation.

**Root cause**: an unresolvable `--diff-file` path is treated as *absent* rather than as
*supplied-and-unreadable*. ⛔ **A could-not-look is reported with the same token as a
nothing-to-look-at**, and `skip` reads as benign in every downstream summary
(`summary.skipped`, the compiled report section, any cross-plan audit counting evaluated
predicates). That is precisely this plan's own subject, one flag over.

**Deliverable**: either resolve a plan-relative `--diff-file` against the plan directory
(matching the SKILL.md capture pattern **and** the sibling `collect-fragments --fragment-file`
flag, which DOES accept `work/...`), or **fail loudly** on a supplied-but-unresolvable path.
⛔ **Do not report `skip`.** Whichever is chosen, the SKILL.md capture pattern and the script
must agree — today they do not, and the disagreement is silent **in the direction of a clean
result**.

⚠ **The asymmetry is what makes this invisible**: a caller who successfully used the relative
form on `collect-fragments` in the same workflow has every reason to expect it on the next flag.

⭐ **This lands on the same file as the plan's existing scope.** The 2026-08-08 correction
already widened D1 beyond the single named `_BOOKKEEPING_PREFIXES` site to include
`check-routing-decisions.py:65` — **this is a third concern in that same script**, so verify at
outline whether the deliverable count still clears the split guard.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
