# Epic: Lessons Handling 26-08-26

slug: lessons-handling-26-08-26-01

> Ledger document for one epic under `.plan/local/orchestrator/lessons-handling-26-08-26-01/`.
> The layout and authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Drain the lessons that have accumulated since the 2026-08-08 drain into the three live
sibling epics, so accumulated lessons become owned work rather than a growing backlog.
Each lesson is (1) read, (2) clustered by failure mode, (3) routed to the sibling epic
that owns its surface, and (4) given an auditable per-lesson disposition. "Done" is:
every scanned lesson carries a disposition, and every routed cluster has landed in a
sibling epic's inbox.

This is the **second** lessons-handling epic. The first
(`lessons-handling-26-08-08-01`) drained 203 lessons into 24 clusters. This one scans a
corpus that regrew to 87 active lessons in the 18 days since.

## Routing Model

This epic is a **router**, not an implementer. Its queue items are routing decisions, not
plans it launches itself. The standing three-way routing rule applies:

| Destination | Takes |
|-------------|-------|
| `review-apparatus` | PR-review / review-bot reliability lessons (tested first, wins outright) |
| `code-intelligence-substrate` | Token-reduction, context-economy, measurement-substrate lessons |
| `truthful-signals` | Everything else — confident-signal-hides-a-caveat, false-green, vacuous-guard lessons |

Cross-epic hand-off goes through the destination epic's `inbox/` via
`orchestrator inbox write`, never by a direct edit of a sibling's tree.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug lessons-handling-26-08-26-01
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: CORPUS SCANNED, ROUTED AND RETIRED. Scan 2026-08-26, retirement 2026-08-27 (operator-directed). 87 active lessons -> 19 clusters -> 18 inbox messages: truthful-signals 13 (msgs -001..-013), review-apparatus 3 (-001..-003), code-intelligence-substrate 2 (-001..-002). Stream CLOSED at all three siblings, so each drain reads FINISHED not EMPTY. PLAN-LH2-18 (corpus integrity) kept here, not routed. DISPOSITIONS: 84 clustered-into, 3 standalone, 0 already-covered, 0 stale - both zeros DELIBERATE (neither verification was performed; claiming either is the fail-open PLAN-TRUTH-044 repairs). RETIREMENT: 87 remove calls, 81 success with tombstone, 6 not_found; corpus 87 active -> 5 active, so 82 files gone against 81 tombstones. DERIVED: 81+6=87 calls, 87-5=82 removed. ⛔⛔ NEW OBSERVED DEFECT, the worst finding here: manage-lessons remove DESTROYED 2026-08-25-05-001 while returning not_found. Before: list active AND get success. One remove call, returned error not_found. After: gone from both. No tombstone, so that retirement has NO audit record. Strictly worse than the known remove defect, which merely REFUSES - this one refuses AFTER destroying, so a caller retrying on not_found or reading it as nothing-happened is wrong unrecoverably. Unestablished: whether the unlink precedes the metadata read, or the tombstone write failed after a successful unlink. ⛔ 5 lessons SURVIVE and cannot be removed by any sanctioned verb (19-001, 19-003, 23-13-001, 23-13-002, 24-14-001) - all five refused with not_found; each subject is already carried in a routed inbox message. Also still present: 5 pre-existing superseded stubs, prunable via cleanup-superseded (dry-run confirms all 5 have tombstones); NOT pruned, they were never in this drain's scope. ⛔ DO NOT wipe .plan/local/lessons-learned wholesale - that destroys .tombstones/, the audit trail for all 81 recorded retirements. NEXT ACTION: siblings drain their inboxes and return fold-or-decline verdicts; then stamp each PLAN-LH2-NN row with the accepting plan id.
**Phase**: orchestrating
**Inbox (derived)**: no inbox directory (nothing to drain from)
**Queue** (staged, in order):
- (empty)
- PLAN-LH2-01 (WS-01) — status: transferred
- PLAN-LH2-02 (WS-01) — status: transferred
- PLAN-LH2-03 (WS-01) — status: transferred
- PLAN-LH2-04 (WS-01) — status: transferred
- PLAN-LH2-05 (WS-01) — status: transferred
- PLAN-LH2-06 (WS-01) — status: transferred
- PLAN-LH2-07 (WS-01) — status: transferred
- PLAN-LH2-08 (WS-03) — status: transferred
- PLAN-LH2-09 (WS-02) — status: transferred
- PLAN-LH2-10 (WS-02) — status: transferred
- PLAN-LH2-11 (WS-02) — status: transferred
- PLAN-LH2-12 (WS-01) — status: transferred
- PLAN-LH2-13 (WS-01) — status: transferred
- PLAN-LH2-14 (WS-01) — status: transferred
- PLAN-LH2-15 (WS-01) — status: transferred
- PLAN-LH2-16 (WS-01) — status: transferred
- PLAN-LH2-17 (WS-03) — status: transferred
- PLAN-LH2-18 (WS-04) — status: transferred
- PLAN-LH2-19 (WS-01) — status: transferred
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-LH2-18 — the only cluster this epic kept. Its subject is the corpus itself, and
  three of its inputs are first-party observations from this run's own scan. **CLOSING
  UPDATE (2026-09-21):** ported into `lessons-routing` as `PLAN-LR-06` rather than left
  here — this epic never implements, and its tooling-shaped defect belongs in the
  permanent router's new WS-05 (corpus integrity), not in a dated one-shot epic.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug lessons-handling-26-08-26-01, and rewritten in
     place by the compact stage at cleanup. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- ⚠ **`(spec missing)` on every row is CORRECT, not an error.** This is a router epic: its
  queue items are routing decisions delivered as inbox messages to sibling epics, not plan
  specs staged under `plans/`. `corpus enumerate` will report `rows_without_spec: 19` of
  `rows_total: 19` for the same reason. ⛔ **The `next` verb can therefore never emit here** —
  the emit is a one-line pointer to a spec file that does not exist. This epic terminates by
  stamping each row with the accepting sibling's plan id, not by launching anything.
