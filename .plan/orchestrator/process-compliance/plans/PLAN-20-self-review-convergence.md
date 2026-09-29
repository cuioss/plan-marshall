# PLAN-20: Pre-submission self-review convergence and operator dispositions

> ✅ **Staged 2026-09-28 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-20-self-review-convergence.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make `default:pre-submission-self-review` terminate. In PLAN-13 it spent all 5 finalize loop-back
iterations. Each round's fixes moved the same defect class one contract hop outward. It left the
PR-review loop no ceiling, and it could only be closed by moves no document sanctions: `mark-step-done
--force`, a hand-resolved finding, and skipped re-fires recorded as free-text warnings.

## Deliverables

1. **A fixer and a residual-acceptance disposition.** Branch B (`loop_back`, target `6-finalize`)
   calls the findings "amendments to the diff in hand" but names no one who amends the diff, so a
   replay without a fixer re-surfaces the same findings until `max_iterations` refuses. The operator
   had to choose "fix inline" by hand. Name the fixer. Add a sanctioned disposition that accepts named
   residual findings and closes the step, recorded structurally so a later audit can tell it apart
   from a missed round. Settle whether an ordinary findings-bearing round (`accepted` + `may_close:
   no`) must also file `further_round_owed`.
2. **A sanctioned "no more review rounds" waiver.** Honouring the operator's "fix the found issues but
   no more review round, just continue" took three unsanctioned moves: (a) `mark-step-done --force`
   from `loop_back` to `done`; (b) resolving `verdict_refused` as `accepted` by hand; (c) skipping the
   head-dependent re-fires of lessons-housekeeping / simplify / plugin-doctor, recorded only as a
   decision-log WARNING. Give each move a structured, audit-visible form. Re-entering finalize after a
   ceiling refusal must also be able to make progress: today the persisted `loop_back_iteration` stays
   at 5/5, so re-entry gets no new round.
3. **Loop-back ceilings per source.** One `loop_back_iteration` counter caps every loop-back source.
   The self-review spent all 5, so the first genuine PR-review loop-back (2 CodeRabbit fixes) hit the
   ceiling and needed an operator override. Budget each source separately, so a runaway self-review
   cannot starve PR review.
4. **Self-review qgate findings are resolvable.** Step 3b files `verdict_refused` /
   `further_round_owed` findings with no file path, so `resolve-evidenced` (keyed on changed paths)
   can never resolve them. They stay pending and block the pre-merge findings gate. Give them a
   resolution path.
5. **The verifier and candidates contracts survive real sizes.** (a) For a clean round the
   orchestrator passed per-list candidate counts. The verifier summed them (161) against `counts.total`
   (122) and refused, because `counts.total` excludes review-anchor lists and the verifier template
   does not say so. Carry the `in_total` membership in the template, or forbid restating per-list
   counts. (b) The surfacer returned 80.6 KB of TOON, over the harness inline-output limit, while
   `requires_prompt_fields: candidates` demands the verbatim TOON in the prompt. Add a file-reference
   form.

## Claim Labels

- OBSERVED: 5/5 iterations spent; operator waiver; forced `done` at `3720898`; 2 CodeRabbit fixes blocked by the shared ceiling — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-004.md` §§ 8, 14, 19, 20, 23 and the landing message `-007` § Residue; landing record `landings/PLAN-13.md`
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: commit 3720898 exists; one shared counter (phase-6-finalize/SKILL.md L697); no waiver or residual-accept disposition in the inventory (run counts not re-derivable)
- OBSERVED: one `loop_back_iteration` counter caps every source — read at HEAD in `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` (§ Step 3, "Read the persisted `loop_back_iteration` count"; `max_iterations`)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: phase-6-finalize/SKILL.md L697-707 single status.metadata.loop_back_iteration; execution.md L647 'capped by max_iterations (counted across both tiers)'
- OBSERVED: verifier refusal 161 vs 122; 80.6 KB candidates envelope — cited at `plan-13-…-004.md` §§ 9, 15
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: workflow/pre-submission-self-review.md Step 3b template L439 passes only {N}, no in_total note; candidates required verbatim (L52, L244); self_review surface --help has no file-output option
- OBSERVED: `verdict_refused` has no file path — cited at `plan-13-…-004.md` § 17; HYPOTHESIS for the keying — confirm/refute at the `resolve-evidenced` implementation in `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/` (verify-at-outline)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md L513-517 qgate add carries no --file-path; _findings_core.py resolve_qgate_findings_by_evidence L1257-1291 leaves pathless findings pending

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — loop-back ceiling, waiver, re-entry
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — Branch B, Step 3b, verifier template (corrected cleanup 2026-09-28: the step document lives under `workflow/`, not `standards/`)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — L647 "capped by max_iterations (counted across both tiers)" (D3) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` — § Loop-back continuation (D3) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — candidates/counts contract (D5) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/` — resolution path for pathless qgate findings
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — per-source loop-back counters, structured waiver record
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/` — candidates envelope file-reference form
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — ceiling / waiver tests
- OBSERVED: `test/plan-marshall/manage-findings/` — resolution test

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-21 (shares `phase-6-finalize/SKILL.md` and `standards/`), PLAN-12 (running; touches `phase-6-finalize/standards/branch-cleanup.md`). Sequence after PLAN-12 lands and do not pair with PLAN-21.
- Prior art (cleanup 2026-09-28): archived truthful-signals-26-09-21 PLAN-TRUTH-148 ("a self-review that decides its own close") shipped as #1488. This spec is its continuation, not a duplicate: the PLAN-13 run hit non-convergence after #1488 had landed. Read #1488's contract before redesigning the close.
- Scope-bloat guard: 5 deliverables.

## Folded inbox material (same act)

- `plan-13-finalize-mechanism-defects-004.md` items 8, 9, 14, 15, 17, 19, 20, 23 (second half): deliverables 1–5

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-20-self-review-convergence.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
