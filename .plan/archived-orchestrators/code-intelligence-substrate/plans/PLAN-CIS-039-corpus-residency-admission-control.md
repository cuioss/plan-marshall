# PLAN-CIS-039: Half Of Every Tool-Result Byte Is Plan-Marshall Reading Plan-Marshall

epic: code-intelligence-substrate
workstream: WS-06

> Staged 2026-08-09 from the PLAN-CIS-031 landing (#1126), whose six-phase instrumented
> `metrics.toon` is the first record able to split exploration by what a substrate could
> address. Self-sufficient spec.

## Objective

The epic was built on the premise that exploration of the **codebase** is the addressable
cost. The first six-phase measurement says otherwise:

| bucket | share of exploration bytes |
|---|---:|
| `exploration_index_answerable_bytes` — what a code substrate could remove | **15.9%** |
| `exploration_doc_residency_bytes` — documents a step must read to execute at all | **65.2%** |
| `exploration_unattributed_bytes` | 18.9% |

Exploration is ~77% of tool-result bytes across `2-refine`…`6-finalize`, so doc-residency
alone is **≈50% of every tool-result byte**. The system spends more context reading its own
skills, standards and workflow docs than on everything else combined.

**Apply to plan-marshall's own corpus the admission-control discipline plan-marshall already
enforces on the codebase.** Today the codebase side is rigorous — structured queries first,
`search --content` returning location and strength but never lines, no Glob/Grep exploration.
The corpus side has none of it: `Skill:` loads a whole `SKILL.md`, a referenced standard is
read whole, and nothing ranks, slices, or bounds any of it.

## Why this is the epic's largest single lever

`persona-plan-marshall-agent` alone is a **14,835-byte** `SKILL.md` with **101,897 bytes** of
`standards/` behind it, loaded unconditionally by **every** dispatch. That is one skill of the
145 registered components. ⭐ **The discipline already exists and is written down** —
`code-intelligence.adoc` § "Location and strength, never the lines" argues the exact cost
asymmetry this plan applies one corpus over: *"returning line bodies makes the response size a
function of the corpus's match density; returning files makes it a function of file count"*.
**Nobody applied it to the documents.**

## ⚠ Why this is NOT the "examine less" anti-goal — state this in the outline

⛔ The #1069 effort analysis established that reducing examination improves the token number
while degrading detection, and that such levers are **rejected on that ground, not weighed.**
This plan is not one of them, and the distinction must be deliverable-level, not rhetorical:

- **In scope**: loading a smaller *slice* of a document that is read anyway — the section a
  step actually needs rather than the whole standard; ranked retrieval over the corpus; not
  re-reading a document already resident in the same envelope.
- ⛔ **Out of scope**: loading *fewer skills*, dropping standards from a profile, or shortening
  documents to make them cheaper. Those reduce what is examined.

The success test is **binary and structural** — *can a dispatched leaf obtain the one section
it needs without the whole file, yes or no?* Sizing the saving needs the WS-04 instrument;
doing it does not. (Standing rule from the token-reduction directive.)

## Deliverables

1. **D1 — GATE: derive the corpus-residency population, mutates nothing.** Establish, across
   the post-`9b689d65b` archived plans (**n=5 at staging**), which documents are read, how
   often, how many times *within one envelope*, and how much of each read document a step
   actually consumes. ⛔ **Report per phase with the population size — do not pool.** The
   whole finding is that phases differ (`2-refine` 90.7% doc-residency vs `4-plan` 43.9%).
   ⛔ **Implement the three-state archived-record read** (`current` / `old-schema` /
   `pre-#812`) per the `metrics-record-cannot-represent-re-entered-phase` notification — the
   partiality keys were renamed with no shim, and defaulting an old-schema record is how a
   bare rename manufactures a clean verdict.
2. **D2 — a section-granular read verb for the corpus.** A dispatched leaf can obtain a named
   section of a `SKILL.md` or `standards/*.md` without loading the file. ⛔ **It must carry the
   same coverage contract the content reader already ships** — the caller must be able to tell
   *the section does not exist* from *the file could not be read* from *the section is empty*.
   A silent empty return is the confident-empty archetype this epic exists to remove.
3. **D3 — re-read elimination within an envelope.** A document already resident in a dispatch's
   context is not read again. D1 supplies the magnitude; if D1 finds intra-envelope re-reads are
   rare, **drop this deliverable and record the refutation** rather than building for it.
4. **D4 — state the epic's value case against the corpus measurement.** The epic's own vision
   names a codebase substrate. If the addressable share on the phases that matter is
   codebase-15.9% versus corpus-65.2%, **say so in `epic.md` § Vision and re-scope.** ⭐ This is
   the deliverable permitted to conclude that the epic has been aimed at the smaller half.

Four deliverables, D1 a gate — below the split guard.

## Claim Labels

- **OBSERVED (first-party, recomputed by the orchestrator from
  `.plan/local/archived-plans/2026-08-09-self-review-resweeps-full-surface-every-round/work/metrics.toon`)**:
  every figure in the table above, the per-phase split, and the ~77% exploration share.
  The three byte buckets sum exactly to `exploration_result_bytes` in each phase row.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Recomputed at HEAD from the archived 2026-08-09 metrics.toon: index_answerable + doc_residency + unattributed sum EXACTLY to exploration_result_bytes in all 6 phases; whole-plan shares 15.9 / 65.2 / 18.9 percent and the ~77 percent exploration share reproduce to the stated precision.
- **OBSERVED (first-party, `wc -c`)**: `persona-plan-marshall-agent/SKILL.md` = 14,835 bytes;
  its five `standards/*.md` total 101,897 bytes.
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: no | evidence: REFUTED at HEAD by direct byte count. persona-plan-marshall-agent/SKILL.md is 15874 bytes, not the cited 14835; its standards/ directory now holds SIX files totalling 114977 bytes, not five totalling 101897 - argument-naming.md was added since staging. The figures are stale rather than wrong in kind: the residency argument survives, but every cited byte count must be re-derived at outline before it is used.
- **OBSERVED (first-party, `execution-context.md` Step 2)**: `persona-plan-marshall-agent` is
  loaded unconditionally by every dispatch and is not nameable in `skills[]`.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: marketplace/bundles/plan-marshall/agents/execution-context.md line 24 makes the persona-plan-marshall-agent load unconditional, and line 76 states it MUST NOT appear in skills[]. Both halves of the claim hold verbatim.
- ⛔ **HYPOTHESIS — the load-bearing one**: that the doc-residency share generalises beyond
  **n=1 plan**. **D1 is this verification.** ⚠ The epic has now twice recorded a phase-specific
  figure being read as a whole-corpus one (`PLAN-CIS-036`'s founding concern, and the 76–85%
  band being false at `4-plan` on `plan-45`). **Do not build D2 on n=1.**
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Unreached population, and the reason is the plan's own halt: D1 never ran (the cloud run halted at D0). The archived-plans corpus has grown to 36 metrics.toon files - up from the n=1 that made this a hypothesis - but NO check at HEAD aggregates the three-way split across them, so the generalisation is still unmeasured rather than refuted. This is exactly what staged PLAN-CIS-056 would supply.
- **HYPOTHESIS**: that a step's *needed* fraction of a document is materially smaller than the
  document. Plausible and unmeasured — D1 must measure consumption, not just residency.
  ⚠ **If a step genuinely needs most of what it loads, D2's ceiling is low and the plan
  re-scopes.** This is the honest way this plan can return an unwelcome answer.
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: No instrument exists at HEAD that measures per-section consumption against residency, and D1/D2 never ran, so the claim stays exactly as unmeasured as the spec itself states. Unverifiable rather than corroborated: nothing was reached that could settle it either way.
- ⛔ **Verify-first**: `Skill:` loading is a **platform** mechanism, not ours. Establish at
  outline what the harness actually admits when a skill loads — whether progressive disclosure
  already bounds it to `SKILL.md`, and whether a section-granular read is reachable at all from
  inside a dispatched envelope. **If the harness forecloses D2, the plan re-scopes to the
  `standards/*.md` reads that go through `Read`, which we do own.**
  - verdict: unverifiable | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: The verify-first clause was never discharged because the run halted at D0. Partial ground truth at HEAD: CIS-039's own landing found two --section verbs exist (manage-plan-documents.py and manage-solution-outline.py) but both operate over plan and solution-outline documents only; NEITHER reaches SKILL.md or standards files, which is the surface the clause is about. Section-granular skill loading remains unestablished.

## Expected Surface

- **OBSERVED**: `work/metrics.toon` in plans archived after `9b689d65b` — read-only corpus (D1)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/skill-loading.md` — the loading contract (verify-at-outline)
- **HYPOTHESIS**: a corpus read verb's home — `manage-architecture` (it already owns
  `search --content` over the inventory) or a new surface. **Decide at outline.**
  ⛔ **Do NOT ship a second content-search verb** — `PLAN-CIS-001` shipped one and
  `PLAN-CIS-024` D3 already carries that prohibition.
- **HYPOTHESIS**: `doc/concepts/token-management.adoc` § 4 — the skill-driven-guidance claim,
  which today asserts pre-loaded skills *prevent* the exploration loop. **They prevent the
  codebase loop and are themselves the larger cost.** (verify-at-outline)

## Dependencies and Sequencing

- **Depends on**: nothing hard. `PLAN-CIS-042` (WS-04) **should land first** where a figure is
  load-bearing — it settles the two `unattributed` populations, and D1's split inherits them.
- ⭐ **Coordinates with `PLAN-CIS-041`** (LSP in execute, WS-03): a live language-server client
  in a dispatched envelope is the same protocol shape D2 needs pointed at the corpus.
  **Coordinate; do not fork a second client.**
- ⚠ **Overlaps `PLAN-CIS-007`** (skill-LSP server, WS-03) in subject and not in consumer:
  CIS-007 is an editor-facing Tier-2 accelerator for humans, this is a token lever for
  dispatched leaves. **Re-verify at outline that the two are not building one index twice.**
- ✅ **MAY pair with `PLAN-CIS-040`** (same workstream, disjoint surfaces) — ⚠ both touch the
  `execution-context` agent body; re-verify the file set at emit.
- ⛔ **Never pair with any WS-04 plan** that edits `manage-metrics` emission.

## Anti-goals

- ⛔ **Do not load fewer skills.** See § Why this is NOT the "examine less" anti-goal.
- ⛔ **Do not shorten standards documents to make them cheaper.** Document quality is not the
  variable; how much of a document enters a context is.
- ⛔ **Do not quantify a saving.** Report measured shares; the saving claim belongs to WS-04.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-039-corpus-residency-admission-control.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
