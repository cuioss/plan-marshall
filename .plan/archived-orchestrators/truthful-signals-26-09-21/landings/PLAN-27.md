# Landing Analysis: PLAN-27 — openrewrite log-finding retrieval

epic: truthful-signals
workstream: WS-01
pr: #995 (https://github.com/cuioss/plan-marshall/pull/995) — squash-merged, f514edcdc

> Landing record for one shipped plan. Reconciled 2026-07-25 — the finalize shipped 07-25 but the
> epic ledger was not reconciled at the time (landing-record-completeness gap: finalize does not
> notify the orchestrator). Corroborated against the merged diff at f514edcdc + the prior-session
> capture in project memory.

## Deliverable Fidelity vs Spec

Spec: add a log-based finding-retrieval complement (Signal B) beside the PLAN-23 tree-scan detector,
in the `pm-dev-java-cui/search-markers` ownership home. Shipped as specified, plus the
descriptor-list generalization the two-signal design required.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — log parser beside the relocated detector | shipped-as-specified | new `pm-dev-java-cui:parse-rewrite-log` skill (SKILL.md +120, parse_rewrite_log.py +205, test +268) |
| WARN-format re-grounding against #118 | shipped-as-specified (added provenance) | `fixtures/warn-corpus/` + `PROVENANCE.md` (WARN format captured via research-reader from cuioss/cui-open-rewrite PR#118, validated through untrusted-ingestion) |
| Additive build-maven consumer, complement-not-replacement | shipped-as-specified | `_maven_cmd_rewrite_log.py` +264, maven.py +39, fail-closed `parse_error`/`not_observed`/`domain_inactive` (never false clean, ADR-009); search-markers tree-scan untouched |
| `provides_domain_verb()` → descriptor **list** (enabling two signals) | shipped-as-added | extension_base.py, `_cmd_skill_domains.py`, ext-point-domain-verb.md, plan-marshall-plugin/extension.py |

## Metrics and Anomalies

- Tokens/duration: ~2.8M tokens / 3h43m worked / 3d wall (prior-session capture).
- Anomalies (all resolved): TASK-1 infeasible on first dispatch — a leaf cannot synthesize a real #118
  WARN corpus; unblocked by an orchestrator-authorized research-reader. Base advanced 4 PRs mid-flight
  → a real merge conflict in `test_extension_domain_verb.py` (resolved keeping both our list tests and
  the upstream get_skill_domains/applies_to_module/provides_recipes/config_defaults sections). 5 fix
  commits. Sourcery S603 subprocess finding = persistent false-positive (fixed-argv/no-shell),
  non-required so the merge queue merged anyway.

## Routing and Merge Behavior

- Review: self-review (72f024) + CodeRabbit caught the D-level fail-closed defect (below); Sourcery
  S603 false-positive dismissed.
- CI/merge: green, squash-merged via merge queue (f514edcdc). No unresolved review threads.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-27 → shipped, pr 995, landing landings/PLAN-27.md
- [x] epic.md Ordered Queue row reconciled
- [x] resume_anchor updated (launched 3→2, free slots 1→2)
- [x] START-HERE regenerated

## Follow-Ups

- Two lessons filed at finalize, both in the lessons-triage disposition:
  - `2026-07-24-13-001` (pre-push-quality-gate lacks CI `test-compile: mypy test` parity) — **open**, routed to **PLAN-60** (in-house-gate-ci-parity).
  - `2026-07-24-13-002` (a fail-closed consumer folded a dispatched producer's ERROR into a false clean verdict) — landed #995, residue routed to **PLAN-59** (fail-closed-signal-integrity).
- Unblocking dependency for PLAN-23 (plan-optimization, search-markers home) was already satisfied #986; PLAN-27 landed the complement there.
