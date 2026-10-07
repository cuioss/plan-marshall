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
  --pattern "SessionStart"` returned `count: 46` over `file_count: 23` with clean coverage
  (re-measured at cleanup 2026-09-22, `files_scanned: 3097`; was `count: 42` / `file_count: 21` /
  `files_scanned: 5462` at staging), locating it at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_hook.py` and
  `claude_runtime.py`, with the contract at `platform-runtime/standards/contract.md` (15 matches,
  exact) and the architecture at `standards/terminal-title-architecture.md` (12 matches, exact). The
  seam is heavily tested: `test_claude_runtime.py` (49 matches), `test__claude_runtime_impl.py` (22).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: SessionStart search re-run: count 46/file_count 23 (was 42/21), all named locations hold with exact match counts
- ⛔ **REFUTED at cleanup 2026-09-22 (was OBSERVED).** The seam's present consumer is NOT only the
  terminal title. A second, independent consumer already exists: **session-id capture** —
  `platform-runtime/standards/contract.md` § `session capture` ("Persist the current platform session
  identifier via `manage-status`") and `persona-plan-marshall-agent/standards/tool-usage-patterns.md`
  § "Reading environment variables" ("captured at plan-init time by the platform-runtime `SessionStart`
  hook and APPENDED to `status.json` field `metadata.session_ids`"). Confirmed live:
  `.claude/settings.local.json` carries TWO matcher-less `SessionStart` entries — `claude_hook` (render)
  and `platform_runtime session capture`. On distribution the largest match counts also sit in the
  runtime/test files (49/23/22), above `terminal-title-architecture.md`'s 12. **Consequence, absorbed
  into this spec's scope**: the ⭐ conclusion — "this plan extends an existing, tested seam" — survives
  and is the load-bearing part; deliverable 1 must account for BOTH existing consumers when extending
  the event handling, not assume terminal-title is the only one sharing the hook.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: session-id capture is a second independent consumer (contract.md + tool-usage-patterns.md + two matcher-less SessionStart entries); ⭐ conclusion survives, deliverable 1 must account for both consumers
- HYPOTHESIS: The seam already fires on `compact` and only its payload needs extending, rather than the
  event set — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` (verify-at-outline).
  ⚠ **Unverifiable at cleanup 2026-09-22 — a strong lead, not a confirmation.** `contract.md` (1431
  lines, read in full) contains ZERO occurrences of `compact`; it documents a closed 9-entry render-event
  set naming `SessionStart:matcher-less` and `SessionStart:clear` — no `compact` entry. But
  `.claude/settings.local.json` carries two MATCHER-LESS `SessionStart` groups, and a matcher-less entry
  structurally fires on every `SessionStart` source including `compact`, so the hook process very likely
  already runs with no branch on source. Residue to settle at outline: the single `compact` occurrence
  each in `platform-runtime/scripts/_claude_runtime_impl.py` and
  `standards/terminal-title-architecture.md`. ⛔ This materially changes the plan's size: a payload
  change is small, an event-set change touches the runtime contract and every target that implements
  it — and that sizing question remains open pending the outline residue above.
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: contract.md read in full, zero compact occurrences, closed 9-entry event set with no compact entry; matcher-less SessionStart groups are a strong lead not a confirmation; outline residue named in spec text
- HYPOTHESIS: A live plan's id and phase are resolvable at hook time without loading a skill — confirm/
  refute at `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` (verify-at-outline). A
  hook that must load a skill to decide what to emit is too expensive to run on every session start.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: contract.md session resolve-plan + session render-title: deterministic runtime verbs, no skill load needed, phase-aware already at the hook path
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
