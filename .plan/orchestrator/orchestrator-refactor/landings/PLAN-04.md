# Landing Analysis: PLAN-04 — One vocabulary for "the name of the thing I am operating on" — the decision

epic: orchestrator-refactor
workstream: WS-03
pr: #1543

> Landing record for one shipped plan. Lives at `landings/PLAN-04.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Verified against PR #1543's merged diff (`git diff --name-only a1dd4901f 4804b6976`,
2 files), the landed ADR (`doc/adr/023-...adoc`, read from `origin/main`), and the
inbox landing message's `landing-facts` block (`deliverables_done=4/4`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — derive the identifying-parameter population from live argparse | shipped-as-specified | ADR-023 § Context: 503 flags / 111 derivable notations, method stated as `argparse_surface` over `--help`, not text search; coverage gap (`platform_runtime`, `NotDerivable`) named per ADR-019 |
| D1 — the decision, stated as a rule | **shipped-modified** — the rule is materially different from the epic's own originally-framed option set | ADR-023 § Decision: entity-noun-first with a closed suffix set (`none`/`-id`/`-number`/`-slug`). Epic → `--epic`. Plan stays `--plan-id` (not collapsed). Three of four `--name` occupants renamed to `--module`/`--component`; the fourth (`run_config commit-trailer set --name`, a co-author name) explicitly kept. See "Correction to the epic's own premise" below. |
| D2 — the standard amendment | shipped-as-specified | `argument-naming.md` diff confirmed in the merge commit; Rules 1 and 3 amended, the ~40-row canonical-forms table deliberately left untouched (reserved for PLAN-05, to avoid tripping the build-failing `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` gate on a not-yet-implemented spelling) |
| D3 — an ADR | shipped-as-specified | `doc/adr/023-Entity_identifying_CLI_parameters_use_one_typed_vocabulary.adoc`, `Status: Proposed`, present on `origin/main` at `4804b6976` |
| D4 — the execution brief | shipped-as-specified, delivery-mechanism-improvised | Transmitted to this epic's inbox as `identifier-vocabulary-decision-001.md`, filed `kind: finding` because the inbox schema has no dedicated "execution brief" kind — noted as a gap in the message itself, not a defect in the plan |

**Correction to the epic's own premise.** This epic's Vision (written at `init`) framed
aspect 3 as "rename the `slug` vocabulary to `name`". PLAN-04's actual, better-reasoned
outcome is different: `--name` was explicitly REJECTED as a form-noun spelling (it names
the value's *shape*, not the entity — the same defect `--slug` has), and the epic
identifier is instead `--epic`. This is recorded as a Decision below, not silently
absorbed, because it corrects the epic's own stated premise rather than merely
implementing it.

## Metrics and Anomalies

- Tokens: 17,375,009 total (from `landing-facts`), matching the paste's "17.4M tokens"
- Duration: 68,029s wall (≈18h54m), matching the paste's "18h53m"
- Anomalies:
  - `deliverables_done=4/4`, `cleanup_owed=false` — clean completion per the machine-readable facts.
  - Two finalize forks were harness-killed mid-run and resumed/taken over directly (per the pasted narrative); the inbox landing message independently corroborates one structural cause: a fork taken after `worktree-remove`'s boundary cannot reach the main checkout (cwd-pinned), which is now filed as candidate-lesson `identifier-vocabulary-decision-007`.
  - A `phase-1-init` gap (missing `source_id`) silently dropped `emit-landing`/orchestration routing from this plan's manifest at compose time; discharged manually at finalize per the landing message's own "Residue" section. Independently corroborated by candidate-lesson `identifier-vocabulary-decision-003`, which shows the measurable consequence: this epic's `queue_without_landing_count` was `7` (of 7) until this reconciliation.
  - `references.json`'s `realized_footprint` over-claimed `uv.lock` — the merge commit (`4804b6976`) does not contain it (verified: `git diff --name-only a1dd4901f 4804b6976` returns exactly the ADR and `argument-naming.md`). The dependabot PR #1541 landed the identical re-lock first, collapsing this plan's own copy to a no-op during the pre-merge rebase. Filed as candidate-lesson `identifier-vocabulary-decision-004`.

## Routing and Merge Behavior

- Review: `automatic-review` reported 4 comments found, 2 reviewed, 1 refused (per the
  operator's paste — not independently re-verified line-by-line here). One is
  independently corroborated: CodeRabbit inline comment `fe553a` on
  `doc/adr/023-...adoc:265`, resolution `fixed`, responded on the PR (candidate-lesson
  `identifier-vocabulary-decision-009` — a closed-vocabulary escape-hatch defect caught
  post-push by CodeRabbit despite `pre-submission-self-review` marking `done`).
- CI/merge: `state: merged` (verified via `ci pr view --pr-number 1543`), merge commit
  `4804b6976`, present on `origin/main` (verified via `git log origin/main`). No rebase
  conflicts recorded against a sibling plan — this plan's own `uv.lock` change collapsed
  to a no-op against a preceding, unrelated dependabot PR (#1541), not a collision with
  another `orchestrator-refactor` plan.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `#1543`
- [x] row `landing` stamped → `landings/PLAN-04.md`
- [x] row `plan_marshall_plan_id` stamped → `identifier-vocabulary-decision`
- [x] epic.md queue reconciled from status.json
- [x] Decision recorded: ADR-023's actual outcome (`--epic`, not `--name`) corrects the
      epic's own Vision framing
- [x] PLAN-05 folded with the D4 execution brief (sized surface, ordering constraint,
      survivor-sweep method, `orchestrator queue` redesign note, two-plan-identifier-
      vocabularies note) — same-act Expected Surface update applied
- [x] PLAN-06 folded with the orchestration-detection-reconciliation defect
      (`identifier-vocabulary-decision-003`)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- PLAN-05 (this epic) — folded: the full D4 execution brief. See PLAN-05's updated
  Claim Labels and Expected Surface.
- PLAN-06 (this epic, parked) — folded: the orchestration-detection reconciliation defect
  from `identifier-vocabulary-decision-003`.
- Global lessons corpus — promoted: `identifier-vocabulary-decision-002` (finalize
  dispatch-boundary metrics gap), `-004` (realized_footprint vs merge-commit
  reconciliation), `-005` (forwarded-but-unconsumed retrospective rule),
  `-006` (metrics accumulator absence), `-007` (fork cwd-pinning across
  `worktree-remove`), `-008` (suspicious-perfect-confidence heuristic gap for
  orchestrator-authored specs), `-009` (closed-vocabulary escape-hatch anti-pattern),
  `-010` (ci router `--plan-id` positional recurrence), `-011` (merge_lock
  `--hold-start` float-vs-ISO8601 type disagreement, independently verified as
  convention-inconsistency-only, not doc-contract-divergence).
- Epic Watches (this epic) — added: cross-plan tracking of `2-refine` suspicious-100%
  scores (from `-008`) and of the epic's per-plan argparse-rejection rate (from `-010`,
  `-011`, and discarded standalone `-012`, whose own text asked for exactly this).
- Discarded (not lifted standalone, per its own explicit instruction): `-012` — its
  population-counting ask is served by the new argparse-rejection-rate Watch instead.
