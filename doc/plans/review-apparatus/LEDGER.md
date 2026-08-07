# Cloud bridge ledger — review-apparatus

The mapping between this epic's orchestrator plan specs and the plans executed in the standalone
cloud lane. The lifecycle rule — how a row is created, synced, and collected — is
[`../cloud-bridge.md`](../cloud-bridge.md). Do not restate it here.

**This file is the authority for the cloud leg only.** The orchestrator's `status.json` remains the
authority for the queue itself. Where the two disagree, the disagreement is a finding to reconcile at
ingest, not something either side silently overwrites.

Statuses: `open` (staged in the orchestrator, no cloud plan authored) → `authored` (a plan exists
under `doc/plans/review-apparatus/`) → `implemented` (its PR is merged) → `ingested` (the orchestrator has
reconciled it back into `status.json`).

| Orchestrator plan | Cloud plan | Status | PR | Report |
|---|---|---|---|---|
| PLAN-PR-013 | `participation-credited-from-a-superseded-commit` | open | — | — |
| PLAN-PR-017 | `a-workflow-doc-prescribes-a-flag-no-script-declares` | open | — | — |
| PLAN-PR-006 | `canned-no-op-indistinguishable-from-a-review` | open | — | — |
| PLAN-PR-018 | `self-review-rescans-the-whole-surface-every-round` | open | — | — |
| PLAN-PR-020 | `a-prose-routing-table-is-not-an-enforcement-boundary` | open | — | — |
| PLAN-PR-019 | `post-responses-retransmits-already-sent-replies` | open | — | — |
| PLAN-PR-007 | `absent-names-two-states-with-opposite-remedies` | open | — | — |
| PLAN-PR-010 | `landing-message-carries-the-outcome-post-merge` | open | — | — |
| PLAN-PR-012 | `feed-pr-findings-back-into-local-review` | open | — | — |
| PLAN-PR-003 | `coderabbit-ai-agent-block-strip-vs-extract` | open | — | — |
| PLAN-PR-005 | `participation-derived-from-a-lossy-view` | open | — | — |
| PLAN-PR-008 | `review-barrier-deadlocks-on-a-refusing-bot` | open | — | — |
| PLAN-PR-002 | `org-empty-review-guard-too-broad` | open | — | — |
| PLAN-PR-011 | `review-bots-catch-what-in-house-gates-cannot` | open | — | — |
| PLAN-PR-004 | `pr-agent-charter-unverified-in-effect` | open | — | — |

**15 open plans.** A plan absent from this table is either already shipped, transferred, or superseded in the orchestrator — check `status.json`, not this file.
