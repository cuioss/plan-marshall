# Findings Pipeline Architecture

The plan-marshall findings pipeline routes every quality signal — PR review comments, Sonar issues, build / test / lint failures, and per-phase Q-Gate findings — through a single **FIND → INGEST → VERIFY → one TRIAGE → one RESPOND** flow, gated by the pending-findings invariant. Every producer FINDS (files findings to the `manage-findings` ledger, quarantining untrusted free-text under a `raw_input.{field}` sub-namespace); one batched INGEST pass runs `validate_struct` over every `raw_input.{field}` and promotes the cleaned values to the clean top-level fields; ONE domain-grouped TRIAGE pass then decides dispositions over the whole ledger (reading top-level only, never `raw_input.*`); and ONE RESPOND loop posts the decided dispositions back to the providers. The validity [verify stage](#validity-verification-ext-point-verify) folds into validate-on-file, so triage sees only valid findings. This document is the canonical architectural source of truth. Per-skill SKILL.md files and standards documents document their own slice of the contract (CLI surface, step list, plumbing) and cross-reference here for the architecture-level synthesis.

## Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      FINDINGS PIPELINE — END TO END                         │
│                                                                             │
│  ┌──────────────────────┐  add  ┌──────────────────────┐  list   ┌────────┐ │
│  │      PRODUCERS       │──────▶│    manage-findings   │◀────────│CONSUMER│ │
│  │                      │       │                      │ resolve │   S    │ │
│  │ workflow-integration-│       │  .plan/plans/{id}/   │────────▶│        │ │
│  │  github (PR review)  │       │  artifacts/findings/ │         │ phase- │ │
│  │ workflow-integration-│       │   ├─ pr-comment.jsonl│         │ 6-fin- │ │
│  │  gitlab (MR review)  │       │   ├─ pr-comment-     │         │ alize: │ │
│  │ workflow-integration-│       │   │  overflow.jsonl  │         │  auto- │ │
│  │  sonar (issues)      │       │   ├─ sonar-issue     │         │  matedR│ │
│  │ build-pyproject /    │       │   │     .jsonl       │         │  view, │ │
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
│  │   contract surface)  │       │  CLI: add / list /   │   │ ext-triage-  │ │
│  └──────────────────────┘       │       resolve /      │   │   {domain}   │ │
│                                 │       promote        │   │ (knowledge   │ │
│                                 │       qgate {add,    │   │  skill)      │ │
│                                 │              list,   │   │              │ │
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

The diagram above shows the store-level producer → store → consumer mechanics. The end-to-end **consolidated** flow that phase-6-finalize runs is the FIND → INGEST → one-TRIAGE → one-RESPOND shape:

```text
ci-complete
   │
   ▼
FIND LOOP      all providers: fetch_findings → ledger, untrusted free-text
   │           quarantined under raw_input.{field}. build/lint/test self-file
   │           during the build run; generators (security-audit, self-review) file
   │           find-only (defer triage).
   ▼
INGEST PASS    one batched validate_struct over every raw_input.{field}
   │           → promote clamped values to the clean TOP-LEVEL fields;
   │           [truncated] marker on cap overflow; a rejection resolves the finding.
   ▼
ONE TRIAGE     one domain-grouped pass over the whole ledger (ext-triage-{domain});
   │           reads TOP-LEVEL fields only, never raw_input.* (plugin-doctor
   │           triage-reads-top-level-only guard); disposition self-consistency
   │           gate folded in.
   ▼
ONE RESPOND    post_responses(triaged) → provider (thread-reply / resolve-thread /
               sonar dismiss), keyed by hash_id. The automated-review fix→re-review
               loop runs AFTER triage decides dispositions.
```

Triage is removed from the provider surface: the provider verbs are the two pure zero-LLM `fetch_findings` (FIND) and `post_responses` (RESPOND); the LLM judgment lives only in the single consolidated TRIAGE pass.

CI completion is resolved as a **dispatcher-side precondition** before the `automated-review` consumer's body runs — consumer steps declare `requires: [ci-complete]` in their YAML frontmatter, and the phase-6-finalize dispatcher invokes `ci_complete_precondition.resolve(plan_id, worktree_path, pr_number)` inline ahead of dispatch. The resolver caches success outcomes per HEAD SHA so subsequent same-HEAD lookups short-circuit. On `wait_failed`, the dispatcher skips the consumer body entirely and records `ci_failure (precondition)` as the consumer step's outcome. The precondition isolates CI wait time from the triage budget without introducing a sibling step:

```text
                                                    automated-review step
                                                    (phase-6-finalize, requires: [ci-complete])
   ┌─────────────────────────────┐                  ┌─────────────────────┐
   │ dispatcher Step 3:          │── satisfied ────▶│ fetch_findings      │
   │ ci_complete_precondition   │   or             │ (producer)          │
   │ .resolve(plan_id,           │   wait_succeeded │       ▼             │
   │   worktree_path,            │                  │ per-finding         │
   │   pr_number,                │                  │ dispatch (consumer) │
   │   timeout_seconds=600)      │                  │ — overflow path:    │
   │                             │                  │   pr-comment-       │
   │ per-HEAD cache              │── wait_failed ──▶│   overflow finding  │
   │ (head_sha-keyed)            │   (skip body;    │   + outcome=        │
   │                             │    record        │   loop_back         │
   │ on success: cache populated │    ci_failure    └─────────────────────┘
   │                             │    (precondition)│
   └─────────────────────────────┘   on consumer)
```

The **`pr-comment-overflow` finding** files when the consumer's 900 s triage budget is nearly exhausted before all `pr-comment` findings are processed. Unlike `pr-comment` (a `findings` record produced by `fetch_findings`), `pr-comment-overflow` is filed by the consumer itself — it carries the unprocessed `pr-comment` `hash_id`s in `detail` so the next iteration can prioritise them. The type is non-blocking; the deferred work is handled by `loop_back` re-entry, not by gating the boundary. See [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § `pr-comment-overflow` for the type's full contract.

The pipeline is structurally enforced: producers can never bypass the store (no inline-JSON batch surfaces remain in LLM-callable scope), consumers can never bypass the per-domain decision-grounding knowledge (every triage decision loads `ext-triage-{domain}`), and boundaries can never be crossed with unresolved blocking findings (the invariant raises `BlockingFindingsPresent`).

The pipeline is the canonical finding store for all plan-marshall phases. The two boundary areas most likely to need wiring in a fresh installation are qgate aggregation and intra-finalize re-capture; see plan `findings-pipeline-blocking-fixes` for tracked follow-up work, and the diagram above for the current wiring state.

## Producers

Each producer fetches findings from its upstream source, applies any pre-filter to drop obvious noise, then writes one finding per surviving record into the unified store via `manage-findings add` (or, for Q-Gate findings, `manage-findings qgate add`). Producers never return finding payloads over stdout for downstream parsing — payloads live on disk and are queried, not piped.

Each provider producer exposes exactly two pure zero-LLM verbs — `fetch_findings` (FIND: fetch + pre-filter + file to the ledger, quarantining untrusted free-text under `raw_input.{field}`) and `post_responses` (RESPOND: apply the already-decided dispositions back to the provider, keyed by `hash_id`). Triage is NOT on the provider surface. Both verbs fail loud (a typed `unconfigured` / `unreachable` signal, never a silent no-op) when the provider is not configured.

| Producer | FIND verb | Finding type | Notes |
|---|---|---|---|
| `workflow-integration-github` | `github_pr fetch_findings --pr-number N --plan-id P` | `pr-comment` | Pre-filter: `comment-patterns.json` drops automated/acknowledgment noise. Untrusted comment body quarantined under `raw_input.{body}`; source-specific metadata (thread_id, author, kind=inline\|review_body) indexed. |
| `workflow-integration-gitlab` | `gitlab_pr fetch_findings --pr-number N --plan-id P` | `pr-comment` | Mirror of GitHub; provider-agnostic schema. |
| `workflow-integration-sonar` | `sonar fetch_findings --plan-id P --project K` | `sonar-issue` | Pre-filter: `sonar-rules.json` drops issues already suppressed via NOSONAR. Untrusted issue message quarantined under `raw_input`; severity/rule from the issue. |
| `build-pyproject` / `build-maven` / `build-gradle` / `build-npm` | `run --command-args "…" --plan-id P` (always-on when `--plan-id` is set) | `build-error` / `test-failure` / `lint-issue` | Each parsed log entry self-files during the build run (no respond side). Build tool is the `module` field; issue category becomes `rule`. |

For per-producer CLI specifics see each skill's SKILL.md:
- [`workflow-integration-github/SKILL.md`](../../workflow-integration-github/SKILL.md)
- [`workflow-integration-gitlab/SKILL.md`](../../workflow-integration-gitlab/SKILL.md)
- [`workflow-integration-sonar/SKILL.md`](../../workflow-integration-sonar/SKILL.md)
- [`build-pyproject/SKILL.md`](../../build-pyproject/SKILL.md), [`build-maven/SKILL.md`](../../build-maven/SKILL.md), [`build-gradle/SKILL.md`](../../build-gradle/SKILL.md), [`build-npm/SKILL.md`](../../build-npm/SKILL.md)

### Producer-fidelity contract

Every producer reports `count_fetched` vs `count_stored` mismatches as a `qgate` Q-Gate finding with title prefix `(producer-mismatch)`. Q-Gate findings are blocking by default at every phase boundary, so a producer failure (network blip, parse error, store call fault) surfaces as a fail-loud invariant violation rather than silent under-reporting.

## Store

`manage-findings` (`marketplace/bundles/plan-marshall/skills/manage-findings/`) is the unified plan-scoped store. The CLI surface (`add` / `list` / `get` / `resolve` / `promote` / `ingest` / `qgate {add,list,resolve,clear}` / `assessment {add,list,get,clear}`) is the only access path; direct file I/O on the JSONL files is never permitted.

**Quarantine + ingestion.** Untrusted external free-text (a PR-comment body, a Sonar message) is filed under a quarantined `raw_input.{field}` sub-object, capped per field at `plan.finding_raw_input_max_bytes` (default 64 KiB, `[truncated]` marker on overflow). The `ingest` verb runs one batched `validate_struct` pass over every pending finding's `raw_input.{field}` values and promotes only the validated, clamped output to the clean top-level fields — the containment boundary that keeps triage's read surface clean (`raw_input.*` = audit-only quarantine; top-level = clean-by-construction). See [`manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § "`raw_input` quarantine namespace" and [`untrusted-ingestion/SKILL.md`](../../untrusted-ingestion/SKILL.md) § "Application to the findings ledger".

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

## Validity Verification (ext-point-verify)

The verify stage is an **optional, producer-declared, adversarial-refute pass** that runs in the pipeline AFTER the store and BEFORE the consumer-side triage. It is opt-in per producer: it runs only when a producer declares a `verification_profile`. A producer that declares none keeps the legacy `producer → store → consumer (triage) → gate` flow with no verify hop; a producer that declares one inserts the verify stage:

```text
  producer ──▶ store ──▶ VERIFY (ext-point-verify) ──▶ consumer (triage) ──▶ invariant gate
                              │
                              └─▶ refuted finding ──▶ resolve --resolution rejected
                                  (non-pending; never reaches triage)
```

Each candidate finding a participating producer emits is **challenged** before triage sees it: the verify stage resolves the verify skill from the producer's `verification_profile` (e.g. `security` → the `persona-security-expert` adversarial-refute standard), loads it in-context, and runs its refute procedure over each pending finding. Findings that **survive** refutation are left `pending` and flow on to the consumer-side triage unchanged. Findings the stage **refutes** as false positives close with the terminal resolution `rejected` — a non-pending state that never reaches triage and never contributes to the invariant gate's blocking count.

The verify stage is inserted by the orchestrator's [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md) workflow as an optional pre-stage between the producer query and the `ext-triage-{domain}` handoff; [`triage.md`](../../plan-marshall/workflow/triage.md) carries only a cross-reference noting that refuted findings may already be closed `rejected` before its FIX / SUPPRESS / ACCEPT loop runs. The full contract — producer declaration, runtime invocation parameters, lifecycle, and resolution semantics — lives in [`extension-api/standards/ext-point-verify.md`](../../extension-api/standards/ext-point-verify.md); the per-profile refute methodology lives in the verify skill the `verification_profile` resolves to (the pilot being [`persona-security-expert/standards/adversarial-refute.md`](../../persona-security-expert/standards/adversarial-refute.md)).

> The verify stage (validity-verification of *findings* before triage) is distinct from `ext-point-build-verify-step` (the phase-5 build/verify *command* step — `quality-gate`, `module-tests`, `coverage`). They are unrelated concerns.

## Consumer Dispatch

Under the consolidated flow, triage runs as ONE domain-grouped pass over the whole ingested ledger (not per-producer), reading the clean **top-level** fields only — never `raw_input.*`. The decided dispositions are then transmitted back in ONE `post_responses` RESPOND loop, rather than the provider-side acknowledgment being interleaved into the per-finding triage loop. The per-finding decision mechanics below are unchanged; only where they run (one consolidated pass) and where the provider acknowledgment happens (one respond loop, after triage) changed.

Wherever a triage decision needs to be made, the consumer:

1. **List pending findings** for the relevant type:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
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

The per-finding LLM core (steps 4–5 above — load `ext-triage-{domain}`, decide FIX/SUPPRESS/ACCEPT/AskUserQuestion, act on the decision) factors out into one shared workflow doc, [`plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md), invoked from [`verification-feedback.md`](../../plan-marshall/workflow/verification-feedback.md). The verification-feedback envelope is dispatched under `--phase phase-N --role verification-feedback` with a `producer` runtime input (`build-runner` from phase-5-execute Steps 11/11b, `sonar` / `pr-comment` / `plugin-doctor` / `pr-state` from phase-6-finalize finalize steps and slash commands).

**The dispatch passes `producer` only — never the findings content.** The verification-feedback subagent's first workflow step is its own `manage-findings list --plan-id {plan_id} --resolution pending` call against the same store, which means:

- the store stays the single source of truth (no double-serialization of multi-kilobyte findings into the prompt body),
- loop-back re-entry sees only currently-pending findings (the orchestrator's earlier query result freezes in time; the subagent's own query is fresh), and
- the orchestrator's role at the consumer's "should I dispatch?" decision shrinks to a gate-keeping count.

The smart-grouping algorithm the triage workflow uses (pre-group by `(domain, rule_id)` → one batched LLM decision per group → sequential actions between groups for cross-group feedback) is documented inside `triage.md` itself.

## Invariant Gate

The `pending_findings_blocking_count` invariant in [`plan-marshall/scripts/_invariants.py`](../../plan-marshall/scripts/_invariants.py) raises `BlockingFindingsPresent` at guarded boundaries when any **actionable** finding is in `pending` resolution.

The gate counts only `pending` findings — every terminal resolution is non-blocking. The terminal (non-pending) resolutions are `fixed`, `suppressed`, `accepted`, `taken_into_account`, and `rejected`. The last, `rejected`, is the [verify stage](#validity-verification-ext-point-verify)'s false-positive outcome: a finding the adversarial-refute pass invalidates closes `rejected` and therefore never contributes to the blocking count, exactly like the other terminal states. A `rejected` finding is closed by the verify stage before it ever reaches triage; the gate simply never sees it as `pending`.

### Actionable vs knowledge finding types (fixed rule)

The blocking rule is a **fixed, hardcoded** distinction between two classes of finding type — there is no per-phase configuration partition and no `marshal.json` seed. The set lives as a hardcoded constant in `_invariants.py`:

| Class | Finding types | Blocking behaviour |
|---|---|---|
| **ACTIONABLE** | `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate`, `pr-comment` | Block when `pending` at the guarded boundary — these are correctness / review gates that must clear before the boundary advances. |
| **KNOWLEDGE** | `insight`, `tip`, `best-practice`, `improvement` | **Never block** — long-lived knowledge types that accumulate across plans. They are excluded by the fixed rule regardless of pending count. |

This is **not** a naive "any pending finding blocks" rule: knowledge types are excluded by the fixed actionable-set membership test. Whether a non-zero actionable pending count actually *raises* `BlockingFindingsPresent` is a separate concern controlled by [Guarded boundaries](#guarded-boundaries) — captures at non-guarded phases read the count passively without raising. The actionable-vs-knowledge classification is not configurable and is not seeded into `marshal.json`.

### Guarded boundaries

| Boundary | How the gate fires |
|---|---|
| `5-execute → 6-finalize` | `phase_handshake capture --phase 6-finalize` issued by the Phase Entry Protocol on entry to `6-finalize` |
| `automated-review → branch-cleanup` (intra-finalize) | `automated-review.md` re-issues `phase_handshake capture --phase 6-finalize` between the consumer dispatch loop and `mark-step-done` |
| `sonar-roundtrip → next` (intra-finalize) | `sonar-roundtrip.md` re-issues `phase_handshake capture --phase 6-finalize` between the consumer dispatch loop and `mark-step-done` |

Every other phase capture reads the `pending_findings_blocking_count` row passively (so retrospective analysis sees the queue at every boundary) but does NOT raise.

### qgate aggregation contract

Q-Gate findings live in `qgate-{phase}.jsonl` rather than the canonical `findings/{type}.jsonl` layout — the `qgate` actionable type therefore cannot be reached via the canonical `manage-findings list --type qgate` path (`query_findings` iterates only `FINDING_TYPES`, which excludes `qgate`). The blocking-count helper routes the `qgate` actionable entry through `_query_pending_qgate_count_aggregated` which loops `QGATE_PHASES` and sums each per-phase `qgate list --phase {p} --resolution pending` result. Producer-mismatch findings filed by `add_qgate_finding(...)` from `github_pr.py` / `gitlab_pr.py` / `sonar.py` / `_build_shared.py` therefore block the boundary regardless of which phase they were filed under.

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
| Per-producer CLI surface | [`workflow-integration-github/SKILL.md`](../../workflow-integration-github/SKILL.md), [`workflow-integration-gitlab/SKILL.md`](../../workflow-integration-gitlab/SKILL.md), [`workflow-integration-sonar/SKILL.md`](../../workflow-integration-sonar/SKILL.md), [`build-pyproject/SKILL.md`](../../build-pyproject/SKILL.md), [`build-maven/SKILL.md`](../../build-maven/SKILL.md), [`build-gradle/SKILL.md`](../../build-gradle/SKILL.md), [`build-npm/SKILL.md`](../../build-npm/SKILL.md) |
| Per-consumer step list | [`phase-6-finalize/workflow/automated-review.md`](../../phase-6-finalize/workflow/automated-review.md), [`phase-6-finalize/workflow/sonar-roundtrip.md`](../../phase-6-finalize/workflow/sonar-roundtrip.md), [`workflow-pr-doctor/standards/automated-review-lifecycle.md`](../../workflow-pr-doctor/standards/automated-review-lifecycle.md) |
| Invariant capture / verify plumbing, row schema, structured error envelope | [`plan-marshall/references/phase-handshake.md`](../../plan-marshall/references/phase-handshake.md) |
| Extension contract, implementor list, resolver | [`extension-api/standards/ext-point-triage.md`](../../extension-api/standards/ext-point-triage.md) |
| Verify-stage contract (producer `verification_profile`, `rejected` resolution, lifecycle) | [`extension-api/standards/ext-point-verify.md`](../../extension-api/standards/ext-point-verify.md) |
| Glossary entries (finding, Q-Gate, assessment) | [`glossary.md`](glossary.md) |
| Data-layer overview | [`data-layer.md`](data-layer.md) |
| Manage-* contract (TOON / errors / etc.) | [`manage-contract.md`](manage-contract.md) |
