# PLAN-CIS-059: Fold `pm-code-intelligence` into the core bundle

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Authored by the orchestrator on 2026-08-22 at operator direction, after analysing where the
> bundle came from and why it is standalone. See § Provenance for that analysis.

## Objective

`marketplace/bundles/pm-code-intelligence/` is a whole registered bundle that exists to hold **one
resolver identity**. It ships no skill domain, no scripts, and no configuration — its manifest
returns `[]` from `get_skill_domains()` and declares `applies_to_module()` permanently
non-applicable, because, in its own words, asserting a domain with no skills *"would put an empty
entry in front of every domain-selection surface."* Four tracked files.

It is standalone because of a **registration-slot collision, not a domain boundary** (§ Provenance).
This plan folds it into `plan-marshall`, whose Axis-C slot is free, and retires the bundle.

## Deliverables

Five deliverables.

1. **D0 — Re-ground the slot analysis, and take the inertness decision (gating).** Before moving
   anything, re-derive at HEAD that (a) `plan-marshall`'s `extension.py` still registers **no**
   Axis-C resolver, and (b) `pm-dev-python`, `pm-documents` and `pm-plugin-development` still hold
   `python`, `documentation` and `markdown` respectively. If core's Axis-C slot has been taken since
   2026-08-22, **halt and report** — the move is unavailable and the plan re-scopes.

   ⚠ **Then settle the one genuine objection, and record the answer either way.** The harvest that
   materializes this resolver's input is `pm-plugin-development`'s, and it covers **marketplace-bundle
   modules only**. Moving the resolver into core therefore registers `lsp` for **every consumer
   project**, including those that will never carry a harvest record. That is not a false-signal
   defect — the resolver reports `ran: false` with a reason, honestly — but it is a **permanently
   inert registration** for most consumers, where today the bundle is simply not installed. Decide
   explicitly whether that is acceptable, and write the reasoning into the shipped documentation.
   ⛔ **Do not treat this as settled by the fact that the plan exists.**

2. **D1 — Move the resolver onto core's extension.** `plan-marshall`'s
   `skills/plan-marshall-plugin/extension.py` becomes
   `Extension(ExtensionBase, PathAttributionBase, DerivationResolverBase)` and gains
   `derivation_resolver_id()`, `derive_edges()` and `derivation_file_patterns()`, moved from the
   retiring extension.

   ⛔ **`derivation_resolver_id()` MUST keep returning the exact string `lsp`.** Resolver activation
   is bound by **id** in the machine-local `derivation_resolvers` config, and every persisted edge in
   `derived.json` carries `lsp` in its `producers[]`. Changing the id would silently orphan both.
   ⛔ **`derive_edges()` must remain a pure function of its arguments** — no filesystem access, no
   subprocess, no server boot. That constraint is the whole reason the harvest is a discovery-time
   engine, and it does not relax by moving.

3. **D2 — Retire the bundle and its registration.** Delete the four tracked files under
   `marketplace/bundles/pm-code-intelligence/`, drop its entry from
   `marketplace/.claude-plugin/marketplace.json`, and update the production-bundle count wherever it
   is asserted — including `CLAUDE.md`'s *"11 production bundles with 157 registered components"* and
   the `_PRODUCTION_BUNDLES` roster in `test/plan-marshall/extension-api/test_extension_discovery.py`.

   ⛔ **The roster is a population-derived guard; keep it that way.** It exists to fail when the
   bundle set changes. Update the expected set — never weaken the assertion to accommodate the move.

4. **D3 — Relocate the tests, and prove the resolver still resolves.** `test/pm-code-intelligence/`
   (one 257-line module) moves under the core bundle's test tree. ⛔ **Add a test that fails if the
   resolver is not discovered from its new home** — a suite that passes because the resolver was
   silently dropped from discovery is the exact vacuity this epic exists to remove, and a relocation
   is precisely when it can happen. A matched negative control is required: strip the
   `DerivationResolverBase` base from core's extension and the new test must go red.

5. **D4 — Correct every document that explains the current topology.** Five surfaces name the bundle
   or its rationale:
   - `extension-api/standards/ext-point-derivation-resolver.md` — **two** mentions, one of them the
     § "Why the markdown, python, documentation, and lsp joins are separate resolvers" paragraph,
     which names the four-bundle split as *"what makes per-edge provenance expressible at all."*
     ⭐ **That claim stays TRUE after the move** — provenance rides the returned id, not the bundle
     name — but the sentence names the wrong set and must be re-derived.
   - `extension-api/standards/ext-point-domain-bundle.md` — two mentions
   - `extension-api/standards/extension-contract.md` — one mention
   - `README.md` and `doc/user/installation.adoc` — one each
   - `pm-plugin-development/skills/tools-corpus-language-server/SKILL.md` — one cross-reference

   ⚠ **Re-derive that list at outline.** It was swept on 2026-08-22 and the tree moves. `doc/plans/**`
   hits are historical run reports and are **out of scope** — do not edit them.

