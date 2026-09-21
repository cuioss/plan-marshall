# PLAN-TRUTH-011: Provider & Shared-Logging Path/Boundary Containment

> Renamed from **PLAN-63** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25). Gathers the security/containment family: an open
> plan_id-validation gap on the shared-logging path plus a set of landed containment residues to
> promote into the security/provider standards. (The live `build_queue.py` FIFO-ordering bug that was
> originally bundled here was **extracted to PLAN-66** for priority.)

## Objective

One open boundary defect (an unvalidated client-supplied `plan_id` reaching a log path) plus several
landed containment fixes whose durable rule was never generalized. Close the open one and promote a
single input-containment discipline into the governing security/provider standard.

## Deliverables

### D1 — GATE: confirm the open defect + promotion home (mutates nothing)
Verify `plan_logging.log_entry`/`get_log_path` still lack the `is_valid_plan_id` guard. Choose the
promotion home (`persona-security-expert` standard).

### D2 — validate client-supplied plan_id on the shared-logging path
- `2026-07-20-00-001` + `2026-07-20-20-002` (same defect): `plan_logging.log_entry` (:254) and `get_log_path` (:162) call `is_valid_plan_id` before resolving a path from `plan_id`, matching the sibling `log_work`/`log_decision` guards (path-influence risk).

### D3 — promote containment residues (governing standard) + retire
Promote the landed residues into one rule — **a daemon/privileged executor or migration/normalization
boundary must containment-verify EVERY independently client-settable field (cwd, env, argv, config
path), normalize caller keys before any membership test (CWE-178), contain every failure a lazy
read-path migration raises, and defer module-level home/env resolution so import never fails in a
restricted environment.** Retire all carried lessons at finalize.

## Lessons Carried (bound 2026-07-25 · lessons-triage)
- `2026-07-20-00-001`, `2026-07-20-20-002` — **OPEN** — plan_logging log_entry/get_log_path no plan_id validation (D2).
- `2026-07-17-21-001` — lazy read-path credentials migration must contain every failure — landed #923, promote.
- `2026-07-17-21-002` — module-level `Path.home()` needs a HOME-less fallback (`resolve_home`) — landed, promote.
- `2026-06-30-16-001` — case-normalize caller-controlled keys before a denylist check (CWE-178) — landed, promote.
- `2026-07-18-17-001` — daemon containment-verifies every client-settable path field, not just the primary — landed, promote.

## Expected surface
- `manage-logging/plan_logging.py` (D2)
- `persona-security-expert` / `manage-providers` standards (D3); tests under `test/plan-marshall/**`

**Disjointness:** manage-logging + security standards + manage-providers. Disjoint from the in-flight
plans and from PLAN-66 (the extracted `build_queue.py` FIFO fix).

## Logging-escape probes were written into the plan's permanent work log

Observed on PR #1034 (message-supplied; HYPOTHESIS until re-verified at outline). Probe entries
written to *test* whether logging escapes correctly were emitted into the plan's **permanent work
log**, where they are indistinguishable from real work records.

Same family as this plan's containment subject: the logging seam accepted writes it should have
rejected or routed elsewhere. ⚠ It is also a **test-authored-evidence** instance — the same shape
**PLAN-82** owns for the freshness store — so coordinate on the isolation approach rather than
inventing a second one.

## Write-Boundary
Repository source + tests only; NO `.plan/local/orchestrator/` writes. See orchestration-model.md § Ledger Write-Boundary.
