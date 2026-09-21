# PLAN-04: A developer can deploy the generated OpenCode tree in one command

epic: multiplattform
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Ingested from `archive/original-staged-specs/040-sync-opencode-inner-loop.md` and re-grounded
> against HEAD `2cd1a19c`.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim, act on what the tree says, and report divergence from the figure stated here.
- **Never edit another plan's surface**, even for an obvious adjacent fix — the neighbour may be running concurrently. Record the finding in the PR body and the inbox message instead.
- **Confirm the Expected Surface against the tree as the first action** and report — rather than silently absorb — any file the work turns out to need beyond it.

## Objective

The Claude inner loop is one command: edit `marketplace/bundles/`, run `/sync-plugin-cache`, done.
The OpenCode inner loop has no equivalent, so deploying generated `target/opencode/` output means
hand-copying with a structural rename. Ship `/sync-opencode` — a project-local skill that deploys a
generated tree into an OpenCode config directory with the singular→plural rename in one command,
removing stale entries it manages while never touching user-managed ones, testable without a live
OpenCode install. Separately, correct `distribution.adoc`, which describes a Claude-only publish
matrix and hypothetical OpenCode publication while the workflow already publishes both.

## Deliverables

1. **D1 — The `sync-opencode` project-local skill.** `.claude/skills/sync-opencode/` with `scripts/sync_opencode.py`: `target/opencode/skill/` → `{dest}/skills/`, `agent/` → `{dest}/agents/`, `command/` → `{dest}/commands/`. **Deletion is bounded to managed entries** — the destination is the shared `~/.config/opencode/` where user-managed skills also live, so the sync removes only stale entries the generated tree owns (those matching the generated `{bundle}-{skill}` namespace of the bundles being synced) and never touches entries outside that managed set; with `--bundles`, unselected bundles' entries are likewise preserved. The boundary model is the OpenCode emitter's own prune behaviour. Default destination `~/.config/opencode/`; flags `--source`, `--target-dir`, `--bundles`, `--dry-run`. Project-local for the same reason `sync-plugin-cache` is: only this repository generates OpenCode output.
   *Done when:* running it against a generated tree produces the plural layout at the destination with stale **managed** entries removed and unmanaged entries untouched; the skill is invocable as `/sync-opencode`; the SKILL.md mirrors the `sync-plugin-cache` shape (source-of-truth statement, parameters table) and states the deletion boundary.
2. **D2 — Unit tests** under `test/sync-opencode/`, mirroring the `test/sync-plugin-cache/` precedent: the singular→plural path mapping, `--dry-run` (no filesystem effect, actions listed), `--bundles` subsetting, stale-managed-entry deletion, **preservation of unmanaged destination entries**, and **preservation of unselected bundles' entries under `--bundles`** — all against temp directories, no live OpenCode install.
   *Done when:* the tests pass in the verify gate and each behaviour above has at least one case.
3. **D3 — Inner-loop documentation.** `doc/developer/marketplace-build.adoc` gains the OpenCode inner loop (generate → `/sync-opencode` → test) and the deploy options with the precedence caveat spelled out: (a) sync into the global config dir for daily work; (b) point `OPENCODE_CONFIG_DIR` at a plural-renamed staging copy, noting that a committed project-local `.opencode/` shadows the env-var directory and that the env var cannot point at the singular `target/opencode/` directly; (c) a marketplace-install path exercises distribution, not rapid iteration, and is unverified until the validation protocol runs.
   *Done when:* the section exists, cross-references rather than duplicates the generator documentation, and every claim is exercisable without a live OpenCode session or is explicitly marked validation-gated.
4. **D4 — `distribution.adoc` states the live matrix.** The document describes the actual two-entry publish matrix (`dist-claude`/`dist-opencode` branches, `claude`/`opencode` tag prefixes, unified source-tag versioning) and states plainly that the OpenCode consumption path against those refs is unverified on a live client.
   *Done when:* the document contains no claim that the matrix is Claude-only or that OpenCode publication is hypothetical, and its statements match `.github/workflows/claude-distribute.yml` read at run time.

