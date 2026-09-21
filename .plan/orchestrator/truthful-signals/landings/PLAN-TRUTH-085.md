# Landing Analysis: PLAN-TRUTH-085 — orchestrator inbox lifecycle, cleanup and landing payload

epic: truthful-signals
workstream: WS-01
pr: #1317 — merged as `9038b8c6e`
cloud-run: `cloud-runs/520-orchestrator-inbox-lifecycle-cleanup-and-landing-payload/`

> A gap-fix plan authored by the epic audit (PR #1298) and executed in the cloud lane. It shipped
> with **no `verification.md` and no `gaps.md`** — the post-run verification was performed during
> ingestion on 2026-08-22 and both files were authored then, to the same method as the other 44.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | 8/8 landed — D7 the only non-clean cell (`Complete? Partial`, G6) |
| Upstream gaps claimed closed | 30 |
| **Genuinely closed** | **29** |
| Partially closed | 1 — `250/G7` |
| Not closed | **0** |
| New gaps filed | 8 (high 0 · medium 4 · low 4) |

**Source set is SEVEN directories** (090, 120, 180, 250, 280, 300, 302), 51 ids total, 31 accountable.
The audit's "six" was wrong and its own correction is confirmed here.

## ⭐ `302/G1` is CLOSED — verified by EXECUTION, not reading

The highest-severity gap in the orchestrator group (`'n/a'` is truthy, so a landing that transmitted
nothing reads `complete: true`) is genuinely closed. Executed at HEAD:

- `tokens`/`steps`/`deliverables_*` = `n/a` → `(False, [those four keys])`
- `pr=n/a` + `merge_state=n/a` with all else real → `(True, [])` — the sanctioned asymmetry
- `' N/A '` → rejected · a genuine `0` → accepted · all-`n/a` → `(False, ['schema'])` via the schema branch
- Dropping `steps` from `LANDING_SENTINEL_REJECTING_KEYS` turns the pinning test **RED**

## `250/G7` — partially closed

`close-stream` is correctly reclassified as an append everywhere, but `inbox-envelope.md` states two
different in-place-edit counts **12 lines apart**: the Invariants bullet says "two in-place edits"
while the sibling clause above still says "the one sanctioned in-place edit". The substantive fix
landed; the doc sentence lags. Carried forward as this plan's own **G6** — not lost.

## Gaps filed

| Gap | Sev | Kind | Summary |
|---|---|---|---|
| G1 | medium | stale-statement | Survivor S2 closed by CR-4; § Survivors still says "not fixed" |
| G2 | medium | incomplete-sweep | Expected surface misses `decompose.md`; two off-list surfaces, not one |
| G3 | medium | stale-statement | Contract check says 13 `marketplace/**` paths; the diff has 14 |
| G4 | medium | missing-test | No guard pins `--workflow` at the three dispatch doc sites CR-4 fixed |
| G5 | low | stale-statement | Residue item 3 falsified by this landing's own `compaction_migrated[]` |
| G6 | low | doc-drift | `inbox-envelope.md` states two in-place-edit counts 12 lines apart |
| G7 | low | false-signal | `merge_state: unknown` ("could not be read") still reports `complete: true` |
| G8 | low | stale-statement | `_marker_indices` docstring's return contract is wrong (pre-existing) |

## ⛔ Carry-forward — the review cycle silently widened the diff

**The CodeRabbit cycle added `decompose.md` and `effort-roles.md` AFTER the report's derived figures
were written and after the last verification round.** Consequence: **every count in that report taken
before the review cycle is one low**, and three separate "inconsistencies" (survivor count,
off-list-surface count, 13-vs-14 marketplace paths) are **the same unswept CR-4 fix at three
different sites**. The report asserts and denies the same fact about the dispatch sites 100 lines
apart (S2 vs CR-4); the tree agrees with CR-4.

⚠ The fix that actually closes `280/G7` at the two resolving sites **is held by nothing but prose** (G4).

## What was NOT checked

- The 8 verification rounds, 4 cold reads and their token figures — conversation events with no
  committed artifact. Outcomes verified; the narratives are not re-derivable.
- Historical CI figures. The 5 changed test modules (399 passed) and the whole `plan-orchestrator`
  suite (586 passed) were run at HEAD; **no full `./pw verify`**.
- The D6(iv) `[DISPATCH]` log line — running a resolve WRITES into `.plan/local/logs/`, forbidden to
  this verification. The mechanism was verified instead (`_cmd_effort.py:529-546` gates emission on
  `--workflow`; all three sites pass it).
- The rebase range-diff, the 31/35 citation rewrites, PR review-thread state (squash merge; no API).
- `250/G4`'s physical archive migration — its population is under git-ignored `.plan/local/`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1317`
- [x] row `landing` = `landings/PLAN-TRUTH-085.md`
- [x] `verification.md` + `gaps.md` authored at ingestion and retained under `cloud-runs/520-…/`
- [x] upstream closure re-derived: 29 closed / 1 partial / 0 not-closed
