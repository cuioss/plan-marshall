# Landing Analysis: PLAN-CIS-049 — The architecture store, its query surfaces and the detectors over them

epic: code-intelligence-substrate
workstream: WS-07
pr: 1489 — https://github.com/cuioss/plan-marshall/pull/1489
plan id: architecture-store-query-truthfulness

## Ground Truth Corroborated Before Any Ledger Write

The operator's narrative and the plan's own landing message are both **leads**. Each headline fact was
checked first-party before this record was written and before the queue transition:

| Claim | Checked against | Verdict |
|-------|-----------------|---------|
| PR #1489 merged | `ci pr view --pr-number 1489` → `state: merged` | corroborated |
| merge commit `7a028157e` | `merge_commit_sha 7a028157eab86d5c…` == the commit's own sha | corroborated |
| landed on main | `git merge-base --is-ancestor 7a028157e origin/main` → YES; `git log origin/main` names it | corroborated |
| squash landing | head branch `feature/architecture-store-query-truthfulness`, one commit on main | corroborated |
| plan archived | archive dir `.plan/local/archived-plans/2026-09-15-architecture-store-query-truthfulness` listed | corroborated (directory exists) |
| landing payload complete | `inbox landing-check` → `complete: true`, `missing_keys[0]` | corroborated — the epic's second `complete: true` landing |

