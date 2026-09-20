> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The in-house build gate passes what CI would fail

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The local pre-push quality gate reports a **clean pass** for footprints CI then rejects. Each known
instance is a different hole in the same property: **the in-house gate's coverage is a strict subset of
CI's, and it never says so.**

Five holes have been observed, and they fall into **two independent dimensions** — which is the whole
reason this is a parity plan and not a configuration tweak:

**Scope holes** — the gate does not look at everything CI looks at:

- The `RUF` rule family is absent from the local ruff `select=`, so CI-visible findings are locally
  invisible.
- The pre-push gate lacks `mypy test` test-compile parity — and **the cost is already paid, not
  hypothetical**: the quality gate excludes `test/`, and three mypy errors reached `verify` as a direct
  result.
- The module-tests divergence gate has a **zero-scoped-modules / docs-only branch that resolves to a
  clean pass**.
- A non-bundle root footprint (`marketplace/targets/**`) is not escalated to the whole-tree gate.

**A staleness hole — sharper than all four, and it defeats a scope-only fix:**

- The local test-compile gate **passed in 2–5 seconds** across consecutive rounds. CI, on the same
  tree, checked 660 files and found **2 real type errors**. The cause was a stale **mypy incremental
  cache**: the gate answered *"nothing I have cached changed"* and that was consumed as *"the tree
  type-checks."*

⛔ **A coverage-parity fix that only widens what the gate examines does NOT close the fifth hole.** The
gate was looking at the right scope and answering from a cache. **Cache validity is a distinct
dimension from scope**, and the plan must treat it as one.

⭐ **And every one of these presents as a clean pass, never as an incomplete one.** That is the epic's
theme exactly: confident signal, suppressed caveat.

## Goal

The local gate's coverage matches CI's along both dimensions — scope and freshness — and where it
cannot check something, its own output says so, rather than reporting a pass that means less than it
appears to.

## Deliverables

1. **D1 — GATE: derive the parity population before fixing any instance.** Mutates nothing. Enumerate
   where local gate coverage and CI coverage diverge, **from the tool configuration on both sides**,
   and produce the parity table.
   *Done when:* the table exists, derived from configuration rather than from the list above, with the
   population it was derived from stated.
   ⛔ **Do NOT scope the fix to the five instances named above — they are the observed SAMPLE.** This
   project has repeatedly shipped a detector built from a sample rather than a derived population, and
   this deliverable exists specifically to break that habit.
   ⛔ **Treat cache validity as a distinct dimension in the table.** A parity table with only a scope
   axis cannot represent the fifth hole and will declare victory without closing it.
2. **D2 — Linter and type-check parity.** Close the scope divergences D1 finds on the tooling axis.
   *Done when:* the local rule set and the local file set both match CI's.
   ⚠ **Widening the file set and widening the rule set are independent holes.** Closing either alone
   still passes what CI fails — a whole-tree test-compile gate sees failures that type-checking `test/`
   alone cannot, and vice versa.
3. **D3 — Divergence-gate branch integrity.** Close the branches that resolve to a clean pass without
   having checked anything, and escalate non-bundle root footprints to the whole-tree gate.
   *Done when:* no branch of the gate can report clean without stating what it examined.
   ⛔ **DEDUP CONSTRAINT — read before scoping.** The zero-scoped-modules → docs-only → clean-pass
   branch is **the same conflation** as a sibling plan's finding that test-scope resolution returns a
   null target for Python source it cannot resolve: in both, *"no module matched"* and *"no tests
   needed"* are the same signal. **These are two consumers of one defect and must not be fixed twice in
   different shapes.** ⇒ **This plan and the fail-closed-signal-integrity plan are a serialization
   pair — never run concurrently.** Whichever reaches outline second re-grounds against the other's
   actual fix.
4. **D4 — Freshness: an implausibly fast gate is a failure signal.** Close the stale-cache hole, and
   add a **duration sanity check** so a gate that returns implausibly fast is treated as suspect rather
   than as reassurance.
   *Done when:* a stale cache can no longer produce a clean verdict, and an implausible duration is
   surfaced.
   ⭐ **This is the "never trust a routed build's outer status" archetype arriving through a cache
   rather than a router** — confident, fast, and repeated, read as reassurance. ⚠ The gate legitimately
   *can* be fast on a warm cache, so the check must distinguish plausible-fast from
   impossible-fast rather than simply flagging speed.
5. **D5 — The gate reports what it did NOT check.** Make the gate's own output name its coverage
   boundary, so a footprint it could not fully check is **distinguishable from one that genuinely
   passed**.
   *Done when:* a partially-checked footprint produces a distinguishable verdict, not a clean one.
   ⭐ **This is the through-line of D2–D4**, and it is the deliverable that still has value even if the
   individual holes are closed: the next hole will also present as a clean pass unless the gate can say
   "incomplete". Cross-link the epic's existing fail-closed discipline rather than re-authoring it.
