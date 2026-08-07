# Cloud bridge ledger — code-intelligence-substrate

The mapping between this epic's orchestrator plan specs and the plans executed in the standalone
cloud lane. The lifecycle rule — how a row is created, synced, and collected — is
[`../cloud-bridge.md`](../cloud-bridge.md). Do not restate it here.

**This file is the authority for the cloud leg only.** The orchestrator's `status.json` remains the
authority for the queue itself. Where the two disagree, the disagreement is a finding to reconcile at
ingest, not something either side silently overwrites.

Statuses: `open` (staged in the orchestrator, no cloud plan authored) → `authored` (a plan exists
under `doc/plans/code-intelligence-substrate/`) → `implemented` (its PR is merged) → `ingested` (the orchestrator has
reconciled it back into `status.json`).

| Orchestrator plan | Cloud plan | Status | PR | Report |
|---|---|---|---|---|
| PLAN-CIS-031 | `self-review-resweeps-full-surface-every-round` | open | — | — |
| PLAN-CIS-034 | `post-run-band-contract-and-ordering-residue` | open | — | — |
| PLAN-CIS-035 | `dispatch-spend-on-dispatches-that-produced-nothing` | open | — | — |
| PLAN-CIS-036 | `exploration-split-measured-on-one-phase-and-it-is-the-worst-case` | open | — | — |
| PLAN-CIS-024 | `documentation-surface-provider` | open | — | — |
| PLAN-CIS-032 | `executor-rejects-invalid-invocations-before-spawn` | open | — | — |
| PLAN-CIS-002 | `lsp-shaped-query-api` | open | — | — |
| PLAN-CIS-025 | `project-local-artifact-provider` | open | — | — |
| PLAN-CIS-029 | `architecture-store-concept-model` | open | — | — |
| PLAN-CIS-033 | `empty-skill-resolution-indistinguishable-from-minimal` | open | — | — |
| PLAN-CIS-010 | `finalize-dispatch-evidence-is-missing` | open | — | — |
| PLAN-CIS-011 | `finalize-dispatch-manifest-observability` | open | — | — |
| PLAN-CIS-026 | `lsp-derivation-resolver` | open | — | — |
| PLAN-CIS-004 | `native-coordinate-resolvers` | open | — | — |
| PLAN-CIS-005 | `resolver-configuration` | open | — | — |
| PLAN-CIS-006 | `validate-precision` | open | — | — |
| PLAN-CIS-007 | `skill-lsp-server` | open | — | — |
| PLAN-CIS-008 | `scope-estimate-vocabulary-closure` | open | — | — |
| PLAN-CIS-009 | `documented-enum-diverges-from-argparse-choices` | authored | — | — |
| PLAN-CIS-012 | `footprint-read-outside-its-window` | open | — | — |
| PLAN-CIS-013 | `chat-signal-provenance-filter-under-inclusive` | open | — | — |
| PLAN-CIS-014 | `aggregate-cost-invisible-to-per-call-ceiling` | open | — | — |
| PLAN-CIS-015 | `outline-plan-scope-derivation-integrity` | open | — | — |
| PLAN-CIS-016 | `auditor-detector-integrity` | open | — | — |
| PLAN-CIS-017 | `freshness-gate-cannot-distinguish-test-authored-evidence` | open | — | — |
| PLAN-CIS-018 | `main-sha-records-the-pinned-cwd` | open | — | — |
| PLAN-CIS-019 | `manifest-cross-check-discards-production-tree` | open | — | — |
| PLAN-CIS-020 | `retrospective-report-sections-structurally-dead` | open | — | — |
| PLAN-CIS-021 | `self-review-cannot-see-a-duplicate-claimable-key` | open | — | — |
| PLAN-CIS-022 | `token-ledgers-disagree-and-the-smallest-is-named-actual` | open | — | — |

**30 open plans.** A plan absent from this table is either already shipped, transferred, or superseded in the orchestrator — check `status.json`, not this file.
