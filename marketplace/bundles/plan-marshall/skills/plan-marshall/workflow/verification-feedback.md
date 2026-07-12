---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Verification-Feedback Workflow

Thin orchestrator that unifies the LLM-driven feedback flows under a single dispatch shape and enforces the consolidated **FIND → INGEST → TRIAGE → RESPOND** pipeline. Branches on the `producer` runtime input for the producer-side FIND work in Step 1, runs the single batched INGEST pass (Step 1.6) that promotes every quarantined `raw_input.{field}` value to the clean top-level fields, hands off to the canonical Steps 1-6 in [`triage.md`](triage.md) for the per-finding FIX / SUPPRESS / ACCEPT / AskUserQuestion loop (which reads TOP-LEVEL fields only, never `raw_input.*`), then transmits the decided dispositions back to the provider in ONE RESPOND loop (Step 8, `post_responses` / `sonar_rest transition`, keyed by `hash_id`).

Dispatched under the **phase-scoped** `verification-feedback` role key — the resolver bubbles from `<caller-phase>.verification-feedback` to `<caller-phase>.default` to `effort`. Phase-5 dispatches use `--phase phase-5-execute --role verification-feedback`; every phase-6-finalize dispatch (sonar, pr-comment, plugin-doctor, pr-state) uses `--phase phase-6-finalize --role verification-feedback`.

## Producer modes

| `producer` | Caller surface | Producer-side work (Step 1) | Pre-flight gate |
|------------|----------------|-----------------------------|-----------------|
| `build-runner` | phase-5-execute Step 11 + Step 11b | Build-runner / quality-gate log parse → findings store. **Mechanical, pre-flight** — the orchestrator runs the build, captures findings via `manage-findings add`, dispatches this workflow only when `manage-findings list | count > 0`. Step 1 here is a store-only query. | Count > 0 |
| `sonar` | phase-6-finalize `sonar-roundtrip` | `workflow-integration-sonar:sonar fetch_findings` — files one `sonar-issue` finding per surviving issue to the ledger with the untrusted message quarantined under `raw_input`. **Mechanical, pre-flight.** Step 1 here is a store-only query. | Count > 0 |
| `pr-comment` | phase-6-finalize `automated-review` | `workflow-integration-github:github_pr fetch_findings` (or GitLab equivalent) — files one `pr-comment` finding per surviving comment with the untrusted body quarantined under `raw_input`. **Mechanical, pre-flight.** Step 1 here is a store-only query. | Count > 0 |
| `plugin-doctor` | `project:finalize-step-plugin-doctor` + `/plugin-doctor` slash command | Marketplace static analysis — **LLM-heavy**, runs inside this envelope as Step 1: iterate the plugin-doctor rule catalog in-context, scope-filter, emit one finding per violation to the store. | None — analysis IS the producer step. |
| `pr-state` | `/workflow-pr-doctor` slash command | Wait for CI checks; fetch build status, PR comments, and Sonar issues sequentially; emit each finding-type to the store. Step 1 here orchestrates the multi-source sweep, then the unified triage in Steps 3-6 processes the aggregated set. | None — the producer always runs; Steps 3-6 short-circuit on zero findings. |

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `producer` | Yes | One of `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`. Selects the Step 1 branch and which `ext-triage-{domain}` skills are pre-loaded in Step 2. |
| `plan_id` | Yes | Forwarded to every `manage-findings` / `manage-tasks` / `tools-integration-ci` call. |
| `WORKTREE` | Yes | Used verbatim for `git -C {WORKTREE}` and as the root for every Edit/Write/Read. |
| `pr_number` | Conditional | Required for `pr-comment` (thread replies) and for `pr-state` (CI wait + multi-source fetch). |
| `caller_phase` | Optional | Explicit caller-phase override the main-context orchestrator passes when dispatching this phase-agnostic workflow, so the level resolver tracks the caller's phase. See `ext-point-execution-context-workflow.md` § Phase-context propagation for phase-agnostic workflows. |
| `iteration` | No | Loop-back iteration number (1..3). Surfaced in `display_detail` on `loop_back` outcomes. |

Skills the caller MUST forward in `skills[]`:

- `plan-marshall:manage-findings` — store queries, batched `ingest`, and disposition resolutions
- `plan-marshall:manage-tasks` — fix-task allocation
- `plan-marshall:manage-architecture` — `which-module` for domain detection
- `plan-marshall:manage-config` — extension resolution
- `plan-marshall:tools-integration-ci` — CI wait when `pr_number` is set (`producer=pr-state`)

Producer-specific additions:

