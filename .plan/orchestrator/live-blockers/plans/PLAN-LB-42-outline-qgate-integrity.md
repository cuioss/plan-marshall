# PLAN-LB-42: Outline Q-Gate integrity — no guaranteed assessment-coverage failure, no pass over zero validator runs, no plan left without a domain

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-42-outline-qgate-integrity.md` and is queued as one row file, `queue/PLAN-LB-42.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from three Open Defects:
> - deep-lane outline writes no assessments (`lessons-routing-022.md`; `-028` items 162, 174, 191);
> - 4-plan Q-Gate skips its validators on the 3-outline hash (`lessons-routing-023.md`; `-028` item 185);
> - domain narrowing can empty `references.domains` (`lessons-routing-010.md`).
>
> The fourth part of `-010` — `set-list --values ""` exiting 2 — is already fixed at HEAD and is dropped (see Claim Labels).

## Objective

Three outline-phase defects either interrupt the operator on every affected plan or report a pass that never happened:

- **Every deep-lane plan in a domain without a component-analysis step fails Q-Gate check 2.2.** No assessment is ever written, so every deliverable fails the check.
- **The 4-plan Q-Gate inherits the 3-outline whole-outline hash.** Its own validators (module mapping, scope criterion) never run, yet the result reads as a pass. No script computes the hashes, so each run computes them by hand.
- **Domain narrowing can drop every domain**, and the outline then writes an empty domain list on purpose.

This plan makes each of these report what actually ran, and never leave a plan with zero domains.

## Deliverables

1. **Assessment coverage reports "not run" when no assessment exists.**
   - In `q-gate-validation.md`, check 2.2 (Assessment Coverage) and Step 5 (Missing Coverage) run only when the plan's assessment store holds at least one record.
   - When it holds none, they record no Q-Gate finding. The run logs `2.2 not run: no assessments recorded`, and the return TOON names the skipped checks in a `not_run_validators[]` field, so the result reads as "not run", never as a failure or a pass.

   *Done when:* a doc-contract test asserts that § 2.2 and Step 5 state the not-run outcome, and that the Output block carries `not_run_validators`. The test fails at HEAD, where § 2.2 (L168-182) flags every file not covered by a CERTAIN_INCLUDE assessment.

2. **The hash skip is keyed by phase, and a cached skip is reported as not run.**
   - The `work/deliverable-hashes.toon` artifact records the phase that wrote it, either as a per-phase file or a `phase` column.
   - Step 3.5's whole-outline short-circuit fires only on a stored row from the **same** phase, so the first 4-plan pass after a 3-outline pass runs every 4-plan validator.
   - A skipped validator is reported as `not run (cached from phase {X})`, never counted as passed.
   - Steps 6 and 8 take `{phase}` from the activation context instead of the hard-coded `3-outline`.
   - The orchestrator readers in `planning-outline.md` and the phase-4-plan Q-Gate block read the phase-keyed artifact.

   *Done when:* a doc-contract test asserts that Steps 3.5, 6 and 8 carry `{phase}` and the same-phase condition. A fixture with a 3-outline artifact shows 4-plan's whole-outline gate not firing. Both fail at HEAD.

3. **A deterministic `manage-solution-outline deliverable-hashes` verb.**
   - The verb computes the per-deliverable SHA-256 hashes and the `__whole_outline__` aggregate with the outline parser the validators already use (`_plan_parsing`). It returns them as TOON, and with `--phase P --write` persists the phase-keyed artifact.
   - Step 3.5 calls it instead of having the agent compute hashes by hand.

   *Done when:*
   - The verb returns one row per deliverable plus the aggregate, and the hash is unchanged when the outline is re-read unchanged.
   - Editing one deliverable changes exactly that row and the aggregate.
   - `q-gate-validation.md` Step 3.5 names the verb.

   At HEAD no such verb exists.

4. **Domain narrowing never empties the domain set.**
   - `domain-narrow` adds a fourth claim leg: a domain that any outline deliverable declares in its `domain:` metadata is retained.
   - A run that would retain no user domain returns `status: error, error: would_empty` and writes nothing.
   - `phase-3-outline/SKILL.md` step 3 (L626-633), which currently calls clearing the list "the correct outcome", is rewritten. `light-lane.md` is aligned.

   *Done when:* a fixture where every deliverable declares `domain: documentation` and no file glob matches keeps `documentation`. A fixture with no deliverable domain and no claims returns `would_empty`. Both fail at HEAD (`_cmd_domain_narrow.py` drops both).

