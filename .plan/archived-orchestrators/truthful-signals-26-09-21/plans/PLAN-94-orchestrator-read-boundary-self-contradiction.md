# PLAN-94: The orchestrator's read boundary contradicts itself, and the strict half makes its own verbs unperformable

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`orchestration-model.md` § Carve-Outs states two rules about orchestrator reads that directly
contradict each other, in the same section, four lines apart. The permissive rule is the correct one:
the strict rule, read literally, makes the `analyze` verb's own mandatory ground-truth step
unperformable. Because the contradiction is unresolvable from the text, a session complies with
whichever half it happens to recall — and the observed cost is real: verification work that the
standard *requires* has twice been declined by citing the half that forbids it. This plan settles the
boundary in one direction, states the mechanism that makes it safe, and removes the losing prose.

## The contradiction — OBSERVED, first-party at HEAD

Both rules live in `persona-marshall-orchestrator/standards/orchestration-model.md` § Carve-Outs:

- **Strict half** (`:91`, closing the direct-file-access carve-out): *"Any Read/Write/Edit outside the
  epic's own `{slug}/` tree — repository source, another epic's tree, `.plan/local/plans/` — is out of
  bounds for the orchestrator."*
- **Permissive half** (`:99`, the small-ops carve-out, nine lines later): *"**Read-only analysis** —
  reading code, artifacts, PRs, logs, and pasted content to verify claims and reconcile the ledger."*

`:99` names *code* and *artifacts* as permitted reads. `:91` names *repository source* and
`.plan/local/plans/` as forbidden. **There is no reading under which both hold.** Neither cites the
other, neither is scoped as an exception to the other, and no precedence rule exists in the document —
the "when a workflow doc and this standard disagree, this standard wins" clause governs doc-vs-standard
conflicts, not a standard-internal one.

## Why the permissive half must win — OBSERVED

This is not a coin-flip between two defensible rules. The strict half makes the orchestrator's own
documented obligations impossible:

1. **`analyze.md` Step 2 is mandatory and requires forbidden reads.** *"Before recording anything,
   corroborate each material claim against actual ground truth — the real diff, the real PR state, the
   real artifacts, the real code."* Under `:91`, reading the real code is out of bounds. The verb's
   central discipline cannot be executed.
2. **`analyze.md` Step 4 names the forbidden path explicitly.** Its dispatchable corroboration covers
   *"the plan's on-disk artifacts"*, and the on-disk input mode (§ The four input modes) is defined as
   *"a finished plan's artifacts named by the operator (archived plan dir, metrics, execution
   manifest)"* — i.e. `.plan/local/plans/**` and its archive, the exact tree `:91` forbids.
3. **The verify-first contract presumes it.** *"The consuming phase verifies against the implementing
   source"*, and the orchestrator's own claims are explicitly in scope of that contract.

So the strict half is not merely stricter — it is **wrong**, and it is the half that must be corrected.

## Observed cost — this is not hypothetical

- **2026-07-26, PLAN-57.** A session declined to inspect a live plan's `request.md` and recorded the
  refusal in the spec: *"Orchestrator boundary note: `.plan/local/plans/**` is outside the
  orchestrator's carve-out, so the running plan's `request.md` was NOT inspected."* The claim it would
  have settled — defect 5, the truncated-scored-body hypothesis — **is still unconfirmed today**,
  blocking a deliverable in a staged plan.
- **2026-07-28, this epic.** In ONE session the orchestrator read repository source freely to
  corroborate two operator reports (`_cmd_planning_lane.py`, `phase-1-init/SKILL.md`), then declined to
  read a plan's `status.json` citing the strict half — **both halves applied within minutes, to
  materially similar reads.** The operator identified the inconsistency; the orchestrator had not.
  The plan-lane data was then obtained through `manage-status metadata`, a *script* read of the very
  same file, which the strict half does not cover — demonstrating that the prose forbids the tool
  while permitting the identical access through a different seam.

⚠ **This is the epic's own archetype, one level up.** A boundary that reads as authoritative, is cited
in refusals, and cannot actually be complied with. Adjacent to the vacuous-authority family
(a documented owner that implements nothing) but distinct: here the documented rule is *enforceable*
and *enforced*, and it is the enforcement that causes the harm.

## Deliverables

1. **D1 — settle the boundary and state the mechanism that makes it safe.** Decide the exact rule.
   Recommended shape, for D1 to confirm or overturn: **reads are unrestricted; WRITES are bounded to
   the epic tree.** That is what the two carve-outs were plainly trying to say jointly, it is what the
   `analyze` verb needs, and the prime directive already bars the orchestrator from *acting* on what it
   reads. D1 must state the residual risk it accepts — an orchestrator that reads widely burns context
   and may re-derive what a plan should derive — and name the countervailing rule that bounds it (the
   small-ops "anything larger becomes a plan" threshold at `:101` is the existing candidate).
   ⚠ **D1 must NOT resolve this by tightening `:99`.** Deleting the read permission would make Step 2
   of `analyze` unperformable in the other direction and is the strictly worse arm.
