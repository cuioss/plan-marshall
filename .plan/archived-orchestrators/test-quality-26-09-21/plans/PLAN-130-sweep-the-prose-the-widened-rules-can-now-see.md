# PLAN-130: Sweep the Prose the Widened Rules Can Now See

epic: test-quality
workstream: WS-02

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion**, from a defect class four independent
> ground-truth checks found and no landed plan owns.

## Objective

Four reduction plans reported their **B3** docstring deliverable clean, and at HEAD three of the four are
not. The cause is not regression in their work — it is that **PLAN-090 later widened the detection rules**
(making the deliverable-id `D` prefix optional and matching a bare `#NNN` PR reference), which correctly
exposed pre-existing citations those plans had **recorded and declined to fix on the ground that the rule
could not then see them**. PLAN-090's own out-of-scope forbids it from editing `test/**`, so *"the rule
can now see it"* landed and *"it is fixed"* never did. **No plan in this epic owns re-sweeping an
already-landed reduction slice against a later rule change.** Close that gap for the prose rule, tree-wide,
in one pass.

## Deliverables

1. **D1 — Derive the live population and classify every member.** ⛔ **Gating and halting.** Run the
   doctor's `test-conventions` scope whole-tree and per-slice, and classify **every**
   `test-docstring-historical-prose` finding into exactly one of:
   * **real citation** — an incident, PR number, lesson id, plan id or deliverable id in prose; **fix it**;
   * **test data** — the identifier is the value the test asserts on, inside a string literal or a backtick
     span; **exempt, leave it**, and confirm the rule's own exemption already covers it;
   * **legitimate domain term** — e.g. `legacy` in a module testing a legacy-format migration; **leave it**;
   * **rule false positive** — the match is none of the above; **record it for WS-03**, do not work around it.

   ⚠️ **Also derive the half the rule cannot see.** **B3**'s own text forbids superseded-behaviour
   narration (`used to`, `no longer`, `previously`, `the old`), and the rule checks only five citation-id
   patterns. The epic's census command returns a much larger population — **245 hits in slice `030` alone**,
   which that plan never measured before declaring its deliverable done. Classify these the same way.
   *Done when:* every finding in both populations carries exactly one class with its evidence; the
   whole-tree and per-slice counts are recorded with their commands; and any member fitting no class has
   halted the run with the member named.

2. **D2 — Fix the real citations, and only those.** Rewrite each real-citation docstring to state the
   invariant in the present tense.
   ⛔ **The rationale stays; only the citation goes.** PLAN-040's cold read found **four of ten** rewritten
   docstrings from which a maintainer could no longer recover *why the contract matters* — **every one
   because the rewrite chased a number**. That is the failure mode of this exact deliverable, observed, and
   it is why this plan has no count target.
   ⚠️ **"Never cite" is not "never name."** A docstring often must state the exact identifier the test
   asserts on, and that is the contract rather than a citation. Write such a value in an inline literal and
   leave a citation bare — the rule exempts matches inside a backtick span or a quoted string, so the
   **formatting is what carries the distinction**.
   *Done when:* the rule's whole-tree count is reported before and after; every finding not fixed is named
   with its class from D1; and a **cold read** confirms that a maintainer can still recover the *why* from a
   sample of rewritten docstrings (dispatch a sub-agent with the rewritten docstrings and **no other
   context**, ask what each contract is for, and record the answers verbatim).

3. **D3 — Retire the fixture README that predates the standard.**
   `test/plan-marshall/phase-6-finalize/fixtures/ci-wait/README.md` carries a plan slug (twice), a lesson
   id, two TASK ids, a Q-Gate id and an `Authored 2026-05-24` line — a direct `CLAUDE.md`
   § Documentation Standards violation ("No version history", "No timestamps", "Current state only").
   PLAN-040 recorded it; nothing owns it.
   *Done when:* the file states what the fixtures are and what contract they serve, in the present tense,
   with no date, no plan slug, no lesson id and no task id.

