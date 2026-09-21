# PLAN-09: `interaction_mode` — one persisted preference for how much the system asks

epic: operator-ux
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-09-interaction-mode.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Introduce `interaction_mode` (`basic` | `advanced` | `expert`) — one persisted preference,
chosen at `/marshall-steward` and changeable later, that scales how much plan-marshall asks
and explains. It is deliberately the epic's last plan: the mode is a multiplier on behaviour
the earlier plans establish, and a knob layered over unfixed defaults would add a dimension to
the confusion rather than remove one. The name is settled — `interaction_mode`, not
`profile` — because `skill_domains.active_profiles` already means work-activity profiles, and
a second meaning for the same word in one `marshal.json` is a defect waiting to be written.

## Deliverables

1. The `interaction_mode` field in `marshal.json` with its validator and its default
   (`advanced`, matching what the earlier plans establish as the baseline, so the knob is
   inert until deliberately changed).
2. The `manage-config` read/write surface for it.
3. A `/marshall-steward` menu entry that sets it on first run and on later invocation, with
   each mode described in terms of what the user will experience, not what the system will do.
4. The mode-to-behaviour mapping, expressed against what the earlier plans actually landed:
   how much context a prompt carries (PLAN-05), how much output a phase boundary emits
   (PLAN-07), and whether a borderline gate asks or proceeds (PLAN-04's census).
5. Tests: each mode resolves; an invalid value is refused; an absent field resolves to the
   default without error.

## Claim Labels

- OBSERVED: `profile` is already taken. `skill_domains.active_profiles` and
  `skills_by_profile` denote work-activity profiles (`implementation`, `module_testing`,
  `integration_testing`, `quality`, `documentation`) — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py`
  § the `active_profiles` preservation block, and
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/skill-domains-setup.md`
  § Configure Active Profiles. The name `interaction_mode` was chosen by the operator to avoid
  this collision.
  - verdict: corroborated | checked_at: 8fc353b6e | by: operator-ux/cleanup | rescoped: n/a | evidence: FULLY CORROBORATED AT THIS SHA, ARTIFACT AND LINE CITES BOTH INTACT. `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py` exists (1075 lines) and both prior cites resolve: :858-925 is the active_profiles preservation block (existing_domain_active_profiles at :861, the global sibling at :883-894) and :1028-1067 is the global/per-domain split (:1028 ap_result['global'] then the per-domain loop). `skill_domains.active_profiles` IS the live config spelling - :888 reads skill_domains.get('active_profiles') as a top-level sibling of the per-domain entries, and per-domain active_profiles is read at :867. So 'profile' is taken at BOTH levels, exactly as the claim states. The word is additionally live vocabulary across the extension API (extension-contract.md:414,424 and 9 bundle extension.py files), so the collision the claim names is wider than the one file. NOTE FOR THE READER: an earlier stamp of this claim in this same cleanup pass recorded the artifact as deleted; that reading searched marshall-steward/scripts/ instead of manage-config/scripts/ and was wrong. This verdict replaces it.
- OBSERVED: No experience-level, verbosity or interaction-mode concept exists today. Asserted
  as an ABSENCE and verified as one by a marketplace-wide search over `*.md` and `*.py`.
  - verdict: corroborated | checked_at: 8fc353b6e | by: operator-ux/cleanup | rescoped: n/a | evidence: CLEAN-COVERAGE ZERO, RE-RUN AT THIS SHA. grep for interaction_mode|experience_level|verbosity_level across marketplace/ and doc/ returns NO file at all. The scope narrowing recorded by the prior verdict still stands and is unchanged: PLAN-06 (#1382) and PLAN-07 (#1387) landed user-communication.md, so a verbosity STANDARD exists while no verbosity KNOB does - read the claim as 'no user-settable mode exists'. PLAN-08 (#1447) rewrote 10 doc/user/*.adoc files and introduced no such concept either
- HYPOTHESIS: A top-level `marshal.json` scalar is the right home, sibling to `orchestrator`
  and `plan` rather than nested inside either — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` § the
  top-level block inventory (verify-at-outline). The knob governs both tiers, so nesting it
  under `plan` would be wrong by construction.
  - verdict: corroborated | checked_at: 8fc353b6e | by: operator-ux/cleanup | rescoped: n/a | evidence: THE PROPOSED HOME EXISTS AND HAS PRECEDENT. `orchestrator` is a top-level marshal.json block, explicitly documented as a sibling of `plan` (marshal-json-reference.md:151), and it already carries scalars of exactly the proposed shape: `orchestrator.parallelization_scope` (int >= 1, :155) and `orchestrator.auto_emit` (bool). A top-level scalar sibling is therefore a supported, precedented shape rather than a new structural form
- HYPOTHESIS: The steward menu supports adding an entry of this shape without restructuring —
  confirm/refute at
  `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md`
  § the menu entry inventory (verify-at-outline).
  - verdict: corroborated | checked_at: 8fc353b6e | by: operator-ux/cleanup | rescoped: n/a | evidence: MENU STRUCTURE SUPPORTS THE ADDITION. menu-configuration.md (952 lines at this sha) is organised into per-area sections - Plan Phase Settings :169, Review Gates :214, Quality Pipelines :264, Skill Domains :453, Project Structure :558 - so an entry of this shape lands in an existing section without restructuring. ⚠ WEAKEST OF THE FOUR: this is a structural-precedent reading, not an implementation read. PLAN-08 (#1447) rewrote this file, so the outline must re-read the target section at its own HEAD rather than trusting this verdict's line numbers
- Verify-first clause: the mode-to-behaviour mapping must be authored against what PLAN-04,
  PLAN-05 and PLAN-07 ACTUALLY landed, re-read at outline — not against this spec's
  expectation of them. A mapping written from expectation is a mapping to behaviour that may
  not exist.
- ⛔ Constraint, not a claim: `expert` must NOT re-enable the domain prompt PLAN-01 removes.
  That removal is a correctness fix — the detector held the information all along — and
  re-exposing it as a preference would reframe a defect as a taste. An expert who wants to
  override a resolved domain set uses the existing `--domain-override`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/skill-domains-setup.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md`
- OBSERVED: `test/plan-marshall/manage-config/`

## Dependencies and Sequencing

- Depends on: **PLAN-04** (the census names what there is to modulate), **PLAN-06** and
  **PLAN-07** (the vocabulary and volume rules are what `basic` dials up). PLAN-05 is a soft
  dependency — the mapping is richer if the prompt standard exists, but does not require it.
- Overlaps with: PLAN-04 and PLAN-06 (`_config_defaults.py`, `manage-config/SKILL.md`),
  PLAN-08 (`menu-configuration.md`, `wizard-flow.md`).
- Adjacent to: `skill_domains.active_profiles` — the surface this knob is deliberately named
  away from, and must not touch or rename.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-09-interaction-mode.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
