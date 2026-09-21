# PLAN-01: Script surfaces refuse input they cannot honour

epic: tooling-truthfulness
workstream: WS-02

> Staged plan spec — one shippable unit of work. This spec is SELF-SUFFICIENT: the emitted
> command is a one-line pointer and carries no brief, so every per-plan carry is authored here.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** a fix that cannot be shown to FAIL before it lands is the vacuous pin this epic exists to remove. Every guard is red-first.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it. ⛔ A surface expansion updates this section IN THE SAME ACT — disclosure in a report is NOT declaration, and the gate reads only the declaration.

## Objective

Two orchestrator script surfaces accept input they cannot honour and report success. Both were
found by USING them during the `multiplattform` epic, not by reading them — the documentation
describes both correctly and prevented neither. `queue --transition` writes any string to a row's
status field; `corpus set-verdict --claim-index` addresses a claim by an ordinal whose base and
population no consumer surfaces. Make each surface refuse what it cannot honour, or report what it
actually addressed.

## Deliverables

1. **D1 — `queue --transition` validates the status token.** The verb accepts an arbitrary string and writes it to `plans[].status`. ⛔ **CONFIRMED LIVE, destructively:** a probe set a real landed row to `bogus-token-xyz` and the call returned `status: success`; the row was restored by hand. A status value outside the vocabulary silently breaks every consumer that groups by status — `resume-summary` renders it as a residual per-status line, and `no_terminal_in_live_queue` cannot classify it.
   *Done when:* an out-of-vocabulary token is refused with a distinct error naming the accepted set, the vocabulary has ONE definition the verb reads rather than a second copy, and a red-first test drives the refusal AND a matched positive control (every legal token still transitions).
2. **D2 — `corpus set-verdict --claim-index` is addressable without guessing.** The index is positional over ALL top-level `- ` bullets of `## Claim Labels`, but a section may interleave non-claim bullets (`⚙️ RE-SCOPED` narrative), so an enumeration by claim-type prefix silently shifts every later ordinal. ⛔ **CONFIRMED LIVE:** five verdicts landed on the wrong claims in one cleanup pass, overwriting two settled RE-SCOPED verdicts that had to be re-derived from source.
   *Done when:* a caller can determine the correct index WITHOUT re-implementing the parse — either a read surface enumerates claims with their indices, or the stamp is addressable by something stable that is not a positional ordinal. ⛔ Whichever is chosen, state why in the PR body; a docstring naming the base is NOT sufficient, because the existing documentation already describes the surface correctly and did not prevent the failure.

## Claim Labels

- OBSERVED: `queue --transition` accepted `bogus-token-xyz` on a live row and returned success — observed directly 2026-09-10, row restored. Reproduce before scoping; do NOT reproduce against a live ledger row.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: orchestrator.py cmd_queue writes args.status via _set_row_field(row,'status',value) with NO status-vocabulary validation at :1161-1164; TERMINAL_PLAN_STATUSES=('shipped','landed') is the only status constant and is not applied to the transition write path
- OBSERVED: the claim index is positional over all `^- ` bullets, and `PLAN-07-runtime-fact-prose-and-single-sources.md` in the `multiplattform` corpus is a real spec whose section interleaves two `⚙️` bullets at positions 0 and 2 — read at that file § Claim Labels.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: multiplattform/plans/PLAN-07-runtime-fact-prose-and-single-sources.md Claim Labels interleaves two top-level RE-SCOPED bullets at :61 and :65 among claim bullets; ordinal claim addressing over all ^- bullets would shift
- HYPOTHESIS: the status vocabulary has a single existing definition somewhere in the orchestrator scripts that D1 can read rather than restate — confirm/refute at `orchestrator.py` before introducing a constant (verify-at-outline). ⛔ If no single definition exists, creating one is part of D1; creating a SECOND one is not.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: orchestrator.py:223 TERMINAL_PLAN_STATUSES=('shipped','landed') is a single status-vocabulary definition the transition path does NOT validate against; no other status constant exists in the file
- Verify-first clause: **D2's remedy shape is deliberately open.** A read surface and a stable address are different designs with different consumers. Enumerate the callers of `set-verdict` before choosing; a refutation of the assumption that callers can accept a new addressing form loops back to re-scope.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: D2's remedy shape (read surface vs stable address) is the launched plan's outline decision after enumerating set-verdict callers - not source-settleable

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — D1, D2
- OBSERVED: `test/plan-marshall/plan-orchestrator/**` — the red-first guards for both

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-04** and **PLAN-05**, which also touch `orchestrator.py`. ⛔ Not concurrent with either.
- Adjacent to: `epic_spec_parser.py` (the `## Claim Labels` reader). D2 may need to READ it; it does not edit it — that file is PLAN-04's neighbourhood.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-01-script-surface-validation.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
