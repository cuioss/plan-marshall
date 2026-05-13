# Findings Pipeline Architecture

The plan-marshall findings pipeline routes every quality signal — PR review comments, Sonar issues, build / test / lint failures, and per-phase Q-Gate findings — through a single producer → store → consumer → invariant-gate flow. This document is the canonical architectural source of truth. Per-skill SKILL.md files and standards documents document their own slice of the contract (CLI surface, step list, plumbing) and cross-reference here for the architecture-level synthesis.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      FINDINGS PIPELINE — END TO END                         │
│                                                                             │
│  ┌──────────────────────┐  add  ┌──────────────────────┐  query  ┌────────┐ │
│  │      PRODUCERS       │──────▶│    manage-findings   │◀────────│CONSUMER│ │
│  │                      │       │                      │ resolve │   S    │ │
│  │ workflow-integration-│       │  .plan/plans/{id}/   │────────▶│        │ │
│  │  github (PR review)  │       │  artifacts/findings/ │         │ phase- │ │
│  │ workflow-integration-│       │   ├─ pr-comment.jsonl│         │ 6-fin- │ │
│  │  gitlab (MR review)  │       │   ├─ pr-comment-     │         │ alize: │ │
│  │ workflow-integration-│       │   │  overflow.jsonl  │         │  auto- │ │
│  │  sonar (issues)      │       │   ├─ sonar-issue     │         │  matedR│ │
│  │ build-python /       │       │   │     .jsonl       │         │  view, │ │
│  │ build-maven /        │       │   ├─ build-error     │         │  sonar-│ │
│  │ build-gradle /       │       │   │     .jsonl       │         │  round-│ │
│  │ build-npm            │       │   ├─ test-failure    │         │  trip  │ │
│  │   (with --plan-id)   │       │   │     .jsonl       │         │        │ │
│  └──────────────────────┘       │   ├─ lint-issue      │         └───┬────┘ │
│            │                    │   │     .jsonl       │             │      │
│            │ producer-mismatch  │   ├─ qgate-{phase}   │             │      │
│            │ (Q-Gate finding)   │   │     .jsonl       │   per-finding      │
│            ▼                    │   ├─ assessments     │   dispatch         │
│  ┌──────────────────────┐       │   │     .jsonl       │             │      │
│  │  qgate-{phase}.jsonl │       │   └─ … per-type      │             ▼      │
│  │  (producer fidelity  │       │                      │   ┌──────────────┐ │
│  │   contract surface)  │       │  CLI: add / query /  │   │ ext-triage-  │ │
│  └──────────────────────┘       │       resolve /      │   │   {domain}   │ │
│                                 │       promote        │   │ (knowledge   │ │
│                                 │       qgate {add,    │   │  skill)      │ │
│                                 │              query,  │   │              │ │
│                                 │              resolve}│   │ Severity,    │ │
│                                 │       assessment {…} │   │ suppression, │ │
│                                 └──────────┬───────────┘   │ pr-comment   │ │
│                                            │               │ disposition  │ │
│                                            │ pending count └──────────────┘ │
│                                            ▼                                │
│                          ┌──────────────────────────────┐                   │
│                          │  phase_handshake invariant   │                   │
│                          │  pending_findings_           │                   │
│                          │   blocking_count             │                   │
│                          │                              │                   │
│                          │  Guarded boundary:           │                   │
│                          │   6-finalize entry  +        │                   │
│                          │   intra-finalize re-issues   │                   │
│                          │   (automated-review →        │                   │
│                          │    branch-cleanup;           │                   │
│                          │    sonar-roundtrip → next)   │                   │
│                          │                              │                   │
│                          │  Raises BlockingFindings-    │                   │
│                          │   Present when any           │                   │
│                          │   blocking-type finding is   │                   │
│                          │   pending at boundary        │                   │
│                          └──────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The diagram shows the per-finding dispatch path. A separate **completed-CI signal** lane upstream of the `automated-review` consumer is documented below — `ci-wait` does not produce a `manage-findings` record; it writes a `phase_steps["6-finalize"]["ci-wait"].outcome` record on `manage-status` that `automated-review` reads before invoking the producer-stage. Splitting CI-wait out of `automated-review` keeps the consumer's per-iteration triage budget bounded by comment volume rather than CI queue depth:

