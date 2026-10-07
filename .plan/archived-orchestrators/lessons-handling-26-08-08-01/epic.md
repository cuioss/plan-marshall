# Epic: Lessons Handling 26-08-08

slug: lessons-handling-26-08-08-01

> Ledger document for one epic under `.plan/local/orchestrator/lessons-handling-26-08-08-01/`.
> The layout and authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Drain the active lessons-learned corpus (203 active lessons at scan time) into the three live
sibling epics, so that accumulated lessons become owned work rather than an ever-growing
backlog. Each lesson is (1) validity-checked against current ground truth, (2) deduplicated
into a cluster, (3) routed to the sibling epic that owns its surface — as an addendum to an
existing staged plan where one fits, or as a new plan spec where none does — and (4) moved
into this epic's local `archive/` and retired from the active corpus. "Done" is: every scanned
lesson carries an auditable disposition, every routed cluster has landed in a sibling epic's
inbox, and the active corpus holds only lessons this run deliberately kept.

## Routing Model

This epic is a **router**, not an implementer. Its queue items are routing decisions, not plans
it launches itself. The three-way sibling routing rule applies:

| Destination | Takes |
|-------------|-------|
| `review-apparatus` | PR-review / review-bot reliability lessons (tested first, wins outright) |
| `code-intelligence-substrate` | Token-reduction, context-economy, code-navigation-substrate lessons |
| `truthful-signals` | Everything else — confident-signal-hides-a-caveat, false-green, vacuous-guard lessons |

Cross-epic hand-off goes through the destination epic's `inbox/` via
`orchestrator inbox write`, never by a direct edit of a sibling's tree.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug lessons-handling-26-08-08-01
     Paste the returned block verbatim between the markers. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: epic closed - see history.md
