envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T07:44:15Z

# FORWARDED CLUSTER — evidence emission: the audit trail is unpopulated, partial, or structurally unwritable

**Forwarded from `truthful-signals` 2026-07-29 under the inbound routing rule** (evidence emission →
this epic). ⚠ **Leads, not facts** — re-verify before any ledger write.

| Source message | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-010` | PLAN-99 / #1043 | The dispatch-boundary audit trail is **unpopulated, unvalidated AND uncounted** — *"three failures that all read as"* success |
| `self-review-cannot-see-an-unreachable-guard-007` | PLAN-81 / #1042 | Per-task `[ARTIFACT]` emission **stops after the first per-deliverable commit batch** |
| `runnable-slice-keys-…-018` | PLAN-89 / #1044 | A step's **structural caveat stayed in the work log and never reached its outcome** |
| `one-coherent-automated-review-contract-017` | PLAN-92 / #1041 | `record-step` for `archive-plan` is **structurally unsatisfiable** |

## The sharpest one, quoted because it is a genuine contract collision

`archive-plan` cannot ever record its own execution-log row. Two documented constraints collide:

- dispatcher item 5e: *"this row is recorded for EVERY finalize step — dispatched OR inline"*, after
  the step completes;
- `archive-plan` ordering: it **MUST be last**, and it **moves the plan directory** — including
  `execution.toon`, the row's own target.

Observed: `status: error, file_not_found, execution.toon not found`. ⇒ **Not a bug in either rule —
the pair is unsatisfiable.** One of them must yield, and the choice is a design decision, not a fix.

## Owners already in this epic

- **PLAN-104 `finalize-dispatch-evidence-is-missing`** — the evidence seam; owns the missing
  `[DISPATCH]` rows and partial `[ARTIFACT]` emission. **Fold messages 010 and 007 here.**
- **PLAN-64 `finalize-dispatch-manifest-observability`** — the step-contract seam. **Fold 017 and
  018 here**, and note 017 forces a contract decision D-level, not a patch.
- ⛔ **PLAN-104 runs BEFORE PLAN-64** (existing split decision; 64 cannot measure its own divergence
  while the `shape_violation` audit is vacuous). Same bundle — **never pair.**

⭐ **What the cluster adds:** the three failure modes in message 010 — *unpopulated, unvalidated,
uncounted* — are **independent**, so fixing emission alone still leaves a trail nothing validates and
nothing counts. PLAN-104's D1 should scope all three, not the emission gap it was staged from.
