# PLAN-CIS-024: The Documentation-Surface Provider — pm-documents owns the doc corpus

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The documentation corpus — `doc/**`, plus the repo-root `README.md` / `CLAUDE.md` / `AGENTS.md` /
`CONTRIBUTING.md` family — is indexed **twice**: once by the `documentation` module (70 files) and
once by the root `default` module (878 `doc`-category files, which include all 70). A consumer
asking "how many files match?" gets a row count spanning both indexes, not a file count.

`pm-documents` already implements `discover_modules()` (directory-based, doc dirs), so the domain
that understands documentation already has a discovery seat. Make it the **owner** of the doc
surface: claim the corpus through PLAN-CIS-023's attribution seam, de-duplicate against the root
module, and give the domain a real search capability over the content it owns — including the
cross-document reference resolution (`xref:`, markdown links) that no other bundle can do.

## Deliverables

1. **Doc-corpus attribution claim** through PLAN-CIS-023's seam: `doc/**` and the repo-root
   documentation family, attributed to the documentation module with provenance.
2. **De-duplication against the root module.** ⚠ **This is the load-bearing deliverable and the
   riskiest.** The root `default` module is not a synthetic catch-all — it is an *alias for the
   real root module* (`_cmd_client_query.py`:620–627), so its inventory legitimately contains
   repo-root files. The fix is not "stop indexing doc/** in the root" by fiat; it is a defined
   precedence between an owned claim and the root crawl. Decide it explicitly and document it.
3. **Doc-surface search** — content search over the owned corpus, answering "which documents
   mention X", which `architecture find` (a path glob) structurally cannot. ⛔ **Coordinate with
   PLAN-CIS-001**, which owns the general content-search seam: this deliverable supplies the
   *doc-domain implementation behind* that seam, and MUST NOT ship a second, parallel search verb.
   If PLAN-CIS-001 has not landed, this deliverable narrows to the corpus claim and defers search.
4. **Cross-document reference resolution** — resolve `xref:` and markdown links to their targets,
   and report unresolvable ones. This is the capability that makes ADR-007's *deleted heading /
   xref anchor* survivor class detectable, and it is domain knowledge only `pm-documents` holds.
5. **Documentation** — the doc-surface ownership and search contract in `pm-documents`, plus the
   attribution model addition to `doc/concepts/code-intelligence.adoc`.

## Claim Labels

- **OBSERVED (probed against HEAD 2026-08-01)** — `architecture files --module documentation`
  returns 70 files under a single `doc` category; `architecture files --module default` returns
  878 `doc`-category files including the same `doc/adr/**` entries. `doc/concepts/code-intelligence.adoc`
  resolves via `which-module` to `documentation`; `README.md` resolves to `default`.
- **OBSERVED** — `architecture find --pattern "*code-intelligence*"` returns `count: 2` for one
  physical file, indexed as `default`/`doc` and `documentation`/`doc`. **This is the mechanism
  behind the epic's standing "`find` returns a ROW count, not a FILE count" open defect** — that
  defect asked whether dual-module indexing predates #1056; it does not depend on #1056 at all.
- **OBSERVED** — `default` is an alias for the real root module, resolved once at
  `_cmd_client_query.py`:620–627 — so the duplication is root-crawl-plus-domain-claim, **not** a
  catch-all bug.
- **OBSERVED** — `pm-documents` is listed as an existing `discover_modules()` implementor
  ("Directory-based (doc dirs)") in `extension-api/standards/module-discovery.md` § Existing
  Implementations, and `pm-documents/skills/plan-marshall-plugin/SKILL.md` declares
  `get_skill_domains` / `provides_triage` / `provides_recipes` — and **no** derivation or
  attribution face.
- **HYPOTHESIS** — de-duplication is safe for every `files` / `find` / `which-module` consumer.
  Confirm/refute by enumerating consumers of the files-inventory readers (verify-at-outline).
  ⛔ **Derive the population.** A consumer that today reads both rows and de-dupes itself will
  double-correct once the source de-dupes.
- **HYPOTHESIS** — the repo-root documentation family (`README.md`, `CLAUDE.md`, `AGENTS.md`,
  `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE.md`) should move to the documentation module.
  Confirm/refute at outline. ⚠ **`CLAUDE.md` and `AGENTS.md` are agent-instruction files, not
  prose documentation** — they may belong with the root module or with plan-marshall. Decide
  per-file, and do not sweep the whole root by glob.
- **Verify-first clause**: D2 changes counts that other components may already compensate for.
  Enumerate before scoping; refutation loops back and re-scopes.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/` — extension manifest and `extension.py`
- **HYPOTHESIS**: a new or extended search/resolution script under `marketplace/bundles/pm-documents/skills/` (verify-at-outline — placement depends on PLAN-CIS-001's seam shape)
- **OBSERVED**: `doc/concepts/code-intelligence.adoc` — attribution model
- **OBSERVED**: `test/pm-documents/` — tests
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-architecture/` — ⚠ **only if** de-duplication requires a core precedence change. If this plan finds itself editing core beyond registering a claim, **that means PLAN-CIS-023's seam was incomplete — loop back rather than patching core here.**

## Dependencies and Sequencing

- **Depends on**: **PLAN-CIS-023** (the attribution seam). ⛔ Hard gate — without it this plan can
  only hardcode, which is the defect.
- **Coordinates with**: **PLAN-CIS-001** (content-search seam) for D3. Not a hard gate: D3 narrows
  to a deferral if PLAN-CIS-001 has not landed. ⛔ **Never ship a second search verb.**
- **Overlaps with**: nothing in the current queue on `pm-documents`. ✅ **Surface-disjoint from
  every WS-02/WS-04/WS-05 plan** — a good second-slot candidate once PLAN-CIS-023 lands.
- **Adjacent to**: `manage-architecture` core — claimed through the seam, never edited here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-024-documentation-surface-provider.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