**Phase**: closed
**Inbox (derived)**: 0 queued, 0 archived
**Queue** (staged, in order):
- (empty)
- PLAN-LH-01 (WS-01) — plan=truthful-signals/PLAN-TRUTH-067 — status: retired
- PLAN-LH-02 (WS-01) — plan=truthful-signals/PLAN-TRUTH-027 (lead; spec edit NOT made) — status: retired
- PLAN-LH-03 (WS-02) — plan=code-intelligence-substrate/PLAN-CIS-017 (shipped #1279) — status: retired
- PLAN-LH-04 (WS-01) — plan=truthful-signals/PLAN-TRUTH-045+065 (re-routed; suggested TRUTH-042 had shipped) — status: retired
- PLAN-LH-05 (WS-03) — plan=review-apparatus/PLAN-PR-005+013 (distributed across members) — status: retired
- PLAN-LH-06 (WS-03) — plan=review-apparatus/PLAN-PR-011 (became D4 empirical population) — status: retired
- PLAN-LH-07 (WS-02) — plan=code-intelligence-substrate/PLAN-CIS-002 (merged with review-apparatus-005 as one surface) — status: retired
- PLAN-LH-08 (WS-02) — plan=code-intelligence-substrate/PLAN-CIS-022 +3 specs (2 re-routed against suggestion) — status: retired
- PLAN-LH-09 (WS-02) — plan=code-intelligence-substrate/PLAN-CIS-020 (2 of 3 members already there; corroboration only) — status: retired
- PLAN-LH-10 (WS-01) — plan=truthful-signals/PLAN-TRUTH-050 (lead; spec edit NOT made) — status: retired
- PLAN-LH-11 (WS-01) — plan=truthful-signals/PLAN-TRUTH-059 (spec edit MADE) — status: retired
- PLAN-LH-12 (WS-02) — plan=code-intelligence-substrate/PLAN-CIS-015 (split made mandatory at orchestrator tier) — status: retired
- PLAN-LH-13 (WS-01) — plan=truthful-signals: UNOWNED, new spec wanted (no spec staged) — status: retired
- PLAN-LH-14 (WS-01) — plan=truthful-signals: UNOWNED, new spec wanted (no spec staged) — status: retired
- PLAN-LH-15 (WS-01) — plan=truthful-signals/PLAN-TRUTH-016 (lead; spec edit NOT made) — status: retired
- PLAN-LH-16 (WS-01) — plan=truthful-signals: UNOWNED, new spec wanted (no spec staged) — status: retired
- PLAN-LH-17 (WS-01) — plan=truthful-signals/PLAN-TRUTH-011 (arrived POST-LAUNCH; could not be scoped in) — status: retired
- PLAN-LH-18 (WS-03) — plan=review-apparatus/PLAN-PR-018 (turned one incident into a population) — status: retired
- PLAN-LH-19 (WS-01) — plan=truthful-signals/PLAN-TRUTH-012 (spec edit MADE) — status: retired
- PLAN-LH-20 (WS-01) — plan=truthful-signals/PLAN-TRUTH-006 (lead; spec edit NOT made) — status: retired
- PLAN-LH-21 (WS-01) — plan=truthful-signals: UNOWNED, new spec wanted (no spec staged) — status: retired
- PLAN-LH-22 (WS-01) — plan=truthful-signals/PLAN-TRUTH-009 (lead; partly SUPERSEDED by msg -016) — status: retired
- PLAN-LH-23 (WS-04) — plan=DISCARDED by truthful-signals: out of epic scope, belongs in the consumer repos — status: retired
- PLAN-LH-24 (WS-04) — plan=truthful-signals msg -016: UNOWNED lead (header-less lesson defect; still unfixed) — status: retired
<!-- END GENERATED: resume-summary -->

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Markers were ADDED at close (2026-08-27); before that this section carried only the
     hand-written table now preserved below, which the compact stage would have reported as
     markers_absent_not_regenerated — a blind spot, not an abstention. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LH-01 | WS-01 | retired | (spec missing) |
| 2 | PLAN-LH-02 | WS-01 | retired | (spec missing) |
| 3 | PLAN-LH-03 | WS-02 | retired | (spec missing) |
| 4 | PLAN-LH-04 | WS-01 | retired | (spec missing) |
| 5 | PLAN-LH-05 | WS-03 | retired | (spec missing) |
| 6 | PLAN-LH-06 | WS-03 | retired | (spec missing) |
| 7 | PLAN-LH-07 | WS-02 | retired | (spec missing) |
| 8 | PLAN-LH-08 | WS-02 | retired | (spec missing) |
| 9 | PLAN-LH-09 | WS-02 | retired | (spec missing) |
| 10 | PLAN-LH-10 | WS-01 | retired | (spec missing) |
| 11 | PLAN-LH-11 | WS-01 | retired | (spec missing) |
| 12 | PLAN-LH-12 | WS-02 | retired | (spec missing) |
| 13 | PLAN-LH-13 | WS-01 | retired | (spec missing) |
| 14 | PLAN-LH-14 | WS-01 | retired | (spec missing) |
| 15 | PLAN-LH-15 | WS-01 | retired | (spec missing) |
| 16 | PLAN-LH-16 | WS-01 | retired | (spec missing) |
| 17 | PLAN-LH-17 | WS-01 | retired | (spec missing) |
| 18 | PLAN-LH-18 | WS-03 | retired | (spec missing) |
| 19 | PLAN-LH-19 | WS-01 | retired | (spec missing) |
| 20 | PLAN-LH-20 | WS-01 | retired | (spec missing) |
| 21 | PLAN-LH-21 | WS-01 | retired | (spec missing) |
| 22 | PLAN-LH-22 | WS-01 | retired | (spec missing) |
| 23 | PLAN-LH-23 | WS-04 | retired | (spec missing) |
| 24 | PLAN-LH-24 | WS-04 | retired | (spec missing) |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, OUTSIDE the generated markers, so a regeneration
     preserves it. This is the routing record the generator cannot derive: which message
     carried each cluster, how many lessons it held, and the fold target proposed at
     hand-off. The ACCEPTED outcome per row lives in status.json's plan_marshall_plan_id,
     stamped at close from the siblings' own decision logs. -->

`(spec missing)` above is correct — this was a router epic and staged no plan specs.

| # | Cluster | Destination | Msg | N | Suggested fold target |
|---|---------|-------------|-----|--:|------------------------|
| 1 | PLAN-LH-01 derive-verification emits an unroutable build_class | truthful-signals | -001 | 8 | **NEW** — 5-way duplicate |
| 2 | PLAN-LH-02 a build reports its own outcome falsely | truthful-signals | -002 | 10 | PLAN-TRUTH-027 |
| 3 | PLAN-LH-03 freshness gate admits a tree whose tests never ran | code-intelligence-substrate | -001 | 4 | PLAN-CIS-017 |
| 4 | PLAN-LH-04 vacuous guards and degenerate zeros | truthful-signals | -003 | 15 | PLAN-TRUTH-042 ⚠ running |
| 5 | PLAN-LH-05 review-bot participation and reliability | review-apparatus | -001 | 9 | PLAN-PR-005/006/007/013 |
| 6 | PLAN-LH-06 in-house gates silent where they claim coverage | review-apparatus | -002 | 14 | PLAN-PR-011 |
| 7 | PLAN-LH-07 dispatched leaf has no search primitive | code-intelligence-substrate | -002 | 4 | PLAN-CIS-002 |
| 8 | PLAN-LH-08 cost and token measurement instruments | code-intelligence-substrate | -003 | 6 | PLAN-CIS-013/014/022 |
| 9 | PLAN-LH-09 retrospective instrument has dead sections | code-intelligence-substrate | -004 | 3 | PLAN-CIS-020 |
| 10 | PLAN-LH-10 finalize step ordering and instrumentation | truthful-signals | -004 | 10 | PLAN-TRUTH-050 |
| 11 | PLAN-LH-11 plugin-cache and executor regen staleness | truthful-signals | -005 | 6 | PLAN-TRUTH-059 |
| 12 | PLAN-LH-12 outline scope derivation is incomplete | code-intelligence-substrate | -005 | 17 | PLAN-CIS-015 ⚠ split |
| 13 | PLAN-LH-13 a premise verified against the wrong artifact | truthful-signals | -006 | 3+3 | **NEW**, small |
| 14 | PLAN-LH-14 change_type and plan scoping under-report risk | truthful-signals | -007 | 5 | **NEW**, small |
| 15 | PLAN-LH-15 agent working discipline residue | truthful-signals | -008 | 8+5 | PLAN-TRUTH-016 |
| 16 | PLAN-LH-16 test-authoring discipline | truthful-signals | -009 | 13 | **NEW** |
| 17 | PLAN-LH-17 security hardening at logging/provider boundaries | truthful-signals | -010 | 6 | PLAN-TRUTH-011 ⚠ running |
| 18 | PLAN-LH-18 self-review completeness | review-apparatus | -003 | 9 | PLAN-PR-018 |
| 19 | PLAN-LH-19 doc-contract divergence | truthful-signals | -011 | 18 | PLAN-TRUTH-012 ⚠ split |
| 20 | PLAN-LH-20 git, worktree and footprint integrity | truthful-signals | -012 | 6 | PLAN-TRUTH-006/-054 |
| 21 | PLAN-LH-21 execute-phase yield and artifact loss | truthful-signals | -013 | 8 | **NEW** |
| 22 | PLAN-LH-22 manage-* script surface gaps | truthful-signals | -014 | 11 | PLAN-TRUTH-009 ⚠ loose |
| 23 | PLAN-LH-23 consumer-repo Java/CUI domain | truthful-signals | -015 | 2 | catch-all arm; read the bundle standards first |
| 24 | PLAN-LH-24 corpus retirement | (self) | -016 | 203 | ✅ **DONE** — 202 retired, 1 blocked |

`Msg` is the message ordinal in that destination's `inbox/` (sender
`lessons-handling-26-08-08-01`). Every hand-off went through the inbox; **no sibling tree was
edited directly.** Each destination decides fold-vs-new for itself.

