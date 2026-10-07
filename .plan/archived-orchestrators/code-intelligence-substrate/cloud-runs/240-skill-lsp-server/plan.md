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

# A language-server surface over the skill corpus

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

Nothing exposes the skill corpus's reference intelligence to an editor: there is no go-to-definition
on a skill notation, no find-references, no live broken-reference diagnostics, no hover.

⭐ **This plan is deliberately RE-SCOPED from its original framing, and the re-scope is the most
important thing in it.** It was staged as *building* the cross-file skill intelligence. **That
intelligence already exists and works** — the dependency resolver answers dependency, reverse
dependency, tree and validation queries over several edge types including parsed Python imports, with
line-level provenance. What remains is **presentation over an existing index**, not construction.
⛔ **Scoping this as greenfield would rebuild a working engine.**

## Goal

The existing reference intelligence is reachable from an editor (or whichever client the protocol
decision selects), strictly opt-in, degrading to a clean no-op when unconfigured.

## Deliverables

1. **D0 — GATE: re-verify the asserted absence, and record a protocol PROPOSAL rather than deciding.**

   Two things must happen before anything is built.

   **(a) Re-verify the absence.** The claim that no language server exists for this surface was
   established by external research at a fixed date, and that ecosystem moves quickly.
   ⛔ **An asserted absence carries the higher verification burden**, and an unverified one sends this
   plan to build something that already exists. **If one has appeared, evaluate integrating it before
   constructing one.**

   **(b) Record the protocol question as a written proposal for the operator — do NOT decide it.**
   ⛔⛔ **This is a genuine fork with materially different downstream consequences, and this run has no
   operator to ask.** The question: is an editor protocol the right surface at all? **The consumers of
   this repository's intelligence are predominantly agents, not humans in an editor** — and at least
   one mature project in this space chose a tool-calling protocol over an editor protocol for exactly
   that reason.
   *Done when:* the absence is re-verified with its date and method, and a **written proposal**
   comparing the options against the actual intended consumer exists in the repository.
   ⛔ **Do not implement a protocol choice this run made unilaterally.** If the proposal is the only
   thing that ships, that is a complete and correct outcome for this deliverable — say so in the run
   report.

2. **D1 — GATE: measure interactive latency.** The validation pass walks the whole component and
   dependency set; **interactive latency was never measured.**
   *Done when:* the existing verbs are timed and the figures recorded.
   ⚠ **If they are too slow for interactive use, an incremental or cached index becomes a deliverable
   and this plan must be re-scoped or split** — do not build an interactive surface over a
   non-interactive index.

3. **D2 — the surface itself**, answering from the existing index: go-to-definition on a skill or
   script notation, find-references, hover (description plus frontmatter).
   ⛔ **The index is consumed, NOT edited.**
   *Done when:* each of the three answers resolves from the existing index with provenance.

4. **D3 — live broken-reference diagnostics**, sourced from the existing validator.
   ⛔ **Hard-gated on the validator's precision work** — see Notes. Surfacing a set with a large
   false-positive share into an editor ships confident-wrong diagnostics at the highest-visibility
   surface this epic has.
   *Done when:* diagnostics stream from the validator and a known false-positive class produces none.

5. **D4 — strictly opt-in configuration, with a documented no-op path when unconfigured.**
   *Done when:* an unconfigured project's behaviour is unchanged, verified rather than asserted.

6. **D5 — documentation across all three trees.**
   The user page is **the highest-value page here**, because this is the only kind of deliverable in
   the epic an operator must actively wire up — **it must state plainly that an unconfigured project
   loses nothing.** The concepts page places the surface in the tier model (an accelerator, never a
   prerequisite). The developer page records **the protocol decision and its rationale**, so the
   choice is not re-litigated later. ⛔ Ship docs **in this plan**.

Six deliverables with two gates — at the split guard; evaluate before implementing.

## Out of scope

- **Building cross-file skill intelligence.** ⛔ Excluded — **it already exists and works.** This plan
  presents it. Rebuilding it is the single largest waste this plan can commit.
