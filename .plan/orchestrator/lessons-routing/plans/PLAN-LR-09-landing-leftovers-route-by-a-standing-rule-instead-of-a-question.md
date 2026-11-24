# PLAN-LR-09: The leftovers of a landing analysis route by a standing fold-by-content rule instead of one operator question per finding

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

After every landing the three-layer analysis produces leftovers (layer-3 defects, layer-2 test gaps, layer-1 spec flaws) of the landed plan. Today each batch stops at the operator: `analyze.md` says a layer-3 defect "becomes a staged fix-plan spec only on the operator's word", and the Step 5b Fold disposition applies only to a message, with the orchestrator left to choose the target spec. This plan makes the operator's standing rule mechanical: a leftover goes, without asking, into the staged plan that fits by content as a new deliverable (same edit as its Expected Surface, claims stamped through `corpus set-verdict`), or into a held-back follow-up container plan for the module when none fits or the fitting plan already holds more than 10 deliverables; the operator is asked only at a real fork. Source: change request `libraries-initial-implementation-079` (operator of that epic, priority high; staged here on the operator's word during the 2026-11-24 drain).

⚠ **Inbound Routing check owed at outline.** This epic owns where a finding goes and whether it survives; the request is mainly `plan-orchestrator` analyze / handle-open behaviour about routing a landing's leftovers into staged specs, which may belong to the orchestrator-tooling epic rather than here. The operator staged it here on 2026-11-24 regardless; outline settles the ownership question against the Inbound Routing rule and `corpus cross-check` and records the result, and a finding that it belongs elsewhere is a reason to hand the spec over, not to continue silently.

## Deliverables

Five deliverables, matching the request's five changes.

1. **Fit predicate.** A verb (suggested `orchestrator corpus route --slug S --paths ... [--module M]`) returning, for a set of repository paths or a module, the staged specs whose declared surface covers them, each with its queue status, `deliverables_total`, whether it is frozen (`launched`, `running`, `parked` with a worktree) and whether it is held back. The rule's choice (a staged, not frozen, fitting plan with at most 10 deliverables; otherwise the module's container) is then a read.
   - Skills: none
   - Persona: implementer
2. **Deliverable-append write.** A verb (suggested `orchestrator corpus fold --slug S --plan PLAN-NN --deliverable-file F --surface path...`) that appends the numbered deliverable with its `Skills:` and `Persona:` lines, adds the named paths to `## Expected Surface` in the same write, refuses a frozen plan, and returns the new `claimed_count` and `deliverables_total`.
   - Skills: none
   - Persona: implementer
3. **Container-plan template and held-back marker.** `templates/plan-spec.md` gets a container variant (objective naming the module group, "later leftovers fold in until launch", the hold-back line). The held-back state is a field of the queue row, not prose in the spec, so `next` refuses it mechanically and `corpus cross-check` reports it as held back, not indeterminate. A configured limit for the deliverable bound (default 10; the scope-bloat guard of about six for an emitted plan stays a separate recorded decision).
   - Skills: none
   - Persona: implementer
4. **Verb text.** `analyze.md` Step 4 "Routing what the three-layer analysis finds" replaces "staged only on the operator's word" with the rule where an epic carries it (an epic-level standing decision, `routing_rule: fold-by-content`, in `status.json` metadata or `epic.md`) and keeps the question for a real fork (a fix that changes a documented behaviour, an owner decision, a finding touching two modules). `handle-open` applies the same rule to Open Defects marked "not yet routed"; `lessons` and `next` read the held-back marker.
   - Skills: none
   - Persona: documenter
5. **Claims and tests.** A folded deliverable's `OBSERVED` claims are stamped through `corpus set-verdict` by the same verb call when the folding run re-read them, never by an edit of the spec text; tests for the acceptance cases.
   - Skills: none
   - Persona: module-tester

Acceptance, from the request: a landing whose layer-3 findings all lie in one module while one staged plan with five deliverables is the only staged plan for it appends a deliverable to that plan, extends its Expected Surface when the paths were not declared, stamps the claims, writes the Open Defect entry and asks nothing; the same findings with the staged plan at 11 deliverables stage or extend the module's container instead; a finding whose only fitting plan is `running` goes to the container; a finding that changes a documented behaviour or needs an owner decision still produces the operator question, once; `next` never emits a held-back container.

## Standing Constraints

- Staging a fix plan never launches or emits it.
- The rule applies only where an epic carries the standing decision; an epic without it keeps today's behaviour.
- The routing is recorded as an Open Defect naming the plan and the deliverable, and as one decision-log line per finding group.
- Re-ground the request's description of `analyze.md`, `corpus surfaces` and `corpus spec-skills` against HEAD before scoping; they are the sender's reading at plugin 0.1.2184.

## Claim Labels

- OBSERVED: `analyze.md` says a layer-3 defect "becomes a staged fix-plan spec only on the operator's word" — read at `plan-orchestrator/workflow/analyze.md` § "Routing what the three-layer analysis finds".
- HYPOTHESIS: `corpus surfaces` and `corpus spec-skills` already publish `derivation_status`, the claimed paths and `deliverables_total`, so a fit predicate needs no new reader — confirm or refute at `plan-orchestrator/scripts/orchestrator.py` § corpus (verify-at-outline).
- HYPOTHESIS: no queue-row field marks a plan held back, and `next` has no mechanical refusal for one — confirm or refute at `manage-status/scripts/_orchestrator_ledger.py` § row fields and `plan-orchestrator/workflow/orchestrate.md` § Step 4 (verify-at-outline).
- Verify-first clause: the Inbound Routing ownership question above.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/handle-open.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_orchestrator_ledger.py` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/**` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-LR-08` (same `analyze.md`, `orchestrator.py` and `SKILL.md`; serialise, do not merge edits), and the `plan-orchestrator` surface other epics declare (`corpus cross-check` at emit time).
- Adjacent to: the `manage-status` ledger layout, where the held-back field would live.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/lessons-routing/plans/PLAN-LR-09-landing-leftovers-route-by-a-standing-rule-instead-of-a-question.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.
