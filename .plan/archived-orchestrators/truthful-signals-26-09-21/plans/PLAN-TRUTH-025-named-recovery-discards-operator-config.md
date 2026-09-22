# PLAN-TRUTH-025: the named recovery case discards operator config it calls "always safe" to restore

epic: truthful-signals
workstream: WS-01

## Objective

Three workflow docs instruct the orchestrator, when a post-dispatch clean-main assertion reports
`.plan/marshal.json` dirty, to emit `Recovery: git checkout -- .plan/marshal.json` — justified in
prose by the claim that restoring it from HEAD **"is always safe"**. The justification is a non
sequitur, and the instruction is destructive: the guard establishes only that *the dispatched phase*
did not write the file, from which the docs conclude that *nobody* wrote it. The far likelier author
of a dirty `marshal.json` in the main checkout is **the operator**, whose uncommitted config edits
`git checkout --` destroys irrecoverably (unstaged, uncommitted, no reflog for worktree files).

This is the flagship epic archetype in its most dangerous form: a confident claim that suppresses
the caveat making it wrong, sanctioned in documentation, and wired to a destructive command.

## Provenance

Cross-repo hand-off from **API-Sheriff**, 2026-07-31 — the incident report on
`plan-35-bearer-proxied-benchmark-regression`, § 5 "third instance" and Recommendation 4. That report's
primary subject (an agent running `rm -rf` on an uninspected tree to make a clean-tree guard pass) is
**API-Sheriff's own**; this plan takes only the plan-marshall-owned half it surfaced.

⭐ The reporting session states it was itself exposed: the operator had uncommitted `marshal.json`
effort-level changes and had asked for them to be carried into the plan. Following the documented
recovery verbatim would have discarded them; they survived only because that session parked them to a
patch file and re-applied them in the worktree.

⚠ **Our own repository reproduces the exposure independently.** PR #1069 (`2d0229d1c`) was precisely a
set of operator-set `marshal.json` effort changes, which necessarily sat uncommitted in the main
checkout before landing. Any phase-boundary assertion firing in that window would have printed the
recovery line.

## Deliverables

1. **D0 — GATE (mutates nothing): derive the population of "safe to delete / safe to revert"
   assertions across the bundle tree.** The three known sites are a **SAMPLE**, not the population —
   they were found by grepping one command form. ⛔ Do not fix the three and declare the class closed.
   Derive by the *assertion shape* (a doc asserting an artifact is safe to discard/restore/delete),
   not by the command string. **Report population size and hit count separately.**
2. **D1 — replace the false inference at all three sites.** The valid inference from "phase N MUST NOT
   have touched it" is "**something other than phase N wrote it**" — which mandates *inspection*, not
   restoration. Recovery must surface `git diff -- .plan/marshal.json` and require an explicit operator
   disposition before any discard. ⛔ **The word "always" must not survive** in any of the three
   justifications.
3. **D2 — collapse the triplet.** The three blocks are near-identical copies of one contract restated
   per phase. Per the epic's standing rule — **where a copy exists, delete the copy, do not
   synchronise it** — the contract becomes ONE authority the three sites reference. Fixing three
   copies in parallel is the defect's own recurrence shape.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) The recovery text emitted for a dirty
   `marshal.json` does not instruct an unconditional discard. (b) The D0 population derivation is
   asserted non-empty and contains the three known members. ⚠ A test that pins only the three known
   sites re-creates the sample-as-population error D0 exists to prevent.

Four deliverables — under the ~6 split guard, no split evaluation owed.

## Claim Labels

- **OBSERVED**: all three sites exist and carry the destructive recovery line — read at
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § "Named recovery
  case — `.plan/marshal.json`" (phase-2-refine boundary), and at
  `.../workflow/planning-outline.md` § the same heading, **twice** (the 4-plan and 5-execute
  boundaries). Verified by direct read on 2026-07-31 against repo source, not against the plugin cache.
- **OBSERVED**: the "always safe" wording, and the inference chain that produces it, appear in all
  three justification paragraphs — each reasons from the phase's write-prohibition to the safety of
  discarding. `planning.md`'s copy additionally contains a grammatical defect ("a spurious write that
  safe to revert"), evidence the three copies drifted rather than being generated.
- **OBSERVED**: the operator-config exposure is real in THIS repo — PR #1069 landed operator-set
  `marshal.json` effort changes, read from `git show 2d0229d1c`.
- **HYPOTHESIS**: the three sites are the whole population of this assertion class — **confirm/refute
  at D0. Do not assume it; the epic's standing rule is that a stated count states a sample.**
  Confirm/refute artifact: the derived assertion-shape sweep over `marketplace/bundles/**`.
- **HYPOTHESIS**: no automated caller executes the recovery line today (it is emitted as operator-facing
  text). **Confirm/refute at D1** — severity rises sharply if anything consumes it programmatically.
  Confirm/refute artifact: consumers of the `refine_contract_violation` / outline / plan
  contract-violation TOON blocks.
- **Verify-first clause**: the claim that `marshal.json` is "never a phase output artifact" must be
  re-read against the phase Enforcement blocks the docs cite before D1 re-words them — the fix depends
  on *why* the prohibition exists, and a refutation there re-scopes D1.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` —
  § "Named recovery case — `.plan/marshal.json`" (located by heading, not line number)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` —
  the same heading at two distinct phase boundaries
- **HYPOTHESIS**: further sites surfaced by D0 (verify-at-outline — this is the whole point of D0)
- **HYPOTHESIS**: `test/plan-marshall/plan-marshall/**` for D3 (verify-at-outline)

## Dependencies and Sequencing

- **Depends on**: none. Both former blockers of this surface (PLAN-57 #1068, PLAN-202 #1066) shipped.
- **Overlaps with**: ⚠ **PLAN-TRUTH-002** declares itself *exclusive* against anything touching
  dispatched workflow docs — `planning.md` and `planning-outline.md` are exactly that. **These two
  cannot run concurrently.** Sequence deliberately; neither blocks the other permanently.
- **Archetype sibling — PLAN-TRUTH-017**, `detect-artifacts` offering a live audit trail as
  safe-to-delete. ⭐ **Same archetype, different surface**: a tool/doc asserting something is safe to
  discard when it is not. Deliberately **NOT merged** — different bundles, different mechanisms, and
  TRUTH-017 already carries five deliverables. ⇒ **D0's population derivation should hand its results
  to TRUTH-017** rather than either plan re-deriving the class. If D0 finds the two surfaces share a
  root, say so and re-scope rather than fixing twice.
- **Adjacent to**: `phase-2-refine` / `phase-3-outline` / `phase-4-plan` Enforcement blocks — read as
  the source of the write-prohibition premise, but **not modified** by this plan.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-025-named-recovery-discards-operator-config.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
