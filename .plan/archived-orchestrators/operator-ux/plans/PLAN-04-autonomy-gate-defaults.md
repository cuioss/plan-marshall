# PLAN-04: Settle the autonomy gate defaults on one checkpoint

epic: operator-ux
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-autonomy-gate-defaults.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Make `plan_without_asking` the single deliberate human checkpoint in the plan lifecycle. Three
of the five `*_without_asking` knobs already default `true`, so the change itself is small:
flip `loop_back_without_asking` to `true`, relying on `phase-6-finalize.max_iterations` as the
real bound, and re-examine the step-owned `final_merge_without_asking`. The larger deliverable
is the **census**: an enumeration of every remaining gate that can pause a run, with a verdict
on each. Without it, "we flipped the knobs we knew about" cannot be distinguished from "no
pause gate remains", and the user's complaint is about the aggregate, not about any one knob.

## Deliverables

1. `_config_defaults.py`: `loop_back_without_asking` defaults to `true`.
2. A decision on `final_merge_without_asking` (step-owned under `default:branch-cleanup`,
   currently `false`), landed either way with its rationale recorded. Merging is
   outward-facing and irreversible, so `false` may well be correct — this deliverable is to
   settle it deliberately, not to presume the flip.
3. The pause-gate census: every gate that can halt a run for user input, in one table, each
   with its default, its owning config path, and a keep/flip verdict. Includes the flat
   `*_without_asking` family, the `gate_mode` gates (`deep_lane`, `escalation`,
   `revalidation`), `lane_selection`, `q_gate_validation`, and the finalize ceremony `lane`
   overrides.
4. Documentation updated in lock-step at every site that states the defaults —
   `manage-config/SKILL.md`, `marshal-json-reference.md`, `wizard-flow.md`,
   `menu-configuration.md`. These restate the default partition in prose and would otherwise
   silently contradict the code.
5. Tests asserting the new defaults, and a test that the documented default set equals the
   declared default set, so this class of drift cannot recur.

## Claim Labels

- OBSERVED: `init_without_asking`, `execute_without_asking` and `finalize_without_asking`
  already default `true`; only `plan_without_asking` and `loop_back_without_asking` default
  `false` — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
  § `DEFAULT_PLAN_INIT` / `DEFAULT_PLAN_OUTLINE` / `DEFAULT_PLAN_PLAN` /
  `DEFAULT_PLAN_FINALIZE`, and restated at
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md` § "The
  defaults are a partition, not 'all pause'".
  - verdict: corroborated | checked_at: 1c4e6febb | by: operator-ux/cleanup | rescoped: n/a | evidence: RE-STAMPED at the true HEAD; #1423 edited wizard-flow.md mid-cleanup so the earlier stamp's anchor needed re-reading. _config_defaults.py is untouched by both #1423 and #1426 and byte-unchanged since 9fd0957, so the five default readings stand; the 'defaults are a partition' anchor is still present in wizard-flow.md (exactly one occurrence) and states the same partition
- OBSERVED: `loop_back_without_asking: false` is documented as deliberate — "reverse halt so
  unattended runs cannot silently re-enter execute" — read at the same `wizard-flow.md`
  anchor. This plan overrides a stated intent, not an oversight, and the PR must say so.
  - verdict: corroborated | checked_at: 1c4e6febb | by: operator-ux/cleanup | rescoped: n/a | evidence: RE-STAMPED at the true HEAD: #1423 landed mid-cleanup and edited wizard-flow.md, so the byte-unchanged evidence written minutes earlier at 80f0b5a79 was already false. Re-read rather than assumed - the deliberate-asymmetry language survives verbatim at the SAME lines, :497 ('so unattended runs cannot silently re-enter execute on a finalize-side fix') and :521 ('reverse halt-and-prompt'). The claim holds; only its prior evidence did not
- OBSERVED: `final_merge_without_asking` is a step-owned param of `default:branch-cleanup`
  defaulting to `false`, read/written via `step get`/`step set` and NOT via `set --field` —
  read at `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` § the step-owned
  param table.
  - verdict: corroborated | checked_at: 1c4e6febb | by: operator-ux/cleanup | rescoped: n/a | evidence: Re-confirmed at the true HEAD: data-model.md is untouched by #1423 and #1426, so :861 (default false), :775 and _config_defaults.py:1144 (step-owned under default:branch-cleanup) and :885 (accessor is step get/set --step-id, NOT set --field) all still read as stamped. NOTE for outline: this project's own marshal.json sets it to true, so the repo cannot observe the default from its live config
- OBSERVED: Reverse loop-back is bounded by `phase-6-finalize.max_iterations` (default 3),
  which "halts and prompts the user when the cap is reached even with the flag set" — read at
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md`
  § the `loop_back_without_asking` paragraph. ⛔ This is the plan's load-bearing safety claim
  and must be re-verified against the implementing dispatcher at outline, not against this
  prose — the prose is the same inference restated.
  - verdict: corroborated | checked_at: 1c4e6febb | by: operator-ux/cleanup | rescoped: n/a | evidence: RE-STAMPED at the true HEAD after #1423 edited wizard-flow.md mid-cleanup; the prior 'unchanged since 9fd0957' evidence was already false when written. Re-read: _config_defaults.py:1109 still carries max_iterations 3 under phase-6-finalize (that file is untouched by #1423) and wizard-flow.md:521 still states the dispatcher halts and prompts at the cap even with the flag set. ⛔ PROSE ONLY - neither is the implementing dispatcher, which the claim requires be read at outline. This verdict corroborates the prose and does NOT discharge that obligation
