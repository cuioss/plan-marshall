# PLAN-NN: {Plan Title}

epic: {slug}
workstream: WS-NN

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

{2-4 sentences: what this plan ships and why, phrased so it can be pasted as the
/plan-marshall request narrative.}

## Deliverables

{Enumerate the expected deliverables. A spec approaching ~6 deliverables is
presumptively split before its command is emitted — record the split-or-proceed
rationale as an epic decision.}

1. {deliverable}
2. {deliverable}

## Claim Labels

{Every claim this spec serializes is labelled `OBSERVED` or `HYPOTHESIS` per
`persona-plan-orchestrator/standards/orchestration-model.md` § Verify-First Contract for
Inferred Claims. Label all three classes: the inferred mechanism, the Expected Surface below,
and every derived count or sharpened finding. A HYPOTHESIS names the file plus symbol that
confirms or refutes it and is marked verify-at-outline. An asserted absence is labelled and
verified exactly like an asserted presence. A claim whose verify-first clause has since been
settled carries at most one nested child bullet recording that settlement — stamped through the
`corpus set-verdict` seam, never hand-typed — whose shape is defined once at
`persona-plan-orchestrator/standards/orchestration-model.md` § Re-Grounding Verdict Field
and is not restated here. Claims are read as TOP-LEVEL `-` bullets of this section, so a
section authored as a table or as prose alone carries no claim the parser can address; such
a section is settled as a whole through the section-scoped stamp instead, and is never
required to be re-authored into bullets.}

- OBSERVED: {claim} — read at `{file}` § `{symbol}`
- HYPOTHESIS: {claim} — confirm/refute at `{file}` § `{symbol}` (verify-at-outline)
- Verify-first clause: {anything the consuming phase must settle against the implementing
  source before it may scope — refutation loops back to re-scope}

## Expected Surface

{Files/modules this plan is expected to touch — the input to the surface-disjointness
check before this plan may run concurrently with another. Label each entry per Claim Labels
above, and re-verify the whole surface against HEAD at outline before scoping on it.

This section is READ BY A PARSER, not by a human alone: `plan-marshall:script-shared`'s
`epic_spec_parser` is the marketplace's single reader of it, and `corpus surfaces` publishes
what it resolved. Four entry shapes resolve — a named file, a directory (`test/x/`), a
recursive glob (`marketplace/bundles/**`), and a filename glob (`test_*.py`) — plus entries
written relative to a rooted path named earlier in the same bullet, and exclusions introduced
by `excluding`. An entry whose first segment is not a real top-level repository entry cannot
be anchored and is reported as unresolved rather than silently claimed.

⛔ **The section's derivation status is DERIVED by that reader, never hand-declared.** Do not
write a status into this section: `declarative` / `derived` / `prose` is the reader's verdict
about what the entries resolved to, and a hand-written one would be a second, unchecked
opinion. A section that resolves to no path at all is `prose`, and a spec with no such section
is `absent`; both are `indeterminate` at the gate, which SEQUENCES the candidate rather than
passing it — see `persona-plan-orchestrator/standards/orchestration-model.md` § The gate's
reading contract.

⛔ **A `HYPOTHESIS` entry is swept against the tree BEFORE the spec is staged — and nothing but
the author enforces that.** An unswept guess here is not a neutral placeholder: it is either
over-declaration, which serializes siblings behind files the plan never touches, or
under-declaration, which admits a plan that genuinely collides. Sweep it, then label what the
sweep found.

This obligation is an AUTHORING rule with no machine backstop, and stating that is part of the
rule. The reader strips `OBSERVED:` and `HYPOTHESIS:` with one and the same label prefix and
keeps no label on the resolved entry, so a `HYPOTHESIS` path is classified as declared surface
exactly like an `OBSERVED` one; `corpus surfaces` and `corpus cross-check` then consume it with
no sweep record to require. No step between authoring and the disjointness gate can tell a swept
guess from an unswept one — which is why an unswept entry reaches the gate silently rather than
being refused there.}

- {OBSERVED|HYPOTHESIS}: `{path}`:{line} — `{symbol}` (verify-at-outline when HYPOTHESIS)

## Dependencies and Sequencing

{Plans that must land first, known overlaps that force sequencing, and adjacency notes —
surfaces this plan sits next to without touching, which a reader needs to avoid re-deriving.}

- Depends on: {PLAN-NN or none}
- Overlaps with: {PLAN-NN surfaces or none}
- Adjacent to: {nearby surface and why it stays untouched, or none}

## Hand-Off Command

{The ready-to-run command the orchestrator emits when this plan reaches the queue head. The
command is a ONE-LINE POINTER to this spec path — the spec body is the brief, so nothing is
transcribed into the command.}

```text
/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