- `producer=pr-comment` — also forward the RESPOND-loop provider `plan-marshall:workflow-integration-github` (or `…-gitlab`) for `post_responses`.
- `producer=sonar` — also forward `plan-marshall:workflow-integration-sonar` for the RESPOND-loop server-side dismissal (`sonar post_responses`).
- `producer=pr-state` — also forward `plan-marshall:workflow-integration-git`, `plan-marshall:workflow-integration-github` (or `…-gitlab`), `plan-marshall:workflow-integration-sonar`, `plan-marshall:tools-integration-ci`.
- `producer=plugin-doctor` — also forward `pm-plugin-development:plugin-doctor` (rule catalog + references) and `pm-plugin-development:tools-marketplace-inventory`.

Domain-triage extensions (`{bundle}:ext-triage-{domain}`) are loaded on demand inside Steps 3-6 — they are NOT pre-loaded by the caller.

## Step 1: Producer-mode branch

### Branch: `producer=build-runner` | `sonar` | `pr-comment` (store-only query)

The orchestrator has already populated the store via the mechanical producer (log parse, Sonar fetch, PR comments fetch). Verify the gate count and continue — the `--include-qgate` flag merges the pending per-phase Q-Gate findings into the per-plan read so the sweep is a single unified query (see `manage-findings` Canonical invocations → `list`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --type {finding_type} --resolution pending --include-qgate
```

`{finding_type}` per producer:

| `producer` | `{finding_type}` |
|------------|------------------|
| `build-runner` | `test-failure` or `lint-issue` (the orchestrator passes the type it staged) |
| `sonar` | `sonar-issue` |
| `pr-comment` | `pr-comment` |

If the store is empty (the pre-flight gate produced a count but findings have since been resolved by a sibling step), return immediately with `status: success`, `display_detail: "0 finding(s) — nothing to triage"`, `loop_back_needed: false`.

### Branch: `producer=plugin-doctor` (inline marketplace analysis)

Load the plugin-doctor rule catalog and references:

```text
Skill: pm-plugin-development:plugin-doctor
Skill: pm-plugin-development:tools-marketplace-inventory
```

Read the runtime `scope` input (one of `agents`, `commands`, `skills`, `scripts`, `metadata`, `skill-content`, `skill-knowledge`, `test-conventions`, `marketplace`, `plan-marshall`) and resolve the matching workflow per the plugin-doctor decision tree (`SKILL.md` § "Workflow Decision Tree"). Execute Phase 1 (Discover + Analyze) of the matching workflow in-context, iterating rules per `references/rule-catalog.md`. Emit one finding per rule violation to the store:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type triage \
  --title "{rule_id}: {component_path}" \
  --severity {warning|error} \
  --rule {rule_id} \
  --file-path {component_path} \
  --detail "{rule prose + per-violation context}"
```

Then fall through to Step 1.4 (batched ingestion), Step 1.5 (optional verify pre-stage), Step 2 (extension load), and Steps 3-6 (per-finding triage). The decision-and-action loop will FIX / SUPPRESS / ACCEPT each emitted finding using the standards in the pm-plugin-development triage extension.

### Branch: `producer=pr-state` (multi-source PR sweep)

Walk the producer surfaces sequentially, emitting findings of each type to the store, then continue to Step 2.

1. **Resolve worktree** — accept `--plan-id` (preferred, auto-resolves via `manage-status get-worktree-path`) OR `--project-dir` (explicit override). The resolved path is forwarded as `--project-dir {worktree}` to every child invocation below.

2. **Get PR number** — auto-detect when absent:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
     --project-dir {worktree} pr view
   ```

   Read `pr_number` from the TOON output. If no PR exists, return `status: success`, `display_detail: "no PR available — nothing to triage"`.

3. **Wait for CI** (when `wait=true`, default). Pass `--adaptive` so this wait seeds its ceiling from — and records its observed duration back into — the persisted `ci:wait` budget (the same #849 ratchet `ci_complete_precondition` drives), instead of the fixed `DEFAULT_CI_TIMEOUT`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
     --project-dir {worktree} checks wait --pr-number {pr_number} --adaptive
   ```

   Bash tool timeout: 1800000 ms (30 min) — the outer ceiling; `--adaptive` seeds the inner `ci:wait` ceiling from the persisted budget so the wait converges on observed CI durations rather than the fixed baseline. On timeout, `AskUserQuestion` (continue / skip / abort).

4. **Fetch build status**:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
     --project-dir {worktree} checks status --pr-number {pr_number}
   ```

   For each failed check in the output, emit a `test-failure` finding to the store with `rule-id` set to the failing step name and `detail` set to the message + `details_url`.

5. **Fetch PR comments** (FIND — body quarantined under `raw_input`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
     fetch_findings --pr-number {pr_number} --plan-id {plan_id}
   ```

   (or `workflow-integration-gitlab:gitlab_pr fetch_findings` equivalent). The producer writes one `pr-comment` finding per surviving comment to the store, quarantining the untrusted body under `raw_input.{body}`.

6. **Fetch Sonar issues** (FIND — message quarantined under `raw_input`):

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
     fetch_findings --plan-id {plan_id} --project {project_key}
   ```

   The producer writes one `sonar-issue` finding per surviving issue to the store, quarantining the untrusted message under `raw_input`. If Sonar is unavailable, log "Sonar skipped — not configured" and continue.

After all three producer surfaces have run, query the store for the union — `--include-qgate` merges the pending per-phase Q-Gate findings into the per-plan read so the union is a single unified query (see `manage-findings` Canonical invocations → `list`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --resolution pending --include-qgate
```

If empty, return `status: success`, `display_detail: "PR #{pr_number} clean — nothing to triage"`. Otherwise continue to Step 1.4.

## Step 1.4: Batched ingestion — promote `raw_input.{field}` to top-level (INGEST)

After the FIND branch (Step 1) has filed the pending findings and BEFORE triage reads them, run the single batched ingestion pass exactly once. It iterates every pending finding, runs the deterministic `validate_struct` validator over each quarantined `raw_input.{field}` value (schema + `maxLength` cap + domain-allowlist), and promotes only the `status: success` clamped output to the clean top-level field name — leaving the `raw_input.*` sub-object un-ingested for audit. A validator rejection resolves the finding (or records a fidelity Q-Gate finding) rather than promoting; top-level therefore becomes clean-by-construction, and triage's TOP-LEVEL-only read (§ Steps 3-6) is safe against the untrusted free-text.

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings ingest \
  --plan-id {plan_id}
```

This is the single deterministic containment boundary that supersedes the retired per-finding `execution-context-reader` + `validate_struct` Step-2b dispatch hop: containment is now one batched pass, not a per-comment reader dispatch. Run it once per dispatch, after all producers in Step 1 have filed and before Step 1.5 / Step 2. On a loop-back re-entry the pass is idempotent — already-promoted findings re-validate to the same clamped top-level value.

## Step 1.5: Verify pre-stage (optional, gated on producer `verification_profile`)

Before the findings reach triage, an OPTIONAL validity-verification pass runs — but ONLY when the producer of the queried findings declared a `verification_profile`. The full contract (the `verification_profile` producer declaration, the implementor-record shape, the resolved verify skill, and the producer→store→verify→triage lifecycle) lives in [`ext-point-verify.md`](../../extension-api/standards/ext-point-verify.md); do NOT inline-copy it here — this step is the orchestrator-side consumer.

1. **Gate check** — determine whether the producer declared a `verification_profile`. A producer that declares none skips this step entirely: continue directly to Step 2 with the pending set unchanged. (Of the current producers, only the security-audit pilot declares one; see the Current Implementations table in `ext-point-verify.md`.)

2. **Resolve and load the verify skill** — the `verification_profile` value names the verify skill that documents the adversarial-refute methodology for that profile (e.g. `security` → `persona-security-expert` adversarial-refute). Load it in-context:

   ```text
   Skill: {resolved verify skill}
   ```

3. **Run the adversarial-refute pass** — for each pending finding, apply the loaded verify skill's refute procedure to decide **confirmed** (a genuine defect) or **refuted** (a false positive).

4. **Close refuted findings as `rejected`** — a refuted finding is resolved with the terminal, non-pending `rejected` resolution so it never reaches triage and never blocks the gate:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
     --plan-id {plan_id} --hash-id {hash_id} --resolution rejected --detail "{refutation rationale}"
   ```

   For a Q-Gate finding, use the `qgate resolve` verb with `--resolution rejected --phase {phase}` (see `manage-findings` Canonical invocations → `resolve` / `qgate resolve`).

5. **Confirmed findings fall through unchanged** — leave every confirmed finding `pending` so Steps 2-6 triage them as today. Then continue to Step 2.

The verify pre-stage is purely subtractive on the pending set: it can only move a finding from `pending` to `rejected`, never the reverse, so a producer without a `verification_profile` and the post-verify confirmed set both reach Step 2 with the legacy behaviour intact.

## Step 2: Pre-load `ext-triage-{domain}` skills

For each finding-type present in the queried set, resolve and load the matching triage extension. Multiple domains may load for the same dispatch (especially in `pr-state` mode):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain {domain} --type triage
```

```text
Skill: {returned_extension_skill}
```

Once loaded for a domain, do not reload for subsequent same-domain groups in Step 3.

## Steps 3-6: Per-finding triage (cross-reference)

Execute [`triage.md`](triage.md) § Step 2 (pre-group), § Step 3 (iterate groups, batched LLM decision, sequential action within group), § Step 4 (deferred AskUserQuestion), § Step 5 (overflow / timeout handling), and § Step 6 (scope-deviation escalation). Those steps are domain-invariant — they read findings from the store and resolve each one using the loaded `ext-triage-{domain}` standards.

The smart-grouping shape and canonical per-finding action bodies (FIX / SUPPRESS / ACCEPT / AskUserQuestion) are documented as a single source of truth in `triage.md`; do not duplicate them here.

### Overflow returns to the orchestrator

This envelope is a leaf — it cannot sub-dispatch. When the per-finding iteration in `triage.md` § Step 5 detects that the wrapper budget is nearly exhausted, it does NOT spawn a fresh `verification-feedback` envelope itself. Instead it returns `overflow_deferred: {O}` to the main-context orchestrator, which re-fires `verification-feedback` on the next entry under the caller's phase context (the orchestrator sets `caller_phase` at that top-level dispatch). See [`ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) for the canonical leaf/dispatch-topology contract.

