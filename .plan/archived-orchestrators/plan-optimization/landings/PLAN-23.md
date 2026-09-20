# Landing Analysis: PLAN-23 — Marker-Detector Ownership & Fixture

epic: plan-optimization
workstream: WS-10
pr: #986 (`058a880c`)

> Landing record. Claims verified against the merge commit, not the finalize report.

## Deliverable Fidelity vs Spec

Verified against `058a880c` — **48 files, +1093/−621. 4/4 shipped.**

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — provenance fixture + regex fix + test-suite rewrite | shipped | `search_markers.py:35` `MARKER_PATTERN = re.compile(r'/\*~~\(TODO:\s*(.+?)\)~~>\*/')` — now closes on `)~~>*/` (was the vacuous `)>*/`); `:32-33` comment pins the delimiter to the fixture, "never re-derive from memory"; `fixtures/cui-rewrite/MarkedSample.java` + `PROVENANCE.md` added; the defect-pinning `test_markers_search.py` **deleted** (−328), rebuilt as `search-markers/test_search_markers.py` (+456) |
| D2 — exit-code contract `total_markers > 0` fails | shipped | `:170 return 1 if result['data']['total_markers'] > 0 else 0` (was `ask_user_count > 0`); SKILL.md:60-61 documents `1` = any marker OR scan error |
| D3 — domain-owned detector in `pm-dev-java-cui` | shipped | detector relocated to `pm-dev-java-cui/skills/search-markers/scripts/search_markers.py` (out of `script-shared`); ownership follows the cui format |
| D4 — core-side ext-point-domain-verb seam + core verb retired | shipped | `script-shared/scripts/build/_build_cli.py` −25 (core verb retired), `extension_base.py` +28 (domain-verb seam), `test_extension_domain_verb.py` +92; `pm-dev-java-cui/plugin.json` + `plan-marshall-plugin/extension.py` register the domain verb |

## Why this closes the vacuous gate

Both halves of the vacuous-guard were confirmed and fixed: the regex terminated on `)>*/` (missing
the trailing `~~` cui-rewrite emits), and the exit predicate fired only on `ask_user_count > 0`. Every
test and checked-in Java fixture hard-coded the defective delimiter, so the suite passed green while
the gate could never detect a real marker — the archetype's purest form. The provenance fixture (a
real cui-rewrite marker with recorded origin) now pins the format, so an upstream wording change
breaks a test rather than silently re-disabling the gate.

Zero loop-backs, CI green on the first pass. This is the **vacuous-guards** archetype's first
confirmed close in the epic.

## Retrospective findings — three, all flagged for truthful-signals

1. **New vacuous guard in the finalize machinery** (lesson `2026-07-22-20-006`): `pre-submission-self-review`
   computes a DISPATCH decision (`total_candidates=151 > 5`) then executes **inline anyway** — a
   dispatched leaf cannot dispatch, so that formula can never fire where it is evaluated. Same family
   as `scope_creep_check` and the saturated markers. → **vacuous-guards-sweep** candidate.
2. **Retrospective aspect-registry silently drops findings** (`2026-06-20-17-003`, **27th recurrence**):
   `compile-report` returned `sections_omitted: ['Phase Dispatch Boundaries']` and the dropped
   fragment was **non-empty — it carried finding #1**. `sections_omitted` being non-empty still
   returns `status: success`. This is the **flagship confident-signal-hides-a-caveat archetype** and
   a 27× recurrence that has closed nothing — **staged as truthful-signals PLAN-51**.
3. **Lessons pipeline records but closes nothing**: 4 of 5 proposals were recurrences, two targets
   over a month old. A signal about the pipeline, not this plan. → candidate.

## Cross-links

- **Scope mis-estimate confirmed load-bearing**: the router saw `distinct_paths=1` → routed `light`;
  realized footprint was **48 files / 5 bundles**. The operator's escalation to `deep` at init was
  load-bearing. Trigger = the `"implement <spec-file>"` request shape (merged into `2026-07-21-17-003`).
  **This is exactly what truthful-signals PLAN-41 fixes** — phase-1-init reading the referenced spec
  would feed the router the real footprint. Cross-linked to PLAN-41.
- **Daemon still pre-fix in this session**: PLAN-23's session hit the pre-fix supervisor and needed
  manual job-log verification per routed build. Consistent with the known item — the confirmed
  restart (pid 42648, 0.1.1194) post-dates this session; discharged going forward.

## Reconciliation Actions

- [x] status.json `plans[]` → `shipped`, pr `986`, landing `landings/PLAN-23.md`
- [x] **truthful-signals PLAN-27 UNBLOCKED** — its `pm-dev-java-cui` ownership home now exists
      (`pm-dev-java-cui/skills/search-markers/`); PLAN-27's D1 log parser lands beside it
- [x] Watch **vacuous-guards** — CLOSED one (this plan), OPENED one (lesson `2026-07-22-20-006`
      pre-submission-self-review)
- [x] Watch **confident-signal-hides-a-caveat** — reinforced (aspect-registry silent drop → PLAN-51)
- [x] resume_anchor updated (plan-optimization now 20 shipped, 1 running); START-HERE regenerated
- [x] PLAN-41 cross-link recorded (scope mis-estimate = the "implement <spec-file>" shape it fixes)

## Follow-Ups

- **plan-optimization drains when PLAN-35 lands** — then archive via #937.
- **truthful-signals PLAN-51** staged for the aspect-registry silent-drop (27× recurrence).