- **PLAN-LH2-06** (15 lessons) and **PLAN-LH2-10** (8 lessons) exceed the scope-bloat guard.
  Both are routed as single clusters because they are one coherent failure mode; the
  receiving epic decides fold-vs-split. Each carries an internal pair that is one defect
  observed twice — folding those is a merge, not a discard.
- **PLAN-LH2-03** carries **four independent observations of one defect**. The recurrence
  count is derived from the enumeration in `dispositions.md`, not asserted.
- **PLAN-LH2-16** and **PLAN-LH2-17** are single-lesson (`standalone`) items. Both are
  routed anyway: 16 because its actionable half does not depend on its unknown cause, 17
  because its reframing of the checkpoint metric is the valuable part.
- **PLAN-LH2-08** is routed to `code-intelligence-substrate` rather than `truthful-signals`
  because every member is a reason the cost of a run cannot be measured, and measurement
  is that epic's blocking dependency — not because the defects are token-shaped.

## Per-Lesson Dispositions

The full 87-row table lives in [`dispositions.md`](dispositions.md) — one row per lesson,
grouped by cluster, carrying the disposition AND how much of the lesson this run could read.

| Disposition | Count |
|-------------|------:|
| `clustered-into` | 84 |
| `standalone` | 3 |
| `already-covered` | 0 |
| `stale` | 0 |
| **Total** | **87** |

The scan population is `manage-lessons list`: 87 active of 92 total. The 5 excluded are
pre-existing `superseded` stubs on the separate `cleanup-superseded` retention lifecycle —
not active lessons, and deliberately untouched.

`already-covered` and `stale` are both **deliberately zero**. Each requires a verification
this run did not perform: `already-covered` needs a named covering clause plus the concrete
input its own worked example resolves; `stale` needs the premise re-checked against HEAD.
Claiming either without that evidence is the fail-open `PLAN-TRUTH-044` exists to repair.

## Read-Coverage of the Scan

The scan did not read all 87 lessons equally, and the difference is load-bearing:

| Read outcome | Count | Meaning |
|--------------|------:|---------|
| `full` | 71 | `get` returned metadata and a body |
| `title-only` | 11 | `get` succeeded; the record carries **no body at all** |
| `unresolvable` | 5 | `list` enumerates it `active`; `get` returns `not_found` |

⛔ **Every `title-only` and `unresolvable` cluster assignment is a HYPOTHESIS**, derived
from the title and from sibling lessons citing it — never from a body this run read. The
receiving plan re-checks it at outline. This is stated here rather than buried in the
disposition table because 16 of 87 rows — 18% of the corpus — rest on it.

