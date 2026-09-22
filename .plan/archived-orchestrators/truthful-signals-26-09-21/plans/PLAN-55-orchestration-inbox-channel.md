# PLAN-55: Orchestration Inbox Channel — Plans Drop Structured Results, Not Global Lessons

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator proposal 2026-07-23. The plan/finalize half of a two-plan capability
> (its orchestrator-side pickup is PLAN-56). Closes the standing `landing-record-completeness` watch
> ("finalize does NOT notify the orchestrator on merge") and the candidate-(f) lessons-pipeline
> problem. See `persona-marshall-orchestrator/standards/orchestration-model.md` for the write-boundary
> this plan narrowly amends.

## Objective

Today an orchestrated plan's only channel back to the epic is its PR, and the orchestrator
reconstructs every landing by hand from an operator paste plus git ground truth. Worse, the plan
writes its lessons straight into the GLOBAL lessons store, where recurrences pile up because a single
plan has no cross-plan context to know it is the Nth recurrence (the candidate-(f) "records-but-closes-
nothing" problem). Give an orchestrated plan a structured, one-way channel: on finalize it writes a
message (landing summary + findings + candidate-lessons) to a new `inbox/` OUTBOX under the epic tree,
instead of writing the global lessons store. The orchestrator (PLAN-56) picks it up and decides. The
plan's console output is unchanged; the inbox message is additive.

## Deliverables

1. **D1 (design gate) — the inbox message envelope, forward-compatible for orchestrator↔orchestrator.**
   Define the envelope written to `inbox/{sender}-{seq}.{ext}`: `sender` (a struct
   `{type: plan | orchestrator, id: PLAN-NN | epic-slug}` — so the SAME channel later carries
   orchestrator→orchestrator messages, not only plan→orchestrator), `epic` slug, `kind`
   (`landing` | `finding` | `candidate-lesson`), a stamped creation marker, and a typed `payload`.
   The landing payload carries what the orchestrator reconciles today (PR#, deliverable fidelity,
   metrics, routing/merge behaviour). Design the schema so a reader can validate it; name the
   validation seam. Settle the file format (TOON vs md-with-frontmatter) against what PLAN-56 must parse.
2. **D2 — orchestration-context detection + finalize writes the inbox message.** Detect that a plan is
   orchestrated from its spec path (`.plan/local/orchestrator/{slug}/plans/…`) — the SAME seam PLAN-41
   builds for spec ingestion; reuse it, do not add a parallel detector. In orchestration context,
   finalize's landing/lessons step writes one inbox message and the global-lessons-store write is
   SKIPPED entirely (see D4). A non-orchestrated plan is completely unchanged.
3. **D3 — the narrow write-boundary carve-out.** Amend
   `orchestration-model.md` § Ledger Write-Boundary: `inbox/` is a sanctioned, append-only,
   plan-writable OUTBOX — a plan may write ONLY its own `inbox/{sender}-{seq}` message file and NOTHING
   else under `orchestrator/{slug}/` (status.json, epic.md, landings/, plans/, workstreams/ stay
   orchestrator-only). Frame it as a message channel, not shared state: plans write messages, never
   authority. The existing prohibition on every non-inbox surface must remain enforced and tested.
4. **D4 — the global-lessons step is SKIPPED for an orchestrated plan; ALL lessons become inbox
   candidates.** An orchestrated plan writes NOTHING to the global lessons store — that finalize step is
   skipped as an intrinsic property of being orchestrator-driven. Every lesson/finding it would have
   captured is emitted to the inbox as a `candidate-lesson`. The plan does NOT classify global-vs-epic:
   it CANNOT, because that judgement needs the cross-plan context only the orchestrator holds (this is
   the whole reason for the channel). The promote-to-global-store decision belongs solely to the
   orchestrator's pickup (PLAN-56 D3), never to the plan. Non-orchestrated plans keep writing the global
   store exactly as today — the skip is conditional on orchestration context only.
5. **D5 — tests.** An orchestrated plan writes a well-formed inbox message and does NOT write the
   global lessons store AT ALL (the step is skipped, not filtered — assert zero global-store writes for
   ANY lesson kind); a non-orchestrated plan is byte-for-byte unchanged (still writes the global store);
   a plan attempting to write `status.json` / `epic.md` under the epic tree still FAILS the boundary
   (the carve-out did not widen); the envelope validates against D1's schema.

Five deliverables (D1 a gate) — under the split guard.

## Claim Labels

- OBSERVED: the ledger write-boundary today forbids ALL plan writes under `orchestrator/{epic}/` —
  read at `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
- OBSERVED: the standing gap this closes — read at this epic's Watches, "landing-record-completeness
  (HANDOFF IS THE GAP — finalize does NOT notify orchestrator on merge)".
- HYPOTHESIS: the finalize lessons-capture step is the right write-site to redirect in orchestration
  context — confirm/refute at `phase-6-finalize` § the lessons-capture step and its global-store write
  (verify-at-outline). If landing-summary and lessons are separate finalize steps, D2 touches both.
- HYPOTHESIS: orchestration-context detection can reuse PLAN-41's spec-path seam rather than a new
  detector — confirm/refute at PLAN-41's landed D2 ingestion site (verify-at-outline; PLAN-41 must land
  first, see Dependencies).
- Verify-first clause: before D3 widens the boundary, confirm against the standard's actual wording
  that no existing consumer relies on "plans write NOTHING under the tree" as an absolute (e.g. a
  plugin-doctor rule or a test asserting zero plan writes) — if one does, D3 updates it in lock-step so
  the carve-out is enforced, not merely documented.

## Expected Surface

- OBSERVED: `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary (D3).
- HYPOTHESIS: `phase-6-finalize/**` — the lessons-capture / landing step and the global-lessons-store
  write site (D2/D4); exact files verify-at-outline.
- HYPOTHESIS: `manage-lessons/**` — only if D4's global-vs-inbox routing touches the store's write path
  (verify-at-outline).
- OBSERVED: a new inbox-envelope schema/validator location — co-located with whatever PLAN-56 reads
  (settle at D1).
- OBSERVED: tests under `test/plan-marshall/phase-6-finalize/**` and the boundary test suite.

Re-verify at outline against HEAD: PLAN-41 lands the detection seam this plan reuses.

## Dependencies and Sequencing

- **Depends on: PLAN-41** (single-source spec ingestion) — it builds the spec-path detection seam D2
  reuses. Sequence AFTER PLAN-41 ships; do not build a parallel detector.
- Pairs with: **PLAN-56** (orchestrator pickup) — B consumes A's D1 envelope schema, so PLAN-56
  depends on this plan. Coordinate the envelope contract across the two at outline.
- Adjacent to: **PLAN-48** (emit-autonomy) — the gold-path directory Monitor that auto-scans the inbox
  is PLAN-48's auto-action territory (auto-reconcile OK, auto-emit stays gated by emit≠running); the
  channel this plan builds is what that Monitor would watch. Coordinate at PLAN-48 outline.
- Not in flight-collision with the current four (PLAN-41 phase-1-init, PLAN-27 java-markers, PLAN-46
  title, PLAN-45 routed-verdict) beyond the PLAN-41 dependency above.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-55-orchestration-inbox-channel.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests (the finalize step,
the standard, the schema, tests) — it creates and edits NO file under `.plan/local/orchestrator/`
during execution, and reports its outcome through its PR alone. (The `inbox/` carve-out it DEFINES is
a runtime channel for FUTURE orchestrated plans, not a licence for this implementing plan to write the
ledger.) See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
