---
name: default:sonar-roundtrip
description: Sonar analysis roundtrip
order: 40
---

# Sonar Roundtrip

Pure executor for the `sonar-roundtrip` finalize step. Drives the producer-side Sonar fetch+store call, then dispatches per-finding through `manage-findings` + the domain-specific `ext-triage-{domain}` extension to decide and act on each Sonar issue.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `sonar-roundtrip` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as a Task agent (`plan-marshall:sonar-roundtrip-agent`) under a **15-minute (900 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The budget covers the full roundtrip: producer fetch+store, per-finding triage dispatch, optional fix-task creation, and (on loop-back) the `manage-status set-phase --phase 5-execute` handoff.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:sonar-roundtrip timed out after 900s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 900s"`.
3. The dispatcher continues with the next manifest step. Sonar timeouts MUST NOT block the rest of finalize — knowledge/lessons capture, branch cleanup, archive, and metrics still run.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority.

## Inputs

- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `sonar`, `ci`, build, and `manage-findings` script invocations below MUST pass `--project-dir {worktree_path}` for Bucket B notations (Bucket A `manage-*` scripts remain cwd-agnostic).

## Execution

### Producer: stage Sonar issues as findings (entry-point)

Call the producer-side fetch-and-store subcommand once. It pulls Sonar issues for the project (optionally scoped to the active PR), applies pre-filters (severity floor, file scope, dismissed-status filter), and writes one `sonar-issue` finding per surviving issue into the per-plan findings store.

```bash
python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
  --project-dir {worktree_path} fetch-and-store --plan-id {plan_id}
```

The producer is the ONLY surface that fetches and stores `sonar-issue` findings. This document does not classify, decide, or act on issues inline — every consumer-side action below reads from the findings store via `manage-findings query`.

If the producer reports `status: error` because Sonar is not configured for the project (no SonarQube/SonarCloud credentials, no project key), proceed directly to "Mark Step Complete" Branch C with `Sonar not configured`.

### Consumer: enumerate pending sonar-issue findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings query \
  --plan-id {plan_id} --type sonar-issue --resolution pending
```

If the result's `findings` list is empty, the gate is clean — proceed directly to "Handle findings (loop-back)" with `loop_back_needed = false`, then "Mark Step Complete" Branch A (`quality gate passed`).

### Per-finding dispatch loop (consumer-side triage)

For each finding in the query result, perform the following sequence. Process findings sequentially — never batch the per-finding decision through a single LLM call.

**1. Detect domain** from the finding's `file_path`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture which-module \
  --path {finding.file_path}
```

Read the resolved domain key from the TOON output. If the path falls outside any registered module, default to the project's primary domain as recorded in `marshal.json` `skill_domains`.

**2. Resolve the triage extension skill for the domain**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain {detected_domain} --type triage
```

Read the returned `skill` reference (e.g., `pm-dev-java:ext-triage-java`).

**3. Load the resolved triage extension into the main context**:

```
Skill: {bundle}:ext-triage-{domain}
```

The loaded extension brings its `standards/severity.md`, `standards/suppression.md`, and `standards/pr-comment-disposition.md` into context. For Sonar findings, the `severity.md` and `suppression.md` documents are the load-bearing inputs (the disposition table is PR-comment-specific; severity drives the Sonar fix-vs-suppress-vs-accept decision).

**4. Decide per-finding** using the loaded standards. The four canonical outcomes are:

| Decision | Meaning |
|----------|---------|
| **FIX** | The Sonar rule identifies a real defect. Create a fix task and loop back. |
| **SUPPRESS** | The rule is correct in pattern-match terms, but the loaded standards justify suppressing it (false positive, framework-mandated pattern, generated code, etc.). Apply the domain-specific NOSONAR / `@SuppressWarnings` annotation. |
| **ACCEPT** | The issue addresses an acceptable trade-off or is out of scope for this plan. Dismiss in Sonar with rationale. |
| **AskUserQuestion** | The loaded standards leave the call genuinely ambiguous (e.g., MAJOR severity in a non-domain file with no matching suppression rule). Ask the user — one question per finding, never batched. |

**5. Act on the decision**:

- **FIX** — Create a fix task via the two-step prepare-add → commit-add flow (see "Handle findings (loop-back)" below). Then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution fixed \
    --detail "{rationale referencing the fix task number}"
  ```

- **SUPPRESS** — Apply the domain-specific suppression annotation (NOSONAR comment, `@SuppressWarnings("java:S{rule}")`, `# noqa: {rule}`, `// eslint-disable-line {rule}`, etc.) to the source location identified by `{finding.file_path}:{finding.line}`, using the syntax from the loaded `suppression.md`. Then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution suppressed \
    --detail "{rationale referencing the loaded standard rule}"
  ```

- **ACCEPT** — Dismiss the issue in Sonar with rationale (via the workflow-integration-sonar dismissal surface; see that skill's standards for the canonical command). Then:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution accepted \
    --detail "{rationale}"
  ```

- **AskUserQuestion** — Ask the user via the `AskUserQuestion` tool. Then act on the user's answer using the matching path above. After acting:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
    --plan-id {plan_id} --hash-id {finding.hash_id} --resolution {fixed|suppressed|accepted|taken_into_account} \
    --detail "{user's stated rationale}"
  ```

### Handle findings (loop-back)

**On findings** that resolved to **FIX** (one or more `sonar-issue` findings closed with `--resolution fixed` and a fix-task reference), `loop_back_needed = true`:

1. Create fix tasks for the FIX-decision Sonar issues (same two-step prepare-add → commit-add flow as `automated-review.md`).
2. Loop back to phase-5-execute via:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
     --plan-id {plan_id} --phase 5-execute
   ```

3. Continue until clean or max iterations (3).

When NO finding resolved to **FIX** (every finding closed as SUPPRESS / ACCEPT / taken_into_account, or the query returned empty), `loop_back_needed = false` — proceed directly to "Mark Step Complete".

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. Mark done only on the terminal pass that returns clean (or on a skip); loop-back iterations do not terminate the step.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the Sonar quality gate result. The payload differs by branch:

**Branch A — quality gate passed** (terminal Sonar pass returns clean — every finding closed as SUPPRESS / ACCEPT, or the query was empty from the start):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate passed"
```

**Branch B — quality gate failed** (gate stayed red after max loop-back iterations; the step still marks `done` because the handshake records that the workflow executed — remediation is deferred to human follow-up):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "quality gate failed"
```

**Branch C — Sonar not configured for project** (the dispatcher ran this step but the producer determined Sonar is not configured — e.g., no SonarQube/SonarCloud credentials, no project key):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step sonar-roundtrip --outcome done \
  --display-detail "Sonar not configured"
```

Note: there is no "config disabled" branch — when the manifest excludes `sonar-roundtrip`, the dispatcher does not run this document at all, so no step record is written.
