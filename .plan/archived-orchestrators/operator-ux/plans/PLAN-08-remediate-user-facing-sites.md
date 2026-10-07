# PLAN-08: Bring the prompt-dense user-facing sites into conformance

epic: operator-ux
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-08-remediate-user-facing-sites.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Apply the standards established by PLAN-05 (prompt structure), PLAN-06 (language and
vocabulary) and PLAN-07 (output volume) to the surfaces users actually meet — in ONE pass per
site, not one pass per rule. The heaviest sites carry every defect at once, so a per-rule sweep
would edit the same files three times and collide with itself. Success is measured by the
PLAN-05 doctor rule rather than by reading, plus a manual check of the judgement-bearing
property the rule cannot express: that each surviving prompt is answerable by someone who has
not read the codebase.

## Deliverables

1. Remediate the prompt-dense sites named in the Expected Surface: each surviving prompt gets
   decision context, consequence-bearing options, a marked recommendation, and a preamble free
   of workflow step numbers, tool-API type names, and internal nouns.
2. Remediate the user-facing report text at phase boundaries against PLAN-07's rule, applying
   the completeness floor first — no failure, skip or partial result is trimmed.
3. A conformance report: every site touched, every prompt deleted rather than rewritten (a
   prompt a sibling plan removed needs no rewrite), and every site the doctor rule flags that
   this plan deliberately did not change, with the reason. An audit that does not name what it
   declined to touch is indistinguishable from one that missed it.
4. A clean `plugin-doctor` run over the touched bundles for the new rule.

## Claim Labels

- OBSERVED: The prompt-dense sites and their reference counts at HEAD are
  `marshall-steward/references/menu-configuration.md` (29),
  `phase-6-finalize/standards/branch-cleanup.md` (24), `phase-1-init/SKILL.md` (20),
  `plan-marshall/workflow/planning.md` (18), `marshall-steward/references/wizard-flow.md` (12),
  `marshall-steward/references/provider-setup.md` (11), `plan-marshall/workflow/triage.md` (10),
  `marshall-steward/SKILL.md` (10). DERIVED counts from a grep at HEAD, labelled as derived;
  they will have moved by the time this plan runs and MUST be re-derived at outline rather
  than trusted.
  - verdict: corroborated | checked_at: 1c4e6febb | by: operator-ux/cleanup | rescoped: n/a | evidence: RE-STAMPED at the true HEAD: #1423 landed DURING this cleanup and added 4 lines to each of marshall-steward/SKILL.md, menu-configuration.md, provider-setup.md, phase-1-init/SKILL.md and plan-marshall/workflow/planning.md, so the stamp written minutes earlier at 80f0b5a79 named three of those as byte-unchanged and was already false. Cumulative drift since 9fd0957 now reaches 7 of the 8 named sites; only workflow/triage.md is untouched. The claim ADMITS regardless because it labels its own counts DERIVED and requires re-deriving at outline from the PLAN-05 doctor rule's flagged set, which it names as the authoritative population - drift is the predicted state. ⛔ But the drift is no longer 'within' anything: outline must treat every one of the eight counts as unusable and re-derive all of them
- HYPOTHESIS: The site list above is substantially complete for user-facing prompts — that is,
  the long tail below ten references contains no site whose prompts are heavily used —
  confirm/refute by re-running the sweep at outline and by consuming the PLAN-05 doctor rule's
  own flagged set, which is the authoritative population (verify-at-outline). ⛔ If the doctor
  rule flags materially more than these eight sites, SPLIT this plan along bundle boundaries
  (`plan-marshall` / `marshall-steward` / everything else) rather than growing it — the
  scope-bloat guard applies and a split is the recorded default.
- HYPOTHESIS: PLAN-01 and PLAN-04 will have deleted some of the prompts counted above, so the
  remediation population is smaller than the count suggests — confirm/refute at outline
  against whatever those two plans actually landed (verify-at-outline).
- Verify-first clause: this plan may not begin before PLAN-05, PLAN-06 and PLAN-07 have landed.
  Remediating against a standard still in motion means doing the sweep twice. Confirm all three
  are merged at outline; if any is not, the plan halts rather than proceeding on a draft.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/provider-setup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md`

## Dependencies and Sequencing

- Depends on: **PLAN-05, PLAN-06 and PLAN-07** — all three, hard.
- Should also follow **PLAN-01** and **PLAN-04**, which delete prompts this plan would
  otherwise rewrite.
- Overlaps with: PLAN-01 (`phase-1-init/SKILL.md`), PLAN-04 (`menu-configuration.md`,
  `wizard-flow.md`, `phase-6-finalize/SKILL.md`), PLAN-09 (`marshall-steward` references).
  This is the epic's broadest surface — **expect it to run alone**, with the second
  concurrency slot deliberately unfilled.
- Adjacent to: the standards themselves, which this plan CONSUMES and never edits. A
  remediation that finds the standard wrong reports it back rather than amending it in place.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-08-remediate-user-facing-sites.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