2. **D2 — rewrite `:82-101` so the two carve-outs state one coherent rule.** The direct-file-access
   carve-out becomes a *write* boundary; the small-ops read permission stays and is cross-referenced
   from it so a future reader cannot encounter one without the other. Remove the contradicting clause
   rather than annotating it (house rule: no transitionary prose).
3. **D3 — sweep the consumers.** `marshall-orchestrator/SKILL.md` § Enforcement restates the strict
   half (*"Never Read/Write/Edit outside the epic's own tree"*) and must move in lock-step, or the
   contradiction simply relocates. HYPOTHESIS: `persona-marshall-orchestrator/SKILL.md` identity
   attribute 3 restates it too. Enumerate the restatements **population-derived** — grep the marketplace
   for the clause rather than fixing the three sites this spec happens to name.
4. **D4 — a regression that fails pre-fix.** The defect is prose, so the test targets the property, not
   the wording: assert that no marketplace document states an orchestrator read prohibition covering a
   path that another states is readable. Shape is D1's call; a doc-contract test in the plugin-doctor
   family is the likely home. **Verify it FAILS against HEAD** before the fix — the test-pins-the-defect
   archetype has shipped twice in this epic.

Four deliverables, under the split guard.

## Claim Labels

- OBSERVED: the two contradicting clauses — read first-party 2026-07-28 at
  `persona-marshall-orchestrator/standards/orchestration-model.md` `:91` and `:99`.
- OBSERVED: `analyze.md` Step 2 / Step 4 / § The four input modes require reads `:91` forbids — read
  first-party at `marshall-orchestrator/workflow/analyze.md`.
- OBSERVED: the SKILL.md Enforcement restatement — read first-party at
  `marshall-orchestrator/SKILL.md` § Enforcement.
- OBSERVED: the 2026-07-26 declined read — quoted from
  `plans/PLAN-57-lane-router-scale-blind-false-negative.md` § "Third live instance".
- OBSERVED: the 2026-07-28 both-halves-in-one-session inconsistency — this orchestrator's own conduct,
  logged in `logs/decision.log` for this date.
- HYPOTHESIS: `persona-marshall-orchestrator/SKILL.md` identity attribute 3 carries a third
  restatement — confirm/refute at that file § Identity Attributes item 3 (verify-at-outline).
- HYPOTHESIS: no OTHER standard-internal contradiction of this shape exists in the orchestrator
  document set — confirm/refute by D3's population-derived sweep (verify-at-outline). **An asserted
  absence: verify it, do not assume it.**
- Verify-first clause: D1 must re-read `:82-101` at HEAD before scoping. If a landing between staging
  and outline has already reconciled the two clauses, this plan is REFUTED and must be closed rather
  than re-implemented.

## Expected Surface

- OBSERVED: `plan-marshall/skills/persona-marshall-orchestrator/standards/orchestration-model.md`
  `:82-101` — § Carve-Outs, both sub-sections.
- OBSERVED: `plan-marshall/skills/marshall-orchestrator/SKILL.md` — § Enforcement, the
  prohibited-actions bullet restating the strict half.
- HYPOTHESIS: `plan-marshall/skills/persona-marshall-orchestrator/SKILL.md` — identity attribute 3
  (verify-at-outline).
- HYPOTHESIS: additional restatements found by D3's sweep — enumerated at outline, not guessed here.
- OBSERVED: tests under `test/plan-marshall/**` — exact home is D4's call.

**Disjointness:** `persona-marshall-orchestrator` + `marshall-orchestrator` (docs only, plus one test).
⚠ **OVERLAPS PLAN-93** (`marshall-orchestrator`, in flight) and **PLAN-49** (renames both orchestrator
skills). Do not pair with either. PLAN-93 touches `_orchestrator_inbox.py` and the `inbox archive`
docs while this touches SKILL.md § Enforcement — plausibly file-disjoint within the same bundle, but
**verify against PLAN-93's real touched files before pairing**, and prefer sequencing after it lands.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-93 (same bundle, in flight — sequence after), PLAN-49 (renames both skills —
  PLAN-49 stays last regardless).
- Adjacent to: PLAN-57, which is the plan whose defect-5 verification the strict half blocked. This
  plan unblocks that verification but does **not** perform it — PLAN-57 keeps it.
- ⚠ Note for whoever emits this: while PLAN-93 is launched, this plan is NOT emittable.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-94-orchestrator-read-boundary-self-contradiction.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
