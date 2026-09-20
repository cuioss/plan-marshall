# PLAN-CIS-002: Reshape the Architecture Query API to LSP Vocabulary

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`manage-architecture` exposes 24 verbs in a vocabulary invented here — `graph`, `path`, `neighbors`,
`impact`, `find`, `which-module`, `files`, `derived-module`. Every consumer must learn it, and the
concepts map almost one-to-one onto a vocabulary that agents, editors and tooling already speak:
LSP's `definition`, `references`, `hover`, `documentSymbol`, `workspaceSymbol`.

Align the query surface with LSP structure to simplify usage. This is a **presentation** change over
PLAN-02's derivation seam, and it is what makes PLAN-CIS-007's language-server surface a thin adapter
rather than a translation layer.

## Deliverables

1. An LSP-shaped query vocabulary over the existing capability set, with the current verbs mapped
   onto it (`impact` → reverse `references`, `find`/`which-module` → `workspaceSymbol`-family,
   `module`/`derived-module` → `hover`-family).
2. A capability-report verb: what this project's substrate can and cannot answer right now, given
   the resolvers actually active. Closes the *not-derivable vs genuinely-empty* ambiguity for the
   whole query surface.
3. The vacuous-consumer guard: `phase-2-refine`'s Feasibility Check reasons over graph output and
   cannot fire at zero edges — it must receive real edges or be told the answer is underivable.
4. **Documentation — the heaviest doc load in the epic, because this is a vocabulary change.**
   `doc/concepts/` — the LSP-shaped query model on the substrate page PLAN-02 creates.
   `doc/developer/` — the verb-by-verb mapping from the old vocabulary to the new, which is what
   makes the change navigable for anyone reading existing call sites. `doc/user/` — the query
   surface as an operator actually invokes it. Plus `manage-architecture`'s SKILL.md and
   `standards/client-api.md`. ⛔ Ship docs **in this plan**: a renamed API whose documentation lags
   is the doc-contract-divergence archetype in its purest form.

## Evidence Fold — 2026-08-08, ONE surface from TWO senders (`lessons-handling-…-002` cluster C07 + `review-apparatus-005`)

⭐ **These two messages arrived independently and are about the SAME primitive, so they are folded as one
item rather than two.** C07 says a dispatched leaf has no search primitive at all; `review-apparatus-005`
says the primitive it is left with mis-measures. Together: **`architecture search --content` is not one
option among several for a dispatched leaf — it is the ONLY one, and it has two measurement defects.**
That is what makes this a substrate obligation rather than a convenience.

### The grant is a runtime fact, not a declaration (4 corpus instances, C07)

| Lesson | Claim | Category |
|--------|-------|----------|
| `2026-07-29-08-001` | dispatched `execution-context` leaves have Grep/Glob **revoked at harness runtime despite being declared**; no project surface can widen the grant | `arch-constraint` |
| `2026-08-03-09-001` | a broad content sweep is **unexecutable in a dispatched leaf** — Grep/Glob deniable at runtime, Bash `grep`/`find` hook-blocked, no fallback | `anti-pattern` |
| `2026-07-22-13-001` | denial is **non-deterministic within one session** — a coverage gap must be re-dispatched, never folded into the success criterion | `anti-pattern` |
| `2026-07-22-20-003` | a mechanism substitution must be checked against the **EXECUTING envelope's** grant, not the substituted tool's verb list | `anti-pattern` |

⛔ **Three consequences for D2 (the capability report), which is the deliverable this lands on:**

1. **Do not read the agent tool declaration as the grant.** `2026-07-29-08-001` is an `arch-constraint`
   precisely because declared and effective tool lists disagree and nothing in this project reconciles
   them. A capability report built on the declaration reports a capability the leaf does not have —
   this epic's own archetype, inside the deliverable that exists to close it.
2. **"Probe then branch" is NOT a sound fallback.** Denial varies *within* one session, so a leaf that
   probed successfully can be denied on the next dispatch. A capability answer must not be cached across
   dispatches.
3. **The report must answer for the EXECUTING envelope**, not in the abstract — which is the same
   generalisation `2026-07-22-20-003` makes about substitution checks.

### ⛔ The substitute primitive mis-measures — CORROBORATED FIRST-PARTY 2026-08-08

