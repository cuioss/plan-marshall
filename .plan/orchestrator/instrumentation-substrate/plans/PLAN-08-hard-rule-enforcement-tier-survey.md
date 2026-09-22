# PLAN-08: Hard-rule enforcement-tier survey

epic: instrumentation-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

Staged from inbox `next-level-002` during the 2026-09-14 drain, with `next-level-008` folded in.

## Objective

`CLAUDE.md` opens its hard-rule block by stating the rules exist "because Claude regularly violates them
despite softer guidance" — a written admission that a body of prose is carrying load prose cannot carry.
Survey that rule set and partition it by **where each rule's enforcement belongs**: deterministic code,
deletion, or prose that WS-01's harness must measure because nothing cheaper can decide it.

The value is in both currencies this epic tracks. A rule moved to a deterministic check produces a
violation count instead of an assertion. A rule that leaves the prose block shortens a payload present
in every model call on every runtime.

## Deliverables

1. A **derived** enumeration of the hard-rule population — every rule, from the stated source, with the
   completeness of the enumeration itself derived rather than asserted.
2. A per-rule classification on the three-way partition below, each cell carrying its evidence.
3. A derived violation record per rule: is there an actual violation history, or is this prose nobody
   has ever breached? ⛔ Answered from the repository's own recorded history, not from impression.
4. The routing verdict per rule, with a stated cost ceiling attached to every rule landing in the
   semantic cell.

## The three-way partition — `next-level-008`'s correction, and the reason this spec is shaped this way

`next-level-002` proposed a two-axis partition: *mechanically checkable* × *chronically violated*, routing
the intersection to hooks. ⛔ **`next-level-008` establishes that "mechanically checkable" silently
contains two tiers with different cost profiles, and that the coarse version would route this survey's
hardest cases into an unbounded per-tool-call model spend and call it enforcement.** The partition is
therefore three-way from the start:

| Cell | Route |
|------|-------|
| **Structural + chronically violated** | Deterministic check. Cheap, binary, no model call — and it shrinks the static prose tier. Plausible members: direct `.plan/` access, bare `gh`/`glab`, hard-coded `./pw`/`mvn`/`npm`, temp files outside `.plan/temp/`. |
| **Structural + never violated** | **Deletion candidate** from the static tier — the rule is carrying no load. ⭐ This cell is easy to forget and is half the token argument. |
| **Semantic — not regex-decidable** | ⛔ **NOT automatically enforcement material.** Each member needs a stated cost ceiling before it is gated, or it stays prose and becomes WS-01's measurement subject instead. Plausible members: "Workflow steps: no improvisation", "Structured queries first" — which is *why* they have survived as prose. |

The third row is the finding. A semantic gate is a model call on every intercepted tool call, on a
substrate already spending 48–81% of a run inside its verification layer (`next-level-005`, folded into
PLAN-01). The obvious move — put a judging model in front of the calls prose cannot gate — is the move
this repository's own cost record warns against.

## Claim Labels

- OBSERVED: `CLAUDE.md` § "Workflow Discipline (Hard Rules)" states the rules exist "because Claude
  regularly violates them despite softer guidance" — read at `CLAUDE.md`. This is the admission the
  survey acts on, and it is also an undederived empirical claim, which is why PLAN-02 baselines it.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md hard-rule opening sentence unmodified at HEAD, same verbatim quote as PLAN-01 idx1
- ⛔ OBSERVED — **a correction to `next-level-002`, made at drain time.** The message claimed
  plan-marshall "runs **one** hook family — the PreToolUse R1 group" and that "every other hard rule is
  exhortation". The machine-local `.claude/settings.local.json` in this checkout declares **six** hook
  events — `SessionStart`, `UserPromptSubmit`, `Notification`, `Stop`, `PostToolUse` (2 matcher groups)
  and `PreToolUse` (3 matcher groups). Measured in this checkout on 2026-09-14; re-confirmed at cleanup
  2026-09-22 — PostToolUse 2 ✓, PreToolUse 3 ✓, UserPromptSubmit 1, Notification 1, Stop 1, still six
  events total. ⚠ One addition the spec does not state: `SessionStart` itself now carries **3** matcher
  groups (two matcher-less + one `clear`) — a sub-count within the six events, not a seventh event. ⚠
  The message's **substance** survives — most hard rules have no mechanical enforcer, and the R1 family
  is context-gated to plan contexts so a fresh clone and every cloud session carry none of it — but its
  **count** is wrong, and deliverable 1 must derive the existing-enforcer population rather than
  inheriting the claim.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: six hook events re-confirmed at HEAD, exact matcher-group counts hold; SessionStart sub-count noted (3 groups, not a 7th event)