## Claim Labels

- OBSERVED: the only declared implementation of the component-analysis contract, which writes the assessments check 2.2 reads, is `pm-plugin-development:ext-outline-workflow` — `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/component-analysis-contract.md` § Implementors (L14-16). A deep-lane plan in any other domain (Java, generic) writes none. A content search for `assessment add` / `CERTAIN_INCLUDE` turns up no other writer.
- OBSERVED: check 2.2 flags every affected file without a CERTAIN_INCLUDE assessment and has no not-run outcome — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` § 2.2 (L168-182). Step 5 has the same dependency (L797-813).
- OBSERVED: the hash artifact rows are `hashes[]{deliverable,hash}` with no phase or validator-set key (L111). The whole-outline short-circuit is hash-only and fires whenever a stored `__whole_outline__` row is present (L133-137), so a 4-plan first pass meets the 3-outline row as a re-entry. Module-mapping (§ 2.11) is a 4-plan-only validator (L466).
- OBSERVED: Step 6 (L826-832) and Step 8 (L864-865) hard-code `--phase 3-outline`, while Step 3.5 uses `{phase}` (L116-117).
- OBSERVED: the hashes are computed by the agent from prose — "no new script surface are introduced" (L146). A content search for `deliverable-hashes` finds only `q-gate-validation.md` and `planning-outline.md`, with no script.
- OBSERVED: `domain-narrow` has three claim legs — task, `always_on`, `file_globs` — and none reads deliverable-declared domains. An all-dropped run returns `status: success` with an empty `retained` — `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py` L312-346.
- OBSERVED: `phase-3-outline/SKILL.md` L633 calls clearing the list on an all-dropped run "the correct outcome for that state".
- OBSERVED (dropped item): the generated executor forwards an empty option value. `architecture find --pattern ""` returned `pattern: ""` with `status: success` at this checkout, and `set-list` turns `''` into `[]` (`manage-references/scripts/_cmd_list.py` L69). The `set-list --values ""` exit-2 failure no longer occurs.
- HYPOTHESIS: the phase-4-plan Q-Gate block reads `work/deliverable-hashes.toon` — confirm at `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` § Step 8b (verify-at-outline).
- HYPOTHESIS: `_plan_parsing.py` exposes the deliverable block boundaries the validators use — confirm at `manage-solution-outline/scripts/_plan_parsing.py` (verify-at-outline).
- HYPOTHESIS: deliverable `domain:` metadata is reachable through an existing `manage-solution-outline` reader — confirm the verb before adding a parser (verify-at-outline).
- Verify-first clause: deliverable 1 trades a guaranteed false failure for a not-run report. It must not hide a plugin-domain plan whose component analysis failed to write. The not-run line must name the plan's resolved outline skill so that case stays visible.
- Evidence clause: the pm-mcp-core evidence (eleven plans) rests on the lessons-routing ingest and was not re-checked here.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md` — § 2.2, Step 3.5, Step 5, Step 6 phase, Step 8 phase, Output (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — whole-outline re-run gate reader (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — only if its Q-Gate block reads the artifact (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` — `deliverable-hashes` verb (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — reused parser (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` — canonical invocation (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_narrow.py` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — `domain-narrow` reason codes (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md` — § Domain Narrowing step 3 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` (D4)
- OBSERVED: `test/plan-marshall/q-gate-validation-agent/` — new doc-contract test module (D1, D2)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_manage_solution_outline_cli.py` (D3)
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_narrow.py` (D4)
- OBSERVED: `test/plan-marshall/manage-config/test_domain_narrow_reason_codes_documented.py` (D4)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with:
  - PLAN-LB-26 (running) on `plan-marshall/workflow/q-gate-validation.md`. PLAN-LB-26's D4 rewrites the Step 6 "deduplicates by title" note, while this plan changes the Step 6 `--phase` argument — the same section — so run after PLAN-LB-26 or rebase onto it.
  - PLAN-LB-39 (running) on `phase-4-plan/SKILL.md`, only if the HYPOTHESIS entry holds.
  - None of the other four candidates in this batch.
- Adjacent to: PLAN-LB-40 (staged) edits other `manage-config` scripts (`_cmd_sync_defaults.py`, `_config_core.py`, `_config_defaults.py`, `_cmd_quality_phases.py`) and does not touch `_cmd_domain_narrow.py`; the executor template is untouched (its empty-value handling is already correct).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-42-outline-qgate-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