- **Rebuilding the existing agent-to-code-language-server bridges.** Excluded: the mature projects in
  this space bridge **ordinary code** language servers to agents, each requiring a per-language server
  installed, and each explicitly carrying **no markdown or documentation support**. ⛔ **Do not
  rebuild them — if per-language code intelligence is wanted, integrate them.**
- **Becoming a prerequisite for anything.** ⛔ Excluded by the tier contract: this is an
  **accelerator**. Prioritising it does not reclassify it as load-bearing, and it must degrade to a
  clean no-op when unconfigured.
- **Deciding the protocol.** ⛔ Excluded from this run's authority — see D0(b). The run records a
  proposal; the operator decides.

## Expected surface

- A new skill under `marketplace/bundles/pm-plugin-development/skills/` — the server or surface.
  **HYPOTHESIS**, verify at outline; the placement convention puts marketplace-domain tooling in that
  bundle.
- `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/` — **consumed
  as the index, NOT edited.** **OBSERVED.**
- The client configuration surface — shape depends on D0's proposal. **HYPOTHESIS.**
- `test/pm-plugin-development/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| No language server exists for this surface; the ecosystem ships only file-local spec-conformance validators | **OBSERVED (external, at a fixed research date) — AND AN ASSERTED ABSENCE** | ⛔ **D0(a) re-verifies it.** This is the highest-risk claim in the plan: an unverified absence produces duplicate work against something that already exists, and there is no operator here to sanity-check it. |
| The mature "language server for agents" projects run the **opposite** direction — bridging code language servers to agents, per-language, with no documentation support | **OBSERVED (external, same date)** | Re-verify with the same pass as D0(a). ⛔ **Do not rebuild them.** |
| The cross-file skill intelligence already exists and returns real edges with line-level provenance | **OBSERVED, verified live** | ⛔ **Re-verify in the clone by running the existing verbs.** This is what makes the plan small; if it were false the plan would be an order of magnitude larger. |
| An editor protocol is the right surface at all | **HYPOTHESIS — and a GENUINE FORK** | ⛔ **Not decidable by this run.** See D0(b): record a proposal, do not choose. The consumers here are predominantly agents rather than humans in an editor. |
| The index is fast enough to answer interactively | **HYPOTHESIS — never measured** | **D1.** ⚠ If it is not, an incremental or cached index becomes a deliverable and the plan re-scopes. |

## Verification

- **D0(a) is verified by a dated, method-stated re-check**, not by repeating the original claim. The
  run report names what was searched and when.
- **D0(b) is verified by the proposal existing and being decision-shaped** — options, the consequence
  of each, and the consumer evidence that bears on it. ⛔ A proposal that quietly recommends one option
  and then implements it has not met this deliverable.
- **D4 is verified on an unconfigured project**: behaviour must be unchanged. Assert it rather than
  asserting the configured path works.
- **D5's user page carries a cold read.** Its whole value is whether a reader comes away believing
  they must configure something. Dispatch the pre-PR verification sub-agent to read it cold and report
  whether it read as *"you must wire this up"* or *"you lose nothing if you don't"*. **The second is
  the correct reading.**
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Dependencies, and one of them is hard.** ⛔ **The validator-precision plan is a HARD GATE for D3.**
  ⚠ The query-vocabulary plan **shrinks this plan a second time**: with the substrate already speaking
  definition / references / hover, this becomes a thin protocol adapter rather than a translation
  layer. ⛔ **Do not carry the "thin adapter" assumption past that plan's landing** — if it descoped to
  an additive facade, this plan **absorbs the translation work and must be re-scoped upward.**
- **Index coverage** affects find-references: gaps in what the index sees produce false negatives.
  Confirm the coverage situation before promising completeness.
- **Adjacency.** A sibling resolver consumes the same index but exposes it to the architecture surface
  rather than to an editor. Different surface, same substrate — a landing in either informs the other.
- ⛔ **Never run concurrently with the live-language-server plan or the derivation-resolver plan** —
  shared server and configuration surface.
