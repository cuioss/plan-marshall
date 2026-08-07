# Cloud bridge ledger — truthful-signals

The mapping between this epic's orchestrator plan specs and the plans executed in the standalone
cloud lane. The lifecycle rule — how a row is created, synced, and collected — is
[`../cloud-bridge.md`](../cloud-bridge.md). Do not restate it here.

**This file is the authority for the cloud leg only.** The orchestrator's `status.json` remains the
authority for the queue itself. Where the two disagree, the disagreement is a finding to reconcile at
ingest, not something either side silently overwrites.

Statuses: `open` (staged in the orchestrator, no cloud plan authored) → `authored` (a plan exists
under `doc/plans/truthful-signals/`) → `implemented` (its PR is merged) → `ingested` (the orchestrator has
reconciled it back into `status.json`).

| Orchestrator plan | Cloud plan | Status | PR | Report |
|---|---|---|---|---|
| PLAN-TRUTH-002 | `inert-thinking-directives-in-dispatched-docs` | open | — | — |
| PLAN-TRUTH-003 | `migration-shims-have-no-expiry` | open | — | — |
| PLAN-TRUTH-004 | `invented-plan-scoping-flags-are-an-overgeneralized-convention` | open | — | — |
| PLAN-TRUTH-005 | `marshalld-self-reload-on-version-signal` | open | — | — |
| PLAN-TRUTH-006 | `baseline-reconcile-persists-merge-commit` | open | — | — |
| PLAN-TRUTH-007 | `key-order-canonicalization-unreachable-and-false-green` | open | — | — |
| PLAN-TRUTH-008 | `executor-preflight-stamp-not-resolution` | open | — | — |
| PLAN-TRUTH-009 | `surface-every-knob-in-marshal-json` | open | — | — |
| PLAN-TRUTH-011 | `provider-logging-path-containment` | open | — | — |
| PLAN-TRUTH-012 | `canonical-block-diverges-from-argparse-choices` | open | — | — |
| PLAN-TRUTH-013 | `hook-timeout-unit-confusion` | open | — | — |
| PLAN-TRUTH-014 | `landed-residue-promotion-sweep` | open | — | — |
| PLAN-TRUTH-015 | `rename-marshall-orchestrator-to-plan-orchestrator` | open | — | — |
| PLAN-TRUTH-016 | `skills-carry-incident-history-as-normative-prose` | open | — | — |
| PLAN-TRUTH-017 | `detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete` | open | — | — |
| PLAN-TRUTH-018 | `configurable-display-timezone-for-rendered-timestamps` | open | — | — |
| PLAN-TRUTH-019 | `build-gate-coverage-parity` | open | — | — |
| PLAN-TRUTH-020 | `graduate-deployment-diagram-type-from-api-sheriff` | open | — | — |
| PLAN-TRUTH-021 | `operator-posture-answer-never-reaches-the-immunity-channel` | open | — | — |
| PLAN-TRUTH-022 | `orchestrator-cleanup-verb` | open | — | — |
| PLAN-TRUTH-023 | `split-and-complete-the-user-configuration-doc` | open | — | — |
| PLAN-TRUTH-024 | `respread-the-effort-preset-ladder` | open | — | — |
| PLAN-TRUTH-025 | `named-recovery-discards-operator-config` | open | — | — |
| PLAN-TRUTH-027 | `build-ledger-is-the-build-time-oracle` | open | — | — |
| PLAN-TRUTH-028 | `domain-invariant-chain-hardcodes-the-python-toolchain` | open | — | — |
| PLAN-TRUTH-030 | `finalize-retriggers-ci-after-it-has-already-gone-green` | open | — | — |
| PLAN-TRUTH-032 | `inbox-has-no-emission-quiescence-signal` | open | — | — |
| PLAN-TRUTH-033 | `a-plan-has-two-identities-and-the-terminal-shows-only-one` | open | — | — |
| PLAN-TRUTH-034 | `orchestrator-state-is-narrated-where-it-should-be-typed` | open | — | — |
| PLAN-TRUTH-036 | `deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null` | open | — | — |
| PLAN-TRUTH-038 | `inbox-has-no-amend-or-supersede-verb` | open | — | — |
| PLAN-TRUTH-039 | `argparse-rejection-log-discards-the-only-recoverable-part` | open | — | — |
| PLAN-TRUTH-040 | `the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field` | open | — | — |
| PLAN-TRUTH-041 | `java-skills-route-authors-to-an-anti-pattern-they-never-warn-about` | open | — | — |
| PLAN-TRUTH-042 | `a-rule-that-is-green-because-it-examined-nothing` | open | — | — |
| PLAN-TRUTH-043 | `every-config-write-is-a-lost-update-waiting-and-added-count-reports-intent` | open | — | — |
| PLAN-TRUTH-044 | `the-lesson-retirement-path-fails-open-in-three-independent-places` | open | — | — |
| PLAN-TRUTH-045 | `the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one` | open | — | — |
| PLAN-TRUTH-046 | `main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully` | open | — | — |
| PLAN-TRUTH-048 | `self-review-is-priced-but-not-scoped-and-a-refuted-arm-reads-as-a-gap` | open | — | — |
| PLAN-TRUTH-049 | `two-producers-write-one-marker-field-in-two-encodings-and-one-is-not-ours` | open | — | — |
| PLAN-TRUTH-050 | `the-operator-report-is-an-evidence-surface-the-inbox-cannot-see` | open | — | — |
| PLAN-TRUTH-053 | `cost-has-no-yield-denominator-in-the-metrics` | open | — | — |
| PLAN-TRUTH-054 | `baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges` | open | — | — |
| PLAN-TRUTH-055 | `the-metrics-record-cannot-represent-a-re-entered-phase` | open | — | — |
| PLAN-TRUTH-056 | `the-enforcement-hook-scans-for-shell-metacharacters-without-respecting-quoting` | open | — | — |
| PLAN-TRUTH-057 | `references-affected-files-is-absent-and-three-consumers-silently-under-scope` | open | — | — |
| PLAN-TRUTH-058 | `no-remote-conflates-never-pushed-with-merged-and-deleted` | open | — | — |
| PLAN-TRUTH-059 | `sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry` | open | — | — |

**49 open plans.** A plan absent from this table is either already shipped, transferred, or superseded in the orchestrator — check `status.json`, not this file.
