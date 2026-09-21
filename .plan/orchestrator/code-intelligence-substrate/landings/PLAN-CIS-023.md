# Landing: PLAN-CIS-023 — path-attribution-seam

epic: code-intelligence-substrate
workstream: WS-01
plan: `path-attribution-seam`
PR: #1072 — merged `bf6b0aa59`

## Corroboration

⛔ **Verified before the `shipped` transition, per standing rule 1 — not taken from the paste.**

- `git log origin/main` — `bf6b0aa59 feat(extension-api): add path-attribution seam for which-module claims (#1072)` present on `origin/main`.
- `ci pr list --state all` — #1072 `merged`, head `feature/path-attribution-seam`.
- **Objective probed live, not inferred**: `architecture which-module --path .plan/execute-script.py` now returns `module: plan-marshall` (was `null`), carrying the new `attributors[1]: plan-marshall` / `attributor_count: 1` / `attributor_notes[0]` fields.
- **Regression probe**: `.claude/skills/sync-plugin-cache/SKILL.md` still returns `plan-marshall` — the re-home through the seam preserved the answer.
- **Expected non-answer confirmed as expected, not as a defect**: `.claude/commands/marshall-steward.md` still returns `module: null` with `attributor_count: 1`. ⭐ **This is the fail-closed contract working, not a miss** — one attributor ran and declined to claim the path. `.claude/commands` was never in this plan's scope; it is **PLAN-CIS-025 D1**.

## Outcome

**7 deliverables shipped against a 6-deliverable spec**, all green, 21/21 finalize steps.

The seam landed as a **fourth sibling axis — `PathAttributionBase`, Axis-D** — alongside Axis-A (skill loading), Axis-B (file-to-build), and PLAN-02's derivation-resolver axis. The extension-topology diagram went from nine to twelve. `_PROJECT_LOCAL_PREFIX_MAP` is retired; core keeps merge, provenance, and resolution order and owns no claim.

## Both hypotheses resolved — one needed correcting

- ⭐ **H1 (ambiguous-key transfer) — transferred, but NOT verbatim, exactly as the spec warned.** The spec flagged an asymmetry: an edge is an unweighted boolean so union is idempotent, whereas an attribution is a *function* and therefore genuinely conflictable. That asymmetry was real. **ADR-014 refuses a precedence rule because an unweighted boolean has no expressible conflict; a path claim is a keyed mapping, so a conflict IS expressible and the seam needed its own rule, not a cross-reference.** ⛔ **Do not "harmonise" the two seams' conflict rules later — the difference is load-bearing.**
- ✅ **H2 (no consumer depends on `null`) — CONFIRMED BY ENUMERATION, not by sample.** A full sweep of **131 `which-module` hits** found exactly **one** consumer branching on `module is None`; D4 pins it with a test. ⭐ The spec demanded a derived population over an orchestrator-supplied list, and it got one.
- **Split guard**: evaluated at outline, **shipped unsplit with a recorded rationale** — D4 could have shipped alone, but D5's residue reporting exists *because of* the `.plan` null answer. Compliant with the guard.

## Review

**Three review-driven fixes landed that the plan's own gates missed** — the plan's gates were not sufficient, and the bots were:

- **pr-agent** — an unguarded loop that could blank the whole ownership map.
- **CodeRabbit** — a normalization asymmetry (`./x`, `.plan\x` answered `null`) and vacuous dot-relative claims.
- ⭐ **Triage REFUTED part of CodeRabbit's claim by probing the live verb** — trailing-slash already worked — and pinned it against regression rather than "fixing" what was not broken. **This is the correct handling of a bot finding as a lead rather than an instruction**, and it is the first time this epic has recorded a refutation rather than an acceptance.

⭐ **The pre-merge comment barrier earned its keep, concretely.** CodeRabbit refused two iterations with rate limits and only reviewed on the **third** HEAD — *after* `automatic-review` had already marked done. The barrier re-fetched at merge time and blocked. **Without it, its only review would have gone unread.** This is direct evidence for the standing rule that a green finalize is not proof the bots saw the diff.

## Findings raised for the epic

1. ⛔ **The adaptive build timeout produced four false reds in one run, and the mechanism is SELF-REINFORCING** — each false timeout raises the learned duration. Observable inversion: `module-tests plan-marshall` now resolves orchestrator-tier at **643s** while `verify plan-marshall`, *which contains it*, resolves per_task at **456s**. A containing command cheaper than its own contained part is a proof of corruption, not a tuning artifact. Lesson `2026-08-01-13-001` covers it; this run added three more sightings. **Tool-layer fix owed.**
2. ⛔ **`plan-retrospective` is scheduled where two of its inputs do not exist** — `branch-cleanup` deletes the worktree it derives its footprint from, so `affected_files_recall` scored **0% against a 21/21 exact footprint**. ⭐ **Vacuous on every standard-posture plan, not just this one.** This is the same archetype as PLAN-10's finalize-ordering defect: a step scheduled where its input is already gone. **Squarely ours — measurement integrity, WS-04.**

## Ledger effects

- Row stamped: status `shipped`, pr `1072`, landing `landings/PLAN-CIS-023.md`.
- ⭐ **Its gate on PLAN-CIS-024, PLAN-CIS-025 and PLAN-CIS-026 D2 is RELEASED.** Those three are mutually disjoint by bundle — the epic's first genuinely parallel cluster.
- ⚠ **The recorded CIS-023/CIS-003 adjacency did not bite.** CIS-023 added a sibling registry rather than generalising shared discovery plumbing, which is the branch that keeps the pairing safe. Both ran concurrently with no observed collision. ⚠ One good pairing is still not a validated method — keep recording both outcomes.
- 12 inbox messages filed by this plan (1 landing, 11 candidate-lessons), one of which (`-004`) the plan flagged as probably belonging to `review-apparatus` and deliberately did **not** route locally. ⭐ **Correct behaviour** — routing is the orchestrator's call.
