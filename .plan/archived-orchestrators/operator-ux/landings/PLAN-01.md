# Landing Analysis: PLAN-01 — Over-provision the domain set instead of prompting

epic: operator-ux
workstream: WS-01-domain-resolution
pr: #1380 — https://github.com/cuioss/plan-marshall/pull/1380

> Landing record for one shipped plan. Lives at `landings/PLAN-01.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Ground truth checked before any ledger write: `ci pr view --pr-number 1380` returns
`state: merged`, `merge_commit_sha: bf012b2cd81dfcf220b1fcf4f4c3982b65af7816`;
`git merge-base --is-ancestor` confirms it is in `main`; `git show --stat` reports
**17 files, +353 / −84**.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Zero-match branch resolves to the union, `ambiguous: false`, new `reason` | shipped-as-specified | `_cmd_domain_detect.py` in `bf012b2cd` |
| 2. Bounded escape when the union would be empty | shipped-as-specified | Landing states the ambiguous escape is retained "where there is genuinely nothing to over-provision" |
| 3. `phase-1-init` Step 7 stops raising the multiSelect | **shipped-widened** | Landed as "realign the phase-1-init **and phase-2-refine** caller contracts" — a second caller the spec never named |
| 4. Tests | shipped-as-specified | `test_cmd_domain_detect.py`, plus two test files the spec did not name |
| 5. `skill-domains.md` + `manage-config/SKILL.md` contract docs | **shipped-widened** | Landed across those two plus `doc/user/configuration.adoc`, `dispatch-granularity.md`, `ext-point-outline.md`, `call-graph.md`, `outline-workflow-detail.md` |
| — (not in spec) | **added-unplanned** | "Widen `resolve-outline-skill` into an N-to-1 domain selector" — `_cmd_skill_resolution.py`, `manage-config.py`, `query-config.py`, `phase-3-outline/SKILL.md` |

**The acceptance test is met.** The epic's governing test — the operator's api-sheriff
ambiguous-domain prompt must not fire — is satisfied by deliverable 1: a zero narrative match
now resolves silently to the union of the ranked candidates. Deliverable 2 preserves the only
case where a prompt is still correct (nothing to over-provision).

## Metrics and Anomalies

- Tokens: 4,616,201. Duration: 3h35m worked / 18h25m wall (14h49m idle).
- Phase 6 alone: 2,688,431 tokens (58%) in 1h37m worked against 15h54m wall.
- **Anomaly — ledger pairing reproduced the prior plan's ratio almost exactly.** 8 of 20
  finalize rows paired, `channel_completeness.ratio 0.409` to three decimals, matching
  PLAN-05's 8-of-20. Two independent plans landing on the same ratio is evidence of a
  systematic defect rather than per-run noise. Folded onto `2026-09-02-13-002`.
- **Anomaly — 7 self-review rounds, 26 findings, and rounds 2–4 each found defects introduced
  by the previous round's fix prose.** Same class PLAN-05 hit, one layer deeper: round 6's
  delete-everywhere commit claimed the contract "lives nowhere else" on the strength of
  enumerating sites it already knew; round 7 disproved it with one
  `architecture search --content` call. Recorded as `2026-09-02-14-001`.
- **Anomaly — the pre-archive findings-check could not run.** `metadata.worktree_path` still
  named the worktree `branch-cleanup` removed three steps earlier, and the phase-entry
  assertion fires ahead of the findings verdict. The executor answered the blocking question
  directly (0 pending, both stores) and logged it. ⛔ **Any post-cleanup findings-check in the
  same run is unrunnable by construction** — an ordering defect, not a one-off. See Follow-Ups.

## Routing and Merge Behavior

- Review: merged via the queue, all checks green. Two structural gaps found by running the
  review machinery rather than auditing it — the Sourcery quota refusal matching no registered
  pattern (a declination credited as participation, propagating into four metrics), and
  `_DEF_OR_CLASS` omitting `async def` where three sibling detectors include it (six live
  sites in `marshalld.py`).
- **Executor error, caught by a leaf, and recoverable because the leaf did not silently
  self-correct.** Both retrospectives were dispatched with `orchestrated: false` without
  running the `item-4b.a0` detection; the plan is epic-bound, so four lesson dispositions
  initially routed to the global store. The retrospective noticed the disagreement with
  `request.md`, **honoured the caller's input rather than recomputing**, and filed a warning —
  which is exactly why it was recoverable. Corrected by a compensating inbox write
  (`domain-over-provision-001.md`).

### ⛔ Under-declaration: the gate's declared surface was wrong by 12 files

**Declared: 5 entries. Realized: 17 files. 12 undeclared (71%)** — squarely in the
"about two thirds" under-declaration class the standard documents as the dominant residual.

| Undeclared file | Whose declared surface it belongs to |
|---|---|
| `phase-2-refine/SKILL.md` | **PLAN-03** |
| `phase-3-outline/SKILL.md` | **PLAN-03** |
| `manage-config/scripts/_cmd_skill_resolution.py` | nobody |
| `manage-config/scripts/manage-config.py` | nobody |
| `script-shared/scripts/query/query-config.py` | nobody |
| `extension-api/standards/ext-point-outline.md` | nobody |
| `extension-api/standards/dispatch-granularity.md` | nobody |
| `ref-workflow-architecture/standards/call-graph.md` | nobody |
| `pm-plugin-development/.../outline-workflow-detail.md` | nobody |
| `doc/user/configuration.adoc` | nobody |
| `test_cmd_skill_resolution.py`, `test_manage_config_cli.py` | nobody |

**No collision actually occurred** — PLAN-03 was dependency-sequenced behind PLAN-01 for
independent reasons, so the two never ran together. That is luck, not the gate working: had
PLAN-03 been dependency-free it would have been a candidate for the second slot on the
strength of a comparison that was missing two of its files. The gate's promise is bounded by
declaration honesty, and this landing is a measured instance of the bound.

**Correction applied in the same act** (per the standard's same-act rule): PLAN-03's spec now
records that `phase-2-refine/SKILL.md` and `phase-3-outline/SKILL.md` were modified by
PLAN-01, so its outline re-verifies against the post-PLAN-01 state rather than the state it
was written against. PLAN-02's spec is annotated with the same warning for
`_cmd_skill_resolution.py` / `manage-config.py`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-01 --status shipped`
- [x] row `pr` stamped — `#1380`
- [x] row `landing` stamped — `landings/PLAN-01.md`
- [x] row `plan_marshall_plan_id` stamped — `domain-over-provision`
- [x] 5 inbox messages drained, each dispositioned and archived
- [x] Under-declaration corrected on PLAN-02 and PLAN-03 specs (same-act rule)
- [x] Open Defect opened — post-cleanup findings-check unrunnable by construction
- [x] Open Defect opened — `_DEF_OR_CLASS` omits `async def`
- [x] Watch opened — declared-surface honesty across the remaining corpus
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **`2026-09-02-14-002/3/4`** promoted to the corpus from the three native candidate-lessons.
  `001` was a routing back-fill; its two named lessons (`2026-09-02-14-001`,
  `2026-09-02-08-001`) were verified present in the corpus, so it was discarded rather than
  re-promoted.
- **Findings-check ordering defect** — recorded as an epic Open Defect. It is a
  `phase-6-finalize` step-ordering bug, not operator-UX work, so it is not staged here.
- **`_DEF_OR_CLASS` / `async def`** — recorded as an epic Open Defect and covered by lesson
  `2026-09-02-14-003`. Six live sites in `marshalld.py` currently invisible to the
  `user_facing_strings` detector, which matters to this epic because that detector is one of
  the instruments PLAN-08 will rely on.
