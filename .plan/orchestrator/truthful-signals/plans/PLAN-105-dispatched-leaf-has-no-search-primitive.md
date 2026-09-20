# PLAN-105: A dispatched execution-context leaf has no documented working broad-search path

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from the PLAN-94 landing (#1040), inbox message 005.

## ⛔ RE-QUEUED 2026-07-29 — this was closed as superseded WITHOUT LANDING, and the gap is live

PR **#1046 was closed, never merged**. The plan was retired as superseded by the sibling epic's
PLAN-03 (`content-search-seam`) — but **PLAN-03 is itself still staged and unstarted**, so the gap
had no owner while continuing to bite. Operator-approved re-queue. Its stale `pr` / `landing` stamps
were cleared: this plan will produce a new PR and a new landing.

⭐ **New first-party evidence from PLAN-110's run (#1061), which is what forced the re-queue.** The
earlier spec argued the contradiction from documentation; this is the mechanism, observed:

- **`Grep` and `Glob` are unavailable to dispatched agents**, and **recursive `Bash` grep is
  hook-blocked**. That is the empty intersection, named concretely rather than inferred.
- It **blocked the phase-5 leaf outright** — not a degradation, a hard stop.
- It **fired again inside BOTH `lessons-capture` and the retrospective**, so the gap is not confined
  to implementation leaves: it reaches the finalize-time dispatched steps too.

⚠ **Three independent firings in a single plan run.** Re-verify each at HEAD before scoping — the
harness surface and hook set have both changed since #1046 — but scope for **at least** the leaf, the
lessons-capture, and the retrospective call sites. ⛔ **Treat those three as a SAMPLE**, not the
population: they are simply where this one run happened to look.

⚠ **Coordinate with the sibling before implementing.** `code-intelligence-substrate` PLAN-03
(`content-search-seam`) was judged to own the same seam. Confirm by SLUG whether it still does and
whether it has started — **two plans against one seam is the duplicate-work failure the disjointness
rule exists to prevent**, and this plan's own supersede history is what that judgement produced last
time.

## Objective

A dispatched `execution-context` leaf asked to perform a broad content sweep has, on paper, **no
permitted primitive that can perform it**. Three constraints hold simultaneously and their
intersection is empty, so every sweep-class deliverable currently completes by improvisation or
silently degrades to a sample. Close the contract by making one sanctioned primitive real and
documented, so a leaf that reports coverage has actually enumerated.

## The contradiction — OBSERVED across every dispatch in PR #1040's run

1. **`Grep` and `Glob` were denied to every dispatched subagent that session.** The
   `execution-context` agent declares them in `tools:`, but the runtime grant was narrower — which
   the agent body itself anticipates (*"the harness MAY deny them to a subagent"*).
2. **Bash `grep` / `find` are hook-blocked unconditionally**, by the project's "No shell file
   operations" hard rule and its enforcement hook — explicitly, per the agent body, *not* a fallback
   whether or not `Grep`/`Glob` were granted.
3. **The documented fallback cannot do the job.** `architecture find --pattern P` queries the
   structured inventory (registered scripts/modules); it does **not** do free-text content matching
   across markdown and AsciiDoc prose. `Read` scans inside an *already-known* file. Neither answers
   *"which documents in this repo restate sentence S"*.

PR #1040's D2 sweep completed **only via `git grep`** — Bash `git`, sanctioned by the explicit git
carve-out and therefore not caught by the file-operation hook. ⛔ **That path is nowhere documented as
the sweep primitive. It was improvised.**

⚠ The `execution-context` body's degradation instruction currently says the leaf *"MUST NOT silently
degrade to spot-checks — it returns the coverage gap to the orchestrator."* **Taken literally with no
working primitive, EVERY sweep-class dispatch should be bouncing back, and none are.**

## Deliverables

1. **D1 — GATE (mutates nothing): establish which of the three constraints is actually movable.**
   Determine whether the `Grep`/`Glob` denial is a harness-level grant that can be widened, or a
   fixed property the docs must accommodate. Verify constraint 2 against the live enforcement hook and
   constraint 3 against `architecture find`'s actual matching behaviour. Decide the primitive.
2. **D2 — make the chosen primitive real and documented.** Either (a) grant `Grep` to
   `execution-context` leaves so the declared and granted tool surfaces agree, or (b) document
   `git grep` as the sanctioned broad-content-sweep primitive in `persona-plan-marshall-agent`
   § "Bash: No file operations" as an explicit carve-out alongside the existing git carve-out.
3. **D3 — reconcile the degradation instruction.** The `execution-context` runtime-tool-availability
   section must name a primitive that actually works, and cross-reference D2's carve-out. A leaf that
   cannot enumerate must still have a real bounce-back path — but it must no longer be the *only*
   path.
4. **D4 — a test that fails pre-fix.** Pin the contract: assert the documented sweep primitive is
   named in both the agent body and the persona rule, and that the named primitive is one the leaf's
   granted surface can actually invoke. A doc-contract regression in the shape #1040 proved out.

## Claim Labels

- OBSERVED (first-party, PR #1040 run): all three constraints; the `git grep` improvisation; the
  degradation instruction's exact wording.
- HYPOTHESIS: that the `Grep` denial is a *harness grant* rather than an agent-declaration defect —
  confirm/refute at the `execution-context-{level}` agent definition § `tools:` against an observed
  denial in a live dispatch (verify-at-outline).
- Verify-first clause: **re-confirm at HEAD that `architecture find --pattern` still cannot do
  free-text prose matching.** If it can, D1's premise collapses and the plan re-scopes to "document
  the existing primitive" rather than adding one.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/agents/execution-context*.md` — the `tools:` block and
  the runtime-tool-availability section
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/**` — the
  "Bash: No file operations" rule
- HYPOTHESIS: the enforcement hook's blocked-command list (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none currently staged — `persona-plan-marshall-agent` is touched by no other queued plan
- Adjacent to: PLAN-97 (`inert-thinking-directives-in-dispatched-docs`) touches dispatched-doc prose
  but not the tool-grant surface. ⚠ **Re-check disjointness before pairing** — both edit agent-facing
  docs.

## ⭐ Why this is worth doing BEFORE more sweep-class plans are staged

A leaf returning *"42 candidates examined, 0 findings"* without a working search primitive emits a
confident coverage signal whose caveat — **the sweep was a sample, not an enumeration** — is invisible
at the return site. Same shape as the recorded **volume-read-as-coverage** archetype, but with a
*tooling* root cause rather than a reporting one: **the leaf could not have enumerated even if it
intended to.** The epic's remaining plans are largely sweep-class (doc-contract reconciliation,
SSOT-drift detection) and every one of them will hit this.

⚠ **Related but DISTINCT — do not merge:** the harness-denial of `Grep`/`Glob` is a *runtime grant*
problem; the hook-block of Bash `grep` is a *deliberate project rule working as designed*. The defect
is the absence of a documented intersection, not either constraint individually.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-105-dispatched-leaf-has-no-search-primitive.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
