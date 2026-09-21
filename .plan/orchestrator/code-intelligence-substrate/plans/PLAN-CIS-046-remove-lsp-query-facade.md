# PLAN-CIS-046: Remove the LSP query facade

epic: code-intelligence-substrate
workstream: WS-02

> ⚠ **POINTER SPEC — this plan has already SHIPPED (PR #1214).**
> It is not a hand-off brief and must never be emitted. It exists so the queue row and the spec
> corpus reconcile in both directions; `corpus enumerate` would otherwise report this row as
> `rows_without_spec`.

## Provenance

Authored MID-FLIGHT in the cloud lane as an operator correction to PLAN-CIS-002, which had shipped the facade this plan removes. It never passed through this ledger as a staged spec, so this file is a POINTER seated during the 2026-08-22 ingest to keep the queue and the spec corpus reconcilable in both directions.

## The authoritative spec

The plan body this run actually executed is archived verbatim at:

```text
cloud-runs/135-remove-lsp-query-facade/plan.md
```

Read that file, not this one, for what the plan required.

## Outcome

See `landings/PLAN-CIS-046.md` for the landing analysis — deliverable verdicts, the gaps carried out of the
landing, the inconsistencies verified against the tree, and where the follow-ups were routed. The
run's own account, the independent post-run verification, and the recorded gap entries are archived
beside the plan body under `cloud-runs/135-remove-lsp-query-facade/`.

## Hand-Off Command

None. **This plan has shipped.** A pointer spec carries no hand-off command, and emitting one would
re-run landed work.