## Out of Scope

- **Running against a live OpenCode install** — D2's temp-directory tests are the verifiable substitute; live confirmation belongs to WS-05's validation protocol. Excluded so the plan cannot stall on an environment it cannot have.
- **Shipping `sync-opencode` in a marketplace bundle** — consumer projects never generate OpenCode output.
- **Pinning the OpenCode install path** — a live-client question; D4 states it as unverified rather than guessing. Owned by PLAN-17.
- **CI changes** — the generation gate and distribution workflows already cover OpenCode.

## Claim Labels

- OBSERVED: no `sync-opencode` skill and no `sync_opencode.py` exists anywhere in the tree — an **asserted absence, the high-risk kind**. Re-derived at HEAD `2cd1a19c`: a `*sync_opencode*` pattern search returns zero hits, and `*sync-opencode*` matches only the plan document itself. Re-derive again before building; a hit refutes the premise and HALTS the plan for re-scoping.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: Tree-wide pattern search for *sync_opencode* returned zero hits; *sync-opencode* matched only the plan document itself. The asserted absence holds.
- OBSERVED: the generator emits singular `skill/`/`agent/`/`command/` directories — read at `marketplace/targets/opencode/emitter.py` § `emit_bundles`, which writes `output_dir / 'skill'|'agent'|'command'`.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: marketplace/targets/opencode/emitter.py section emit_bundles writes output_dir / skill|agent|command - singular, confirmed by full read
- HYPOTHESIS: OpenCode discovers plural `skills/`/`agents/`/`commands/` directories — an external-product fact **no artifact in this repository can settle**. Confirm/refute at WS-05's `../reference/opencode-validation-protocol.md` § 1.2 (verify-at-outline). D1's `--target-dir` flag keeps the rename correctable if the assumption is refuted, and the run states the assumption in its PR body and inbox message rather than as fact.
  - verdict: unverifiable | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: The settling population is a live OpenCode install. No clone artifact can reach it; WS-05 protocol section 1.2 owns the check. Unverifiable is not a refutation - the premise may well hold.
- OBSERVED: `sync-plugin-cache` is the shape to mirror — read at `.claude/skills/sync-plugin-cache/SKILL.md` and `scripts/sync.py` (source-of-truth statement, parameters table, staleness guard all present).
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: .claude/skills/sync-plugin-cache/SKILL.md carries the described shape - source-of-truth statement, parameters table, staleness guard
- OBSERVED: project-local skill tests live under `test/{skill-name}/` — read at `test/sync-plugin-cache/`, which holds `__init__.py`, `test_reconcile_daemon.py`, `test_staleness_guard.py`, `test_sync_engine.py`, `test_target_source.py`.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: test/sync-plugin-cache/ holds five test modules - __init__.py, test_reconcile_daemon.py, test_staleness_guard.py, test_sync_engine.py, test_target_source.py
- OBSERVED: `claude-distribute.yml` carries a live `opencode` matrix entry — read at `.github/workflows/claude-distribute.yml` § `strategy.matrix.include`, which holds `target_name: opencode` / `branch_name: dist-opencode` / `dist_tag_prefix: opencode` beside the `claude` entry. ⚠️ This file is **outside the content-search inventory**; it was verified by direct read, and the run must do the same rather than trusting a zero-hit search.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: .github/workflows/claude-distribute.yml lines 38-48 carry a live two-entry matrix including target_name opencode / branch dist-opencode / tag prefix opencode. Verified by direct Read - this path is outside the content-search inventory.
- OBSERVED: `distribution.adoc` claims a single-entry Claude-only matrix and hypothetical OpenCode publication — read at `doc/developer/distribution.adoc:87`: *"Today the matrix has one entry (`claude`)… Adding a future target (for example `opencode`)…"*. A live, current drift.
  - verdict: corroborated | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: n/a | evidence: doc/developer/distribution.adoc:87 still reads Today the matrix has one entry (claude) ... Adding a future target (for example opencode). Live drift against the two-entry workflow.