## Decisions

- 2026-08-26 — **Opened as a routing epic, not an implementing one**, following the model
  the 2026-08-08 lessons epic established under operator direction and the standing
  three-way finding-routing rule. Alternative considered: stage the 19 clusters as plan
  specs in this epic and emit them from here, which is what the bare `lessons` workflow
  doc describes. Rejected because the surfaces belong to three sibling epics that already
  hold related staged work, and a fourth ledger holding plans against their surfaces is
  the duplicate-work failure the cross-check exists to prevent.
- 2026-08-26 — **`manage-lessons aggregate` was run and NOT adopted as the clustering.**
  It grouped 64 of 87 lessons into 15 groups on cross-reference and shared-component
  signals only. Both proved noisy: its largest cross-ref group folded six topically
  unrelated lessons that merely cite one co-captured sibling, and its largest
  shared-component group folded 16 lessons under `phase-6-finalize` — a component bucket,
  not a failure mode. Used as a corroborating input; the clustering is by failure mode.
- 2026-08-26 — **No retirement performed.** The prior epic drained its corpus under
  explicit operator direction and hit one file no sanctioned verb could touch, requiring a
  filesystem `rm`. That direction was for that run and is not standing authority; the
  `remove` defect it surfaced is still unfixed. Deferred to an operator decision.
- 2026-08-26 — **Cluster-level validity only.** Per-lesson ground truth is deferred to the
  receiving plan at outline. No lesson's premise was re-checked against HEAD in this run,
  which is why `stale` is zero rather than "none found".

## Retirement (operator-directed, 2026-08-27)

The operator directed retirement of all ingested lessons. 87 `remove` calls were issued with
`--coverage-verdict superseded`, each tombstone naming its cluster, destination epic and inbox
message. `completely_covered` was used **nowhere** — its evidence pair was never verified.

| | Count | Derivation |
|---|--:|---|
| `remove` returned success (tombstone written) | 81 | counted from the call results |
| `remove` returned `not_found` | 6 | counted from the call results |
| **calls issued** | **87** | 81 + 6 |
| active lessons remaining | 5 | `list --status all` |
| **files actually gone** | **82** | 87 scanned − 5 remaining |

⛔ **82 files gone against 81 tombstones.** The gap is derived from the two independent counts
above, not asserted — and it is one specific file, named below.

## Open Defects

- ⛔⛔ **`manage-lessons remove` DESTROYED a lesson while reporting `not_found`
  (`2026-08-25-05-001`).** All three states observed first-hand in this session:
  **before** — `list` enumerated it `active` **and** `get` returned success with metadata and
  title; **operation** — exactly one call, `remove --coverage-verdict superseded`, returning
  `status: error`, `error: not_found`; **after** — `get` returns `not_found` and the file is
  absent from `list --status all`. Nothing else touched it.
  Because `remove` reported failure it wrote **no tombstone**, so this one retirement has no
  audit record — 81 tombstones for 82 removals.
  ⇒ **This is strictly worse than the recorded `remove` defect.** That one conflates
  *file-absent* with *header-missing* behind one `not_found` and merely **refuses**; this one
  **refuses after destroying**. A caller that retries on `not_found`, or that treats the error
  as "nothing happened", is wrong in the unrecoverable direction.
  **Unestablished:** whether the unlink precedes the metadata read, or the tombstone write
  failed after a successful unlink. Owned by `lessons-routing/PLAN-LR-06` (ported from
  PLAN-LH2-18 at close, 2026-09-21).

Three further corpus defects were observed **first-party** during this scan — reproducible by
re-running the enumeration, not inferred from any lesson's narrative:

- ⛔ **Five lessons enumerate as `active` while `get` returns `not_found`** —
  `2026-08-08-19-001`, `2026-08-08-19-003`, `2026-08-23-13-001`, `2026-08-23-13-002`,
  `2026-08-24-14-001`. No documented read path resolves them. Lesson `2026-08-25-05-002`
  records this class at **n=2**; the population has since grown to **5**. Owned by
  `lessons-routing/PLAN-LR-06` (ported from PLAN-LH2-18 at close, 2026-09-21).
  ⚠ **These same five are the only survivors of the retirement** — `remove` refused all five
  with `not_found`, so the corpus cannot be emptied by any sanctioned verb. They are the
  residue an operator must clear by hand; each one's subject is already carried in a routed
  inbox message, per `dispositions.md`.
