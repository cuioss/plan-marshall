> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-059`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-008: Executor Preflight Reports `fresh` From a Version Stamp It Never Cross-Checks Against What the Executor Resolves

> Renamed from **PLAN-68** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced by the operator's 2026-07-25 `/marshall-steward upgrade` session
> (PR #1003): Stage 3 preflight reported `executor_action: fresh` at `0.1.1212` while the executor's
> actual script mappings still pointed at `0.1.1194`. Grounded at HEAD by the orchestrator.
>
> **GATED: do not emit until PR #1003 lands.**
>
> ⚠ **SEQUENCING (added 2026-07-26): run AFTER PLAN-69.** The cross-repo TokenSheriff finding
> established that the divergence this plan detects has a named root cause — two version-selection
> legs, one marker-aware and one marker-blind (`marketplace_bundles.py`). PLAN-69's item 4 is
> literally this plan's D2. Building a resolution check before 69 single-sources the answer would
> mean asserting against an ambiguity rather than a contract. **Never run these two concurrently** —
> same file, same function family. Revisit a merge at PLAN-69's D1: if the single selector lands,
> this plan may shrink to "preflight calls it and reports divergence" and could fold in.

## Objective

`generate_executor preflight` decides executor freshness by comparing **version stamps** — the
executor's embedded `MARSHALL_VERSION` against the installed manifest's `executor_changed_at_version`
— plus a multi-version directory-pollution check. It never reads back what the executor actually
resolves to. An executor whose stamp is current but whose embedded script-directory mappings point at
a superseded version therefore reports `executor_action: fresh`, and every downstream stage trusts
it. Make preflight verify resolution, not just the stamp.

This matters beyond cosmetics: Stage 3 preflight is sequenced deliberately so that a version-stale
executor cannot resolve a later `manage-config` call to stale code
(`marshall-steward/SKILL.md:473-480` states this dependency outright). A preflight that clears an
executor whose mappings are stale defeats the exact guarantee it exists to provide.

## ⚠ Mechanism — OBSERVED, verified at HEAD by the orchestrator (2026-07-25)

- OBSERVED — `tools-script-executor/scripts/generate_executor.py:1789-1799` (`cmd_preflight`,
  defined `:1713`): `executor_action = 'fresh'`, then the ONLY staleness test is
  `if executor_changed_at and _version_tuple(executor_version) < _version_tuple(executor_changed_at)`.
  `executor_version` comes from `read_executor_version()` (`:1234-1246`), a regex over the embedded
  `MARSHALL_VERSION` literal — a **stamp read**, not a resolution check.
- OBSERVED — `:1805-1819`: the second regeneration trigger is `_detect_multi_version_pollution`, a
  check over version **directories on disk**. It does not read the executor's embedded paths either,
  and it cannot fire once superseded version dirs have been pruned.
- OBSERVED — `collect_script_dirs` is consumed only at GENERATION time (`:761-762`, embedding
  `extra_dirs_code`). No call site inside `cmd_preflight` reads the embedded
  `_MARKETPLACE_SCRIPT_DIRS` back to compare against the resolved bundle version.
- Therefore: stamp-current + no surviving polluted dirs ⇒ `executor_action: fresh` regardless of what
  the embedded mappings actually point at. The operator's session is the observed instance
  (stamp `0.1.1212`, mappings `0.1.1194`, 300 old dirs pruned, reported `fresh`).
- ~~HYPOTHESIS: the stamp/mapping divergence arises from a non-atomic regen write.~~
  **RESOLVED 2026-07-26 — REFUTED, and the real cause is now OBSERVED.** The TokenSheriff cross-repo
  finding plus the orchestrator's verification pass identified the actual mechanism: two
  version-selection legs over the same cache dirs with different predicates — `find_bundles`
  (marker-aware, `marketplace_bundles.py:67`) vs `resolve_bundle_path` / `collect_script_dirs`
  (marker-blind, `:124-133` / `:170-174`) — so any `.orphaned_at` marker on the newest dir splits
  them. Nothing to verify at outline here any more; see **PLAN-69**, which owns the root cause. This
  plan's scope is unchanged (preflight must verify resolution regardless), but its D1 should consume
  PLAN-69's single-source selector rather than inventing a comparison.

## Deliverables

### D1 — GATE: choose the resolution check and its failure mode (mutates nothing)

Decide what preflight compares. Candidates: (a) parse the executor's embedded
`_MARKETPLACE_SCRIPT_DIRS` and assert every entry's version segment equals the resolved/newest
bundle version; (b) resolve one known script through the executor's own resolution path and compare
the returned path's version; (c) both. Decide the verdict vocabulary — a mapping mismatch should
regenerate in place (consistent with the existing "derived state per ADR-002" treatment of executor
staleness) and report a distinct `executor_action`, NOT a silent `fresh` and NOT a bare
`regenerated` that hides which signal fired. Confirm the seven-field TOON return contract (`:1760`,
`:1850`) can carry the new field without breaking its consumers.

### D2 — preflight verifies resolution, not just the stamp

Implement the D1-chosen check inside `cmd_preflight`, ahead of the `fresh` verdict. An executor whose
embedded mappings do not resolve to the current version is never reported `fresh`.

### D3 — the report names which signal fired

`executor_action` (or an accompanying field) distinguishes stamp-staleness, directory pollution, and
mapping divergence. A caller reading the TOON can tell WHY the executor was regenerated — today all
three collapse into `regenerated`, and the third cannot occur at all.

### D4 — tests

(a) An executor with a current stamp but mappings pointing at a superseded version is NOT reported
`fresh` and IS regenerated. (b) A genuinely fresh executor still reports `fresh` with no regeneration
(no false positive — this is the guard against over-triggering). (c) Each of the three signals
produces its distinct D3 verdict. (d) If the D1 gate adopts check (b)'s resolve-a-real-script form,
the test asserts against the real resolver, not a mock of it.

## Expected surface

- OBSERVED: `tools-script-executor/scripts/generate_executor.py` — `cmd_preflight` (`:1713-1850`),
  `read_executor_version` (`:1234-1246`), `_detect_multi_version_pollution` (`:1621-1663`)
- OBSERVED: `tools-script-executor/SKILL.md` — the `generate_executor preflight` Canonical
  invocations block (return contract gains a field; plugin-doctor reads this as source-of-truth)
- HYPOTHESIS: `marshall-steward/SKILL.md:473-480` and `references/upgrade-flow.md:345-357` — the
  Stage 3 preflight contract prose, touched only if the new verdict vocabulary makes the current
  wording wrong (verify-at-outline)
- OBSERVED: tests under `test/plan-marshall/tools-script-executor/**`

**Disjointness:** `tools-script-executor` — single skill, disjoint from the four in flight
(PLAN-66 `manage-locks`, PLAN-53 `marshall-orchestrator`, PLAN-51 `plan-retrospective`, PLAN-57
`manage-status`) and from PLAN-TRUTH-007 (`manage-config` + `marshall-steward`). PLAN-TRUTH-007 and PLAN-TRUTH-008 share
only the *steward-docs* adjacency, and only if each one's HYPOTHESIS doc-surface is confirmed at
outline — re-check disjointness then if both are in flight together.

## Notes

- Flagship archetype instance: a confident `fresh` verdict conceals that the thing it certifies was
  never actually inspected. Closely related to PLAN-39 (manifest-tier truthful stamp) and #979
  (routed-build false green) — all three trust a recorded value instead of the state it describes.
- Cross-reference: this is the **second** independent instance in one session of "a stamp was
  compared where the underlying state should have been read." Orchestrator lesson
  `2026-07-21-22-001` (recorded-claim-as-ground-truth) names the class.

## `generate.py` self-invalidates its own emit sentinel

**`generate.py` auto-bumps the version into `marketplace/bundles/` on every run, so `sync.py`'s
staleness guard ALWAYS fires on the first pass.** The reporter had to run it twice. **The guard is
structurally unsatisfiable in a single pass** — the act of generating creates the staleness the next
step then refuses on.

This lands here because it is the same family this plan owns: **a staleness guard whose verdict is
about its own bookkeeping rather than about the world.** Preflight compares a stamp instead of what is
anchored; this compares a sentinel the generator just invalidated. Both report a confident staleness
verdict that says nothing about actual drift.

⚠ **Surface caveat — this may not belong here.** `generate.py` / `sync.py` live in
`marketplace/targets/` and the project-local sync surface, **not** in `tools-script-executor`. It is
folded in on family resemblance, not on shared files. **If D1 finds the surfaces genuinely disjoint,
split it back out and say so** — under the epic's merge rule, disjoint work is a parallel slot and
should not be absorbed. Recorded openly so the decision is deliberate rather than inherited.

## ⭐ FOLDED 2026-07-30 — a FOURTH divergence axis: doc/script layer skew

Folded from inbox `code-intelligence-substrate-007.md` (sibling epic `code-intelligence-substrate`),
after the orchestrator corroborated the mechanism at HEAD. The sibling warned that "the plugin cache
at `0.1.1240` still carries the pre-#1057 regex while the executor embeds `0.1.1269`". **Corroborated
by symbol, and it generalises past their framing.**

- OBSERVED — `_orchestrator_inbox.py` `_SOURCE_ID_RE` in cache copy `0.1.1240` is
  `^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/PLAN-\d+[^/]*\.md$` — `PLAN-` followed by digits
  ONLY. In cache copy `0.1.1269` the same symbol is the three-way alternation
  `(?:PLAN-(?:[A-Z0-9]{2,8}-)?\d+|[A-Z0-9]{2,8}-\d+)`. The two copies of one symbol disagree about
  what an orchestrated pointer IS.
- OBSERVED — the `re.compile` carries no `IGNORECASE` flag, so `[A-Z0-9]{2,8}` is uppercase-only and
  case-sensitive. A lowercase code slug returns `unrecognised_id`, and the plan then writes **no inbox
  message at finalize** — silent at both ends.
- OBSERVED — 30 version directories are live under
  `~/.claude/plugins/cache/plan-marshall/plan-marshall/` (`0.1.1194` … `0.1.1269`).
- OBSERVED — the executor embeds exactly ONE version: 129 paths at `0.1.1269`, and the only
  `0.1.1069` occurrence is a docstring example on `_orchestrator_inbox.py`-adjacent line 371 of
  `.plan/execute-script.py`, not a path. **So this instance would NOT be caught by D2's mapping check
  or by `_detect_multi_version_pollution` — the mappings are internally consistent.**

⛔ **Why this is a fourth axis and not an instance of the three D3 already names.** Stamp-staleness,
directory pollution, and mapping divergence are all properties of the *executor*. Here the executor is
correct: it resolves `0.1.1269` uniformly. The divergence is that the **skill router served a live
session its prose from `0.1.1240`** while every script call in that same session resolved `0.1.1269`
through the executor. The doc layer and the script layer were on different versions **with no signal
of any kind**, and no existing check inspects that pair.

**D3 consequence.** The verdict vocabulary should not be closed at three signals on the assumption
they are exhaustive — that assumption is itself the archetype this plan owns. Either name this fourth
axis or state explicitly why it is out of scope.

**Verified NOT to have harmed us**, and the check that establishes that is recorded because the weaker
check was nearly accepted in its place: all 19 staged `PLAN-TRUTH-*` specs plus 49 legacy rows were
diffed **name-level and bidirectionally** against `status.json` `plans[]` — 68 rows ↔ 68 files, 0
orphans, 0 mismatches, empty diff. ⭐ Per the sibling's own correction in
`code-intelligence-substrate-008.md`, `inbox detect` is a pure function of the id GRAMMAR and never
opens the file, so "N pointers detect as orchestrated" is ONE assertion repeated N times and could not
have found a missing or misnamed file. The bidirectional enumeration is the check that bites.

## ⭐ RE-AIMED HERE 2026-07-30 — a THIRD instance, this one with a measured consequence

Re-aimed out of PLAN-TRUTH-012, where it was misattributed as a canonical-block divergence (see that
spec's retraction). `review-apparatus-006` supplied the diagnosis and it was re-verified here.

- OBSERVED — two subagents on `#1064` invoked `review_completeness --enabled-bots` and got argparse
  exit 2. OBSERVED — **no `--enabled-bots` flag exists anywhere in `marketplace/bundles/`** (verified by
  grep; every hit is the retired `enabled_bots` *config knob* in migration prose). The flag lives only in
  a **stale plugin-cache copy** of the script.
- ⇒ **Agents resolve skills from the plugin cache, so a badly split cache serves them a RETIRED SURFACE
  as current.** That is why two subagents hit it independently — not coincidence, mechanism.
- OBSERVED (sibling measurement, and it sharpens the axis into one sentence): the executor embeds
  **exactly one** version (`0.1.1271`, no pin/orphan inversion), skills load from cache **`0.1.1240`**,
  and **32 versions coexist** under the cache root. ⇒ **WHAT WE READ IS 31 VERSIONS BEHIND WHAT WE RUN.**

⛔ **This is the consequence half the plan previously lacked.** The first two instances of this axis were
*potential* (a regex that disagrees between copies; a session reading stale prose). This one **cost real
work**: two dispatched agents failed against a flag that has not existed in source for many versions, and
the failure surfaced as an opaque exit 2 rather than as "you are reading a stale cache."

⇒ **D1/D3 consequence:** the divergence this plan must report is not only *executor stamp vs executor
mappings* but **cache-version-serving-skills vs executor-version-running-scripts**. A preflight that
verifies resolution while ignoring which cache version the agent will READ from certifies half the system.

⚠ **Do not over-apply the stale-cache archetype in the other direction.** It invalidates an artifact; it
must never acquit a real defect. The retraction it justified was independently grounded in a grep of the
source, not in the archetype's plausibility.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