All 23 routable clusters are delivered: truthful-signals 15, code-intelligence-substrate 5,
review-apparatus 3. PLAN-LH-24 (retirement) is this epic's own work and is not routed.

## Per-Lesson Dispositions

The full 203-row table lives in [`dispositions.md`](dispositions.md) — one row per lesson,
grouped by cluster, with the claim labels and confirm/refute artifacts.

| Disposition | Count |
|-------------|------:|
| `clustered-into` | 193 |
| `already-covered` | 8 |
| `standalone` | 0 |
| `stale` | 2 |
| **Total** | **203** |

`standalone` is zero because every lesson found a cluster of two or more or an existing covering
clause — 203 lessons became 23 queue items, never 203.

## Decisions

- 2026-08-08 — Epic opened as a routing epic rather than an implementing one: the operator's
  brief makes sibling-orchestrator routing the deliverable, so queue items are hand-off
  decisions, not plans this epic launches.
- 2026-08-08 — Operator: **archive by copy first, retire later.** The corpus was snapshotted
  verbatim into `archive/` before any analysis.
- 2026-08-08 — **SUPERSEDED by operator reaffirmation of the original brief**: the lessons must
  LEAVE `.plan/local/lessons-learned`, not merely be copied. The deferral behind
  `PLAN-TRUTH-044` was my caution, not a requirement; the drain ran in this session.
  202 of 203 retired via `manage-lessons remove`, each tombstone naming its cluster, destination
  epic and inbox message.
  **Verdicts**: `superseded` for routed lessons, `redundant` for the 6 confirmed duplicates.
  `completely_covered` was **deliberately used nowhere** — it demands a covering clause plus the
  concrete input on which that clause's own worked example resolves, and no such verification
  was performed in this run. Claiming it would have been precisely the fail-open `PLAN-TRUTH-044`
  exists to repair. The 8 `already-covered` lessons therefore carry `superseded` with their
  covering clause named in the reason and the verification recorded as owed.
  A batch driver script was classifier-blocked; the drain ran as individual sanctioned verb
  calls instead, with **no raw `.plan/` file operations**.