6. **D6 — Tests, each verified to FAIL pre-fix.** One per closed hole, plus: a stale-cache scenario
   produces a non-clean verdict; a zero-scoped-modules footprint is distinguishable from a genuinely
   docs-only one; the parity table's population is derived and **asserted non-empty**.
   *Done when:* all hold and the report states each was seen red first.

Six deliverables, at the split presumption. **No split** — D1's table is the input to D2–D4, and D5 is
the property all of them share. Splitting would ship holes closed with no honest-coverage verdict, or
an honest verdict over holes still open.

## Out of scope

- **Changing what CI checks.** This plan moves the *local* gate toward CI, never the reverse. Loosening
  CI to match a weaker local gate would close the parity gap in exactly the wrong direction.
- **Promoting the landed lesson residues.** The source spec carried a deliverable to promote several
  lesson residues and retire the carried lessons. ⛔ **It is excluded here** because the lessons live in
  a `manage-lessons` store under `.plan/` — **git-ignored and absent from this clone** — so the
  identifiers cannot be resolved and their content cannot be recovered. A sibling plan in this epic
  owns residue promotion and carries the same constraint. Attempting it here would mean inventing
  rules from identifiers, which is worse than not promoting them.
- **The review-side half of the original finding.** This plan is the build-gate half of a split; the
  review half lives in another epic under its own id. Do not re-absorb it.

## Expected surface

- The local ruff and mypy configuration, and the CI workflow that must match it. **D1 names the exact
  files** — they are deliberately not guessed here.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`.
- The module-tests divergence-gate implementation — ⛔ **locate by SYMBOL, never by line number.**
- The corresponding gate tests.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count and
every file path. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The `RUF` rule family is absent from the local ruff `select=` | HYPOTHESIS | the local ruff configuration versus CI's — an asserted **absence**, verified as a presence |
| The pre-push gate lacks `mypy test` test-compile parity, and the quality gate excludes `test/` | HYPOTHESIS | the gate standard and the mypy invocation it describes |
| Three mypy errors reached `verify` as a direct result | HYPOTHESIS | git history for that change. ⚠ Recorded as motivation; **not reproducible from this clone** |
| The divergence gate has a zero-scoped-modules branch resolving to a clean pass | HYPOTHESIS | the divergence-gate implementation — **by symbol** |
| `marketplace/targets/**` is not escalated to the whole-tree gate | HYPOTHESIS | the footprint-classification path — an asserted **absence** |
| The local test-compile gate passed in 2–5 s while CI found 2 real type errors over 660 files, because of a stale mypy incremental cache | HYPOTHESIS | ⛔ **REPORTED, not re-derived**, and observed against an older bundle. **Confirm the mypy-incremental configuration at D1 before designing around it** — if incremental mode is already disabled, this hole may not exist and D4 re-scopes |
| The five holes are the whole population | HYPOTHESIS | ⛔ **D1's derivation.** They are the **sample**; treating them as the population is the mistake D1 exists to prevent |
| No existing mechanism already reports partial gate coverage | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — check before building D5 |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5's coverage-boundary output is text-whose-value-is-what-a-reader-does**, so it gets a **cold
  read**: show the Step 6 verification sub-agent a gate verdict for a partially-checked footprint, with
  no other context, and ask *"is it safe to push?"* The correct answer is **no, the gate did not check
  X**. If the reader takes it as a pass, the wording has reproduced the defect.
- ⛔ **D4's duration check must be demonstrated in both directions** — an implausibly fast run is
  flagged, and a legitimately warm-cache run is **not**. A check that flags every fast gate will be
  disabled within a week, which is worse than not having it.
- **D6's parity-table population must be asserted non-empty.** A parity table derived from nothing
  looks identical to perfect parity, and that is this epic's namesake defect appearing inside its own
  fix.
- **Re-verify the serialization pairing at outline** against the sibling plan's live state — not from
  the note above. A note written at staging time is a lead about the world at staging time.
- Python, configuration, and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Cross-epic coupling.** If D2 or D5 moves `pre-push-quality-gate.md`, that file is another epic's
  candidate home for a coverage-parity standard. **Name this plan's PR to that epic when it opens**, so
  the deferral is retired by checking rather than by remembering. ⛔ Re-verify the collision at outline
  against their live queue, not from this note.
- ⭐ **The dedup constraint in D3 was recorded at staging, not discovered at outline** — it was visible
  only because two signals were drained in one session, and it would not have survived a fresh context.
  That is why it is written down here in full rather than left to be rediscovered.
- ⛔ **Do not go looking for the orchestrator spec, the lessons store, the delegating message, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone.
  Everything needed is in this file.