4. **D4 — Report the measured deltas.** The rule's whole-tree count before and after; the per-slice
   breakdown; the full classification with one row per finding and its class; the census-population figures
   for the narration half; the cold-read answers verbatim; and the collected test count before and after.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: the whole-tree `test-docstring-historical-prose` count is **226** at HEAD `bf1b7ed6` —
  re-derived by RUNNING the doctor's `test-conventions` rules whole-tree (`rules_run` tally). ⛔ **Re-scoped
  FIVE times, 201 → 205 → 214 → 227 → 226**, by commits almost none of which belong to this epic. ⚠️ The
  227 → 226 step is the FIRST DECREASE this population has ever shown, and it crosses `bf1b7ed6`, a
  521-file landing of this epic's own — so the rule set is not monotonic and a falling count is not
  evidence of remediation. **Treat this number as a moving target and re-derive it in D1
  rather than executing from it**: all three of this epic's `warning`-severity rule populations moved
  in the same window, and D1 is gating precisely because they are live
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: doctor rules_run tally at bf1b7ed6 reports test-docstring-historical-prose 226, against the 214 this claim recorded and the 227 measured at 9fd095718. Re-scoped to 226, and the 227 to 226 step is the FIRST DECREASE this population has shown - recorded in the claim because it refutes monotonic growth
- OBSERVED: PLAN-050 reported this rule at **0** over its slice and
  `test/plan-marshall/audit-archived-plan-retrospectives/` **alone** now returns **26** at `bf1b7ed6`
  (re-scoped from 22), and they are ⛔ **NOT all bare `#NNN`**: 25 are `pr_reference` and **1 is
  `plan_deliverable_id`** (plan `blind`, at `test_audit_check_input_integrity_detection.py:258`), so D1's
  classification must split this directory across two patterns rather than one — read at
  `_analyze_test_conventions.py:117` (`_PR_REFERENCE_RE`) and the doctor sweep over that directory
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: the directory returns 26 at bf1b7ed6, not 22, and they are NOT all bare pr_reference citations: 25 are pr_reference and 1 is plan_deliverable_id (plan blind at test_audit_check_input_integrity_detection.py:258). Re-scoped on both count and composition
- OBSERVED: PLAN-060 reported this rule at **0** over its slice and the fourteen directories now sum to
  **14** at `bf1b7ed6` — the count is unchanged, but ⛔ **the composition claim is refuted**: 12 are
  `plan_deliverable_id` and **2 are `pr_reference`** (`platform-runtime/test_opencode_runtime.py:663` and
  `tools-file-ops/test_safe_main_canonical.py:12`), so they are NOT all bare `deliverable N` — read at `_analyze_test_conventions.py:128`
  (`_PLAN_DELIVERABLE_ID_RE`, whose `D` is now optional)
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: the fourteen directories still sum to exactly 14 at bf1b7ed6, so the COUNT holds, but the composition claim is refuted: 12 plan_deliverable_id plus 2 pr_reference (platform-runtime/test_opencode_runtime.py:663 and tools-file-ops/test_safe_main_canonical.py:12). Re-scoped on composition only
- OBSERVED: PLAN-040 disclosed **92** citations in shapes the rule could not then match and routed them to
  PLAN-090 § D4, **which widened the detection and could not fix the prose** — its out-of-scope forbids
  editing `test/**`
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: PLAN-040 archive report-01.md:86 confirms 92 prose citations remain, and PLAN-090's Expected Surface lists no test/** prose edits, consistent with widened detection that could not fix the prose
- OBSERVED — **and the plan that owned it never measured it**: PLAN-030 declared its **B3** deliverable
  "Done" against the rule's five citation patterns while the deliverable's own text also required stripping
  superseded-behaviour narration; the epic's census command returns **261** hits in that slice at
  `bf1b7ed6` (re-scoped from 245, +16)
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: re-derived by direct source inspection over PLAN-030's six slice directories at bf1b7ed6: 261 matching lines, not 245. Re-scoped
- HYPOTHESIS — **re-derive; it sizes D2**: a substantial share of the **226** findings are **test data**, not
  citations. PLAN-040's own re-derivation found that 3 of 3 `PR #\d+` hits and 1 of 1 `TASK-\d{3}` hit in
  its slice were string-literal fixture titles, correctly exempt — confirm/refute per finding during D1's
  classification (verify-at-outline). ⛔ **This is why D1 is gating**: a run that treats the count as a
  work list will edit test data and break assertions
  - verdict: unverifiable | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: the specific 3-of-3 and 1-of-1 sub-finding could not be located in PLAN-040's accessible archived report-01.md, which discusses the 92-citation residue broadly but not that classification; the claim itself defers to verify-at-outline

## Expected Surface

⛔ **This plan crosses the whole partition by construction** — the rule's findings do not respect slice
boundaries, exactly as PLAN-110's skip sites do not. It is therefore surface-incompatible with every other
`test/`-editing plan and must be sequenced, not paired.

- OBSERVED: `test/` — ⛔ **the whole tree.** The rule's 205 findings do not respect slice boundaries, so
  this plan's surface is the test tree entire, and it pairs with no other `test/`-editing plan
- OBSERVED: `test/plan-marshall/` — the bulk of the population, across all six reduction slices
- OBSERVED: `test/plan-marshall/audit-archived-plan-retrospectives/` — the largest single concentration
  (22 findings), PLAN-050's slice
- OBSERVED: `test/plan-marshall/script-shared/`, `test/plan-marshall/tools-script-executor/` — PLAN-060's
  slice, 3 and 7 findings
- OBSERVED: `test/pm-plugin-development/**`, `test/marketplace/**` — PLAN-080's slice
- OBSERVED: `test/plan-marshall/phase-6-finalize/fixtures/ci-wait/README.md` — D3
- OBSERVED: **no `marketplace/bundles/**` file.** A rule false positive is **recorded** for WS-03, never
  worked around here

## Dependencies and Sequencing

- Depends on: PLAN-090 (landed — it is what widened the rules).
- ⛔ **Must not run concurrently with PLAN-135**, which sweeps the same tree for a different rule and will
  touch overlapping files. Run **130 first**: prose edits are contained to docstrings, while PLAN-135's
  preamble migration changes what a module binds at import time, so doing prose second would re-run the
  riskier change against a moved target.
- ⛔ **Must not run concurrently with PLAN-140** (any campaign run) or **PLAN-105 § D5**, both of which move
  code between modules in slices this plan edits.
- ⛔ **Must not run concurrently with PLAN-110**, whose skip sites likewise cross every slice.
- Adjacent to: `test/conftest.py` and `test/_shared/**` — read, never edited.

## Standing-Enforcement Note

⚠️ **This plan closes the backlog; it does not stop it recurring.** Two things reopen it: a rule widening
(what happened here), and **new code landing in an already-converted slice that does not follow the norm** —
PLAN-080's "211 of 211 converted" was falsified within two days by an unrelated epic's PR. The rule already
runs at `severity: warning`, so a non-conforming new module is reported and ignored. **Whether to flip it to
`error` is a policy decision with a named owner in WS-03 and is deliberately not taken here** — but this run
should record what the count would have to reach for that flip to be safe, since it is the only run
positioned to know.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-130-sweep-the-prose-the-widened-rules-can-now-see.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
