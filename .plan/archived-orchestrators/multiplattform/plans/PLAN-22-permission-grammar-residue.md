# PLAN-22: The permission-grammar residue and the direct-route false zero

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-22-permission-grammar-residue.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command; it never launches the
> plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and
> carries no brief, so every per-plan carry is authored here and nowhere else.

## Provenance

⚙️ **Staged at the PLAN-10 landing as the SECOND RESOLUTION of PLAN-10's split guard, not as new
scope.** PLAN-10 was widened five → seven on an operator decision, adding these two rows as D6 and
D7. The widening was recorded with an explicit escape: *"if the outline finds D6+D7 do not share
D1–D5's implementation shape, split them out as one spec rather than forcing the fit."* The plan
found exactly that — D1–D5 are layout/path relocations; these two are permission-grammar work, and
D2 below is a fail-closed dispatch change rather than a relocation — and took the escape. Splitting
them out of PLAN-10 removed their only home, so this spec IS that home. Source evidence:
`../reference/coupling-inventory.md` §B rows 5 and 6.

⚠️ **One discrepancy is unresolved and is NOT silently decided here.** PLAN-10's hand-off report
described the split as leaving "§C 5/6" open. D6/D7 are **§B** rows 5 and 6; §C 5 and 6 are D4's
ceiling constant (closed by PLAN-10) and D5's `detect_ide` (declined by PLAN-10 as a per-host
fact). This spec is scoped to the **§B** rows, which is what PLAN-10's merged diff supports — both
`permission_fix.py` and `permission_doctor.py` are absent from it. ⛔ If §C was genuinely meant,
this spec's scope changes and it must be re-staged rather than reinterpreted at outline.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

Two coupling-inventory rows have outlived every plan that came near them. Both were made unowned by
this epic's own landings — the `permission_fix.py` residue was orphaned when WS-01 closed, and
`permission_doctor`'s enforcement half was left explicitly open when PLAN-14 narrowed its row. They
are the last two rows in §B that no plan owns, and they share one shape: **the Claude permission
DSL living in a general script, where no path-literal sweep can find it.**

## Deliverables

1. **D1 — `permission_fix.py`'s permission-DSL residue.** `EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, the `Skill(…)` / `SlashCommand(…)` wildcard generators, `TIMESTAMP_PATTERN` / `DATE_PATTERN`, `normalize_path_perm` and `is_individual_script_permission` render and parse Claude permission-DSL strings inside a general script. The *default* permission set already renders behind the runtime; this residue does not. ⛔ It carries **no path literal**, which is why every `.claude`-literal sweep in this epic missed it — it is the same grammar-in-a-general-script class as the `workflow-permission-web` row PLAN-14 closed, and that row is the precedent to follow.
   *Done when:* the DSL grammar is reached through the runtime seam or honestly declined per the no-op policy; a test asserts a non-Claude target does not receive Claude permission-DSL output. ⛔ Re-derive the symbol set before acting — it is a lead from the inventory, not a measurement.
2. **D2 — `permission_doctor`'s direct-script route stops reporting a FALSE ZERO.** The rule-pack *declaration* is settled and was deliberately kept rather than moved (PLAN-14 landing: relocation considered and rejected). ⛔ **What remains is enforcement, not declaration** — the declaration is structural, not a dispatch path, so the direct-script `detect-*` route still runs the Claude rules against a non-Claude target and returns a clean zero. That is an unchecked negative presented as a checked one: the `could-not-evaluate reported as a clean zero` class this epic has now recorded eight times. The documented `platform_runtime permission analyze` path is already honest; only the direct route is not.
   *Done when:* the direct `detect-*` route fails closed on a non-Claude target — returning could-not-evaluate rather than zero — with a red-first test pinning the distinction between "checked, found nothing" and "could not check". ⛔ Governing authority: **ADR-019**.

⚙️ **Two deliverables. The split guard does not fire.**

## Out of Scope

- ⛔ **The three permission standards documents** (`permission-architecture.md`, `permission-validation-standards.md`, `permission-anti-patterns.md`). Their Claude-rule-pack provenance declaration is settled PLAN-14 work; D2 is enforcement only and must not reopen it.
- **Relocating the rule-pack knowledge.** Considered and rejected at the PLAN-14 landing — the knowledge remains by design, declared rather than moved.

## Claim Labels

- OBSERVED: both rows carry `— (unclaimed)` in the inventory's `Drawn by` column — read at `../reference/coupling-inventory.md` §B rows 5, 6. ⚠️ **That column is stale by construction** (see the epic's Open Defect), so an unclaimed marking is NOT evidence of unowned work on its own; these two were confirmed unowned by partitioning the corpus at `b64db6671`, not by reading the column.
- OBSERVED: neither file was touched by PLAN-10 — read from the merged diff of `a7ca9e491`, where both `permission_fix.py` and `permission_doctor.py` are absent. This is what makes them still open after the split.
- HYPOTHESIS: the `workflow-permission-web` row PLAN-14 closed is the nearest precedent for D1's remedy shape — confirm/refute at `landings/PLAN-14.md` and the `workflow-permission-web` scripts before scoping D1 (verify-at-outline).
- Verify-first clause: **D1's symbol set is a LEAD from the inventory, not a measurement.** The inventory names seven symbols; re-derive the actual set against HEAD before scoping. A refutation of the count or the membership loops back to re-scope, exactly as PLAN-10's own `generate_executor.py` count was refuted (2 claimed, 7 actual) at re-grounding.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py` — D2, **the direct-script `detect-*` dispatch path only**
- OBSERVED: `test/plan-marshall/tools-permission-fix/**`, `test/plan-marshall/tools-permission-doctor/**`

⚠️ All four entries were swept on disk at HEAD `b64db6671` before staging; all four resolve.
⛔ **If D1's remedy turns out to need a platform-runtime op** — as PLAN-10's D4 did — that is a
surface change of the same kind that produced this epic's worst under-declaration, and it updates
this section **in the same act**, before the code lands. See the epic's Open Defect on the in-flight
widening gap.

## Dependencies and Sequencing

- Depends on: **PLAN-10** (landed, #1449) — it is where these two deliverables were split from.
- Overlaps with: **PLAN-08** and **PLAN-14**, both LANDED, at exactly these two files. That overlap is expected and corroborating — those plans landed the registry and rule-pack work and left this residue. Neither is concurrent.
- Adjacent to: the three permission standards documents, which sit beside D2's file and are declared Out of Scope above.

## Hand-Off Command

⛔ This epic emits **OpenCode runbook commands**, not `/plan-marshall` pointers — the ledger's
EMIT FORM directive in `epic.md` § Queue annotations is authoritative and this section is a
convenience copy that loses on any divergence.

```text
Plan: .plan/local/oc-plans/multiplattform/220-permission-grammar-residue/plan.md
Staged orchestrator spec: .plan/orchestrator/multiplattform/plans/PLAN-22-permission-grammar-residue.md

Execute it per the runbook at .plan/local/opencode/RUNBOOK.md — it is the working contract
(Step 3 authors the plan from the staged spec; Steps 4–9 then apply). Do not delete the
orchestrator spec; it remains the source record.
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