- 2026-08-08 — Operator: **validity assessed at cluster level**, per-lesson ground truth deferred
  to the receiving plan at outline, with every claim labelled OBSERVED or HYPOTHESIS and every
  HYPOTHESIS carrying a named confirm/refute artifact.
- 2026-08-08 — Operator: **fold aggressively** into existing sibling plans; new specs only where
  nothing fits. 17 of 22 clusters propose a fold; 5 propose a new spec.
- 2026-08-08 — Operator: **hand off via the sibling's inbox** so each orchestrator ingests and
  decides. One message per cluster, never a bundle — the bundled-granularity failure is already
  recorded in `truthful-signals` as PLAN-TRUTH-032.
- 2026-08-08 — Messages sent as `kind: finding` rather than `kind: candidate-lesson`. A
  `candidate-lesson` payload must carry a lesson body in the corpus's own `key=value` + markdown
  shape so the receiving pickup can lift it into `manage-lessons` with zero transcoding. These
  payloads are routed cluster proposals, not lesson bodies; mis-shaping them would break that
  contract for the consumer.

## Open Defects

- ⛔ **CONFIRMED, OBSERVED — lesson `2026-08-07-21-001` could not be retired by any sanctioned
  verb; removed from the filesystem by operator direction.** The defect below stands unchanged;
  only the blocked file is gone. ⚠ **A filesystem `rm` bypasses the tombstone writer**, so this
  is the one retirement of 203 with **no record under `.tombstones/`** — the corpus audit trail
  carries 202 tombstones for 203 removals. Its record lives instead in the verbatim body under
  `archive/`, the disposition row in `dispositions.md` § C22, and `truthful-signals` msg -016.
  The asymmetry is deliberate and recorded here so it is not later found as a mystery.
  It has **no `key=value` metadata header at all**, so `read_lesson` returns `{}`, `cmd_remove`
  hits its `if not metadata:` guard, and it reports `not_found` for a file that is present on
  disk and that `manage-lessons list` enumerates as `active` in the same session. `remove`
  conflates *file absent* with *header missing* behind one error code — two states with opposite
  remedies. `update` / `set-body` / `set-title` / `supersede` share the `read_lesson` seam, so
  the repair verbs are unavailable for the same reason. The only way out is a raw file
  operation, which the hard rules bar.
  **Left in place deliberately** as the live reproduction; the body is preserved in `archive/`.
  Filed to `truthful-signals` as msg **-016** (OBSERVED, not HYPOTHESIS — it reproduced during
  this epic's own drain), superseding the weaker empty-`component` framing in msg -014.
  Unestablished: how the header went missing; whether other header-less files exist (**n=1 is a
  sample** — a sweep for files whose first line is not `key=value` would settle it); and whether
  the repair verbs actually fail in a run, as opposed to on a code read.
- ~~PLAN-LH-23 has no owner.~~ **RESOLVED 2026-08-08** by operator direction: routed to
  `truthful-signals` (msg -015) under the catch-all arm of the three-way routing rule. Leaving it
  unowned was an under-application of that rule on my part — the rule already assigns
  everything not-ours and not-PR/review to `truthful-signals`. The open question travels with it:
  whether the practice belongs in `pm-dev-java-cui:cui-http-testing`'s standards (a plan-marshall
  change) or in the consumer repo's own CI (leaves this corpus). Unsettled; needs the bundle
  standards read first.

## Watches

- **`manage-change-ledger` `kind=build` rows are contested between two clusters.** C02 (routed to
  `truthful-signals`) and C03 (routed to `code-intelligence-substrate`) both name them. If both
  destinations plan against that surface, they collide. Re-check at each destination's emit.
- **`finalize-step-simplify` scope boundary is contested between two epics.** C10's
  `2026-06-25-08-003` (deletes out-of-scope code) went to `truthful-signals`; C05's
  `2026-07-17-09-001` (reverts an in-run reviewer fix) went to `review-apparatus`. They may be
  one surface.
- **Three documented expected-false-positives in one Q-Gate family** (C13's already-covered set).
  A gate whose expected-failure list keeps growing is being trained to be ignored. No action
  filed; re-check if a fourth appears.
- **The 8 `already-covered` verdicts are unverified against their covering clause's own worked
  example** — which is the evidence standard `manage-lessons remove --coverage-verdict
  completely_covered` requires. They must not be retired on this run's say-so.
