# PLAN-01: Over-provision the domain set instead of prompting on a zero narrative match

epic: operator-ux
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-domain-over-provision.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The domain detector prompts the user whenever a plan's request narrative contains no literal
token naming a configured domain and both inclusion legs (`always_on`, `file_globs`) are empty
— which, because those legs are absent by default and nothing seeds them, is the common case
in every project. Change the zero-narrative-match branch from *ask* to *over-provision*: union
the detector's own ranked candidates into the resolved domain set and resolve silently. The
detector already computes and ranks those candidates with per-candidate rationale, so the
information needed to answer the prompt is present at the moment the prompt is raised — the
prompt asks the user to supply something the system already has. Over-provisioning costs extra
skills loaded into a plan; it never produces wrong work. The multi-match branch is a separate
case and is **not** changed by this plan.

## Deliverables

1. `_cmd_domain_detect.py`: the zero-narrative-match branch resolves to the union of
   `candidates` ∪ `additional_candidates` ∪ the inclusion legs, returning `ambiguous: false`
   with a new distinguishable `reason` (e.g. `over_provisioned_zero_match`) rather than
   `ambiguous: true`.
2. A bounded escape: when the resolved union would be empty (no configured non-system domain
   at all), the existing ambiguous path is retained — over-provisioning nothing is not a
   resolution, and this branch must stay distinguishable from a successful one.
3. `phase-1-init/SKILL.md` Step 7: the caller stops raising the multiSelect on the
   zero-match branch, and the retained multi-match branch is stated explicitly so the
   remaining prompt has a named trigger.
4. Tests in `test/plan-marshall/manage-config/test_cmd_domain_detect.py` covering: zero match
   with candidates present → silent union; zero match with no configured domains → still
   ambiguous; multi-match → unchanged; inclusion legs non-empty → unchanged
   (`inclusion_only_resolve`).
5. `standards/skill-domains.md` and `manage-config/SKILL.md`: the `domain-detect` contract
   describes the new branch and its `reason` value.

## Claim Labels

- OBSERVED: The detector composes `{narrative} ∪ always_on ∪ glob_matched`, and `ambiguous` is
  `true` on a multi-match OR on a zero-match whose inclusion union is empty — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § module docstring and the zero-match return branch.
- OBSERVED: Narrative matching is a literal lowercase token match — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § `_tokenize`. A request naming a file path but not the domain word scores zero.
- OBSERVED: `always_on` / `file_globs` are absent by default with no seed into
  `DEFAULT_SYSTEM_DOMAIN` / `get_default_config()` — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md`
  § Domain Inclusion.
- OBSERVED: `additional_candidates` already carries the configured-but-unmatched domains
  precisely so the ambiguous-branch prompt can offer them — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § `_additional_candidates`. This plan consumes that same set as the union source.
- HYPOTHESIS: `phase-1-init` Step 7 is the only caller that raises the multiSelect on
  `ambiguous: true`, so suppressing the branch there suppresses the prompt everywhere —
  confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` § Step 7 domain detection,
  and by sweeping every `domain-detect` caller for a read of `ambiguous` (verify-at-outline).
- HYPOTHESIS: No consumer of `references.domains` fails or degrades on a wider-than-minimal
  domain set — confirm/refute at the persona/skill resolution path that reads
  `references.domains` (`manage-personas resolve` and the phase-4 skill-resolution step)
  (verify-at-outline). ⛔ This is the plan's load-bearing safety claim: if a wider set changes
  behaviour rather than merely loading more standards, over-provisioning is not free and the
  approach must be re-scoped before shipping.
- Verify-first clause: confirm at outline that `reason` is a free-form string in the return
  contract and that adding a new value breaks no existing consumer that switches on it.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md`
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_detect.py`

## Dependencies and Sequencing

- Depends on: none. This is the epic's entry plan and its highest-value single change.
- Overlaps with: PLAN-03 (same detector file — PLAN-03 sequences after this);
  PLAN-02 (`skill-domains.md`, `manage-config/SKILL.md`); PLAN-04
  (`manage-config/SKILL.md`); PLAN-08 (`phase-1-init/SKILL.md`).
- Adjacent to: `_cmd_skill_domains.py` — PLAN-02's surface. It writes the config this plan
  reads, and stays untouched here so the two can be reviewed independently.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-01-domain-over-provision.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
