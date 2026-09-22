# History: Lessons Handling 26-08-26

slug: lessons-handling-26-08-26-01
closed: 2026-09-21

## Vision as pursued

Drain the lessons that had accumulated since the 2026-08-08 drain into the live sibling
epics, so accumulated lessons become owned work rather than a growing backlog. Each of the
87 active lessons found at scan time was read, clustered by failure mode, routed to the
sibling epic owning its surface, and given an auditable per-lesson disposition. This is the
second lessons-handling epic; the first (`lessons-handling-26-08-08-01`) drained 203
lessons into 24 clusters on 2026-08-08.

## Outcome

87 active lessons → 19 clusters → 18 inbox messages, delivered and drained by all three
receiving siblings before this close:

| Destination | Clusters routed |
|---|---:|
| `truthful-signals` | 13 (PLAN-LH2-01..07, 09, 12..16, plus PLAN-LH2-19 was one of these 13 — see queue for exact mapping) |
| `review-apparatus` | 3 |
| `code-intelligence-substrate` | 2 |

PLAN-LH2-18 (`manage-lessons-corpus-integrity`) was the one cluster this epic did not
route to a sibling content epic — it is a tooling defect in `manage-lessons` itself,
surfaced by this run's own retirement pass, not a lesson-content finding. At close it was
**ported into `lessons-routing` as `PLAN-LR-06`**, under a new WS-05 (corpus integrity)
created for it, per the operator's standing rule that `lessons-routing` is the permanent
distribution point and the destination for tooling-shaped findings the routing mechanism's
own dogfooding surfaces.

All 19 rows are now `transferred`. Retirement: 87 `remove` calls issued against the
lessons corpus, 81 succeeded with a tombstone, 6 returned `not_found`; 82 files were
actually removed from disk (87 − 5 remaining), one short of the 81 recorded tombstones.

## Decision record

- Opened as a routing epic, not an implementing one (2026-08-26), following the model the
  first lessons-handling epic established.
- `manage-lessons aggregate`'s automatic clustering (64/87 lessons, 15 groups) was run and
  rejected as noisy; final clustering is by failure mode, corroborated by but not derived
  from the automatic pass.
- Retirement was operator-directed (2026-08-27); the standing default is no retirement
  without explicit direction.
- At close (2026-09-21): PLAN-LH2-18 ported directly into `lessons-routing` rather than
  staying in this dated epic, and the 18 already-routed rows transitioned to `transferred`
  — consolidating the two active lessons epics per the operator's restructuring directive.

## Unresolved defects and watches carried forward

These survive the close and are not resolved by it — carried into `lessons-routing/PLAN-LR-06`
(WS-05) and, where noted, into the receiving sibling epics via the inbox messages already
delivered:

- ⛔⛔ **`manage-lessons remove` can destroy a lesson while reporting `not_found`, with no
  tombstone written** — observed on `2026-08-25-05-001`. Strictly worse than the
  previously-known `remove` refusal defect: this one destroys AFTER reporting failure.
  → `lessons-routing/PLAN-LR-06` D1.
- ⛔ **Five lessons enumerate as `active` while `get`/`remove` return `not_found`**
  (`19-001`, `19-003`, `23-13-001`, `23-13-002`, `24-14-001`) — unremovable by any
  sanctioned verb; each subject already lives on in a routed inbox message, so no content
  is lost, but the corpus cannot be mechanically cleaned of them. The standing
  YAML-frontmatter explanation for this class was refuted first-party during this run.
  → `lessons-routing/PLAN-LR-06` D2.
- ⛔ **Five pre-existing `superseded` stubs are confirmed prunable** (dry-run, all carry
  tombstones) but were out of this drain's scope. → `lessons-routing/PLAN-LR-06` D3.
- ⛔ **Eleven lessons carry a title and no body** — `add` allocated the stub, `set-body`
  never ran, and the write reported success; all eleven fall in a contiguous
  2026-08-24→26 date band, pointing at a producer change. → `lessons-routing/PLAN-LR-06`.
- ⚠ **Watch — corpus regrowth rate.** The corpus regrew from 0 to 87 active lessons in 18
  days (≈4.8/day) between the 2026-08-08 and 2026-08-26 drains. Two points are a slope,
  not a trend; re-check the rate at the next dated content sweep before treating it as
  steady. Relevant to whether `lessons-routing` needs a standing cadence rather than
  periodic campaigns.
- ⚠ **Watch — cross-epic seam collisions** flagged at scan time and not yet re-checked:
  `review_commitments reconcile` (3 clusters' worth, all in `truthful-signals`'s intake),
  `affected_files` (named by two separate routed clusters, both bound for
  `truthful-signals`'s `manage-references` surface). Re-check at whichever sibling next
  emits against those surfaces.
- ⚠ **Watch — orchestrator-tooling blind spot to router epics**, observed running this
  epic's own `cleanup`: `corpus cross-check` returns a vacuous `collision_detected: false`
  over `specs_scanned: 0` for a router epic (it stages no `## Expected Surface` specs), and
  `cleanup restart-check` scored `not_ready` solely because `corpus_reconciliation` cannot
  distinguish "spec missing" from "this epic has none by design." Neither finding had a
  route to `truthful-signals` (owner of orchestrator tooling) because this epic's inbox
  stream there was already closed — recorded here since it had nowhere else to land.
