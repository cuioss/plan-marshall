# PLAN-TRUTH-023: Split `doc/user/configuration.adoc`, derive its coverage against the real knob population, and evict the meta-project content

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-30 from an operator request. **LOW PRIORITY.** Four parts: document the `lane` config,
> split the file, verify every config aspect is documented, and move meta-project content to
> `doc/developer/`.

## Objective

`doc/user/configuration.adoc` is **587 lines across 26 subsections** under 5 top-level sections. It is
the largest user doc by a wide margin (`efforts.adoc` 195, `parallelism-and-locking.adoc` 55), it
**admits its own coverage gap in prose**, and it carries meta-project-only content in a consumer-facing
page.

## ⭐ Three findings from the staging pass that shape the work

### 1. The split convention already exists — follow it, don't invent one

`doc/user/` already contains topic pages carved out of this same doc: `efforts.adoc`,
`parallelism-and-locking.adoc`, `terminal-title.adoc`. ⭐ **And the pattern for the leftover stub is
already demonstrated in-file**: `=== Effort and model selection` (`:52-55`) is **three lines that point at
`efforts.adoc`** rather than duplicated content.

⇒ **That is the target shape for every extracted section** — a short pointer stub, not a deletion, so
existing xrefs and reader habits survive. **Do not invent a `configuration-part-2.adoc` scheme.**

### 2. ⛔ The doc enumerates the knobs it does NOT document — in a hand-written prose list

`:49` carries a single parenthetical naming roughly **25 knobs** (`branch_strategy`, `use_worktree`,
`confidence_threshold`, `compatibility`, `simplicity`, `commit_and_push`, `per_deliverable_build`,
`cost_size_token_table`, `per_envelope_budget_tokens`, `max_iterations`, `open_in_ide`, the
`system.retention.*` set, `checks_wait_timeout_seconds`, the step-owned params, the `project.*`
branch-naming knobs, …) followed by *"see the canonical per-key reference in `data-model.md`."*

⭐ **This is the operator's item 3 already half-answered, and it names its own authority:** the population
is `manage-config/standards/data-model.md`, and the coverage sweep is a **diff of the doc's covered set
against that key set** — mechanical, not a judgement call.

⛔ **But that parenthetical is itself the defect this epic tracks: a DERIVABLE SET WRITTEN AS NARRATIVE.**
It will drift the moment a knob is added, and nothing detects it. ⇒ **Do not rewrite it as a better
prose list.** Either generate it, or replace it with a pointer and let `data-model.md` be the single
enumeration. **A hand-maintained "everything else" list is a guaranteed future divergence.**

### 3. ⚠ The meta-project content is identifiable, and one class of it is subtler than prose

Item 4's targets found in the staging pass:

- `:230` — an explicit **"Meta-project derived-state caveat"** paragraph (cache-deploy steps,
  `deploy-target`, `sync-plugin-cache`, on-main executor regeneration).
- `:212` — *"and the meta-project derived-state steps"* embedded mid-sentence in the `minimal` lane
  description. ⚠ **Prose-embedded, not a separable block** — a section-level move will miss it.
- ⚠ **HYPOTHESIS, and the interesting one:** the doc's canonical-reference escape hatch links to
  `link:../../marketplace/bundles/plan-marshall/skills/…` at **`:47`, `:49`, `:128`, `:142`, `:167`,
  `:193`, `:203`, `:246`, `:275`, `:287`** — i.e. its primary "for everything else, see X" route points
  **into marketplace internals**. *Confirm/refute artifact:* determine whether a consumer-project reader
  reaches `doc/user/` with `marketplace/bundles/` present. **If they do not, the doc's main escape hatch
  is broken for exactly the audience it is written for** — which would make this the highest-value part
  of item 4, not the tidying part. **Settle this at D1 before moving anything.**

## Deliverables

### D1 — GATE: derive the population and settle the split (mutates nothing)

1. **Derive the knob population** from `data-model.md` (and cross-check `_config_defaults.py`), and diff
   it against what `configuration.adoc` actually documents. **Output the covered / uncovered / mentioned-
   but-undocumented split as a list**, not a count. ⚠ **Re-derive rather than trusting `:49`'s
   parenthetical** — that list is the artifact under suspicion.
2. **Settle the reference-link question** in finding 3 above. It determines whether item 4 is a move or a
   re-pointing.
