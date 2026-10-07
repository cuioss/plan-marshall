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

# The documentation domain owns the documentation corpus

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

The documentation corpus — `doc/**` plus the repo-root `README.md` / `CLAUDE.md` / `AGENTS.md` /
`CONTRIBUTING.md` family — is indexed **twice**: once by the documentation module and once by the
root module, whose inventory includes the same files. A consumer asking *"how many files match?"*
gets a **row** count spanning both indexes, not a **file** count.

⭐ **This is the mechanism behind a standing defect**: a path search returning `count: 2` for a single
physical file, indexed once per attributing module. The duplication is **not** a catch-all bug — the
root module is an alias for the real root module, so its inventory legitimately contains repo-root
files. It is root-crawl-plus-domain-claim, and the remedy is a **defined precedence**, not a decree
that the root stops indexing documentation.

The documentation bundle already implements module discovery (directory-based, over doc directories),
so the domain that understands documentation already has a discovery seat. It does **not** have an
attribution or derivation face.

## Goal

The documentation domain **owns** its corpus: it claims those files through the attribution seam with
provenance, the duplication against the root crawl is resolved by a documented precedence rather than
by accident, and the domain gains the one capability only it can provide — resolving cross-document
references and reporting the ones that do not resolve.

## Deliverables

1. **D1 — doc-corpus attribution claim.** Claim `doc/**` and the repo-root documentation family for
   the documentation module, with provenance, **through the existing attribution seam**.
   *Done when:* the claim is registered through the seam and the claimed files resolve to the
   documentation module.
2. **D2 — de-duplication against the root module.**
   ⚠ **This is the load-bearing deliverable and the riskiest.** Define an explicit precedence between
   an owned claim and the root crawl, and **document it**.
   ⛔ **Do not "stop indexing `doc/**` in the root" by fiat** — the root module is a real module with
   a legitimate claim on repo-root files.
   *Done when:* one physical file yields one row from the affected query surfaces, the precedence is
   written down, and the consumer enumeration below has been done.
3. **D3 — doc-surface search.** Content search over the owned corpus, answering *"which documents
   mention X"* — which a path glob structurally cannot.
   ⛔ **This supplies the doc-domain implementation BEHIND the existing content-search seam and MUST
   NOT ship a second, parallel search verb.** If that seam is not present in the clone, **narrow this
   deliverable to the corpus claim and defer search** — say so in the report rather than building a
   parallel path.
   *Done when:* a content query over the doc corpus is answerable through the existing seam.
4. **D4 — cross-document reference resolution.** Resolve `xref:` targets and markdown links, and
   **report the unresolvable ones**. This is the capability that makes the *deleted heading / dangling
   anchor* class detectable, and it is domain knowledge only this bundle holds.
   *Done when:* a deliberately broken reference is reported as unresolvable, and a valid one is not.
5. **D5 — documentation.** The doc-surface ownership and search contract in the documentation bundle,
   plus the attribution-model addition to `doc/concepts/code-intelligence.adoc`.
   *Done when:* the precedence rule from D2 is stated where a future reader will look for it, not
   only in the run report.

Five deliverables — at the split guard's edge; evaluate a split before implementing.

## Out of scope

- **A second content-search verb.** ⛔ Excluded absolutely: one already exists behind a seam, and a
  parallel verb would fork the coverage contract that makes a zero result trustworthy.
- **Editing the architecture core.** Excluded because the claim goes through the seam. ⚠ **If this
  plan finds itself editing core beyond registering a claim, that means the seam is incomplete — loop
  back and report it rather than patching core here.**
- **Sweeping the whole repo root into the documentation module by glob.** Excluded because
  `CLAUDE.md` and `AGENTS.md` are **agent-instruction files, not prose documentation**, and may
  belong with the root module or with the core bundle. **Decide per file.**
- **Fixing the row-versus-file count in every consumer.** Excluded: this plan fixes the *source* of
  the duplication. ⚠ But see the verify-first claim — a consumer that already compensates will
  double-correct.

## Expected surface

- `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/` — the extension manifest and its
  extension module. **OBSERVED.**
- A new or extended search/resolution script under `marketplace/bundles/pm-documents/skills/`.
  **HYPOTHESIS** — placement depends on the content-search seam's shape; verify at outline.
- `doc/concepts/code-intelligence.adoc` — the attribution model. **OBSERVED.**
- `test/pm-documents/` — tests. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/manage-architecture/` — ⚠ **only if** de-duplication
  requires a core precedence change. See Out of scope.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The doc corpus is indexed by both the documentation module and the root module, and a single file returns multiple rows | **OBSERVED** | ⛔ **Re-derive in the clone**: query the module inventories and a path search for one known doc file. **The file counts stated in the originating spec are LEADS — do not carry them.** |
| The root module is an **alias for the real root module**, resolved once in the query client | **OBSERVED** | The alias resolution in `manage-architecture`'s query client. Read it — this is what makes the duplication a precedence question rather than a bug. |
| The documentation bundle implements module discovery but declares no derivation or attribution face | **OBSERVED** | Its plugin manifest, plus the module-discovery standard's list of existing implementors. Both in the clone. |
| De-duplication is safe for every consumer of the files inventory | **HYPOTHESIS — and it is D2's real risk** | ⛔ **Enumerate the consumers before scoping.** A consumer that today reads both rows and de-dupes itself will **double-correct** once the source de-dupes. **Derive the population; do not sample.** |
| The repo-root documentation family should move to the documentation module | **HYPOTHESIS** | Decide **per file** at outline. ⚠ Agent-instruction files are not prose documentation. |
| The content-search seam exists and D3 can sit behind it | **HYPOTHESIS** | Verify in the clone. **If absent, D3 narrows to a deferral** — that is a sanctioned outcome, building a parallel verb is not. |

An asserted **absence** ("no doc-domain search capability exists") is verified exactly as an asserted
presence — confirm it before building, because an unverified absence produces a second search surface
beside one that already exists.

## Verification

- **D2 is verified by the consumer enumeration, not by the query output.** A de-duplicated count that
  breaks a consumer which was compensating is a regression wearing a fix's clothes. The run report
  must list the consumers examined and state how the population was derived.
- **D4 is verified in both directions**: a deliberately dangling reference is reported, and a valid
  one is not. A resolver that reports nothing passes a positive-only test trivially.
- **D3, if deferred, is verified by the report saying so plainly** — an understated outcome is picked
  up again; an overstated one is collected as done.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Dependency.** This plan needs the attribution seam to exist; without it the only way to claim the
  corpus is to hard-code, which **is** the defect. Verify the seam is present in the clone before
  scoping — it has already landed, but confirm rather than assume.
- **Coordination.** D3 depends on the general content-search seam. Not a hard gate; narrow rather
  than fork.
- **Disjointness.** This plan touches the documentation bundle and is disjoint from the measurement
  and detector plans in this epic — a good candidate to run beside one of them.
