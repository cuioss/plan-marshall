# Landing Analysis: PLAN-PR-066 — The charter is assembled at run time and enabled per repo

epic: review-apparatus
workstream: WS-02
pr: plan-marshall#1611 (merged `6df6595699e878af7a5c4546380dfd11730d2c44`); related plan-marshall#1601, #1605; foreign cuioss-organization#288, #290; cuioss-review-bot#66

> Landing record for one shipped plan. Written after verifying every claim in the operator's
> paste against ground truth (dispatched `execution-context-level-5` corroboration, read-only) —
> the paste is a lead, never a fact. Full corroboration transcript preserved in the decision log.

## Deliverable Fidelity vs Spec

Spec declares 13 deliverables (D0–D12). The plan's own `landing-facts` block reports
`deliverables_total=13, deliverables_done=13` — self-reported, and the archived `status.json`
carries no independent deliverable counter, so this figure is corroborated only as "what the
plan itself claims," not independently re-derived deliverable-by-deliverable.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D7/D8 — `enabled` opt-in flag semantics | shipped-as-specified | `assemble-review-charter.py` (cuioss-organization#288): `select_charter()` implements the exact four-state logic (absent block/block without key/`enabled: false`/`enabled: true`) the spec's Claim Labels named. Verified first-party in the FOREIGN repo, not assumed from the paste. |
| D9 — fleet population derived, not asserted | shipped-as-specified, but landed via a NEW mechanism not in the original declared surface | New `ci org list-repos` / `ci org search-code` / `ci repo file read` / `ci repo label list` verbs (`_github_org.py`, 516 new lines) — see "Undeclared surface expansion" below. PR body: "Population derived from `ci org list-repos` rather than asserted: 30 repositories." |
| D10/D12 — settings-repo doc rewrite | shipped-as-specified | cuioss-review-bot#66, merged, `review_decision: approved`. Body enumerates the doc/ module + README.adoc overview matching the spec. |
| D11 — rename to `cuioss-review-bot` | shipped-as-specified, split across 3 PRs | `.github/workflows/pr-agent.yml → cuioss-review-bot.yml` and the settings-repo rename landed via **plan-marshall#1605**, not #1611. `marketplace/targets/pr_agent/ → cuioss_review_bot/`, `pr-agent-packs-publish.yml → cuioss-review-bot-packs-publish.yml`, and the four prose files (`cuioss-review-bot.md`, `landing-cycle.md`, `targets/README.md`, `marketplace-build.adoc`) landed via #1611. `test/default/test_workflow_lint.py` was declared but does not appear in ANY of the three PRs' diffs — declared-but-never-realized (over-declaration, the epic's own "less dangerous" direction, but still a residual). |
| D1–D7 (foreign, org reusable workflow) | shipped-as-specified | cuioss-organization#288 (charter logic + guard/test surface) + #290 (release v0.30.0, workflow SHA `2fa5476de3435e7fc3705646c3f1f3c99be95e71`). Both merged, corroborated first-party in that checkout, not taken from the paste. |
| Pilot opt-in (this repo) | shipped-as-specified | plan-marshall#1601 (key rename `pr-agent:`→`cuioss-review-bot:`, no `enabled` key — central charter) then #1605 (`enabled: true`, `packs: [python, plugin]`). PR #1611's own log: "Assembled review charter (spine; packs: python, plugin; additional rules: 0)" — live confirmation the pilot actually fired. |

## Metrics and Anomalies

- Tokens: **8,161,027 (8.2M)**, matching `record-metrics` facts exactly.
- Duration: **21h38m54s** wall (`total_wall_seconds=77934`); plan created 2026-09-23T13:34:33Z,
  updated 2026-09-24T12:06:24Z (22h32m elapsed, consistent with worked time plus idle gaps).