3. **Decide the split boundaries**, preferring extraction into **existing** topic pages over new files
   where a home already exists (review gates → a review page; merge queue / worktrees →
   `parallelism-and-locking.adoc`). Every extraction leaves a pointer stub in the `:52` style.
4. ⚠ **Confirm the `lane` vocabulary before documenting it** — see the dedicated section below.

### D2 — document the `lane` configuration

The operator's item 1. ⛔ **Blocked on a real ambiguity — do not document the enum until it is settled.**
Three source statements disagree at HEAD:

| Site | Value set |
|---|---|
| `_config_defaults.py:415` `VALID_LANE_OVERRIDE` | `off, minimal, standard, full, ask` |
| `_config_defaults.py:932` (comment) | `off, minimal, standard` |
| `_cmd_finalize_steps.py:68` `_RESOLVED_ASK_LANE_VALUES` | `off, standard, full` — **and `set-lane` validates against THIS**, so it rejects `minimal` |

`_manifest_lanes.py:19` `LANE_TIERS = ('minimal','standard','full')` is the lattice; `off` and `ask` are
**dispositions, not tiers**. The third list may be legitimately narrower (its docstring calls those *"the
resolved answers an `ask` can produce"*), but **`set-lane` accepting a different set than
`validate_lane_override` is a divergence a user hits directly.**

⇒ **Settle which is authoritative, then document.** ⚠ **Documenting the current state as-is would encode
a contradiction into the user doc**, which is worse than the present silence.

⚠ Also disambiguate the two unrelated concepts that share the word — `configuration.adoc:93` names both
in one sentence: the **phase-1-init planning lane** (`light`/`deep`) and the **finalize step lane**
(above). They share nothing but the noun.

### D3 — split, with pointer stubs

Execute the D1 boundaries. Each extracted section leaves a `:52`-style stub. **No content is deleted in
this deliverable** — every line either moves or stays.

### D4 — close the coverage gap

Document the uncovered knobs D1 identified, and **replace `:49`'s hand-written parenthetical** per
finding 2 — generated or pointer, never a new prose list.

### D5 — evict meta-project content to `doc/developer/`

Move `:230`'s caveat and **sweep for prose-embedded mentions** like `:212` — ⚠ **a section-level move
will miss those**; grep for `meta-project`, `sync-plugin-cache`, `deploy-target`, `target/claude`,
`marketplace/bundles` across the whole file. Re-point or relocate per D1's finding-3 verdict.

### D6 — verification

Xref integrity across the split (every moved anchor still resolves, including from files *outside*
`doc/user/`), and the doc-lint / asciidoc gates. ⚠ **The stubs are load-bearing for this** — an extraction
without a stub silently breaks inbound xrefs.

## Expected surface

- OBSERVED: `doc/user/configuration.adoc` (587 lines, 26 subsections — counted this pass)
- OBSERVED: `doc/user/` siblings `efforts.adoc` (195), `parallelism-and-locking.adoc` (55),
  `terminal-title.adoc` — the extraction targets and the stub precedent
- HYPOTHESIS: `doc/developer/` destination file(s) — not yet chosen
- REPORTED (not orchestrator-verified): that `data-model.md` is a complete knob enumeration. **D1 must
  confirm it is the population and not itself a sample.**
- HYPOTHESIS: inbound xrefs from `doc/concepts/`, `doc/developer/`, and bundle docs

**Disjointness:** `doc/**` only — **disjoint from every plan in the queue**, all of which sit in
`marketplace/bundles/**`. ⚠ Except **PLAN-TRUTH-009** (`surface-every-knob-in-marshal-json`): no file
overlap, but a **shared population**. See sequencing.

## Dependencies and Sequencing

- ⚠ **Prefer AFTER PLAN-TRUTH-009.** TRUTH-009 materialises every seeded-able knob into `marshal.json` so
  the config file becomes the discovery surface. If it lands first, D1's population is derivable from the
  materialised file; if this plan lands first, D4 documents a set that TRUTH-009 will then widen, and the
  doc goes stale immediately. **They are not duplicates** — TRUTH-009 is code, this is docs — **but they
  must share one derived population.**
- Not blocked by anything else. `doc/**` collides with nothing in flight.

## Notes

- Low priority by operator instruction.
- ⭐ The operator's framing *"verify all config aspects available and ensure that each is documented"* is a
  **population-derivation gate**, which has been the highest-value deliverable in three consecutive plans
  this week. D1 is that gate; it mutates nothing and should be graded on its own.

## Write-Boundary

`doc/**` only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