```
   ci-wait step                                     automated-review step
   (phase-6-finalize)                               (phase-6-finalize)
   ┌─────────────────┐                              ┌─────────────────────┐
   │  ci wait        │── outcome=done ─────────────▶│ read manage-status  │
   │  (1800 s budget)│   (manage-status, NOT a     │ ci-wait record:     │
   │                 │    findings record)          │ proceed when green, │
   │  on success:    │                              │ surface ci_failure  │
   │  mark-step-done │                              │ when failed/absent  │
   │  ci-wait done   │                              └──────────┬──────────┘
   │  with display:  │                                         │
   │  CI success     │                                         ▼
   └─────────────────┘                              ┌─────────────────────┐
                                                    │ comments-stage      │
                                                    │ (producer)          │
                                                    │       ▼             │
                                                    │ per-finding         │
                                                    │ dispatch (consumer) │
                                                    │ — overflow path:    │
                                                    │   pr-comment-       │
                                                    │   overflow finding  │
                                                    │   + outcome=        │
                                                    │   loop_back         │
                                                    └─────────────────────┘
```

The **`pr-comment-overflow` finding** files when the consumer's 900 s triage budget is nearly exhausted before all `pr-comment` findings are processed. Unlike `pr-comment` (a `findings` record produced by `comments-stage`), `pr-comment-overflow` is filed by the consumer itself — it carries the unprocessed `pr-comment` `hash_id`s in `detail` so the next iteration can prioritise them. The type is non-blocking; the deferred work is handled by `loop_back` re-entry, not by gating the boundary. See [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § `pr-comment-overflow` for the type's full contract.

The pipeline is structurally enforced: producers can never bypass the store (no inline-JSON batch surfaces remain in LLM-callable scope), consumers can never bypass the per-domain decision-grounding knowledge (every triage decision loads `ext-triage-{domain}`), and boundaries can never be crossed with unresolved blocking findings (the invariant raises `BlockingFindingsPresent`).

The contract was activated end-to-end by lesson `2026-05-05-11-001` ("Activate manage-findings as universal finding pipeline"). The two boundary defects (qgate aggregation, intra-finalize re-capture wiring) the lesson left under-wired are tracked by follow-up plan `findings-pipeline-blocking-fixes` and reflected in the diagram above.

## Producers

Each producer fetches findings from its upstream source, applies any pre-filter to drop obvious noise, then writes one finding per surviving record into the unified store via `manage-findings add` (or, for Q-Gate findings, `manage-findings qgate add`). Producers never return finding payloads over stdout for downstream parsing — payloads live on disk and are queried, not piped.

| Producer | Subcommand | Finding type | Notes |
|---|---|---|---|
| `workflow-integration-github` | `comments-stage --pr-number N --plan-id P` | `pr-comment` | Pre-filter: `comment-patterns.json` drops automated/acknowledgment noise. Source-specific metadata (thread_id, author, kind=inline\|review_body) lives in `detail`. |
| `workflow-integration-gitlab` | `comments-stage --pr-number N --plan-id P` | `pr-comment` | Mirror of GitHub; provider-agnostic schema. |
| `workflow-integration-sonar` | `fetch-and-store --plan-id P --project K` | `sonar-issue` | Pre-filter: `sonar-rules.json` drops issues already suppressed via NOSONAR. Severity from issue severity; rule from issue rule. |
| `build-python` / `build-maven` / `build-gradle` / `build-npm` | `run --command-args "…" --plan-id P` (always-on when `--plan-id` is set) | `build-error` / `test-failure` / `lint-issue` | Each parsed log entry becomes one finding. Build tool is the `module` field; issue category becomes `rule`. |