Routed by `review-apparatus` (from PLAN-PR-009's candidate-lesson `-001`) because we own the
content-search seam. **The orchestrator verified both halves against the implementing source rather than
accepting them** — verdict below is `corroborated`, not `reported`:

- ⛔ **Case-sensitivity and verbatim matching are mutually exclusive BY CONSTRUCTION.**
  OBSERVED (`manage-architecture/scripts/_cmd_client_handlers.py:1000`):
  `re.compile(re.escape(pattern) if literal else pattern, re.MULTILINE)` — `re.IGNORECASE` is never
  passed, and there is no `--ignore-case` flag anywhere in the argparse surface
  (`architecture.py:268,272`). ⇒ In regex mode an inline `(?i)` works but **`--help` does not say so**
  (`:268` documents only "Python regex"); in `--literal` mode `re.escape` escapes the `(?i)` so it
  cannot work at all. An author whose pattern contains metacharacters — `--pr-number` is the reported
  real case — must choose between matching verbatim and matching case-insensitively.
- **`count` is a ROW count, not a file count.** ⚠ **This is a RECURRENCE, not a new finding** — it is
  already an Open Defect in `epic.md` from the PLAN-CIS-001 landing probe (three distinct files returned
  as six rows, once per attributed module). `review-apparatus` observed it independently
  (`count: 2` for one file under `default` and `plan-marshall`). **Second sighting, folded onto the
  existing defect, not filed twice.**

⭐ **The blast radius is not academic and is the reason this is not a polish item**: PLAN-PR-009's
residual sweeps returned **0 for phrasings that were live in the tree**, and a false residual-zero
shipped to merged main (`test_ci_base.py:548,561,569`). **The measurement defect and the false claim are
causally linked** — a confident zero over a case-mismatched population.

⚠ **Scope note from the sender, honoured:** `review-apparatus` is explicitly NOT fixing this in
PLAN-PR-018 even though that plan depends on it; they wrote in a constraint not to build a sweep that
assumes case-insensitivity. **If this plan does not close it, that constraint stands indefinitely.**

⚠ **Split guard — this fold pushes the deliverable count toward the bar.** D2 gains constraints (above)
and the seam-defect half is naturally a fifth deliverable. **Evaluate the split at outline and record
the verdict**; the natural cut is *vocabulary reshape* vs *the substitute primitive's measurement
contract*.

**Claim labels** — OBSERVED: the four lesson ids/categories; the `re.compile` call site, the absent
`--ignore-case` flag, and the `--literal`/`re.escape` interaction (all read first-party at the paths
named above). HYPOTHESIS (verify-at-outline): that the runtime Grep/Glob revocation still holds
post-PLAN-CIS-001 — confirm/refute against **an actual dispatched leaf's effective grant, never the agent
declaration**, by this cluster's own first member. The `test_ci_base.py` false-residual-zero is
second-hand from `review-apparatus` and is re-grounded at outline.

## Claim Labels

- **OBSERVED**: `architecture --help` declares 24 subcommands —
  `discover, init, derived, derived-module, info, modules, graph, path, neighbors, impact, module,
  overview, commands, resolve, derive-verification, siblings, suggest-domains, profiles, files,
  which-module, find, diff-modules, descriptor-regression-check, enrich`.
- **OBSERVED (vacuous consumer)**: `phase-2-refine/standards/refine-workflow-detail.md`:494
  § Feasibility Check validates that a request "follows dependency direction (`architecture graph`
  output)" and flags "reverse dependency flows" as `FEASIBILITY: CONCERN`. At zero edges that
  predicate can never fire. `phase-6-finalize/standards/architecture-refresh.md` also reads `graph`.
- **OBSERVED (no consumer)**: `impact` has NO consumer outside `manage-architecture`'s own `SKILL.md`
  — searched across `marketplace/`, `.claude/`, `doc/`. Renaming or reshaping it is therefore
  **cheap**, which is a direct argument for doing the vocabulary change now rather than later.
- ⭐ **DECIDED 2026-08-01 (operator, recorded — this supersedes the former open hypothesis).**
  The mapping is **NOT** one-to-one, the residue **IS** large, and the additive-facade branch
  **FIRES**. This plan ships an **LSP-shaped facade over the existing verbs, not a replacement.**
  The residue is named and bounded: `path`, `impact`, `find`, `which-module` have **no LSP method**
  — LSP is `(uri, position)`-oriented with no module node and no transitive traversal
  (`callHierarchy` is incremental and client-walked, so the *client* owns the walk). Those four
  live as declared `workspace/executeCommand` commands, which is in-spec LSP and preserves the
  operator's one-stack requirement. ⛔ **Do NOT re-derive this at outline** — the enumeration was
  done at the orchestrator tier and the decision is recorded in `logs/decision.log`. What outline
  still owes is the *per-verb* mapping table for the verbs that DO map (`hover`-family,
  `references`-family, `workspaceSymbol`-family), not the fits-or-not question.
- **HYPOTHESIS**: the four residue verbs are the complete residue — no fifth verb turns out to be
  unmappable. Confirm/refute by walking all 24 subcommands against the LSP method list
  (verify-at-outline). ⚠ **The orchestrator checked the four load-bearing traversal/inventory verbs,
  not all 24** — that is a SAMPLE, not an enumeration (standing rule 4). Derive the full residue.
- **HYPOTHESIS**: consumers can absorb a vocabulary change. `graph` has consumers in `phase-2-refine`
  and `phase-6-finalize`; the files-inventory verbs have more. Confirm/refute by enumerating every
  consumer of every renamed verb BEFORE renaming (verify-at-outline).
  ⛔ **An orchestrator-supplied consumer list is a SAMPLE, not an enumeration** — this epic has
  already recorded that archetype. Derive the population; do not trust the two consumers named here.
- **Verify-first clause**: a breaking rename across a 24-verb surface with unenumerated consumers is
  the highest-blast-radius change in this epic. ⭐ **The facade shape is now DECIDED above, which
  removes the rename risk from the traversal/inventory verbs** — they keep their names behind
  `executeCommand`. The consumer enumeration is still owed for the verbs that DO get LSP names.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py` — argparse surface
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — the query implementations
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md` + `standards/client-api.md` — the documented contract and Canonical invocations
- **HYPOTHESIS**: `phase-2-refine/standards/refine-workflow-detail.md`, `phase-6-finalize/standards/architecture-refresh.md` — consumer updates (verify-at-outline)
- **OBSERVED**: `test/plan-marshall/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-02 (the seam supplies the provenance and capability data deliverable 2
  reports). ⛔ Both touch `manage-architecture` — never pair.
- ⚠ **Co-design risk with PLAN-02**: if the reshape changes the seam's return contract, co-design or
  merge the two rather than sequencing. Building the query layer twice is the failure mode.
- **Gates**: PLAN-CIS-007 — an LSP-shaped API makes the language-server surface a thin adapter. If this
  plan is dropped, PLAN-CIS-007 absorbs the translation work and grows accordingly.
- **Overlaps with**: PLAN-01, PLAN-02, PLAN-CIS-001 on `manage-architecture`. ⛔ Never pair.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-002-lsp-shaped-query-api.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
