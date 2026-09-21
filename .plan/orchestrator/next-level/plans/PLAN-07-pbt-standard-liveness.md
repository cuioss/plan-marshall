# PLAN-07: Property-based-testing standard liveness

epic: next-level
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Two skills document property-based testing as a standard. The library it names appears in no source
file, no test file, and no dependency declaration. The standard therefore reads as binding while its
own stated precondition has never once been met — the **vacuous-authority** archetype (n=5 in the
WS-10 defect list) sitting inside the testing standards themselves.

Settle it in one of the two honest directions: adopt the dependency and make the standard live, or
demote the section to a technique that is available and not adopted here. Then derive whether any
sibling testing standard is in the same state, because one confirmed instance of a recurring archetype
is a reason to enumerate, not a reason to stop.

## Deliverables

1. A decision between adoption and demotion, recorded with its reasoning and its cost.
2. The decision applied to both skills that carry the standard, in lock-step — a demotion applied to
   one and not the other would leave the corpus contradicting itself.
3. If adoption: the dependency declared, and at least one real property-based test over a function the
   standard's own discriminator selects — so the precondition is met in fact and not only in
   configuration.
4. A **derived** enumeration of every other prescriptive technique in the testing standards whose
   precondition is likewise unmet. ⛔ Derived from an independent sweep of the standards, never from a
   spot-check: "no others" is a completeness claim and this repository's own rule is that such a claim
   must come from an enumeration.

## Claim Labels

- OBSERVED: `hypothesis` appears in **documentation only** — `architecture search --content --pattern
  "from hypothesis|import hypothesis|@given"` returned `count: 6` over `file_count: 3`, every hit in a
  markdown doc (`pm-dev-python/skills/pytest-testing/standards/testing-pytest.md` ×7,
  `pytest-testing/SKILL.md`, `plan-marshall/skills/recipe-lesson-cleanup/SKILL.md`), with **zero**
  source or test matches. Coverage clean: `files_scanned: 5462`, `unreadable: 0`, `truncated: false`.
  Measured in this session at `main` `77cb2e251`.
- OBSERVED: The standard is carried by two skills — `plan-marshall:persona-module-tester` (whose
  registered description names "property-based testing") and `pm-dev-python:pytest-testing` (whose
  description names "property-based / adversarial testing (Hypothesis)"). Both are registered
  components, so the prescription is advertised in the always-resident surface.
- HYPOTHESIS: `hypothesis` is absent from the dependency declaration — confirm/refute at
  `pyproject.toml` (verify-at-outline). Carried from absorbed inbox message `truthful-signals-010`
  finding 4; the source-tree half was re-derived in this session, the dependency half was not.
- OBSERVED: `pytest-testing/SKILL.md` marks the technique as carrying a "third-party `hypothesis` dep —
  user-approval" qualifier, which is why the decision has a real cost and is not a formality: adoption
  means asking for that approval.
- HYPOTHESIS: An independent team converged on materially the same scoping discriminator this
  repository uses — gating property-based testing to pure functions and serialization round-trips
  rather than mandating it blanket — confirm/refute against the recorded analysis in absorbed inbox
  message `truthful-signals-010` finding 4 (verify-at-outline). ⛔ **This is corroboration, not
  authority**, and it does exactly one thing: it refutes deletion. It does not choose between adoption
  and demotion.
- Verify-first clause: ⛔ **Deleting the standard is refuted before it is proposed.** The content is
  independently corroborated rather than idiosyncratic, and the technique defends against a defect
  shape this repository keeps re-introducing — a model changing source or assertions after the fact so
  the coverage reads correctly, which is the mechanism behind both the test-pins-the-defect and the
  vacuous-guard archetypes. Whichever direction is chosen, that rationale belongs in the standard.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-dev-python/skills/pytest-testing/` — one of the two skills carrying
  the standard
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-module-tester/` — the other
- OBSERVED: `pyproject.toml` — the dependency declaration, touched only on the adoption branch
- HYPOTHESIS: `test/pm-dev-python/` — the single demonstrating property-based test, only on the
  adoption branch (verify-at-outline)

⚠ The demonstrating test is scoped to one bundle's mirror directory rather than declared as `test/`.
A bare `test/` claim contains every other plan's test directory by containment and would serialize the
whole epic behind this row. ⛔ If outline finds the demonstrating case belongs elsewhere, widen this
entry deliberately and re-check disjointness — do not widen it to `test/`.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none. Surface-disjoint from every other row in this epic, which makes it the safest
  candidate to pair if the parallelization scope is ever raised above 1.
- Adjacent to: WS-01's conformance work, which is thematically the same question — a claim nothing
  checks — on a different surface. No shared files; neither blocks the other.

## Non-Goals

⛔ The standard is not deleted (see the verify-first clause). ⛔ No unrelated testing guidance is
rewritten, and no existing test is converted to a property-based one beyond the single demonstrating
case on the adoption branch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/next-level/plans/PLAN-07-pbt-standard-liveness.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