**Split verdict:** five deliverables, below the ~6 threshold. D1 and D2 are one indivisible change
(the resolver cannot be in two places, nor in none), so splitting them would land a broken tree.

## Claim Labels

- **OBSERVED**: the bundle was created by PR **#1243** (`c86de8b5a`), the landing of
  **`PLAN-CIS-026`** — read from `git log --diff-filter=A`. Only three commits have ever touched it:
  #1243, #1252, #1321.
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: git log --diff-filter=A over marketplace/bundles/pm-code-intelligence/ returns exactly three commits: c86de8b5a (#1243, PLAN-CIS-026 landing, creating commit), c0b4f3e8e (#1252), 2c40e7027 (#1321). Matches the claim exactly.
- **OBSERVED**: `plan-marshall`'s extension is `Extension(ExtensionBase, PathAttributionBase)` — it
  registers an Axis-D attributor and **no Axis-C resolver**, so its Axis-C slot is free.
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: extension.py:31 reads 'class Extension(ExtensionBase, PathAttributionBase)' — no DerivationResolverBase, so no Axis-C resolver and the slot is free. Confirmed against the four sibling bundles, each of which DOES carry DerivationResolverBase.
- **OBSERVED**: the Axis-A registration site is the **bundle**, one resolver per site —
  `ext-point-derivation-resolver.md` § "One registration site registers at most one resolver".
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: ext-point-derivation-resolver.md:80 carries the quoted heading verbatim: 'One registration site registers at most one resolver', and :87 states the cardinality is structural because derivation_resolver_id() returns a single string. :236 confirms Axis-A site = bundle for all four resolvers incl. lsp.
- **OBSERVED**: `pm-dev-python` → `python`, `pm-documents` → `documentation`,
  `pm-plugin-development` → `markdown`, `pm-code-intelligence` → `lsp`. Read from each
  `extension.py`.
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: derivation_resolver_id() return values read from each extension.py: pm-dev-python returns 'python', pm-documents 'documentation', pm-plugin-development 'markdown', pm-code-intelligence 'lsp'. All four mappings match the claim.
- **OBSERVED**: the bundle ships four tracked files; `__pycache__` present on disk is untracked
  build residue, not a committed artifact.
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: git ls-files over the bundle returns exactly four paths: .claude-plugin/plugin.json, README.md, skills/plan-marshall-plugin/SKILL.md, skills/plan-marshall-plugin/extension.py. Count and the untracked-__pycache__ distinction both hold.
- **HYPOTHESIS**: no consumer-visible behaviour changes, because activation is keyed on the resolver
  **id** and the id is unchanged — confirm/refute against the `derivation_resolvers` config reader
  and the `derived.json` `producers[]` writer at outline (verify-at-outline). **This is the plan's
  central risk.**
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Both named surfaces check out. Config reader: _cmd_client_query.py:1006-1010 keys activation on record.get('id') passed to is_derivation_resolver_enabled(resolver_id, section) — the resolver ID, never the bundle. Producers writer: :880-883 stamps producers[] with resolver ids, reserving 'declared' and 'sibling-cross-link' for non-resolver sources. The plan's central risk is settled FAVOURABLY, conditional on derivation_resolver_id() continuing to return 'lsp', which the spec already mandates.
- **HYPOTHESIS**: `doc/concepts/code-intelligence.adoc` describes this topology and needs the same
  correction — it did **not** match a `pm-code-intelligence` name search, so it may describe the
  resolver without naming the bundle. Confirm/refute at outline (verify-at-outline).
  - verdict: contradicted | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: yes | evidence: SPLIT VERDICT, actionable half REFUTED. The evidential half holds: doc/concepts/code-intelligence.adoc contains no occurrence of 'pm-code-intelligence'. But the conclusion 'needs the same correction' is FALSE. Its resolver section (:80-100, [#lsp-derivation-resolver]) describes the LIFECYCLE argument only and never names the owning bundle; its sole bundle-path link (:42) points at plan-marshall/skills/lsp-client/, not at pm-code-intelligence. A fold that keeps the resolver id 'lsp' therefore requires NO edit to this document. Re-scoped: the Expected Surface entry is struck per the spec's own verify-first rule.
- **Verify-first clause:** re-derive the reference sweep at outline. Any surface that has since been
  corrected is struck, not re-edited.
  - verdict: corroborated | checked_at: b95d78437e5b6e20fdfc66198a71c91b52380ad5 | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Sweep re-derived at this HEAD rather than deferred. All 13 declared Expected Surface paths resolve under git ls-files. One strike identified per the clause's own rule: doc/concepts/code-intelligence.adoc needs no correction (claim 6). README.md:99 and doc/user/installation.adoc:100 DO name the bundle and genuinely need correction; CLAUDE.md does not name it but carries an 11-bundle count that a fold changes, so it stays in scope.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-code-intelligence/` — the four tracked files, deleted
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py` — gains the Axis-C axis
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/SKILL.md` — documents it
- **OBSERVED**: `marketplace/.claude-plugin/marketplace.json` — registry entry removed
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-domain-bundle.md`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/extension-contract.md`
- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/SKILL.md`
- **OBSERVED**: `test/plan-marshall/extension-api/test_extension_discovery.py` — `_PRODUCTION_BUNDLES`
- **OBSERVED**: `test/pm-code-intelligence/plan-marshall-plugin/test_lsp_derivation_resolver.py` — relocated
- **OBSERVED**: `README.md`, `doc/user/installation.adoc`, `CLAUDE.md`
- ~~**HYPOTHESIS**: `doc/concepts/code-intelligence.adoc` (verify-at-outline)~~ — ⛔ **STRUCK
  2026-08-24 by the `cleanup` re-grounding pass** (§ Claim Labels claim 6, `verdict: contradicted`,
  `rescoped: yes`). The verify-at-outline check was performed at HEAD `b95d78437` and came back
  negative: that document's resolver section describes the LIFECYCLE argument and never names the
  owning bundle, and its only bundle-path link points at `plan-marshall/skills/lsp-client/`. A fold
  that keeps the resolver id `lsp` requires no edit to it. ⭐ Struck, not re-edited — which is
  exactly what this spec's own verify-first clause instructs. Do not re-add it at outline.

⛔ **Out of scope**: `doc/plans/**`. Those are historical run reports of already-landed plans; a
report is a dated record of what a run saw and is never retro-edited.

## Dependencies and Sequencing

- **Depends on**: none.
- **Overlaps with**: `PLAN-CIS-049` touches `extension-api/standards/` (a different file,
  `module-discovery.md`) and `test/`. File-level disjoint, but **re-check at emit** — this is the
  same skill directory.
- **Adjacent to**: `PLAN-CIS-052` — verified disjoint by `corpus cross-check`, so the two may be
  emitted as a pair.
- ⚠ **Removing a bundle is a plugin-cache event.** After merge the cache needs
  `/sync-plugin-cache` and the executor needs regeneration, and a removed bundle is exactly the
  input that exercises the orphan-GC path. Expect the registry-pin inversion to be live afterwards
  and **check the pin before the next plan launch**.

## Provenance — where this bundle came from, and why it is standalone

**It is the artifact of a partially-refuted plan.** `git log --diff-filter=A` puts its creation in
**PR #1243**, the landing of `PLAN-CIS-026` (`200-lsp-derivation-resolver`). That plan's independent
post-run audit returned **PARTIALLY REFUTED**, 2 of 6 deliverables confirmed, and found that **the
resolver derives zero module edges on this repository** — no cross-bundle reference resolves,
because marketplace bare imports depend on the generated executor's runtime `sys.path`, which
pyright at the workspace root cannot follow. See `landings/PLAN-CIS-026.md` and `epic.md`
§ Open Defects D9.

**The standalone shape is a slot collision, not a domain boundary.** On Axis-A the registration site
is the *bundle*, and a site registers at most one resolver. The two bundles `lsp` naturally belongs
with both had that slot occupied:

[the resolver's data comes from `pm-plugin-development`'s harvest] → **slot held by `markdown`**
[the resolver answers a Python question] → `pm-dev-python` → **slot held by `python`**

Core's slot was free — but core's extension had only opted into Axis-D, so it did not present itself
as a resolver host, and a new bundle was created instead.

**The bundle's own README argues the right rule against the wrong alternative.** It says an
LSP-derived edge set added to `pm-dev-python` *"would be stamped `python` and become
indistinguishable from that bundle's AST-import join"* — which is correct, and is a real argument
against **that** merge. It never considers `plan-marshall`, whose slot is free. ⭐ The rule the
README invokes explicitly warns against the reading it then relies on:
*"Do not read this as 'one resolver per bundle'."*

**The feature is currently spread across three bundles**: the client (`plan-marshall:lsp-client`,
already core), the harvest engine (`pm-plugin-development:…:lsp_harvest`), and the resolver
(`pm-code-intelligence`). This plan removes one of those splits. It does **not** move the harvest
engine — that would collide with `markdown` and is out of scope.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-059-fold-pm-code-intelligence-into-core.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message.