- Finalize: all 22 `6-finalize` steps report `done` in the archived `status.json`.
- Anomalies, all corroborated as genuine operator overrides (not silent skips):
  1. **`pre-submission-self-review` hit its 5-round loop-back ceiling** (firing_count 8, 1 failed +
     6 loop_back). Operator closed it on a clean round 6 over the verifier's own `may_close: no`
     (objection: `github-impl.md`/`gitlab-impl.md` unchecked — those docs are selective, so the
     objection was judged non-blocking). `facts.may_close=operator_override`.
  2. **CodeRabbit round on the fix commit was not re-reviewed.** CodeRabbit raised **6** findings on
     `aba708cc9` (the paste's "3 findings" is the fixed subset, not the total): 3 fixed at
     `cf7885e84526910ff6070eb90cacf8d3338a4d84`, 1 accepted, 2 noted. `merge_authorizations`
     records a `barrier-ask-override` with the operator's ruling verbatim: "fix CodeRabbit findings
     inline, push, merge if CI green, no more review rounds."
  3. **`foreign_pr_gate` false-blocked archiving** on two independent bugs, both corroborated and
     both written up as lesson `2026-09-24-12-001`: (a) it read each foreign checkout's
     currently-checked-out branch (`main`, post-cleanup → `pushed_no_pr`) instead of the plan's own
     feature branch, which had actually landed (#288 merged); (b) it still resolved 9 unresolved
     paths under `/Users/oliver/git/pr-agent-settings`, a directory that no longer exists after the
     repo rename (`references.json` records only 8 of those paths — a 1-path discrepancy between
     the lesson and the archived reference set that this pass did not run down). Operator ruled to
     archive over the gate.

## Routing and Merge Behavior

- Review: CodeRabbit reviewed `aba708cc9` (6 findings, 3 fixed / 1 accepted / 2 noted, no
  re-review on the fix commit per the operator's ruling above); Sourcery refused on hard quota
  (optional bot, non-blocking).
- CI/merge: `plan-marshall#1611` merged directly (not through the merge queue) at
  `6df6595699e878af7a5c4546380dfd11730d2c44`, 28 files changed (+1779/−210): 1 rename
  (`pr-agent-packs-publish.yml`→`cuioss-review-bot-packs-publish.yml`), 1 new module
  (`_github_org.py`, 516 lines), 2 renamed target/test files, 1 deleted `__init__.py`, 3 new test
  files, remainder modified.
- **A real, live collision this landing created — flagged, not yet acted on**: `#1611` modified
  `workflow-integration-github/scripts/github_ops.py` (+25/−2, wiring the 4 new CI verbs) and
  `workflow-integration-github/SKILL.md` (+35 lines documenting them) — **additively**, but
  **neither file was on `#1611`'s declared Expected Surface**, and **both are declared by
  `PLAN-PR-067`**, which was emitted alongside `PLAN-PR-066` yesterday specifically because the two
  were verified disjoint (via the corpus-surfaces-membership stopgap, since `corpus cross-check`
  is still non-determinate — see `PLAN-11`). `PLAN-PR-067`'s own worktree branch base
  (`a41de18f5`) predates `#1611`'s merge and its branch has ALREADY made substantial independent
  changes to the same two files (`github_ops.py` +345/−?, `SKILL.md` +63 across its own commits).
  **This is exactly the "collision the gate did not predict" the epic's Standing Constraints
  warn about, live, on the currently-running plan.** `PLAN-PR-067` will need to rebase onto the
  new `main` and reconcile against `#1611`'s additive changes before it can merge; whether that
  reconciliation is a clean rebase or a real textual conflict was not evaluated here (out of this
  read-only pass's scope — PLAN-PR-067's own session owns its worktree).

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `plan-marshall#1611`
- [x] row `landing` stamped → `landings/PLAN-PR-066.md`
- [x] row `plan_marshall_plan_id` stamped → `charter-assembled-at-run-time`
- [x] epic.md narrative reconciled (queue annotation retired, new Open Defect + Watch recorded)
- [x] Open Defect opened: undeclared-surface collision with the running `PLAN-PR-067`
- [x] Watch opened: `API-Sheriff#351` fleet re-pin residue (see Follow-Ups — corrected from the
      paste's claim, which was already stale by the time it was verified)
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated via `orchestrator regenerate-view`
- [x] inbox messages `charter-assembled-at-run-time-001` through `-008` (7 candidate-lessons + this
      landing) drained and archived as part of this same reconciliation

## Follow-Ups

- **Undeclared collision with `PLAN-PR-067`** (`github_ops.py`, `workflow-integration-github/SKILL.md`)
  — recorded as an Open Defect naming both files and both plans; `PLAN-PR-067`'s own session needs
  to rebase and verify no textual conflict before its merge. Not retro-corrected on `PLAN-PR-066`'s
  own Expected Surface — the spec is shipped and a shipped spec's surface has no consumer, per this
  epic's own standing precedent.
- **`API-Sheriff#351` (the fleet re-pin the landing message recorded as still pending) has since
  merged** (`84e07c7ce4e5cfcd30ebbc682aab001dc3339481`) — the paste's "1 of 5 foreign PRs still
  owed" both misnamed the item (it isn't one of the 5 named PRs at all — all 5 named items are
  merged) and is now stale regardless. The landing message's OWN residue names a further
  **17 open consumer re-pin PRs from the v0.30.0 release** that this pass did not re-enumerate —
  recorded as a Watch, population unconfirmed.
- **`.github/` naming residue**: `cuioss-organization`'s `docs/automatic-review/pr-agent.md` still
  carries the old filename (modified by #288, not renamed) and plan-marshall's own
  `cuioss-review-bot.md` still links to it — judged inside the "upstream tool name" carve-out
  (arguable, not corrected), recorded as a note rather than a defect.
- Lesson `2026-09-24-12-001` (the `foreign_pr_gate` two-bug finding) is `active` in the global
  lessons corpus — owned by `plan-marshall:phase-6-finalize`, not this epic; no action here beyond
  confirming it exists and matches the landing's own description.