For per-producer CLI specifics see each skill's SKILL.md:
- [`workflow-integration-github/SKILL.md`](../../workflow-integration-github/SKILL.md)
- [`workflow-integration-gitlab/SKILL.md`](../../workflow-integration-gitlab/SKILL.md)
- [`workflow-integration-sonar/SKILL.md`](../../workflow-integration-sonar/SKILL.md)
- [`build-python/SKILL.md`](../../build-python/SKILL.md), [`build-maven/SKILL.md`](../../build-maven/SKILL.md), [`build-gradle/SKILL.md`](../../build-gradle/SKILL.md), [`build-npm/SKILL.md`](../../build-npm/SKILL.md)

### Producer-fidelity contract

Every producer reports `count_fetched` vs `count_stored` mismatches as a `qgate` Q-Gate finding with title prefix `(producer-mismatch)`. Q-Gate findings are blocking by default at every phase boundary, so a producer failure (network blip, parse error, store call fault) surfaces as a fail-loud invariant violation rather than silent under-reporting.

## Store

`manage-findings` (`marketplace/bundles/plan-marshall/skills/manage-findings/`) is the unified plan-scoped store. The CLI surface (`add` / `query` / `get` / `resolve` / `promote` / `qgate {add,query,resolve,clear}` / `assessment {add,query,get,clear}`) is the only access path; direct file I/O on the JSONL files is never permitted.

Storage layout (under `.plan/plans/{plan_id}/artifacts/findings/`):

| File | Contents |
|---|---|
| `{type}.jsonl` (one per type) | Plan-scoped findings of that type — `pr-comment.jsonl`, `sonar-issue.jsonl`, `build-error.jsonl`, `test-failure.jsonl`, `lint-issue.jsonl`, plus the long-lived knowledge types `bug.jsonl`, `improvement.jsonl`, `anti-pattern.jsonl`, `triage.jsonl`, `tip.jsonl`, `insight.jsonl`, `best-practice.jsonl` |
| `qgate-{phase}.jsonl` (one per phase) | Per-phase Q-Gate findings: `qgate-2-refine.jsonl` … `qgate-6-finalize.jsonl`. Same type taxonomy and resolution model as plan findings; not promotable. |
| `assessments.jsonl` | Phase-3-outline component assessments (certainty / confidence). Working data, read-only after outline. |

For the per-type file list, schema details, dedup semantics, and resolution model:
- [`manage-findings/SKILL.md`](../../manage-findings/SKILL.md) — CLI reference and the canonical storage tree diagram.
- [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) — JSON schema, type taxonomy with promotion targets, severity values, type selection guide.
- [`data-layer.md`](data-layer.md) — manage-findings's place in the broader data layer.
- [`skill-inventory.md`](skill-inventory.md) — one-line skill inventory entry.

## Consumer Dispatch

Wherever a triage decision needs to be made, the consumer:

1. **Query pending findings** for the relevant type:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query \
     --plan-id {plan_id} --type {type} --resolution pending
   ```
2. **Detect the domain** from each finding's `file_path` (the same `architecture which-module` heuristic verification uses):
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module \
     --path {file_path}
   ```
3. **Resolve the per-domain triage skill**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
     resolve-workflow-skill-extension --domain {domain} --type triage
   ```
4. **Load the resolved skill** into main context: `Skill: {bundle}:ext-triage-{domain}`. The loaded skill provides the per-domain decision-grounding knowledge (severity tables, suppression syntax, pr-comment-disposition rules, "Acceptable to Accept" criteria) — see [Extension Contract](#extension-contract) below.
5. **Decide per-finding** in main context using the loaded standards. The four canonical outcomes are: **FIX** (create fix-task and loop back to phase-5-execute), **SUPPRESS** (annotation in source per loaded suppression syntax), **ACCEPT** (no source change; provider-side acknowledgment via `pr thread-reply` + `pr resolve-thread` for PR comments, sonar dismiss / comment for Sonar issues), or escalation via `AskUserQuestion` (one per finding, never batched) when the loaded standards leave the decision genuinely ambiguous.
6. **Record the resolution**:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
     --plan-id {plan_id} --hash-id {hash_id} \
     --resolution {fixed|suppressed|accepted|taken_into_account} --detail "{rationale}"
   ```

