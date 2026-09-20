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

# An LSP-shaped facade over the architecture query surface

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

The architecture skill exposes its query capability through a vocabulary invented here — `graph`,
`path`, `neighbors`, `impact`, `find`, `which-module`, `files`, `derived-module` and others. Every
consumer must learn it, and most of the concepts map closely onto a vocabulary that agents, editors
and tooling already speak: `definition`, `references`, `hover`, `documentSymbol`, `workspaceSymbol`.

Two further problems sit on the same surface, and they are the reason this is a substrate obligation
rather than a naming preference.

**A dispatched leaf has exactly one search primitive.** Grep and Glob are **revoked at harness
runtime despite being declared**, a broad content sweep is unexecutable in a leaf, shell search is
hook-blocked, and the denial is **non-deterministic within one session**. So the content-search verb
is not one option among several for a leaf — **it is the only one.**

**And that one primitive mis-measures, in two ways.** Case-insensitive matching and verbatim matching
are **mutually exclusive by construction**: the pattern is compiled with case-folding never enabled
and no flag to enable it, so in regex mode an inline case-insensitivity marker works but the help
text does not say so, while in literal mode the escaping makes that marker impossible. An author
whose pattern contains regex metacharacters must choose between matching verbatim and matching
case-insensitively. Separately, the result `count` is a **row** count rather than a **file** count.

⭐ **The blast radius is not academic**: residual sweeps have returned **zero for phrasings that were
live in the tree**, and a false residual-zero shipped to merged main. **The measurement defect and
the false claim are causally linked** — a confident zero over a case-mismatched population.

## Goal

The query surface speaks a vocabulary consumers already know, without a breaking rename: an
LSP-shaped **facade** over the existing verbs, with the verbs that have no LSP equivalent preserved
as declared commands. A consumer can ask what the substrate can and cannot answer **right now, in the
envelope it is actually executing in**. And the one search primitive a dispatched leaf has stops
forcing a choice between matching verbatim and matching case-insensitively.

## Deliverables

1. **D1 — an LSP-shaped query vocabulary over the existing capability set**, with the current verbs
   mapped onto it (impact → reverse references; find / which-module → the workspace-symbol family;
   module / derived-module → the hover family).
   ✅ **The shape is already DECIDED and must not be re-derived: this is an additive FACADE, not a
   replacement.** The mapping is **not** one-to-one and the residue **is** large.
   ⛔ **The four traversal/inventory verbs with no LSP method — path, impact, find, which-module —
   keep their names behind declared `workspace/executeCommand` commands.** LSP is
   `(uri, position)`-oriented with no module node and no transitive traversal, so this is in-spec, and
   it preserves the one-stack requirement.
   *Done when:* the facade answers in LSP vocabulary, the four residue verbs remain reachable
   unchanged, and a per-verb mapping table exists for the verbs that **do** map.
2. **D2 — a capability-report verb**: what this substrate can and cannot answer right now, given the
   resolvers actually active. Closes the *not-derivable versus genuinely-empty* ambiguity for the
   whole query surface.
   ⛔ **Three binding constraints, each from a recorded failure:**
   - **Do not read the agent tool declaration as the grant.** Declared and effective tool lists
     disagree and nothing reconciles them. A capability report built on the declaration reports a
     capability the leaf does not have — this epic's own archetype, inside the deliverable that
     exists to close it.
   - **"Probe then branch" is NOT a sound fallback.** Denial varies *within* one session, so a leaf
     that probed successfully can be denied on the next dispatch. **A capability answer must not be
     cached across dispatches.**
   - **The report answers for the EXECUTING envelope**, never in the abstract.
   *Done when:* the report distinguishes *cannot derive* from *derived nothing*, and its answer is
   envelope-scoped and uncached.
3. **D3 — the vacuous-consumer guard.** The refine phase's feasibility check reasons over graph
   output and **cannot fire at zero edges**. It must receive real edges or be told the answer is
   underivable.
   *Done when:* the consumer either gets edges or gets an explicit underivable signal — and a test
   asserts it cannot silently pass on emptiness.
4. **D4 — the search primitive's measurement contract.**
   Give the content search a case-insensitivity option that composes with verbatim matching, document
   the regex-mode behaviour that already exists, and make the result count's population explicit
   (rows versus files).
   ⚠ **The row-versus-file count is a RECURRENCE, not a new finding** — it is the same shape as the
   dual-attribution row count elsewhere in this epic. Fold it onto that understanding; do not file it
   twice.
   *Done when:* a pattern containing metacharacters can be matched case-insensitively and verbatim at
   once, and the count states what it counts.
5. **D5 — documentation, shipped in this plan.**
   The LSP-shaped query model in `doc/concepts/`; the verb-by-verb mapping in `doc/developer/` (this
   is what makes existing call sites navigable); the operator-facing surface in `doc/user/`; plus the
   skill's own contract and canonical invocations.
   ⛔ **A renamed API whose documentation lags is the doc-contract-divergence archetype in its purest
   form.**
   *Done when:* every mapped verb appears in the mapping table and the help text matches the
   implemented behaviour — verified by cold read.

