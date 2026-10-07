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

# Remove the LSP-shaped query facade — one vocabulary, no shim

**Epic:** code-intelligence-substrate
**Branch prefix:** chore — maintenance/refactor: removes a just-shipped additive layer, no behaviour change to any kept verb

## Problem

Plan `130-lsp-shaped-query-api` (PR #1207, merged) added an `lsp` subcommand group to the
`manage-architecture` query client — `lsp hover`, `lsp references`, `lsp workspace-symbol`,
`lsp definition` — as an **additive facade**. Each subcommand is a thin pass-through that dispatches
to an existing verb and returns its answer unchanged: `hover`→`module`, `references`→`impact`,
`workspace-symbol`→`find`, `definition`→`resolve`. It renames nothing and removes nothing.

That is a **duplication** (two command names for one operation) wrapped in a **shim** (four
forwarding handlers). This repository is pre-1.0 and carries no backward-compatibility obligation, so
a synonym layer buys nothing and costs continuously: a second vocabulary to learn, document, test,
and keep in sync with the verbs it mirrors. The facade has **zero adoption** — nothing outside its
own definition, its own test, and the docs that describe it invokes it.

The facade also front-ran real work. The epic's own `240-skill-lsp-server.md` (§ Notes) anticipated
this exact outcome: it expected the query-vocabulary plan to make the substrate genuinely *speak*
`definition`/`references`/`hover`, and warned that **"if it descoped to an additive facade, this plan
absorbs the translation work and must be re-scoped upward."** Plan 130 is that descope — it added LSP
*vocabulary* without LSP *substance*. The substance belongs to `200-lsp-derivation-resolver`
(real symbol edges) and `240-skill-lsp-server` (a real editor/agent surface), not to a verb alias.

**Mechanism (the facade, as landed on `main`).** Argparse registration and dispatch in
`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py`; four
pass-through handlers in `.../scripts/_cmd_client_handlers.py`; re-exports in `.../scripts/_cmd_client.py`;
a dedicated test `test/plan-marshall/manage-architecture/test_lsp_facade.py`; and facade documentation
in `client-api.md`, `SKILL.md`, `doc/developer/lsp-query-facade.adoc`, `doc/concepts/code-intelligence.adoc`,
`doc/user/code-search.adoc`, and `doc/developer/README.adoc`. Exact locations are enumerated under
**Expected surface** as leads to re-derive.

## Goal

The architecture query client exposes exactly **one** vocabulary — its established verbs. The `lsp`
command group, its test, and every piece of its documentation are gone, with no dangling
cross-reference left behind. No verb the facade wrapped changes its name, arguments, or behaviour.
The three genuinely-new pieces plan 130 also shipped — the `capabilities` report, the refine
`UNDERIVABLE` guard, and the `search --content` measurement contract (`--ignore-case`, `file_count`)
— are untouched. `./pw verify` is green.

## Deliverables

Each deliverable is independently verifiable. D0 is a gate.

1. **D0 — GATE: re-derive the removal surface and re-confirm zero consumers.**
   Before deleting anything, re-run the discovery in *this clone* (the tree may have moved since this
   plan was authored): (a) re-list every facade definition/test/doc site, and (b) search the whole
   tree for any *invocation* of `architecture … lsp`, `cmd_lsp_`, or `lsp hover|references|workspace-symbol|definition`
   **outside** the facade's own definition, its test, the docs that describe it, and the historical
   `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/` records.
   *Done when:* the current removal surface is re-listed from the clone **and** the consumer set is
   confirmed empty.
   ⛔ **On a non-empty consumer set: HALT.** Record which consumer invokes the facade and where, and
   do **not** delete. A *used* shim needs its consumer migrated to the underlying verb first — that is
   a change of scope this run **records as a proposal for the operator**, never one it makes silently.

2. **D1 — Retire the `lsp` command group (code + test).**
   Remove, in `manage-architecture/scripts/`: the `lsp` subparser block and its four sub-subcommands
   in `architecture.py`; the `cmd_lsp_*` handler imports and the `elif args.command == 'lsp':`
   dispatch branch; the four `cmd_lsp_hover` / `cmd_lsp_references` / `cmd_lsp_workspace_symbol` /
   `cmd_lsp_definition` handlers in `_cmd_client_handlers.py` (with their section banner and the
   in-code pointer comment to the removed doc section); and the four re-exports in `_cmd_client.py`.
   Delete `test/plan-marshall/manage-architecture/test_lsp_facade.py` wholesale (it is 100 % facade;
   its `test_residue_verbs_remain_reachable_unchanged` case asserts behaviour already covered by the
   per-verb tests such as `test_graph_queries.py`). ⛔ The wrapped verbs `module`/`impact`/`find`/`resolve`
   and their handlers are **not** touched.
   *Done when:* `architecture … lsp hover` (and the other three) exits with an argparse *invalid
   choice* error; the four wrapped verbs answer identically to before; `./pw quality-gate` and the
   `manage-architecture` test module are clean.

3. **D2 — Remove the facade's documentation (surgical; one hazard).**
   Delete `doc/developer/lsp-query-facade.adoc` wholesale. Excise the facade row **and** the facade
   section from each of: `client-api.md` (Command-Summary row + the `## LSP-shaped query facade`
   section), `SKILL.md` (Command-Groups row + the `### lsp` canonical-invocation block),
   `doc/concepts/code-intelligence.adoc` (the `== The query vocabulary: an LSP-shaped facade` section),
   `doc/user/code-search.adoc` (the `== The same verbs, in LSP vocabulary` section), and the index
   bullet in `doc/developer/README.adoc`. Prune every dangling `xref:`/name-anchor left behind (the
   concepts-page and developer-README links to the deleted `.adoc`, and the "see client-api §
   LSP-shaped query facade" name-anchors).
   ⛔ **HAZARD — do not over-delete `SKILL.md`.** The lines immediately *under* the `### lsp` heading
   (around `552-560` at authoring time — **re-derive**, do not trust the number) are **`search`-verb
   content** ("Anchors are per line", "Payload boundary", "Zero-result semantics", "See client-api.md
   § search"), physically misplaced beneath the wrong heading. They must be **preserved** and moved
   under the `### search` block, not removed with the facade section.
   *Done when:* no live document mentions the `lsp` facade; no dangling `xref:` or name-anchor to the
   removed doc/section remains anywhere; the misplaced `search` content survives; plugin-doctor is clean.

4. **D3 — Confirm the single-vocabulary invariant.**
   Full `./pw verify` → SUCCESS, plus a whole-tree grep proving no `architecture lsp`, `cmd_lsp_`, or
   `lsp hover|references|workspace-symbol|definition` invocation-form reference survives outside the
   historical `doc/plans/code-intelligence-substrate/130-*` records (which stay as history).
   *Done when:* `./pw verify` is green and the grep's only surviving hits are those historical
   plan-130 records.

## Out of scope

- **Renaming any query verb to LSP vocabulary** (`module`→`hover`, etc.). Excluded because the goal is
  to *remove a shim*, not to adopt a new vocabulary — and the blast radius is enormous: the wrapped
  verbs are among the most-embedded in the repository (`resolve` ~117 references across ~65 files,
  `find` ~60, reaching CLAUDE.md hard-rules, the persona agent-behaviour standards, and multiple
  build/arch-gate bundles). If LSP naming is ever wanted it is a separate, deliberate decision, not a
  side effect of this cleanup.
- **The real `lsp-client` subsystem** — `marketplace/bundles/plan-marshall/skills/lsp-client/`, the
  `manage-run-config` language-server settings, the `execute-task` opt-in `lookup` verb, and
  `doc/user/lsp-code-intelligence.adoc`. Excluded because it is an **unrelated** feature (a real
  Language Server Protocol transport client); the shared substring `lsp` is coincidental, and a
  match-on-"lsp" deletion would destroy working code. It is the highest-risk confusion in this plan.
- **The `capabilities` report, the refine `UNDERIVABLE` guard, and the `search` measurement contract**
  (plan 130's other deliverables). Excluded because each was audited as **genuinely new behaviour with
  no pre-existing equivalent** — not a shim or a duplication, so not the defect this plan closes.
- **The cosmetic vocabulary nit in `capabilities`** (it labels content-search `available`/`unavailable`
  while the other two capability rows use `derivable`/`not_derivable`). Excluded because it is a naming
  inconsistency, not a shim; folding it in would be scope drift. Recorded as a follow-up in Notes.
- **Editing the historical plan-130 records** under `doc/plans/code-intelligence-substrate/130-lsp-shaped-query-api/`.
  Excluded because they are dated records of a past run, not live documentation of current state; they
  remain as history (this is the standing carve-out for run records).

## Expected surface

Line numbers are **leads captured at authoring time** — re-derive them in the clone (D0), because a
prior edit or a merge can move every one.

**Delete wholesale (100 % facade):**

- `test/plan-marshall/manage-architecture/test_lsp_facade.py` — the facade's only test.
- `doc/developer/lsp-query-facade.adoc` — the facade's dedicated developer map.

**Surgical (remove the facade region, keep the rest):**

- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py` — `lsp`
  subparser block (~`297-342`), handler imports (~`528-531`), dispatch branch (~`606-613`).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — the
  four handlers and their banner/pointer (~`648-727`).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client.py` — re-exports
  (~`94-97`).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` — Command-Summary
  row (~`544`) + `## LSP-shaped query facade` section (~`1409-1451`).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md` — Command-Groups row (~`47`)
  + `### lsp` block (~`537-550`). ⛔ **Preserve the misplaced `search` content ~`552-560`.**
- `doc/concepts/code-intelligence.adoc` — `== The query vocabulary…` section (~`171-204`) + dangling
  xref (~`240`).
- `doc/user/code-search.adoc` — `== The same verbs, in LSP vocabulary` section (~`200-202`).
- `doc/developer/README.adoc` — the `lsp-query-facade.adoc` index bullet (~`18`).

**Do NOT touch** (the real language-server client, a separate feature): `skills/lsp-client/**`,
`skills/manage-run-config/**`, `skills/execute-task/SKILL.md` `lookup` verb, `doc/user/lsp-code-intelligence.adoc`,
`test/plan-marshall/lsp-client/**`, `doc/plans/code-intelligence-substrate/010-lsp-in-execute-lookup-and-write/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The `lsp` group's four handlers are thin pass-throughs to `module`/`impact`/`find`/`resolve`, renaming nothing | OBSERVED | `_cmd_client_handlers.py` `cmd_lsp_*` bodies — read them in the clone. |
| **The facade has no downstream consumer** — nothing outside its own definition/test/facade-docs and the historical plan-130 records invokes it | OBSERVED — **and an asserted ABSENCE (highest-risk claim here)** | D0's whole-tree grep for `architecture lsp` / `cmd_lsp_` / the four verb names. Git-reachable; **re-derive before deleting.** ⛔ A non-empty result changes the plan — HALT per D0. |
| No committed generated/target/plugin-cache copy carries the facade text (only gitignored `.plan/temp/` pytest scratch, which regenerates clean) | OBSERVED | D0's search of `marketplace/targets/`, any `target/`, and `.claude/`. Re-derive. |
| The removal surface is exactly the files listed under Expected surface | OBSERVED | The three research sweeps that produced this plan; re-derived and re-listed by D0. |
| `capabilities`, the `UNDERIVABLE` guard, and `search --ignore-case`/`file_count` are new behaviour, not shims | OBSERVED | Each reuses existing producers to answer a question no prior command answered; none is a one-line forward. Confirmed against the handlers; keep them. |
| In `SKILL.md`, the lines under the `### lsp` heading are `search` content, not facade content | OBSERVED | Read the block in the clone — it names anchors/payload/zero-result and points at `client-api.md § search`. Preserve it. |
| `240-skill-lsp-server.md` anticipated this facade descope and does not depend on the facade surviving | OBSERVED | `doc/plans/code-intelligence-substrate/240-skill-lsp-server.md` § Notes ("if it descoped to an additive facade, this plan absorbs the translation work"). Git-reachable. |

An asserted **absence** ("the facade has no consumer") is verified exactly as an asserted presence and
is the higher-risk half: an unverified absence would delete a command something quietly depends on.
D0 is that verification, and it **halts** rather than guessing.

## Verification

- **Per-deliverable "done when"** conditions above.
- **Full `./pw verify` → SUCCESS** per the lane build gate (this plan changes production Python, so the
  build gate runs).
- **The single-vocabulary invariant (D3):** a whole-tree grep for `architecture lsp`, `cmd_lsp_`, and
  `lsp hover|references|workspace-symbol|definition` returns only the historical `doc/plans/.../130-*`
  records — nothing in source, tests, or live docs.
- **The wrapped verbs are unchanged:** the existing per-verb tests (`test_graph_queries.py`,
  `test_architecture_input_validation.py`, `test_cmd_resolve.py`, the `find`/`which-module`/`module`
  tests) still pass without modification — evidence the removal touched only the facade.
- **Cold read of the post-removal query docs (dispatch the lane's pre-PR verification sub-agent).**
  This is the interpretation check, not an "implemented as specified" check: have an independent reader
  take `client-api.md`, `SKILL.md`, `doc/concepts/code-intelligence.adoc`, and `doc/user/code-search.adoc`
  **cold** and report (a) whether any trace of an "LSP vocabulary/facade" survives as if still offered,
  (b) whether the query surface now reads as **one** coherent vocabulary, and (c) whether the `search`
  documentation in `SKILL.md` is intact and correctly placed (the hazard). The correct reading is
  "one vocabulary, no facade, search docs intact." Any other reading means an edit was incomplete.
- **plugin-doctor clean** — the marketplace-wide structural lint over `SKILL.md`/`client-api.md`.

## Notes

- **Origin.** This plan was authored from a **direct operator request** — "pre-1.0, no duplications
  nor shims; remove the facade" — **not** derived from an orchestrator plan spec under
  `.plan/local/orchestrator/` (which is git-ignored and not in the clone; do not look for it). There is
  therefore **no orchestrator parent plan** for the collect step (`cloud-bridge.md` § Path 3) to
  transition to `shipped`; this is a standalone correction of the merged `130` plan. Record that in the
  landing so a later collector does not hunt for a parent that does not exist.
- **Why this is a shim and why pre-1.0 matters.** A facade over a stable public API earns its keep by
  preserving old callers; here there are no old callers to preserve (zero adoption) and no stability
  obligation (pre-1.0). What remains is pure duplication cost.
- **Alignment with the epic.** Real LSP substance is owned by `200-lsp-derivation-resolver` (symbol
  edges) and `240-skill-lsp-server` (the surface). Removing the vocabulary alias does not remove any
  capability — it clears the way for those plans to add LSP *meaning* rather than inherit an empty
  *name*. `240` already accounts for the "additive facade" case, so nothing downstream breaks.
- **Sequencing.** Prefer landing this **before** `240-skill-lsp-server` runs, so `240` is scoped
  against a clean single-vocabulary surface rather than reasoning around a facade it must strip. It is
  surface-disjoint from every other queued plan except `240` (shared docs) — do not run concurrently
  with `240`.
- **Follow-up (not in this plan).** The `capabilities` handler labels content-search
  `available`/`unavailable` while the other two rows use `derivable`/`not_derivable`. Harmonising that
  vocabulary is a small, separate cleanup — noted here so it is not lost, and kept out of this plan to
  avoid scope drift.
- **Priority prefix.** `135` places this as a high-priority correction immediately after the plan it
  fixes (`130`) and ahead of the queued `140`–`340`. The prefix is the operator's to adjust until the
  plan is handed to a session; it is fixed once a run starts.
