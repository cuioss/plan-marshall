# Landing Analysis: PLAN-02 — Domain glob seeding

epic: operator-ux
workstream: WS-01-domain-resolution
pr: #1406 — https://github.com/cuioss/plan-marshall/pull/1406

> Landing record for one shipped plan. Lives at `landings/PLAN-02.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Input mode: operator paste, corroborated against the `kind: landing` inbox message
`domain-glob-seeding-001.md` (`landing-check` → `complete: true`, `missing_keys: []`), git, and
the read-side CI abstraction. Where the paste and the measured ground truth disagree, the
measurement is recorded and the claim is labelled — see § Metrics and Anomalies.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. A source of per-domain glob knowledge (extension already knows its file types) | shipped-as-specified | `script-shared/scripts/extension/extension_base.py` + `extension-api/standards/extension-contract.md`, `ext-point-domain-bundle.md` — the `provides_file_globs()` accessor is on the Axis-A contract |
| 2. `configure` seeds `file_globs` for each selected domain from that source | shipped-as-specified | `manage-config/scripts/_cmd_skill_domains.py` at the conversion seam both `configure` and `init` route through |
| 3. Preservation semantics — an operator-set `file_globs` is never clobbered | shipped-as-specified | Same file; the landing reports it as "harden operator restore", and `test_cmd_skill_domains.py` + `test_cmd_skill_domains_helpers.py` carry the cases |
| 4. `skill-domains-setup.md` and `standards/skill-domains.md` document the seeding behaviour | shipped-as-specified | Both files in the realized diff, plus `data-model.md`, `domain-residency-audit.md` and `marshal-json-reference.md` — three documentation files the spec did not name |
| 5. Tests in `test_cmd_skill_domains.py` | shipped-as-specified | Present, joined by three further test files the spec did not name |
| — (added unplanned) | added-unplanned, operator-approved | Accessor implemented in **every** registered domain extension: 9 bundles × (`extension.py` + `SKILL.md`) = 18 files. This is the landing's own deliverable 3 and has no counterpart in the staged spec's five |
| — (added unplanned) | added-unplanned, operator-approved | `build.py` — a pre-existing quality-gate defect that hard-failed for any bundle with no test directory. Verified reproducible on clean `main` BEFORE the change; fixed under explicit operator approval (commit `4e85bef`) |

⛔ The spec declared **five** deliverables; the landing reports **four**, and neither set maps
one-to-one onto the other. The plan's four are a re-cut of the same work (the spec's 2 and 3 fold
into the landing's 2, and the spec's 4 and 5 into the landing's 4), plus one genuinely new
deliverable — implementing the accessor across all nine domain extensions — that the spec's
"a source of per-domain glob knowledge" did not scope. The re-cut is not a defect; recording it is
what keeps the count honest, because "4/4 shipped" and "5 deliverables specified" are both true.

## Metrics and Anomalies

- **Tokens**: 12,008,583 (`total_tokens`, corroborated from the `landing-facts` block). This is
  **3.0× PLAN-10's 3,987,911** — the most expensive plan in the epic by a wide margin.
- **Duration**: 66,568 s wall = 18 h 29 m (`total_wall_seconds`). Started 2026-09-03T20:06:39Z,
  landed 2026-09-04T15:49:28Z.
- **Steps**: 23/23 `done`, none skipped, none failed — corroborated element-by-element from the
  `steps` fact by last-colon split (the list carries `project:` and `plan-marshall:` namespaced
  ids, so a first-colon split would have mis-attributed six of them).
- **Merge**: `merge_mechanism: merge_queue`, `merge_state: merged`, merge commit `ef4bf54b5`.
- **Anomaly — `marshalld` unreachable for the entire run.** Every build degraded to in-process.
  The daemon was `idle_and_stale` and was upgraded during the cache-sync step. No build result is
  invalidated by this, but every duration figure above includes the degraded path.
- **Anomaly — four steps re-fired with `firing_count: 2`** (`pre-push-quality-gate`,
  `pre-submission-self-review`, `automatic-review`, `finalize-step-simplify`) without a second
  `[DISPATCH]` emission. The dispatch-audit check classifies **steps, not firings**, so it
  reported no gap. Corpus lesson `2026-09-04-14-001` records the fix shape.
- ⚠ **CONTRADICTED — the "14 lessons" count is not what the store holds.** The paste and the
  message Residue both state 14 lessons (13 retrospective + 1 lessons-capture) went to the global
  store. Measured at HEAD: **12** lessons carry a `2026-09-04` id, of which **7** name
  `domain-glob-seeding` in their body (`12-001`, `14-001` … `14-005`, `14-009`); the remaining
  five (`07-001`, `07-002`, `14-006`, `14-007`, `14-008`) cannot be attributed to this plan from
  content alone, and three other plans were live in worktrees during the same window. The
  paste's own finalize table is the reason for at least part of the gap: it reports
  `lessons-capture — folded into existing, no new lesson`, i.e. that step created **zero** new
  corpus entries, so counting it as 1 of 14 double-counts a fold as a filing.
  ⛔ **What is NOT in doubt, and it is the part that matters:** whatever the true count, **none**
  of them reached this epic's inbox as `kind: candidate-lesson`, so none is drainable here. The
  count is a lead; the bypass is the fact.

## Routing and Merge Behavior

- **Review: none, and the merge barrier could not have caught it.** `review_decision: none`
  confirmed independently via `ci pr view --pr-number 1406`. All three configured reviewers
  produced nothing: `cuioss-review-bot` participated but filed no findings, `coderabbit` refused
  on quota (**awaitable**), `sourcery` refused on quota (hard, ETA ~3 days). The pre-merge barrier
  passed on `proves: participation_only`, which is what it checks — it is not defeated here, it is
  answering a different question than "was this reviewed". `review-retrospective` graded
  `indeterminate` by construction rather than papering over the absence.
  ⛔ `review_rate_window_await: false` is the single setting that would have changed coverage,
  because CodeRabbit's refusal was the awaitable kind. See the Open Defect this landing opens.
- **CI/merge**: all checks green; merged through the merge queue; `finalize-step-sync-baseline`
  rebased onto `origin/main` over 2 upstream commits. No rebase conflicts, no re-verify signals.
- **No surface collision occurred** — PLAN-02 ran alone with slot 2 of 2 deliberately unfilled, so
  there was no concurrent plan to collide with. That is the reason, not disjointness holding.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-02 --status shipped`