- ⛔⛔ **The standing explanation for that class is REFUTED.** `2026-08-08-20-002`
  attributes the `not_found` to YAML frontmatter and names `19-001`, `19-002`, `19-003` as
  the three affected files. But `2026-08-08-19-002` — a YAML-frontmatter file by that
  lesson's own account, enumerating with empty `component`/`category`/`title` exactly like
  its siblings — **resolves through `get` and returns its full body**. YAML frontmatter is
  therefore not sufficient to cause `not_found`, and the real mechanism is unestablished.
  **Unestablished:** what discriminates `19-002` from `19-001` and `19-003`.
- ⛔ **Eleven lessons carry a title and no body at all** — `add` allocated the stub,
  `set-body` never ran, and the write reported success. All eleven fall in a contiguous
  08-24 → 08-26 date band, which points at a producer change rather than eleven independent
  authoring slips. The titles are long enough to carry the finding, which is why the loss
  is survivable and why it is invisible to anyone reading `list`. **Unestablished:** which
  producer, and whether the bodies were ever written. Owned by
  `lessons-routing/PLAN-LR-06` (ported from PLAN-LH2-18 at close, 2026-09-21).

## Cleanup findings (2026-08-27)

Two observed first-party while running `cleanup` on this epic. Both are the **router epic is
invisible to the tooling** shape — neither is a defect in this ledger.

- ⛔ **`corpus cross-check` returned `collision_detected: false` over `specs_scanned: 0`** — a
  vacuous zero. It scanned 9 epics, 4 plans and 337 candidates, but a candidate pair needs
  *this* epic's side too, and a router epic stages no specs carrying an `## Expected Surface`.
  ⭐ **The blindness is demonstrable, not theoretical:** this session found by hand that two of
  this epic's cluster slugs are byte-identical to `lessons-handling-26-08-08-01`'s
  (`doc-contract-divergence`, `review-bot-participation-and-reliability`). The verb reported no
  collision over exactly that pair. ⇒ **Do not read this verb's clean result as evidence of
  non-duplication for a router epic.**
- ⛔ **`cleanup restart-check` returns `verdict: not_ready`, and its only failing signal is
  correct-by-design.** `corpus_reconciliation` reports `19 row(s) without a spec` — which is
  what a router epic *is*. The signal has no notion of an epic that stages no specs, so it
  cannot distinguish *a spec is missing* from *this epic has none by design*. The other four
  scored signals are all `ready`; `registry_parity` is `not_available` and correctly excluded
  from the floor.

⚠ **Neither could be filed to `truthful-signals`**, which owns the orchestrator tooling: this
epic filed a `stream-end` marker there, and `inbox write` now refuses this sender with
`stream_closed`. That refusal is correct — the marker means "no more from me" and would bind
nothing otherwise — but it means **a finding discovered AFTER the drain has no route to its
owning epic from here**. Recorded here instead, and surfaced to the operator.

## Watches

- **The corpus regrew from 0 to 87 active lessons in 18 days** (drained 2026-08-08, scanned
  2026-08-26) — roughly 4.8 lessons/day. The prior epic's drain was a one-off effort; at
  this rate the corpus needs a standing cadence rather than a periodic campaign. Re-check
  the rate at the next drain before concluding it is steady — two points are a slope, not a
  trend.
- **`review_commitments reconcile` appears in three separate clusters' worth of
  observations** (PLAN-LH2-01 holds all three). If `truthful-signals` folds them into
  different plans they will collide on one seam. Re-check at that epic's emit.
- **`affected_files` is named by both PLAN-LH2-05 (its own cluster) and PLAN-LH2-04's
  `26-06-001`** via the freshness-gate route. Both go to `truthful-signals`; if it plans
  against `manage-references` twice they overlap. Re-check at emit.
- **`2026-08-26-05-004` explicitly warns against another bot-charter round.** If
  `review-apparatus` folds PLAN-LH2-10 into a charter plan, that is the move the lesson
  predicts will fail. The failure it records is empty/refused/refused-structural, which no
  charter change addresses.