- HYPOTHESIS: The census is complete at five gate families (flat `*_without_asking`,
  `gate_mode`, `lane_selection`, `q_gate_validation`, ceremony `lane`) — confirm/refute by
  enumerating every `AskUserQuestion` raise in the phase-1..6 skills against the config keys
  that gate it, at `marketplace/bundles/plan-marshall/skills/phase-*/` (verify-at-outline).
  An asserted completeness claim is verified exactly like an asserted presence.
- Verify-first clause: confirm the `max_iterations` halt actually fires with
  `loop_back_without_asking: true` by reading the finalize dispatcher's loop-back branch
  before the default is flipped. A refutation blocks deliverable 1 outright.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `doc/user/configuration.adoc`
- OBSERVED: `test/plan-marshall/manage-config/`

⛔ **The last two were added at the 2026-09-06 cleanup as an UNDERSTATED-surface correction, and
they are not optional extras.** Deliverable 4 says documentation is updated "at every site that
states the defaults", and both state them: `data-model.md` gives
`loop_back_without_asking | bool | false` (:832) and `final_merge_without_asking | bool | false`
(:861) in its knob tables, plus four JSON examples (:101, :123, :792, :814); `configuration.adoc`
gives `plan.phase-6-finalize.loop_back_without_asking | false` (:130) in a **user-facing** table.
Flipping the code default without these leaves the documentation asserting the opposite — which is
the exact drift deliverable 5's "documented default set equals declared default set" test exists
to make impossible, and it would fail on a set the spec did not enumerate.
⚠ `manage-config/standards/api-reference.md` was considered and **deliberately excluded**: its
only mention (:181) cites the `finalize_without_asking` / `loop_back_without_asking` family as an
*analogy* for `orchestrator.auto_emit` and states no default of its own.
⛔ **This correction adds a collision that did not exist before.** `data-model.md` is declared by
PLAN-09, so PLAN-04 and PLAN-09 now overlap there as well as on `_config_defaults.py` and
`manage-config/SKILL.md`. That is a real constraint being surfaced, not created — PLAN-02 and
PLAN-03 both edited this file undeclared, so the gate has been blind to it twice already.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-01/02/03 (`manage-config/SKILL.md`), PLAN-08 and PLAN-09
  (`wizard-flow.md`, `menu-configuration.md`), PLAN-09 (`_config_defaults.py`).
- Adjacent to: the domain detector — also a source of prompts, but a detector gap rather than
  an autonomy knob, and owned by WS-01. The census names it as out-of-family so a reader does
  not expect a knob for it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-04-autonomy-gate-defaults.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