The orchestration is identical across consumers (PR review GitHub, PR review GitLab, Sonar). For the per-consumer step lists:
- [`phase-6-finalize/workflow/automated-review.md`](../../phase-6-finalize/workflow/automated-review.md) — PR review consumer dispatch.
- [`phase-6-finalize/workflow/sonar-roundtrip.md`](../../phase-6-finalize/workflow/sonar-roundtrip.md) — Sonar consumer dispatch.
- [`workflow-pr-doctor/standards/automated-review-lifecycle.md`](../../workflow-pr-doctor/standards/automated-review-lifecycle.md) — pr-doctor's automated-review lifecycle pointer.

### By-reference triage dispatch

The per-finding LLM core (steps 4–5 above — load `ext-triage-{domain}`, decide FIX/SUPPRESS/ACCEPT/AskUserQuestion, act on the decision) factors out into one shared workflow doc, [`plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md), invoked from [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md). The verification-feedback envelope is dispatched under `--phase phase-N --role verification-feedback` with a `producer` runtime input (`build-runner` from phase-5 Steps 11/11b, `sonar` / `pr-comment` / `plugin-doctor` / `pr-state` from phase-6 finalize steps and slash commands).

**The dispatch passes `producer` only — never the findings content.** The verification-feedback subagent's first workflow step is its own `manage-findings query --plan-id {plan_id} --resolution pending` call against the same store, which means:

- the store stays the single source of truth (no double-serialization of multi-kilobyte findings into the prompt body),
- loop-back re-entry sees only currently-pending findings (the orchestrator's earlier query result freezes in time; the subagent's own query is fresh), and
- the orchestrator's role at the consumer's "should I dispatch?" decision shrinks to a gate-keeping count.

The smart-grouping algorithm the triage workflow uses (pre-group by `(domain, rule_id)` → one batched LLM decision per group → sequential actions between groups for cross-group feedback) is documented inside `triage.md` itself.

## Invariant Gate

The `pending_findings_blocking_count` invariant in [`plan-marshall/scripts/_invariants.py`](../../plan-marshall/scripts/_invariants.py) raises `BlockingFindingsPresent` at guarded boundaries when any blocking-type finding is in `pending` resolution.

### Per-phase blocking partition

The blocking partition lives in `marshal.json` under `plan.phase-{phase}.blocking_finding_types` (a list of finding-type strings). The default partition is seeded by `marshall-steward/scripts/determine_mode.py::seed_blocking_finding_types`:

| Included in blocking partition for all phases | Included only inside `6-finalize` | Never included (long-lived knowledge types) |
|---|---|---|
| `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate` | `pr-comment` | `insight`, `tip`, `best-practice`, `improvement` |

Partition membership is per-phase configuration; whether a non-zero pending count actually *raises* `BlockingFindingsPresent` is a separate concern controlled by [Guarded boundaries](#guarded-boundaries). Captures at non-guarded phases read these rows passively without raising.

Projects override by editing `marshal.json` directly; the seed only writes when the slot is absent (idempotent).

### Guarded boundaries

| Boundary | How the gate fires |
|---|---|
| `5-execute → 6-finalize` | `phase_handshake capture --phase 6-finalize` issued by the Phase Entry Protocol on entry to `6-finalize` |
| `automated-review → branch-cleanup` (intra-finalize) | `automated-review.md` re-issues `phase_handshake capture --phase 6-finalize` between the consumer dispatch loop and `mark-step-done` |
| `sonar-roundtrip → next` (intra-finalize) | `sonar-roundtrip.md` re-issues `phase_handshake capture --phase 6-finalize` between the consumer dispatch loop and `mark-step-done` |

Every other phase capture reads the `pending_findings_blocking_count` row passively (so retrospective analysis sees the queue at every boundary) but does NOT raise.

### qgate aggregation contract

Q-Gate findings live in `qgate-{phase}.jsonl` rather than the canonical `findings/{type}.jsonl` layout — the `qgate` blocking type therefore cannot be reached via the canonical `manage-findings query --type qgate` path (`query_findings` iterates only `FINDING_TYPES`, which excludes `qgate`). The blocking-count helper routes the `qgate` partition entry through `_query_pending_qgate_count_aggregated` which loops `QGATE_PHASES` and sums each per-phase `qgate query --phase {p} --resolution pending` result. Producer-mismatch findings filed by `add_qgate_finding(...)` from `github_pr.py` / `gitlab_pr.py` / `sonar.py` / `_build_shared.py` therefore block the boundary regardless of which phase they were filed under.

For the full invariant capture / verify mechanics, the row schema, and the structured error envelope: [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md).

## Extension Contract

Per-domain `ext-triage-{domain}` skills declare the decision-grounding knowledge for the triage extension point. The contract scope covers `pr-comment` and `sonar-issue` finding types — both are dispatched through `ext-triage-{domain}` by the consumer-side flow above.

Each implementor `ext-triage-{domain}` skill ships four standards documents:
- `severity.md` — severity guidelines (when to fix vs suppress vs accept by severity).
- `suppression.md` — domain-specific suppression annotation syntax.
- `acceptable-to-accept.md` — criteria for ACCEPT outcomes that do not need a fix.
- `pr-comment-disposition.md` — per-domain disposition table for PR comments (FIX vs reply-and-resolve vs escalate).

Active implementors:

| Bundle | Skill | Domain |
|---|---|---|
| `pm-dev-java` | `ext-triage-java` | java |
| `pm-dev-frontend` | `ext-triage-js` | javascript |
| `pm-dev-python` | `ext-triage-python` | python |
| `pm-dev-oci` | `ext-triage-oci` | oci-containers |
| `pm-documents` | `ext-triage-docs` | documentation |
| `pm-requirements` | `ext-triage-reqs` | requirements |
| `pm-plugin-development` | `ext-triage-plugin` | plan-marshall-plugin-dev |

For the formal extension contract, the resolver path, and the implementation pattern: [`extension-api/standards/ext-point-triage.md`](../../extension-api/standards/ext-point-triage.md).

## Cross-References

| Sub-domain | Source of truth |
|---|---|
| Storage tree, CLI surface, dedup semantics | [`manage-findings/SKILL.md`](../../manage-findings/SKILL.md) |
| JSONL schema, type taxonomy, severity values, resolution model | [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) |
| Per-producer CLI surface | [`workflow-integration-github/SKILL.md`](../../workflow-integration-github/SKILL.md), [`workflow-integration-gitlab/SKILL.md`](../../workflow-integration-gitlab/SKILL.md), [`workflow-integration-sonar/SKILL.md`](../../workflow-integration-sonar/SKILL.md), [`build-python/SKILL.md`](../../build-python/SKILL.md), [`build-maven/SKILL.md`](../../build-maven/SKILL.md), [`build-gradle/SKILL.md`](../../build-gradle/SKILL.md), [`build-npm/SKILL.md`](../../build-npm/SKILL.md) |
| Per-consumer step list | [`phase-6-finalize/workflow/automated-review.md`](../../phase-6-finalize/workflow/automated-review.md), [`phase-6-finalize/workflow/sonar-roundtrip.md`](../../phase-6-finalize/workflow/sonar-roundtrip.md), [`workflow-pr-doctor/standards/automated-review-lifecycle.md`](../../workflow-pr-doctor/standards/automated-review-lifecycle.md) |
| Invariant capture / verify plumbing, row schema, structured error envelope | [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md) |
| Extension contract, implementor list, resolver | [`extension-api/standards/ext-point-triage.md`](../../extension-api/standards/ext-point-triage.md) |
| Glossary entries (finding, Q-Gate, assessment) | [`glossary.md`](glossary.md) |
| Data-layer overview | [`data-layer.md`](data-layer.md) |
| Manage-* contract (TOON / errors / etc.) | [`manage-contract.md`](manage-contract.md) |
