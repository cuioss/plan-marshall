# PLAN-CIS-028: Post-Run Review Steps Run Before the Run's Evidence Exists

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

The finalize steps whose job is to look back over a run are **ordered before the step that
produces most of the run's evidence**. `review-retrospective` runs at `order: 50` and
`lessons-capture` at `order: 60`; `branch-cleanup` — which hosts the pre-merge barrier, the bot
re-review wait, finding triage, the loop-back trigger and rebase reconciliation — runs after both.

The consequence is not a cosmetic ordering wart. On #1074, `review-retrospective.md` **shipped
three false statements** into a merged plan directory, and a candidate-lesson shipped with a
premise its own run had already refuted. On #1072, `affected_files_recall` scored **0% against a
21/21 exact footprint** because `branch-cleanup` had deleted the worktree it measures.

⭐ **This is the same archetype as the PLAN-10 finalize-ordering defect** — a step scheduled where
its input does not exist — and it now has **four independent sightings across three plans**, so it
is a class rather than a series of incidents.

## Deliverables

1. **Reorder the post-run-review steps after the merge gate**, alongside `plan-retrospective`
   (which sits after `branch-cleanup` and is the only reason any of this was visible at all).
   ⚠ The alternative — keep the order and re-fire on loop-back — is recorded in the source lesson
   as **structurally dishonest and more expensive**: these are post-run steps and the run is not
   over at order 50. **Prefer the reorder; if the re-fire path is chosen instead, record why.**
2. **A structural guard**: no step whose role is post-run-review may be ordered before the merge
   gate. ⛔ **Derive the population of post-run-review steps** — do not hand-list them.
3. **`head_dependent` declared on the project-local finalize steps that need it**, starting with
   `finalize-step-review-retrospective`, which reads the `pr-comment` findings store — i.e. the
   **remote state of tracked source** — and therefore matches #1073's mandatory-declaration
   discriminator exactly. ⚠ #1073 swept the built-ins plus two project steps; **the project tier
   is where the next instance hides.** Sweep it, and persist `--head-at-completion` on the
   terminal `mark-step-done` as the contract requires.
4. **Stop reporting an unresolvable footprint as `0%` coverage recall.** A measurement whose input
   is absent must report *unmeasurable*, not a confident zero. ⭐ This is the epic's
   fail-closed discipline (ADR-009) applied to the retrospective's own instruments — and it is the
   generalisation of *"a wait that cannot observe its target is not a wait"* from waiting to
   measuring.
5. **The remaining retrospective-machinery defects surfaced alongside these** — the four defects in
   the retrospective's own machinery that, per the source lesson, **all fail in the confident
   direction rather than the absent one**. ⛔ **Derive them from the sources named in Claim Labels;
   do not treat this deliverable as a fixed list of four.**

⚠ **Five deliverables and D5 has an unbounded floor.** Evaluate the split guard at outline —
D1+D2+D3 (ordering and declaration) is a coherent unit that can ship without D4+D5.

## Claim Labels

- **OBSERVED (`marketplace-dependency-resolver-012`, first-party to that plan)**: the order table —
  `review-retrospective` 50 @ 19:06:24Z, `lessons-capture` 60 @ 19:10:22Z, `branch-cleanup`
  19:30:54Z → 22:47:47Z — and that the barrier BLOCK (19:43), CodeRabbit's 6 comments (19:52),
  triage (20:01–20:05), loop-back (20:06) and a sibling-PR conflict (21:16) **all** occurred after
  both review steps had written their output.
- **OBSERVED (`marketplace-dependency-resolver-011`)**: `review-retrospective.md` asserts CodeRabbit
  "absent", inline coverage "zero", and "a thin-review landing". **All three are false** —
  CodeRabbit posted 6 actionable comments across 16 files with `evidence_kind=inline`, four of them
  genuine defects that became TASK-011/TASK-012 and landed in `021305e26`. The artifact's closing
  recommendation is **actively misleading**.
- **OBSERVED (`marketplace-dependency-resolver-011`)**: the step's frontmatter carries `lane`,
  `order: 50`, `default_on`, `presets`, `implements` — and **no `head_dependent`**. The loop-back
  re-fire gate's decision list does not mention it: **it was not declined, it was never
  considered.**
- **OBSERVED (`path-attribution-seam-008`, PLAN-CIS-023 landing)**: `plan-retrospective` is
  scheduled where two of its inputs do not exist — the worktree is deleted before it, and metrics
  are not closed until after it. `affected_files_recall` scored **0% on a 21/21 exact footprint**.
- **OBSERVED (`marketplace-dependency-resolver-020`)**: candidate-lesson cl9 shipped with a premise
  its own run refuted — it claimed the run "merged with no durable record that the diff was
  unreviewed"; the barrier blocked at 19:43 and the run did not merge in that state.