- HYPOTHESIS: The hook surface is machine-local only, so no enforcement travels with a clone — confirm/
  refute at `.claude/settings.local.json` versus the checked-in `.claude/` tree (verify-at-outline).
  ⛔ This decides whether a "deterministic check" verdict means anything portable, or whether it means
  "enforced on one developer's machine" — which would make the whole partition's value conditional.
  ⭐ **Corroborated at cleanup 2026-09-22.** The checked-in `.claude/settings.json` (read in full, 30
  lines) declares `extraKnownMarketplaces`, `enabledPlugins`, `permissions` — and NO `hooks` key at all.
  All six hook events live solely in the gitignored `.claude/settings.local.json`. Corroborated at
  `platform-runtime/standards/contract.md` § `project install-hook`: "`claude` resolves to
  `.claude/settings.local.json` in both install modes … because both payloads are machine-local operator
  wiring". **Consequence, absorbed into this spec's scope**: a "deterministic check" verdict for the
  structural+chronically-violated cell means "enforced on one developer's machine" UNLESS the routing
  verdict (deliverable 4) also addresses where enforcement is installed — the partition's value IS
  conditional, exactly as this claim feared. Deliverable 4 must state this explicitly per rule rather
  than leaving it implicit.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: checked-in .claude/settings.json carries no hooks key; all 6 events live only in gitignored settings.local.json; deliverable 4 must state the portability caveat per rule
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** The rule population is NOT bounded by
  `CLAUDE.md` — it extends into `persona-plan-marshall-agent`. Identical refutation to PLAN-02 idx 2, at
  the same named artifact: `persona-plan-marshall-agent/SKILL.md` § "Hard Rules (never override)" carries
  5 always-binding rules absent from `CLAUDE.md`, and `standards/tool-usage-patterns.md` carries 5 more.
  **Consequence, absorbed into this spec's scope**: deliverable 1's "derived enumeration of the hard-rule
  population" must span `CLAUDE.md` + the persona `SKILL.md` + `tool-usage-patterns.md`, and PLAN-02's
  enumeration must be reconciled against the same widened population rather than each plan deriving it
  twice and getting two answers.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: persona-plan-marshall-agent/SKILL.md Hard Rules (5 extra) + tool-usage-patterns.md (5 extra) absent from CLAUDE.md; deliverable 1 widened; identical refutation to PLAN-02 idx2, reconcile enumerations
- Verify-first clause: ⛔ **This is not a de-escalation sweep and may not grow into one.** Demotion moves
  a rule from prose to code. It does not soften the rule, and it does not touch the wording of any rule
  that stays. A plan that finds itself editing rule prose for emphasis has left its scope.

## Expected Surface

- OBSERVED: `CLAUDE.md` — the rule population, and the file a demoted rule is removed from
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/` — the hook seam and its
  enforcement standards, where a demoted rule's check would live
- OBSERVED: `test/plan-marshall/platform-runtime/` — the mirror test directory

⚠ `.claude/settings.local.json` is **deliberately not declared**: it is machine-local, git-ignored, and
absent from a fresh clone, so it is read as evidence and never written as a deliverable.

## Dependencies and Sequencing

- Depends on: none for the survey itself. The **semantic** cell's disposition depends on PLAN-01, which
  is what those rules would be measured by instead of gated.
- Overlaps with: PLAN-06, which also declares `platform-runtime/`. ⛔ Sequenced, never paired.
- Adjacent to: PLAN-02, which shares the rule-population hypothesis and baselines the same rules from
  the measurement side rather than the enforcement side. Reconcile the two enumerations rather than
  deriving the population twice and getting two answers.

## Non-Goals

⛔ No rule wording is edited. ⛔ No rule is deleted in this plan — the deletion cell produces
*candidates* with evidence, and the deletion itself is a separate decision. ⛔ No semantic gate is
implemented, whatever the survey concludes.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-08-hard-rule-enforcement-tier-survey.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