Five deliverables — at the split guard. ⚠ **Evaluate the split before implementing and record the
verdict**; the natural cut is *vocabulary reshape* (D1+D2+D3+D5) versus *the substitute primitive's
measurement contract* (D4).

## Out of scope

- **A breaking rename of the existing verbs.** ⛔ Excluded by decision: the facade is additive.
  Renaming across a surface with unenumerated consumers is the highest-blast-radius change available
  here, and the facade removes that risk entirely.
- **Re-deriving whether LSP fits.** Excluded — the enumeration was done and the additive-facade
  branch was chosen. ⛔ **Do not re-open the fits-or-not question.** What is still owed is the
  per-verb mapping table for the verbs that do map.
- **Building a language-server protocol adapter.** Excluded because a separate plan owns it; this
  plan is what makes that one a thin adapter rather than a translation layer.
- **Fixing every consumer's compensation for the row count.** Excluded; D4 makes the population
  explicit, consumers follow.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py` — the
  argparse surface. **OBSERVED.**
- `.../manage-architecture/scripts/_cmd_client_query.py` and `.../_cmd_client_handlers.py` — the
  query implementations and the pattern compilation. **OBSERVED.**
- `.../manage-architecture/SKILL.md` and `.../standards/client-api.md` — the documented contract and
  canonical invocations. **OBSERVED.**
- The refine and finalize consumers that read graph output. **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The query surface exposes a large invented verb set | **OBSERVED** | `architecture --help` in the clone. ⛔ **Re-derive the verb list — the count is a LEAD**, and it moves. |
| Case-insensitivity and verbatim matching are mutually exclusive by construction | **OBSERVED, first-party, corroborated against the implementing source** | The pattern-compilation call in `_cmd_client_handlers.py` (case-folding never passed) plus the absence of any case flag in the argparse surface. **Read both**; this is the premise D4 rests on. |
| The result count is a row count, not a file count | **OBSERVED — a RECURRENCE, second sighting** | Reproduce in the clone with a file attributed to two modules. |
| A dispatched leaf has Grep/Glob revoked at runtime **despite being declared**, and the denial is non-deterministic within a session | **HYPOTHESIS at HEAD** | ⛔ **Confirm or refute against an ACTUAL dispatched leaf's effective grant, never the agent declaration.** This is D2's central constraint; if the grant has changed, D2's shape changes. |
| The refine feasibility check cannot fire at zero edges | **OBSERVED** | The refine workflow's feasibility section plus the graph verb's output. Read both. |
| One traversal verb has no consumer outside the skill's own documentation | **OBSERVED** | ⚠ A search-derived absence — **re-derive it**, and note that a reviewer's list of call sites is a **sample, not an enumeration**. |
| The four named verbs are the complete unmappable residue | **HYPOTHESIS** | ⛔ **Walk all subcommands against the LSP method list.** The originating check covered the load-bearing traversal/inventory verbs only — **that is a sample, not an enumeration.** Derive the full residue. |
| A false residual-zero shipped to merged main because of the case-matching defect | **HYPOTHESIS (second-hand)** | Re-ground at outline before pinning a test to specific lines. |

An asserted **absence** ("no case-insensitivity flag exists") is verified exactly as an asserted
presence — and it is cheap to check in the clone. Do it before building D4.

## Verification

- **D2 is verified inside a dispatched leaf, not in main context.** A capability report that is
  correct in the orchestrator and wrong in a leaf has failed the deliverable — the whole point is
  that the two differ.
- **D3 is verified by a negative control**: a zero-edge graph must produce an explicit underivable
  signal, asserted to be distinguishable from a genuine no-concerns result.
- **D4 is verified against the real failure case**: a pattern containing regex metacharacters,
  matched case-insensitively and verbatim simultaneously. Assert the previously-impossible
  combination now works.
- **D5 carries a cold read.** Hand the mapping table and help text to the pre-PR verification
  sub-agent cold and ask which verbs it believes were renamed. **If it thinks any existing verb was
  removed or renamed, the facade documentation failed** — that is the single most likely
  misunderstanding this change can produce.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Why the two subjects are one plan.** Two independent reports arrived about the **same
  primitive**: one that a dispatched leaf has no search primitive at all, one that the primitive it
  is left with mis-measures. Together they make the content search a substrate obligation rather than
  a convenience — which is why D4 sits beside the vocabulary work rather than in its own plan. The
  split guard applies; evaluate it.
- **A scope note honoured from another epic**: they deliberately did **not** fix the case-matching
  defect in their own plan even though it depends on it, and wrote in a constraint not to build a
  sweep that assumes case-insensitivity. **If this plan does not close it, that constraint stands
  indefinitely.**
- **Sequencing.** Never run concurrently with another plan touching the architecture skill — several
  in this epic do. ⚠ If the reshape changes the derivation seam's return contract, co-design rather
  than sequence: building the query layer twice is the failure mode.