- **HYPOTHESIS**: reordering after the merge gate breaks no step that currently depends on running
  early. Confirm/refute by enumerating what consumes each step's output and when
  (verify-at-outline). ⚠ `lessons-capture` writes the epic inbox messages — **moving it changes
  when the orchestrator receives them**, which is a contract with this epic, not an internal detail.
- **HYPOTHESIS (population)**: the post-run-review role is mechanically identifiable from
  frontmatter. Confirm/refute at `ext-point-finalize-step.md` (verify-at-outline). If no such
  marker exists, D2's guard needs one **introduced** rather than read.
- **Verify-first clause**: ⛔ **`truthful-signals` reports that finalize step execution is NOT
  uniformly logged** — the `Executing step` marker appears 33× for `sync-baseline` but 1× for
  `sonar-roundtrip` across 39 plans, **so marker absence does not mean the step did not run** and
  any count derived from those markers is a FLOOR. Settle how to enumerate step execution before
  asserting any coverage claim. Their `PLAN-TRUTH-031` (making finalize step records structured
  rather than prose) is the observability prerequisite — **check whether it has landed.**

## Expected Surface

- **OBSERVED**: `.claude/skills/finalize-step-review-retrospective/SKILL.md` — frontmatter (D3)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — step ordering and the re-fire gate (verify-at-outline)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — the `head_dependent` discriminator and any post-run-review marker
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — the recall instrument (D4) (verify-at-outline)
- **OBSERVED**: `.claude/skills/` project-local finalize steps — the sweep target for D3

## Dependencies and Sequencing

- **Depends on**: PLAN-TRUTH-001 (#1073, shipped `8db7b42d4`) for the `head_dependent` contract.
  ⚠ **Cross-epic**: check whether `PLAN-TRUTH-031` has landed before scoping the D-5 enumeration.
- **Overlaps with**: **PLAN-CIS-010** and **PLAN-CIS-011** on `phase-6-finalize` — ⛔ never pair.
  **PLAN-CIS-012**, **PLAN-CIS-019**, **PLAN-CIS-020** on `plan-retrospective` — ⛔ never pair.
- ⚠ **PLAN-CIS-011 is now UNBLOCKED** (PLAN-TRUTH-001 landed) and is the nearest neighbour. ⛔ **The
  roster is 9, not 8** — assert against the derived `head_dependent` frontmatter fact, never a count
  or a hand-maintained list.

## ⛔ Landing-verification obligations (folded 2026-08-02 from the CIS-027 drain)

⚠ **This section was added while the plan was already at PR #1080.** It does NOT re-scope the
running plan — it is the checklist the landing analysis MUST work through, folded here so it is
not re-derived. Source: inbox `plan-cis-027-…-007` (a **fifth** sighting of the finalize-ordering
archetype, first-party to PR #1079).

1. **The 0%-recall case must be gone, and `unmeasurable` must be reachable.** On #1079,
   `affected_files_recall` reported `fail — Recall 0%`, listing all 8 declared files as missing,
   on a plan whose footprint was an **exact 8/8 match in both directions** (verified independently
   here: `git show --stat 5c41364a5` = 8 files, 396 insertions, 55 deletions). D4 is what closes
   this. Verify the shipped `check-artifact-consistency.py` (+312 in the branch) reports
   *unmeasurable*, not a confident zero.
2. ⛔ **`base..HEAD` must NOT be in the fallback chain, and the reason is measured.** Passing the
   plan's phase-4 base SHA produced `files_total: 39, files_kept: 37` against a true footprint of
   **8** — a **4.6x over-count**, because three sibling PRs (#1076, #1077, #1078) landed in
   between. **Sibling landings contaminate any base..HEAD range.** The fallback order that works
   is: (1) live worktree diff, (2) the plan's own merge commit recorded at `branch-cleanup`,
   (3) `references.affected_files` — and it must **never silently return an empty set**.
3. **The metrics half is independent of the ordering half.** On #1079 `record-metrics` had not run
   when the retrospective read `metrics.md`, so finalize — **the single largest phase of that plan,
   1,767,890 tokens across 12 dispatched steps, more than phases 1–5 combined (1,505,604)** — was
   read as zero, understating the Total by **2.17x**. ⭐ The partiality machinery worked correctly
   (`> Partial: unrecorded phases — 6-finalize`, Total stamped `n=4/6`); **the honest floor was
   simply furthest from the truth at exactly the moment the retrospective sampled it.** Confirm the
   branch's `record-metrics.md` / `plan-retrospective` change actually closes the accumulator first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-028-post-run-steps-ordered-before-their-evidence.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
