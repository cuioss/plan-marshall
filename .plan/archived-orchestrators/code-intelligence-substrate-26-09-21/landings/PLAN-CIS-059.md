# Landing Analysis: PLAN-CIS-059 — Fold pm-code-intelligence into plan-marshall

epic: code-intelligence-substrate
workstream: WS-02
pr: 1348
merge_commit: `9aaf22d8f`
plan_marshall_plan_id: fold-pm-code-intelligence-into-core
archived: `.plan/local/archived-plans/2026-08-25-fold-pm-code-intelligence-into-core`

## Outcome

**completed** — 5 of 5 deliverables shipped, all green. PR state corroborated first-party via
`ci pr view --pr-number 1348` → `state: merged`, base `main`, head
`feature/fold-pm-code-intelligence-into-core`.

⚠ **The landing narrative's "main up-to-date (8025b2210)" is about MAIN, not about this plan's merge.**
`8025b2210` is PR **#1349** (`fix(github-pr): anchor participation credit to the merge candidate`);
this plan merged one commit earlier as `9aaf22d8f`. Both statements are true; the landing report stamps
the plan's own merge commit, because a landing record that carries the tip-at-report-time cannot be
joined back to the change it describes.

## Premise verdict — the spec's central risk settled favourably, as re-grounding predicted

The spec's load-bearing premise was that the fold is **behaviour-neutral while `derivation_resolver_id`
returns `lsp`**, because activation keys on the resolver id and producers stamp ids. Corroborated at
`marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/extension.py`: `LSP_DEP_TYPE = 'lsp'`
(`:41`) and the provenance identity method returns `'lsp'` (`:262-263`). `derived.json` `producers[]`
and the machine-local binding therefore keep working, exactly as the 2026-08-24 re-grounding recorded.

## Claims corroborated first-party, and one that needed correcting

| Claim | Verdict | Evidence |
|---|---|---|
| lsp resolver moved onto plan-marshall's Extension | **corroborated** | `extension.py` carries `LSP_DEP_TYPE`, the Axis-C opt-in, and the `lsp` provenance id |
| Bundle retired, 11 → 10 | **corroborated** | `git ls-files 'marketplace/bundles/*/.claude-plugin/plugin.json'` → **10**; `git ls-files marketplace/bundles/pm-code-intelligence/` → **empty**; `git status --porcelain` on that path → clean |
| Components 158 / **154 skills**, derived from live manifests | **corroborated, and the residual gap is a KNOWN defect** | `git ls-files 'marketplace/bundles/*/skills/*/SKILL.md'` → **156** files. The 2-file excess over 154 *registered* is exactly the `a1e704` finding this landing itself routed: `lsp-client` and `recipe-surgical-fix` are live but unregistered. ⭐ An independent derivation reproducing a self-reported defect's magnitude is a stronger signal than either alone |
| Repository topology docs corrected | **corroborated** | `CLAUDE.md` § Repository Overview now reads 10 bundles / 158 components (154 skills) |

⚠ **Cosmetic residue, not a defect**: `marketplace/bundles/pm-code-intelligence/` still exists **on
disk**, holding only gitignored `__pycache__/*.pyc` for the deleted `extension.py`. Git deletes files,
not directories, and will not remove one containing ignored content. It is inert — since PEP 3147,
Python will not import a module from `__pycache__` with no adjacent source — so this is local-tree
litter, and the 11 → 10 claim is TRUE at the git layer, which is the layer that ships.

## Metrics and anomalies

Reported: **3h50m worked / 9h43m wall · 4.7M tokens · 88.4M billing-weighted · 9 tasks · 1 loop-back**,
with **6-finalize alone ≈50% of tokens**.

⛔ **The worked-time figure is self-reported as UNRELIABLE by this plan's own inbox message 003**: a
finalize loop-back leaves 6-finalize half-stamped and **clamps worked time to wall**, rendering a
confident fully-worked row. This run had exactly one loop-back, so the 3h50m/9h43m pair is the
defective shape, not an independent measurement. ⇒ **Do NOT enter this run's worked-time into any
epic-level efficiency figure.** The token and billing-weighted figures are unaffected.

⭐ **The 6-finalize ≈50% share is consistent with the epic's standing observation** that finalize
dominates plan cost (PLAN-TRUTH-013 recorded finalize at 70% of a 109M-billing run). n is now larger
but the figure is still a per-run observation, not a reproduced measurement.

## Routing and merge behaviour

Merged via the merge queue. ⛔ **Two self-reported process mistakes, both recorded because both are
recurrences of archetypes this epic already tracks:**

1. **Pruned a live sibling plan's merge-queue slot (`8d44fd`)** after reading `manage-status read` /
   `list` absences as death. ⭐⭐ Both verbs are **structurally blind to a phase-5+ plan in its own
   worktree** (ADR-002) — this is the *absence-read-as-measurement* archetype, the same family as the
   epic's `91bbe7470` "stop readers from reading absence as measurement" landing, and it recurred here
   in the very session that shipped a fix for a sibling of it. Correct procedure recorded by the plan:
   use `locate-plan-checkout`, and trust `merge_lock check`'s staleness verdict.
2. **Claimed all findings resolved while `8d44fd` was still pending** — caught by the retrospective,
   not by the claim's own gate. *Vacuous-authority* archetype.

## Retrospective findings worth carrying

- ⛔ **The footprint resolver's merge-commit tier is structurally dead for this repository.** Squash
  merges produce one parent, so all four tiers failed. This is a **population** defect, not a tuning
  one: the tier can never fire here.
- ⛔ **6-finalize's metrics row was half-stamped**, with worked time clamped to wall (see Metrics above).

## Reconciliation actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-CIS-059 --status shipped`
- [x] row `pr` stamped `1348`
- [x] row `landing` stamped `landings/PLAN-CIS-059.md`
- [x] row `plan_marshall_plan_id` stamped `fold-pm-code-intelligence-into-core`
- [x] 8 inbox messages drained (`fold-pm-code-intelligence-into-core-001` … `-008`)
- [x] plugin registry pin re-checked — see Follow-ups

## Follow-ups

⛔ **Plugin registry pin is INVERTED as of this landing.** `bootstrap_plugin resolve` returns
**`0.1.1550`** while the orchestrator session's served skill base dir is **`0.1.1544`** — executor ≠
installPath, the pin left behind by 6 versions. This is the steady-state per-landing leak the epic
already tracks, widened by this plan's cache sync. **Repair is operator-only.** Graded against the
steps ahead rather than the version delta: the drain, the queue writes, and the emit all run on stable
script surfaces, so this session proceeded. **Re-check before the next plan launch.**

⚠ `marketplace/bundles/pm-code-intelligence/` on-disk `__pycache__` litter — harmless, removable at
leisure, tracked here only so a future reader does not mistake it for an incomplete retirement.