- HYPOTHESIS (refuted, and already handled): the generated `target/opencode/` tree is committed and present in the clone. It is **not** — `target/` is gitignored at `.gitignore:12`. The spec's own contingency applies: generate it locally as D2's fixture source instead. Not scope drift.
  - verdict: contradicted | checked_at: 2cd1a19c | by: multiplattform/analyze | rescoped: yes | evidence: .gitignore:12 ignores target/ so the generated tree is absent from a fresh clone. The spec's own stated fallback - generate it locally as D2 fixture source - absorbs this, so the re-scope is already written into the claim.

## Expected Surface

- OBSERVED (absent, to be created): `.claude/skills/sync-opencode/SKILL.md`, `.claude/skills/sync-opencode/scripts/sync_opencode.py` — D1
- OBSERVED (absent, to be created): `test/sync-opencode/**` — D2
- OBSERVED (exists): `doc/developer/marketplace-build.adoc` — D3
- OBSERVED (exists): `doc/developer/distribution.adoc` — D4

## Dependencies and Sequencing

- Depends on: none. **Disjoint from every plan in the epic across all of code and tests**, which makes it the standing concurrency partner under `parallelization_scope: 2`.
- ⚠️ **Overlaps with: three plans, on documentation files only.** Found by `corpus cross-check` at ingestion, and it corrects this spec's original "overlaps with: none" claim — that claim was true of the code surface and false of the docs.
  - **PLAN-15** on `doc/developer/marketplace-build.adoc` (its D3 may land the scoping distinction there). ⛔ **This is the one that matters for pairing** — PLAN-15 is otherwise a natural partner for PLAN-04 because its D1 is ADR-only. Confirm PLAN-15's D3 target before pairing the two.
  - **PLAN-18** on `doc/developer/marketplace-build.adoc` — PLAN-18 is `parked`, so no live collision until WS-05 unparks; by then this plan will have landed.
  - **PLAN-17** on `doc/developer/distribution.adoc` — likewise `parked`, and PLAN-17's own spec already sequences itself after this plan.
- **Pairing rule that follows:** PLAN-04 pairs safely with any WS-01 or WS-03 plan, and with PLAN-16. Against PLAN-15, check D3's target first.
- Adjacent to: `marketplace/targets/opencode/emitter.py` — read for the prune-boundary model and the directory names, never edited (WS-02's surface).

## Notes

- The deploy engine mirrors `sync-plugin-cache`'s source-of-truth stance: it consumes generated output (`target/opencode/`), never `marketplace/bundles/` directly.
- Namespacing is `{bundle}-{skill}` with no consecutive `--`; the rename maps directory *kind* (singular→plural), never component names.
- WS-05's validation protocol § 1.2 consumes this skill as its deploy step once it lands; until then it documents the manual fallback.

## Verification

- The full verify gate over the branch diff (Python changes — the build gate applies).
- D2's behaviour tests demonstrated red-first against the not-yet-implemented flags.
- A manual end-to-end run into a temp directory recorded in the PR body: generate, sync, re-sync after deleting a source file, and confirm the stale managed entry is removed while a planted unmanaged entry survives.
- A pre-PR verification pass re-reads D3/D4's documentation claims against the workflow and generator files they describe — documentation that restates another file's facts is the consumer-kind most likely to drift here.
- **Cold read (caveat check):** a reviewer reads D3's deploy-options text cold and answers, without the plan in context: where does OpenCode look for skills when `OPENCODE_CONFIG_DIR` is set and a committed project-local `.opencode/` also exists, and can the env var point at `target/opencode/` directly? Any answer other than "the project-local directory shadows the env var" / "no — the layout is singular there" means the wording failed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-04-sync-opencode-inner-loop.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. In particular it does **not** edit `../reference/coupling-inventory.md`: coupling
rows are retired by the orchestrator from the landing, per the epic decision recorded in `epic.md`.
