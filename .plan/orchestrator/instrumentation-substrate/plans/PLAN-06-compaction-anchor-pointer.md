# PLAN-06: Compaction anchor pointer

epic: instrumentation-substrate
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Project instructions survive compaction because they are re-supplied by the harness. **Live plan state
does not.** A session that compacts mid-plan loses the resume anchor and the current phase's contract
from context and must rediscover them, at the cost of re-reading the files that carried them. Re-inject
a *pointer* to that state through the `SessionStart` seam this repository already owns — the plan id,
its phase, and the one command that reads its anchor.

⛔ **A pointer, never a body.** Injection is resident context by definition: a body would spend exactly
the budget WS-03 exists to recover, and this repository has already recorded that the terminating move
for a restatement is to replace it with a pointer at its source.

## Deliverables

1. `SessionStart` handling extended to the `compact` event (and `clear`, if the seam does not already
   cover it), emitting a pointer to live plan state when a plan context exists.
2. A pointer payload with a hard ceiling on its size, stated in the code and enforced by a test — the
   property that keeps this plan from becoming the thing it was written to avoid.
3. Correct behaviour when there is **no** live plan: emit nothing. An injection that fires in every
   session, including the ones with nothing to point at, is a per-session tax for no benefit.
4. Tests covering the three cases: live plan present, no plan, and plan state unreadable.

## Claim Labels

- OBSERVED: A `SessionStart` seam already exists and is wired — `architecture search --content
  --pattern "SessionStart"` returned `count: 42` over `file_count: 21` with clean coverage
  (`files_scanned: 5462`, `unreadable: 0`), locating it at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_hook.py` and
  `claude_runtime.py`, with the contract at `platform-runtime/standards/contract.md` (15 matches) and
  the architecture at `standards/terminal-title-architecture.md` (12 matches). Measured in this session
  at `main` `77cb2e251`.
- OBSERVED: The seam's present consumer is the terminal title — the bulk of the matches sit in
  `terminal-title-architecture.md` and the title-token surface. ⭐ So this plan **extends an existing,
  tested seam** rather than introducing a hook, which is what keeps its cost low.
- HYPOTHESIS: The seam already fires on `compact` and only its payload needs extending, rather than the
  event set — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` (verify-at-outline).
  ⛔ This materially changes the plan's size: a payload change is small, an event-set change touches the
  runtime contract and every target that implements it.
- HYPOTHESIS: A live plan's id and phase are resolvable at hook time without loading a skill — confirm/
  refute at `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` (verify-at-outline). A
  hook that must load a skill to decide what to emit is too expensive to run on every session start.
- Verify-first clause: ⚠ **This plan's saving has never been independently sized, and PLAN-05 may
  refute its premise.** If PLAN-05 closes unfixed — concluding that always-resident bytes are not worth
  chasing — re-read this objective before scoping. The rediscovery cost avoided here is a different
  quantity from the description bytes PLAN-05 measures, so a PLAN-05 closure does not automatically
  kill this plan; it does mean nobody has yet shown this one pays for itself either.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/` — the seam, its scripts, and
  its contract
- OBSERVED: `test/plan-marshall/platform-runtime/` — the mirror test directory
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/` — touched only if resolving the
  live plan needs a read verb that does not exist (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-05, as an **evidence** gate rather than a technical one. Their surfaces are disjoint.
- Overlaps with: none declared.
- Adjacent to: the multi-target runtime implementations, which each implement the `SessionStart`
  contract. ⚠ A change to the event set rather than the payload reaches all of them; a payload change
  does not.

## Non-Goals

⛔ No instruction body, skill body, or standard is injected into any session. ⛔ The terminal-title
consumer's behaviour is not changed — this plan adds a second payload, it does not rework the first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-06-compaction-anchor-pointer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