## Step 7: Loop-back signalling

`loop_back_needed: true` when any decision in any group resolved to FIX. The calling manifest step (or slash command body) handles the actual re-fire — this workflow does NOT call `manage-status set-phase` directly.

## Step 8: Respond loop — transmit dispositions to the provider (RESPOND)

Triage (Steps 3-6) RECORDED a disposition and a reviewer-ready `resolution_detail` on each finding via `manage-findings resolve`; it did NOT talk to the provider. This single RESPOND loop transmits those already-decided dispositions back to the provider **once**, after all triage has settled — keyed by each finding's own `hash_id`, never by positional pairing (the store-keyed pairing is the structural fix for the historical positional respond mis-pairing defect). It runs for the PR / Sonar producers only; `test-failure` / `lint-issue` / `plugin-doctor` findings have no external provider surface and skip this step.

The respond verbs are the pure zero-LLM provider surface (D3) — they apply dispositions, they never decide them:

1. **PR providers (`pr-comment`, and `sonar-issue` when `pr_number` is set for thread context)** — one `post_responses` call transmits every terminal-disposition finding that carries a `thread_id` and a `resolution_detail`: it posts the stored `resolution_detail` as a thread-reply, then resolves the thread. Findings without a `thread_id` or `resolution_detail` are skipped, never guessed at:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
     post_responses --pr-number {pr_number} --plan-id {plan_id}
   ```

   (or `workflow-integration-gitlab:gitlab_pr post_responses` for GitLab projects — one provider per host).

2. **Sonar server-side dismissals** — one `sonar post_responses` call transmits every terminal `sonar-issue` dismissal keyed by `hash_id`: it maps a `suppressed` resolution to a `wontfix` transition and a `rejected` resolution to a `falsepositive` transition, reading the Sonar issue key from each finding's own record (never a positional pairing). See `workflow-integration-sonar` Canonical invocations → `sonar — post_responses`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
     post_responses --plan-id {plan_id} --project {project_key}
   ```

   This RESPOND-side dismissal is gated by the `do_transition` param (owned by the `default:sonar-roundtrip` step; default `false`): the sonar branch of Step 8 runs `sonar post_responses` only when `do_transition == true`. Under the default `do_transition == false`, dispositions are recorded git-visibly as in-code suppressions during triage and NO server-side transition is transmitted.

