# PLAN-56: Orchestrator Inbox Pickup — Parse, Decide, Reconcile, Clear

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Operator proposal 2026-07-23. The orchestrator-side half of the inbox capability
> (its plan/finalize side is PLAN-55). Depends on PLAN-55's envelope schema. Turns the orchestrator's
> manual, paste-driven landing reconciliation into a directory-scan the orchestrator drives.

## Objective

Once orchestrated plans drop structured messages into `inbox/` (PLAN-55), the orchestrator needs a
verb that ingests them: scan the inbox, parse each message, and DECIDE per finding —
promote-to-global-lessons, fold-into-an-existing-staged-plan, stage-a-new-plan, or discard — then
reconcile the landing (queue→shipped, stamp pr+landing, retire watches) and archive-or-clear the
consumed message so re-scan is idempotent. This is the cross-plan-context decision a single plan
cannot make, and it automates the reconciliation the orchestrator does by hand from pastes today.

## Deliverables

1. **D1 (design gate) — the pickup trigger and verb surface.** Decide whether inbox pickup extends the
   existing `analyze` verb (an "inbox-scan mode" when invoked with no paste) or is a new `intake` verb,
   and define the trigger: the manual "lessons landed" / no-paste invocation is the MVP; a directory
   Monitor is the gold increment and is DEFERRED to PLAN-48 coordination (auto-reconcile OK, auto-emit
   stays gated by emit≠running). Bind to PLAN-55's D1 envelope contract exactly — do not re-derive it.
2. **D2 — scan + parse (untrusted-aware).** Enumerate `inbox/`, parse each message against the
   envelope schema. A message payload may quote third-party text (bot output, PR comments), so embedded
   third-party content routes through the `untrusted-ingestion` posture before it influences any ledger
   write — the plan's own narrative in the message is trusted, quoted external text is a lead.
3. **D3 — decide per finding / candidate-lesson.** For each item the orchestrator applies the standing
   decision: (a) promote a genuinely-global standing rule to the global lessons store; (b) fold an
   epic-specific finding into an existing staged `plans/PLAN-NN` spec; (c) stage a new plan spec + queue
   entry; (d) discard a duplicate/covered item — with a per-item disposition recorded in the ledger
   (the same auditable-disposition discipline the `lessons` verb uses). The recurrence-vs-new judgement
   is the whole point: the orchestrator has the cross-plan context the plan lacked.
4. **D4 — reconcile the landing from the message.** When `kind == landing`, drive the existing landing
   reconciliation from the message payload instead of an operator paste: verify against git ground truth
   (a landing message is a LEAD, not a fact — the same verify-first posture as a paste), write
   `landings/PLAN-NN.md`, transition queue→shipped, stamp pr+landing via the whole-array write, retire
   satisfied watches, regenerate START-HERE.
5. **D5 — archive-or-clear + idempotence.** A consumed message is moved to an orchestrator-local
   `inbox/archive/` (or deleted, per D1) so a re-scan does not re-process it; a partially-processed
   scan is safe to resume. Tests: a landing message reconciles a shipped plan end-to-end; a
   candidate-lesson that is a recurrence folds rather than duplicating; a global rule promotes to the
   store; a re-scan after archive is a no-op; a malformed / third-party-bearing message is validated,
   not trusted.

Five deliverables (D1 a gate) — under the split guard.

## Claim Labels

- OBSERVED: the reconciliation this automates — read at this epic's Watches and at the `analyze.md`
  Step-4 full-ship reconciliation (landings/PLAN-NN.md, queue→shipped, stamp, retire, regen), currently
  driven by an operator paste.
- OBSERVED: the untrusted-ingestion posture a message must route through — read at
  `orchestration-model.md` § Untrusted-Ingestion Boundary and `untrusted-ingestion/SKILL.md`.
- OBSERVED: the per-item auditable-disposition discipline this reuses — read at
  `marshall-orchestrator/workflow/lessons-handling.md` (the local dedup/aggregate obligation).
- HYPOTHESIS: extending `analyze` is cleaner than a new verb — confirm/refute at
  `marshall-orchestrator/workflow/analyze.md` § the three input modes (an inbox scan is a fourth input
  mode; verify-at-outline). If `analyze` already fits, D1 collapses to adding the mode.
- Verify-first clause: before D4 automates landing reconciliation, confirm the whole-array pr/landing
  stamp is still the sanctioned write path (PLAN-53 may land a per-row setter first) — consume whichever
  is current at outline, do not hard-code the whole-array workaround if PLAN-53 shipped.

## Expected Surface

- HYPOTHESIS: `marshall-orchestrator/workflow/analyze.md` (+ a new inbox-scan mode) OR a new
  `intake.md` workflow doc and its verb wiring in `orchestrator.py` — settle at D1.
- OBSERVED: `marshall-orchestrator/scripts/orchestrator.py` — a scan/parse helper for the inbox
  (deterministic enumeration; the decide step stays in the orchestrator LLM context, never dispatched).
- OBSERVED: the inbox envelope schema/validator from PLAN-55 D1 (consumed, not redefined).
- OBSERVED: tests under `test/plan-marshall/marshall-orchestrator/**`.

Re-verify at outline against HEAD: PLAN-55 (envelope schema), PLAN-53 (pr/landing setter), and — if
PLAN-49 has renamed `marshall-orchestrator`→`plan-orchestrator` — the new paths.

## Dependencies and Sequencing

- **Depends on: PLAN-55** (envelope schema + the channel plans write to) — hard dependency; PLAN-56
  consumes what PLAN-55 defines. And transitively on **PLAN-41** (detection seam PLAN-55 reuses).
- Coordinate with: **PLAN-48** (emit-autonomy) — the Monitor auto-scan is PLAN-48's auto-action; this
  plan builds the manual-trigger MVP and leaves the auto-trigger to that coordination.
- Adjacent to: **PLAN-53** (pr/landing setter) — D4's stamp should consume PLAN-53's setter if it has
  landed; verify-first clause above covers it.
- Ordering vs **PLAN-49** (drain-gated rename): PLAN-49 renames `marshall-orchestrator`; this plan edits
  it. Standard drain-gate applies — PLAN-49 stays last.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-56-orchestrator-inbox-pickup.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests (the verb/workflow,
the scan helper, tests) — it creates and edits NO file under `.plan/local/orchestrator/` during
execution, and reports its outcome through its PR alone. The inbox READ-AND-CLEAR behaviour it builds
is exercised by the orchestrator at runtime, not written by this implementing plan. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