⚠ **`origin/main` has advanced past this landing**: `ab86d7cbf` (#1494) and others sit above
`7a028157e`. The three surviving staged specs must be re-grounded against current HEAD, not against
this landing's sha.

## Deliverable Fidelity vs Spec

The spec was **re-cut on 2026-09-12** from six deliverables to ten (absorbing the retired
`PLAN-CIS-058` as D7–D9 and the `truthful-signals-059` inbox fold as D10), and its section verdict was
re-stamped `contradicted / rescoped: yes` at `53ab7dd2e` in the same act. **The plan ran against that
re-cut spec**, and the PR body confirms the shape: *"Ten deliverables in total: seven owned by
`manage-architecture`, three by `plugin-doctor`."*

⚠ **Anomaly — the landing-facts block reports `deliverables_total=12` / `deliverables_done=12` while
the PR body and the spec both say TEN.** Both halves report *complete*, so nothing is outstanding on
either reading, but the two counts are not the same number and neither is derived from the other. Do
not carry either figure forward as *the* deliverable count without re-deriving it from the archived
plan's task set. ⭐ This is the epic's own subject arriving in its own landing record: a count published
without the population it was computed over.

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| D1 concept-document store persists and reports what it holds | shipped-as-specified | PR body: freshness derived from the document's own `generation` header, `unknown` when no document, all writes funnel through `save_module_enriched`, `key_packages` migration written and collision-safe |
| D2 `capabilities` cannot emit an impossible state | shipped-as-specified | `module_edges.status` computed from the full producer population, one `derivable`/`not_derivable` vocabulary across all three rows, `content_search` distinguishes never-crawled from crawled-and-empty |
| D3 every count names its population | shipped-as-specified | Axis-C multiplicity carried through the schema, `find` publishes `file_count` beside `count`, `files_scanned` counts distinct files, `unreadable[]` deduplicated per physical file |
| D4 `skills_by_profile` three-state signal | not separately evidenced in the PR summary read | re-read the PR body's remaining sections or the archived plan before treating it as shipped |
| D5 bounded sweep of architecture-core defects | not separately evidenced in the read excerpt | as above |
| D6 proposals recorded for the operator | not separately evidenced in the read excerpt | as above |
| D7–D9 (merged from `PLAN-CIS-058`) | shipped — three deliverables owned by `plugin-doctor`, per the PR body | the merge's own premise held: D7 was re-scoped to COMPLETE the already-shipped `documented_verb_set_drift` rule rather than build one |
| D10 `diff-modules` indeterminate-vs-changed | shipped-as-specified | PR title and summary name `diff-modules` among the surfaces made truthful |

⛔ **Rows D4–D6 are recorded as NOT ESTABLISHED by this analysis, not as shipped.** The PR body was read
in excerpt; three deliverables fell outside what was read. They are almost certainly shipped — the
plan reports 12/12 done — but *almost certainly* is not corroboration, and this epic does not record
inferred completion as observed completion.

## Metrics and Anomalies

- **Tokens: 5,299,565.** Wall: 209,619 s = **58 h 13 m** across the whole plan.
- ⛔ **Two different cost figures are in play and MUST NOT be conflated.** The landing-facts block
  reports `total_tokens=5299565` for the plan; `plan-retrospective` separately flagged **10.5M against
  a 2.0M anchor — 5.2× — for the finalize+execute stretch ALONE**. A stretch cannot cost twice the
  whole, so the two are measuring different populations (almost certainly dispatched-vs-billing-weighted,
  the distinction this epic's own TOKEN ROADMAP retired every per-phase figure over). **Neither figure
  is publishable without naming which it is.** Re-derive from the archived `work/metrics.toon` before
  either is quoted.
- **Four loop-back iterations in finalize**, plus the CodeRabbit rate-limit recovery cycle, are named
  by the retrospective as the cost drivers. ⭐ This is the **finalize-gate cost archetype** recurring:
  the same shape recorded on PLAN-TRUTH-089 (finalize 81 % of a 13.9M run) and PLAN-CIS-053.
- **CodeRabbit hourly-quota refusal hit twice in round 3**, recovered by two ~90-minute waits under the
  standing operator recovery protocol. ⭐ Correctly handled: no escalation and no PR reopen, because
  CodeRabbit was **actively refusing rather than silent** — the discrimination the protocol turns on.
- `surface_delta: unmeasured`, `could_not_look: declared_not_supplied_and_realized_not_supplied`. The
  footprint base itself was healthy (`origin/main`, remote-tracking, `footprint_base_stale: false`) —
  ⭐ note that is the very resolver `D7` of `PLAN-CIS-050` exists to fix, reading correctly here because
  the base was a remote-tracking ref. The delta is unmeasured because neither footprint was supplied,
  which is the known `affected_files` under-recording defect, not a new one.

## Residue Carried Forward

- **Six genuine out-of-footprint self-review findings** were carried as lessons `2026-09-14-21-001`,
  `-002`, `-003` rather than fixed in-plan: one vacuous test-presence assertion, and **five
  documentation sites restating a superseded `module_edges` / `content_search` status vocabulary**.
  ⛔ Those five are `PLAN-CIS-054`'s subject exactly — a document restating a rule the shipped code has
  superseded — and they are now *known* stale sites naming their own locations. Fold them into
  `PLAN-CIS-054` when its inbox messages are dispositioned.
- ⭐⭐ **The five-site restatement is the SELF-SEEDING archetype**, recorded on PLAN-TRUTH-089 as 27 % of
  its finalize findings: a rule stated in one authoritative place and restated in five others, so
  changing the rule creates five findings. The terminating move recorded there is **replace the
  restatement with a POINTER at its source** — not to correct five copies into five new copies.
- `PLAN-CIS-039` (parked) gains a precedent it must decide against rather than re-derive: two verbs
  already implement the section-addressed read its D2 asks for (`manage-solution-outline read --section`,
  `manage-plan-documents read --section`), neither corpus-facing. Filed by this plan's own D5 sub-item 14.

## Consequence for the Queue

The three surviving staged specs (`PLAN-CIS-052`, `PLAN-CIS-050`, `PLAN-CIS-054`) all declare surfaces
this plan has now moved. ⛔ **Re-run `corpus surfaces` and `corpus cross-check` before the next emit,
and re-ground the selected survivor** — their section verdicts were stamped at `53ab7dd2e`, which is
now two landings stale.