The respond verbs FAIL LOUD when the provider is not configured (typed `unconfigured`, never a silent no-op). Because the respond loop reads back what triage recorded, a loop-back re-entry that re-runs triage on still-pending findings transmits only the newly-decided dispositions — already-responded findings are terminal and no longer pending.

## Output

```toon
status: success | loop_back | error | ci_failure
display_detail: "<≤80 char ASCII summary>"
producer: {producer}
findings_processed: {N}
findings_resolved: {M}
fix_tasks_created: {K}
fix_task_numbers[K]:
  - {task_number_1}
  - ...
overflow_deferred: {O}        # only present when overflow fired
deferred_user_questions: {Q}   # only present when AskUserQuestion fired
```

`status: loop_back` when `fix_tasks_created > 0` OR `overflow_deferred > 0`. `status: ci_failure` is reserved for `producer=pr-state` when the CI wait completed with failed checks AND zero further findings were emitted (the failure itself is the surfaced state). Otherwise `status: success` (every pending finding resolved without creating new tasks).

## Related

- [`triage.md`](triage.md) — canonical Steps 1-6 (decision + action + overflow + scope-deviation).
- [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — store schema and producer/consumer contract.
- [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 5.1 — phase-scoped resolution + producer-mode bundling rationale.
- `pm-plugin-development:plugin-doctor` — rule catalog and references loaded by `producer=plugin-doctor`.
- `plan-marshall:workflow-integration-github` / `…-gitlab` / `…-sonar` — producer-side fetchers used by `producer=pr-state`.