- [x] row `pr` stamped `#1406` — `orchestrator queue --set-row PLAN-02 --field pr`
- [x] row `landing` stamped `landings/PLAN-02.md` — `orchestrator queue --set-row PLAN-02 --field landing`
- [x] row `plan_marshall_plan_id` stamped `domain-glob-seeding` — `orchestrator queue --set-row`
- [x] inbox message `domain-glob-seeding-001.md` archived on consume
- [x] epic.md queue reconciled from status.json; START-HERE and Ordered Queue blocks regenerated
- [x] Open Defect opened — the awaitable-refusal coverage hole (`review_rate_window_await`)
- [x] Open Defect opened — orchestration context resolved late, lessons bypassed the epic inbox
- [x] Open Defect recurrence folded — `prune-local-and-remote-ref` (third instance)
- [x] Watch updated — declared-surface honesty, now with a second measured ratio
- [x] resume_anchor updated

## Follow-Ups

- **Under-declaration measured at 78%, worse than PLAN-01's 71%.** Declared 6 entries covering 8
  realized files; realized **37**. The 29 undeclared files are: the 18 domain-extension files
  (9 bundles × 2), `build.py`, `doc/user/configuration.adoc`, `script-shared/.../extension_base.py`,
  three further `extension-api/` standards, `manage-config/standards/data-model.md`,
  `manage-config/standards/domain-residency-audit.md`, and three test files.
  Folded onto the existing declared-surface-honesty Watch as its second data point rather than
  opened as a new item — the Watch predicted exactly this and asked for each landing's ratio.
- ⚠ **Three staged specs now have stale premises, and two of them were touched invisibly.**
  PLAN-02 modified `extension-api/standards/marshal-json-reference.md` (declared by **PLAN-04**
  and **PLAN-09**) and `manage-config/standards/data-model.md` (declared by **PLAN-09**) — neither
  file was in PLAN-02's own declaration, so the gate never saw the overlap. It caused no collision
  because PLAN-02 ran alone, but **PLAN-04's and PLAN-09's specs now describe files that changed
  under them.** Both must be re-grounded before emission, alongside the PLAN-03 re-grounding the
  epic already owed. Recorded in the resume anchor and in the Queue annotations.
- **PLAN-03's primary file was NOT touched.** `_cmd_domain_detect.py` is absent from the realized
  37, so PLAN-02 does not add to PLAN-03's re-grounding debt — that debt remains exactly the
  PLAN-10 rewrite the ledger already records.
- **The lessons bypass is a drain gap this epic cannot close by draining.** The 7-or-more corpus
  lessons this run produced are durable and correct but sit outside the epic's inbox. They are not
  lost; they are simply not reconcilable through `analyze`. Two of them —
  `2026-09-04-14-004` and `2026-09-04-14-005` — are `workflow-integration-git` defects that belong
  to the **finalize-machinery** epic, and `-14-005` is the **third** recorded instance of the
  `prune-local-and-remote-ref` defect this epic already carries. Routed there as decompose input.
- **Self-review is the sole detector of a false "only X and Y" claim.** The run's self-review filed
  4 contract-drift findings, three of which were already false at HEAD *before* this plan touched
  them, and `lessons-capture` established that no test, no plugin-doctor rule and no quality gate
  detects that class. Self-review only sees the change's own delta, so a pre-existing false
  coverage claim in an untouched file stays false indefinitely. This generalises well beyond this
  plan and is recorded as an Open Defect.
