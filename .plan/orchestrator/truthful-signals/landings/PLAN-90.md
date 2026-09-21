# Landing: PLAN-90 — lessons corpus is written and never read

plan: PLAN-90 · plan_id: `lessons-corpus-is-written-and-never-read` · PR **#1039**
merged: `010ea4615` · 2/2 deliverables · 22/22 finalize steps

## Deliverable fidelity

2/2. `manage-lessons consult` — **the corpus's first prospective read** — wired into
`phase-3-outline` at the single lane-agnostic point where the affected-component set first exists and
can still be changed, plus a regression test proving it fires, surfaces, records, and **never
auto-applies**.

**D1's gate resolved with its reasoning recorded:**

- Consult point is `phase-3-outline` **only** (lane-agnostic, after outline write+validate).
- Surfacing is **judgment-with-disposition**, never auto-application.
- The intersect is **exact-match at `bundle:skill` granularity, not architecture-module** — the
  latter would have returned **~83% of the corpus**, which is indistinguishable from no filter.
- **Chosen failure mode stated explicitly: head-side noise, not silence.** ⭐ A design decision that
  names which way it fails is exactly what this epic asks for.

⭐ **The founding absence claim was CLOSED FIRST-PARTY, not inherited.** The outline flagged that it
could not verify D1(a) exhaustively. The plan then swept **all 22 `manage-lessons` query-verb call
sites** and established every one is retrospective, referential-integrity, own-origin, user-menu, or
on-demand — **zero prospective consult existed.** The Verify-First Contract holds that asserted
*absences* are the higher-risk half; this one was proven rather than assumed.

## Review coverage — the recurrence that matters

- **Sourcery did not review** — weekly rate limit (500k diff chars); its check shows **SKIPPED**.
  ⛔ **`fetch_findings` listed sourcery in `responded_bots` BOTH TIMES.** A detected refusal reported
  as participation — the #1026 archetype, now on a **fourth consecutive PR** (#1034, #1037, #1038,
  #1039).
- **CodeRabbit found 2 real defects that every in-house gate passed**: a negative
  `--max-per-component` producing a spuriously-truncated result, and a duplicated disposition table.
  ⭐ **The plan chose fail-closed (`error: invalid_cap`) over CodeRabbit's proposed silent
  `max(0, …)` clamp, plus a regression test.** Rejecting a bot suggestion that would have introduced
  a silent degradation is precisely this epic's discipline — recorded as a positive instance, and as
  the second time in this epic a bot suggestion was corrected rather than applied.

## Deviation, self-reported

**`automatic-review` and the unified triage ran INLINE where `dispatch-inline-split.md` rosters both
as DISPATCHED.** The work was done correctly, but **the dispatch-audit trail has no `[DISPATCH]` row
for either.** Recorded in `decision.log` rather than left implicit.

⭐ **This is the third distinct site of the roster-vs-reality divergence** (after `architecture-refresh`
at two sites and `finalize-step-simplify`). The pattern is no longer per-step — **the roster and the
runtime disagree broadly**, which is what PLAN-64 must scope for.

## The theme landing on its own machinery

`affected_files_recall` reported a confident **0% / fail** computed from an **empty footprint** —
because it runs *after* `branch-cleanup` removed the worktree. **Real recall was 10/10.** Third
independent report of this defect in two days; systematic beyond doubt. → **PLAN-78**.

## Cost

2.6M tokens / 1h44m worked — **the cheapest of the four landings today** (#1034 2.7M, #1037 3.8M,
#1038 4M), on a 2-deliverable plan with a first-party absence sweep.

## Operational notes

- `marshalld` was **stopped for the whole-tree test runs** (known ambient-state isolation defect,
  lesson `2026-07-19-22-001`) and restarted at the end.
- `marshal.json` provisioning stamp still stale at **0.1.1240**; installed is now **0.1.1247**.
  Operator-owed: `/marshall-steward`.

## Reconciliation

- Row → `shipped`, `pr=1039`, `landing=landings/PLAN-90.md`, plan id stamped.
- ⭐ **PLAN-103 is UNBLOCKED** — it was blocked solely because PLAN-90 held `manage-lessons`. The
  absorb-into-the-running-plan alternative is no longer available; PLAN-103 ships on its own.
- 9 inbox messages drained; dispositions in the epic decision log.
