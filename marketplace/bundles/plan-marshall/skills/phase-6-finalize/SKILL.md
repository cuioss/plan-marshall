---
name: phase-6-finalize
description: Complete plan execution with git workflow and PR management
user-invocable: false
---

# Phase Finalize Skill

**Role**: Finalize phase skill. Handles shipping workflow (commit, push, PR) and plan completion. Verification tasks have already been executed within phase-5-execute.

**Key Pattern**: Shipping-focused execution. No verification steps—all quality checks run as verification tasks within phase-5-execute before reaching this phase.

**Required steps declaration**: This skill opts in to the `phase_steps_complete` handshake invariant. The canonical list of steps that MUST be marked done on `status.metadata.phase_steps["6-finalize"]` before the phase transitions is maintained in [standards/required-steps.md](standards/required-steps.md). Each built-in step's standards document terminates with a `manage-status mark-step-done` call whose `--step` value matches an entry in that file.

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially, respecting config gates. Each config-gated step dispatches to a standards/ document.

**Required skill load** (before any operation):
```
Skill: plan-marshall:dev-general-practices
Skill: plan-marshall:workflow-integration-git
Skill: plan-marshall:tools-integration-ci
```

**Prohibited actions:**
- Never access `.plan/` files directly — all access must go through `python3 .plan/execute-script.py` manage-* scripts
- Never execute a step that is NOT listed in `manifest.phase_6.steps`. The manifest is the single authority — there is no fallback to a default step set, no inference from `marshal.json` config booleans, no per-step skip logic.
- Never skip phase transitions — use `manage-status transition`, never set status directly
- Never improvise script subcommands — use only those documented in this skill's workflow steps
- Never skip a step in the manifest list based on PR state, CI state, or earlier step outcomes. The ONLY valid skip condition is the resumable re-entry check (skip if already marked `done` from a previous invocation). Standards documents handle their own runtime state decisions inside their dispatched bodies.
- Never issue a raw `git` Bash call without `git -C {worktree_path}` (pre-worktree-removal) or `git -C {main_checkout}` (post-worktree-removal). No `cd` chaining, no implicit cwd. `{worktree_path}` and `{main_checkout}` MUST be resolved by the Step 0 entry step before any standards document runs.
- Never invoke a build, CI, Sonar, or GitHub/GitLab script (`ci`, `python_build`, `sonar`, `workflow-integration-*`) without an explicit routing flag. Forward `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` / `--project-dir {main_checkout}` (escape hatch / explicit override after worktree removal). The two flags are mutually exclusive. The executor is cwd-pass-through; routing must be explicit at every call site.

**Constraints:**
- Strictly comply with all rules from dev-general-practices, especially tool usage and workflow step discipline

## When to Activate This Skill

Activate when:
- Execute phase has completed (all implementation and verification tasks passed)
- Ready to commit and potentially create PR
- Plan is in `6-finalize` phase

---

## Phase Position in 6-Phase Model

See [references/workflow-overview.md](references/workflow-overview.md) for the visual phase flow diagram.

**Iteration limit**: 3 cycles max for PR issue resolution.

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `session_id` | string | Yes | Current host-platform session id — forwarded to `default:record-metrics` for `manage-metrics enrich`, which reads the matching transcript JSONL to capture main-context token usage. Without it, `enrich` cannot locate the transcript and session tokens are lost from the final report. |

### How to obtain session_id and transcript_path

Both are resolved via `manage_session` (`current` + `transcript-path` subcommands). Resolver-pipeline mechanism — cache layout, hook source, error contract, forbidden Bash-sandbox patterns — lives in [`references/session-resolver.md`](references/session-resolver.md). Callers obtain `session_id` first, then `transcript_path` keyed by it.

## Phase-Entry Worktree Assertion

The Phase Entry Protocol's `phase_handshake verify --phase 5-execute --strict` call (see [`ref-workflow-architecture/standards/phase-lifecycle.md`](../ref-workflow-architecture/standards/phase-lifecycle.md#phase-handshake-verify-phases-2-6)) asserts the worktree-resolution contract before any phase-6-finalize work begins: when `metadata.use_worktree==true`, `metadata.worktree_path` MUST be non-empty AND filesystem-resolvable (the directory exists AND `git -C {path} rev-parse --show-toplevel` returns the same canonical path). When the assertion fails, the script returns `status: error, error: worktree_unresolved` and (under `--strict`) exits 1 — phase entry refuses to advance until the persisted metadata is repaired. Plans with `metadata.use_worktree==false` skip the assertion (main-checkout flow). The assertion is particularly load-bearing here: phase-6-finalize's branch-cleanup step removes the worktree, so a stale `worktree_path` at entry would point at a directory cleanup is about to delete or has already deleted on a re-entry. The assertion fires uniformly at every phase boundary; see deliverable 8 in the originating lesson plan for the full contract.

## Configuration Sources

The phase-6-finalize step list lives in the **per-plan execution manifest**, not in `marshal.json`. The manifest is composed at outline time by `plan-marshall:manage-execution-manifest:compose` and is the single source of truth for which steps fire on this plan.

**Manifest** (read in Step 2):

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

| Field | Type | Description |
|-------|------|-------------|
| `phase_6.steps` | list | Ordered list of bare step IDs to execute (e.g., `commit-push`, `create-pr`, …). Authoritative. |

**Cross-phase config from `marshal.json`** (read in Step 2 alongside the manifest):

| Field | Type | Description |
|-------|------|-------------|
| `phase-6-finalize.review_bot_buffer_seconds` | integer | Max seconds to wait after CI for new review-bot comments (used as `--timeout` for `pr wait-for-comments`; ceiling, not fixed delay; default: 180) |
| `phase-6-finalize.max_iterations` | integer | Maximum finalize-verify loops (default: 3) |
| `phase-6-finalize.loop_back_without_asking` | bool | Symmetric counterpart to `phase-5-execute.finalize_without_asking`. When `true`, a `loop_back` outcome from any phase-6-finalize step (FIX disposition, `pr-comment-overflow`, sonar-roundtrip FIX) auto-dispatches the execute pipeline inline and re-enters the finalize loop, capped by `max_iterations`. When `false` (default), the dispatcher halts and returns control to the user. See Step 3 § "Loop-back continuation" for the dispatch shape. |
| `phase-5-execute.commit_strategy` | string | per_deliverable / per_plan / none |
| `phase-5-execute.finalize_without_asking` | bool | Forward-direction auto-continuation: when `true`, after `5-execute → 6-finalize` transition the orchestrator dispatches `phase-6-finalize` inline rather than halting and prompting the user. The reverse-direction symmetric counterpart is `phase-6-finalize.loop_back_without_asking`. |
| `phase-1-init.branch_strategy` | string | feature / direct |

A step is active if and only if it appears in `manifest.phase_6.steps`. Absent steps are NEVER executed. The order of steps in the manifest list is the execution order. The `plan.phase-6-finalize.steps` field in `marshal.json` is the *candidate set* — the input list `phase-4-plan` Step 8b passes to `manage-execution-manifest compose --phase-6-steps`. The manifest's `phase_6.steps` is the *resolved per-plan instance* of that candidate set and is the only authority this skill consults at dispatch time. The candidate set drives dispatch transitively; this skill itself never reads `marshal.json` for step selection.

---

## Dispatched workflows vs inline steps

Of the 16 default + project finalize steps, **6 dispatch** and **10 run inline**. Every dispatched step resolves under the phase-scoped registry — `manage-config effort resolve-target --phase phase-6-finalize [--role <subkey>]`. Step → resolved role: `pre-submission-self-review` → `phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`); `create-pr` → `phase-6-finalize` (no `--role`); `lessons-capture` → `phase-6-finalize --role post-run-review`; `automated-review` + `sonar-roundtrip` → `phase-6-finalize --role verification-feedback` (`producer=pr-comment` / `sonar` runtime input); `architecture-refresh` is hybrid (Tier 0 inline scripts; Tier 1 fans out under `phase-6-finalize` per affected module — the only per-iteration parallel dispatch in the contract); `project:finalize-step-plugin-doctor` (meta-project only) → `phase-6-finalize --role verification-feedback` (`producer=plugin-doctor` runtime input). Two opt-in dispatched steps exist outside the default set: **retrospective** → `phase-6-finalize --role post-run-review` (8 LLM aspects iterate inside one envelope); `/workflow-pr-doctor` (slash-command surface) → `phase-6-finalize --role verification-feedback` (`producer=pr-state` runtime input). The 10 inline steps (`commit-push`, `branch-cleanup`, `pre-push-quality-gate`, `record-metrics`, `archive-plan`, `finalize-step-print-phase-breakdown`, `architecture-refresh` Tier 0, `project:finalize-step-deploy-target`, `project:finalize-step-sync-plugin-cache`, `project:finalize-step-regenerate-executor`) are pure scripts or trivial orchestration that earn no envelope. CI completion is no longer a sibling step in this roster — it is a dispatcher-resolved precondition (`requires: [ci-complete]`) checked inline before any consumer step runs; see Step 3 § "Precondition resolution" below. For the rationale see [dispatch-granularity.md](../extension-api/standards/dispatch-granularity.md) § 5 (find the LLM core, not the wrapping step).

## Step Types

Three step types are supported, distinguished by prefix notation:

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:commit-push`) | Strip prefix, read `standards/{name}.md` and follow all steps |
| **project** | `project:` prefix (e.g., `project:finalize-step-foo`) | `Skill: {notation}` with interface contract parameters |
| **skill** | fully-qualified `bundle:skill` (e.g., `pm-dev-java:java-post-pr`) | `Skill: {notation}` with interface contract parameters |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, validate against dispatch table)
- Starts with `project:` -> project type
- Contains `:` (other) -> fully-qualified skill type

Each step declares an `order: <int>` value in its authoritative source — frontmatter on built-in standards docs (`standards/{name}.md`), frontmatter on project-local `SKILL.md` for `project:` steps, and the return-dict `order` field for extension-contributed skills. `marshall-steward` sorts the `steps` list by this value when writing it to `marshal.json`. This skill iterates the list as written and does NOT re-sort or validate `order` at runtime — the persisted order is the runtime order.

### Built-in Step Dispatch Table

| Step Name | Standards Document | Description |
|-----------|-------------------|-------------|
| `default:pre-submission-self-review` | `workflow/pre-submission-self-review.md` | Pre-submission structural self-review (symmetric pairs, regex, wording, duplication, contract drift) |
| `default:commit-push` | `standards/commit-push.md` | Commit and push changes |
| `default:create-pr` | `standards/create-pr.md` | Create pull request |
| `default:architecture-refresh` | `standards/architecture-refresh.md` | Refresh architecture descriptors (tier-0 deterministic discover + diff, tier-1 LLM re-enrichment) |
| `default:automated-review` | `standards/automated-review.md` | CI automated review — orchestration prose; the per-finding LLM core dispatches [`workflow/triage.md`](workflow/triage.md) with `finding_type=pr-comment` (see [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) for the architectural flow) |
| `default:sonar-roundtrip` | `standards/sonar-roundtrip.md` | Sonar analysis roundtrip — orchestration prose; the per-finding LLM core dispatches [`workflow/triage.md`](workflow/triage.md) with `finding_type=sonar-issue` |
| `default:lessons-capture` | `standards/lessons-capture.md` | Record lessons learned |
| `default:branch-cleanup` | `standards/branch-cleanup.md` | Branch cleanup — adapts to PR mode or local-only based on create-pr step presence |
| `default:record-metrics` | `standards/record-metrics.md` | Record final plan metrics before archive |
| `default:finalize-step-print-phase-breakdown` | `standards/finalize-step-print-phase-breakdown.md` | Optional override mode: capture the Phase Breakdown table from metrics.md so the renderer emits it in place of the per-step [OK] block |
| `default:archive-plan` | `standards/archive-plan.md` | Archive the completed plan |

### Interface Contract for External Steps

Project and skill steps receive these parameters:

```
Skill: {step_reference}
  Arguments: --plan-id {plan_id} --iteration {iteration} [--session-id {session_id}]
```

The step skill can access the plan's context via manage-* scripts (references, status, config).

#### Session-id forwarding

`--session-id {session_id}` is forwarded ONLY to external steps on the per-step opt-in whitelist below. The forwarding is opt-in (rather than universal) because some external steps may reject unknown flags; opting in keeps the contract additive for new dependencies without breaking existing steps.

| Whitelisted external step | Why it needs `--session-id` |
|---------------------------|------------------------------|
| `plan-marshall:plan-retrospective` | Aspect 12 (chat-history-analysis) is conditional on `--session-id`. Without it, the aspect is silently skipped and the retrospective report omits the chat-history section. See `plan-retrospective/SKILL.md` → "Input Contract" for the consumer-side declaration. |

`default:record-metrics` is intentionally NOT on this whitelist: it is a built-in step, dispatched via `standards/record-metrics.md`, which already consumes `--session-id` inline. The whitelist scope is project- and skill-type external steps only.

**How to apply** — when defining a new external step that consumes session-scoped state:

1. Declare `--session-id` as an input in the step's authoritative document (project step `SKILL.md` or fully-qualified skill `SKILL.md`/standards).
2. Add the fully-qualified step name to the whitelist table above.
3. Verify by running a finalize end-to-end and confirming the step does not hit a "session_id missing" code path.

The orchestrator is responsible for resolving `session_id` (see "How to obtain session_id" earlier in this file). This skill receives the resolved value via its Input Parameters and forwards it verbatim to whitelisted steps; it does not re-resolve.

**Required termination:** Every external step (project and fully-qualified skill) MUST terminate with a `manage-status mark-step-done` call that carries `--display-detail "{one-line summary}"`. This is REQUIRED, not optional — a missing or empty `display_detail` causes renderer failure in Step 4 (the literal placeholder `<missing display_detail>` will surface to the user and contribute to a `[FAILED]` headline). The detail string is authored by the step itself; the renderer NEVER invents content on the step's behalf.

The full command template (use verbatim, substituting the placeholders):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step {step_name} --outcome {done|skipped|failed} \
  --display-detail "{one-line summary}"
```

MANDATORY annotations for every argument:

- `--phase` — MANDATORY. Always the literal string `6-finalize` for steps dispatched under this operation. This anchors the step record to the finalize phase; any other value routes the record into the wrong phase bucket and breaks the Step 4 renderer grouping.
- `--outcome` — MANDATORY. Must be exactly one of `done`, `skipped`, or `failed`. Any other value (including misspellings or capitalized variants) is rejected by `manage_status`. The choice determines the headline classification and CANNOT be inferred from `display_detail` alone.
- `--step` — MANDATORY. Must match the fully-qualified step name as listed in `marshal.json` (e.g. `default:commit-push`, `project:foo`, or `plan-marshall:some-skill:some-script`). Mismatches here create orphan status records that the renderer cannot pair with the dispatched step.
- `--display-detail` — MANDATORY. Single-line summary of what the step actually did, authored by the step itself. Subject to the constraints listed below. A missing, empty, or whitespace-only value triggers the `<missing display_detail>` placeholder and contributes a `[FAILED]` headline regardless of the `--outcome` value.

**Notation:** the third segment is `manage_status` (with an UNDERSCORE). The hyphenated form `manage-status` is the subcommand name, not the script name. Using `plan-marshall:manage-status:manage-status` triggers an executor lookup failure.

**`display_detail` constraints:**

- ≤80 characters
- No trailing period
- No embedded newlines (single line only)
- Plain ASCII — no unicode glyphs
- Concrete and user-facing (describe what the step did, not how)

See [standards/output-template.md](standards/output-template.md#display_detail-contract-for-step-authors) for the full detail-string convention, ASCII icon rules, and concrete examples per built-in step.

---

## Operation: finalize

**Input**: `plan_id`

### Step 0: Resolve Worktree and Main Checkout Paths

**This step runs before any other finalize step** and makes `{worktree_path}` and `{main_checkout}` available to every subsequent step and standards document. All git Bash calls and all build/CI/sonar/github/gitlab script invocations in the finalize workflow depend on these two values — no standards document may resolve them independently.

Read the plan status and extract the worktree path from metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read \
  --plan-id {plan_id}
```

Extract `metadata.worktree_path`:

- **If present**: the plan ran in an isolated worktree. Capture the value as `{worktree_path}`. The main checkout is the parent of `.plan/local/worktrees/{plan_id}/` — derive `{main_checkout}` by stripping the trailing `/.plan/local/worktrees/{plan_id}` segment from `{worktree_path}`, or resolve it explicitly:

```bash
git -C {worktree_path} rev-parse --path-format=absolute --git-common-dir
```

The `git-common-dir` output ends with `/.git` inside the main checkout — `{main_checkout}` is its parent directory.

- **If absent** (pre-worktree plan or `use_worktree == false`): there is no worktree. Set `{worktree_path}` equal to `{main_checkout}`, where `{main_checkout}` is the repository root resolved via:

```bash
git rev-parse --show-toplevel
```

Log the resolved paths so they remain visible in model context for every subsequent Edit/Write/Read/Bash call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Finalize cwd context: worktree_path={worktree_path} main_checkout={main_checkout} — all git calls MUST use 'git -C' with one of these paths, all Bucket B script calls MUST pass '--plan-id {plan_id}' or '--project-dir <path>' (mutually exclusive)"
```

From this point on, every standards document loaded by the finalize pipeline inherits `{worktree_path}` and `{main_checkout}` from this step. Standards documents MUST NOT re-resolve these values.

### Step 1: Check Q-Gate Findings and Log Start

#### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Starting finalize phase"
```

#### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase 6-finalize --resolution pending
```

If unresolved findings exist from a previous iteration (filtered_count > 0):

For each pending finding:
1. Check if it was addressed by the fix tasks that just ran
2. Resolve:
```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution fixed --phase 6-finalize \
  --detail "{fix task reference or description}"
```
3. Log:
```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize:qgate) Finding {hash_id} [qgate]: fixed — {resolution_detail}"
```

### Step 2: Read Manifest and Cross-Phase Configuration

The phase-6-finalize step list is read from the **per-plan execution manifest** (`execution.toon`), not from `marshal.json`. The manifest is composed at outline time by `plan-marshall:manage-execution-manifest:compose` and is the single source of truth for which Phase 6 steps fire for this plan. This skill reads the manifest verbatim and dispatches — it carries NO per-step skip logic of its own.

#### Read the execution manifest

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

Extract `phase_6.steps` — the ordered list of step IDs (e.g., `commit-push`, `create-pr`, `automated-review`, …) to execute. Step IDs in the manifest are **bare names** (no `default:` prefix). The dispatcher in Step 3 prepends `default:` when looking up built-in steps, but otherwise iterates the list verbatim.

**If the manifest is missing** (`status: error, error: file_not_found`): abort finalize with an explicit error — the manifest is REQUIRED. Re-run `plan-marshall:manage-execution-manifest:compose` from outline phase to repair.

#### Step 1.5: Manifest Loadability Check

After reading `phase_6.steps` from the manifest but BEFORE dispatching any step in Step 3, walk the list once and verify each step's standards file is loadable. This is the manifest fail-fast guard: it converts a confusing mid-dispatch failure (a built-in step pointing at a deleted standards file) into an immediate, actionable error at phase entry.

For each `step_id` in `manifest.phase_6.steps`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate-loadable --plan-id {plan_id} --step-id {step_id}
```

The script returns a structured TOON payload of the form `{status, step_id, standards_path, loadable, message?}`. Aggregate the per-step results across the loop. The caller MAY use the bulk form `--all` instead to validate every step in `manifest.phase_6.steps` in one invocation:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  validate-loadable --plan-id {plan_id} --all
```

The bulk form returns `{status, results[N]{step_id, standards_path, loadable, message?}, unloadable_count}` and is the preferred shape when validating a non-trivial step list.

**On any unloadable step** (`loadable: false` for at least one entry): abort finalize with the canonical actionable message. Log the error and return a `status: error` payload — do NOT enter Step 3:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Manifest loadability check failed — step `{step_id}` referenced by `marshal.json` is missing standards file `{standards_path}` — the plan likely deleted the file without sweeping `marshal.json`"
```

The actionable message is fixed by [`standards/required-steps.md`](standards/required-steps.md) § "Loadability Contract" — the wording above is the canonical phrasing the contract guarantees. Self-modifying plans that delete a `phase-6-finalize/standards/{name}.md` without also pruning `marshal.json::plan.phase-6-finalize.steps` are the motivating failure mode.

**Scope**: the loadability check applies to **built-in** steps only (bare names that resolve to `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/{name}.md`). External steps (`project:` / `bundle:skill`) are not validated here — their loadability is the responsibility of the host plugin cache, and a missing project/skill step surfaces as a `Skill: {ref}` resolution error during dispatch, not as a missing standards file. The `validate-loadable` subcommand returns `loadable: true` with no further check for external step IDs so the bulk-form caller does not have to filter.

#### Read cross-phase configuration

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize get --audit-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute get --audit-plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init get --audit-plan-id {plan_id}
```

Read the config blocks for `review_bot_buffer_seconds`, `max_iterations`, `commit_strategy`, and `branch_strategy`. **Do not** read the `steps` field from `marshal.json` here — that field is the candidate set consumed by `phase-4-plan` Step 8b, not by this skill. The manifest's `phase_6.steps` list is the only valid source for runtime dispatch.

Also read references context for branch and issue information:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

**After reading configuration**, log the finalize strategy decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Finalize strategy: commit={commit_strategy}, manifest_steps={steps_count}, branch={branch_strategy}"
```

### Step 3: Execute Step Pipeline (Manifest-Driven, Resumable, Timeout-Wrapped)

Iterate over `manifest.phase_6.steps` (read in Step 2). The list is the manifest's authoritative ordering — neither this skill nor any standards document re-orders, filters, or skip-conditional any step.

#### Plugin cache freshness

In meta-projects that own marketplace bundles (notably the
plan-marshall repo itself), the project-local Phase 6 ordering
typically pairs `project:finalize-step-deploy-target` (order 12) with
`project:finalize-step-sync-plugin-cache` (order 14), placing both
immediately before any agent-dispatched step. The cache is therefore
always refreshed from the just-generated `target/claude/` output before
the in-flight finalize dispatches any agent loaded from the cache — no
stacked rule is required.

Consumer projects do not own bundle sources, so they do not register
either step. Their finalize dispatches load whatever the host plugin
cache holds, which is exactly the published bundle definitions.

#### Session-Restart Fence

**This fence is normative, not advisory.** When the running finalize dispatch processes `project:finalize-step-sync-plugin-cache` AND the plan's `references.modified_files` contains paths under `marketplace/bundles/plan-marshall/` (i.e., the plan modifies `plan-marshall` itself), the dispatcher MUST halt immediately after the sync step records `outcome=done` and refuse to dispatch any subsequent agent-loaded step in the same Claude Code session.

The fence is the single structural guard against the self-host blind spot — see [`standards/self-host-blind-spot.md`](standards/self-host-blind-spot.md) for the invariant and its three failure surfaces. The two-part remediation (cache sync + session restart) cannot be collapsed into the sync step alone: synchronising the cache does NOT refresh the host platform's in-process skill registry, so any agent dispatched in the same session continues to load the pre-sync skill bodies and workflow notations from its registry snapshot.

**Halt protocol**:

1. Record the fence trigger via `manage-logging work` with the `[BLOCKED]` tag, naming the modified plan-marshall paths from `references.modified_files`.
2. Emit the canonical halt instruction to the user: `"plan-marshall self-modification detected — session restart required before subsequent finalize steps. Re-enter /plan-marshall action=finalize plan={plan_id} in a fresh Claude Code session."`
3. Return a structured `status: blocked` payload with `display_detail: "session-restart fence triggered"`. Do NOT mark the next step `failed`; do NOT advance the manifest pointer. The next session re-enters via resumable re-entry semantics and picks up at the first non-`done` step.

**Why the fence is mandatory, not advisory**: surfaces (1) and (2) in the blind-spot invariant — skill resolution and workflow-notation resolution — both bind to the in-process registry. An advisory "consider restarting" note that left the dispatcher free to continue would let the dispatched `create-pr`, `automated-review`, or `lessons-capture` agent execute against stale skill bodies, producing a PR description / review comment / lesson record that reflects the pre-change shape of the very code the plan just shipped. The fence MUST NOT be skippable by a `--force` flag or a per-plan opt-out; the only escape is the prescribed session restart.

**Scope**: the fence fires only when `references.modified_files` actually touches the `plan-marshall` bundle. Plans that modify sibling bundles only (`pm-dev-java`, `pm-documents`, etc.) do not trigger the fence — those bundles' modified skills become visible to the next session naturally, and the running finalize dispatch is unaffected because its own hot path is unchanged.

**Resumable re-entry semantics**: Before dispatching each step, read the current step record from `status.metadata.phase_steps["6-finalize"]`. If the step is already marked `done`, skip dispatch entirely (no re-run, no log noise — the previous run completed it). If the step is marked `failed`, retry it from scratch. If the step has no record (or any other outcome), dispatch it as a fresh run. This makes finalize safe to re-enter after a partial run, a crash, or an explicit retry — completed steps stay completed, failed steps get exactly one retry per invocation.

**Precondition resolution**: before dispatching any step in the FOR loop, parse the step's frontmatter `requires:` list (if present) and resolve each entry against its mapped resolver. The only precondition currently defined is `ci-complete`, mapped to the dispatcher-internal helper `scripts/ci_complete_precondition.py` (notation `plan-marshall:phase-6-finalize:ci_complete_precondition`). The resolver is invoked inline through the executor proxy (no Task agent dispatch — the helper itself is bounded by `ci wait --timeout 600`, matching the host platform's per-call ceiling):

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_complete_precondition \
  resolve --plan-id {plan_id} --worktree-path {worktree_path} --pr-number {pr_number} [--timeout 600]
```

The helper returns a TOON envelope with `status`, `head_sha`, and `ci_final_status`. Outcome mapping:

| Resolver `status` | Dispatcher action |
|-------------------|--------------------|
| `satisfied` | Cache hit — proceed to dispatch the consumer step normally. |
| `wait_succeeded` | Cache miss → fresh `ci wait` returned success — proceed to dispatch. |
| `wait_failed` | CI failure OR timeout — SKIP the consumer step's body and immediately mark the step's outcome `failed` via `manage-status mark-step-done … --outcome failed --display-detail "ci_failure (precondition)"`. The consumer body never runs. Continue to the next step in the manifest loop. |

**Cache lifecycle**: The helper persists successful outcomes to `.plan/plans/{plan_id}/work/ci-precondition-cache.toon`, keyed by the current `git -C {worktree_path} rev-parse HEAD` SHA. The cache is alive for one dispatcher iteration; a loop-back commit that advances HEAD invalidates the entry implicitly (the next resolve sees a fresh SHA, the stored SHA no longer matches, and the resolver re-polls CI against the new tree). Failed outcomes are NOT cached — re-entry always re-polls so a transient CI failure resolves on the next attempt. Multiple consumer steps in the same dispatcher pass share the cache: the first `requires: [ci-complete]` lookup runs the wait, and subsequent lookups at the same HEAD return `satisfied` without re-polling.

The precondition resolver is dispatcher-internal — it produces no `phase_steps["6-finalize"]` record of its own (the precondition is not itself a finalize step). The dispatcher bears responsibility for the `wait_failed → ci_failure (precondition)` outcome mapping on the consumer step. Consumer step bodies (under `workflow/`) MUST declare `requires: [ci-complete]` in their YAML frontmatter to opt into the precondition; absent the declaration, the dispatcher proceeds directly to the step body and does not invoke the resolver.

**Special case — HEAD-dependent steps**: four steps (`pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`, `commit-push`) are HEAD-dependent. The first three validate the live worktree tree via local quality-gate, PR-comment, and Sonar infrastructure respectively; `commit-push` materializes the worktree's commit/push contract and MUST re-fire when a loop-back fix task produces a fresh commit *after* an earlier `commit-push` recorded `outcome=done` against the prior HEAD. The general rule above is augmented for `step_id IN HEAD_DEPENDENT_STEPS` (defined below) with a worktree-HEAD comparison so a loop-back commit (typically produced by `automated-review` or `sonar-roundtrip` opening a fix task that produces a new commit) re-fires each gate against the newer code instead of skipping it on a stale `done` record:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — gate already validated this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD has advanced past the validated SHA) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE (record is incomplete without a SHA; safe default is to re-run) |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| `outcome == loop_back` | n/a | RE-FIRE (treat as no record — same as the general rule for loop_back) |
| no record OR any other value | n/a | DISPATCH (unchanged — same as the general rule) |

`HEAD_DEPENDENT_STEPS = {"pre-push-quality-gate", "automated-review", "sonar-roundtrip", "commit-push"}`. All four steps MUST persist `head_at_completion` on their terminal `--outcome done` `mark-step-done` call so the comparison above is meaningful. The standards docs for each step (`pre-push-quality-gate.md`, `automated-review.md`, `sonar-roundtrip.md`, `commit-push.md`) carry the per-step instructions for capturing `git rev-parse HEAD` immediately before the `mark-step-done` invocation and forwarding it via `--head-at-completion {sha}`. Branches that mark `loop_back` or `failed` do not need to persist the SHA — the dispatcher's general resumability handling for those outcomes does not consult it. CI completion is a separate dispatcher-resolved precondition (`requires: [ci-complete]`) — its cache key is the same `git rev-parse HEAD` SHA, so the same HEAD-advance signal that invalidates a stale `done` record also invalidates the precondition cache.

**Conditional HEAD-dependent steps**: `CONDITIONAL_HEAD_DEPENDENT_STEPS = {"project:finalize-step-deploy-target", "project:finalize-step-sync-plugin-cache"}` carries the same HEAD-dependency semantics as `HEAD_DEPENDENT_STEPS` but membership is re-evaluated per loop iteration via the predicate:

```
modified_files_intersects_marketplace_bundles(references.modified_files at step's previous done mark)
  := any(path.startswith("marketplace/bundles/") for path in modified_files)
```

A step in this set is treated as HEAD-dependent IFF the predicate evaluates `true` against the `references.modified_files` snapshot at the step's previous `done` mark. Both steps MUST persist `head_at_completion` on `outcome=done` (same contract as the unconditional set) so the comparison is always available; the predicate decides whether to consult it. Loop-back commits that touch only test or doc paths leave the existing `done` record valid (predicate false → SKIP under the general rule); loop-back commits that touch any `marketplace/bundles/**` path invalidate the `done` record (predicate true → consult `head_at_completion` and RE-FIRE when HEAD has advanced). The rationale: both steps deploy generated marketplace artifacts (`target/claude/` + plugin cache) from the source bundles; a loop-back fix task that touches no source bundle leaves the prior deploy/sync output still valid.

Resolve the comparison HEAD inside the dispatcher block at the moment of the per-step check:

```bash
git -C {worktree_path} rev-parse HEAD
```

Do NOT cache the live HEAD across loop iterations — read it fresh per step so a step that advances HEAD mid-loop (e.g., an inline commit produced by an earlier loop-back fix task) is observed correctly by every later step's check. All other finalize steps keep the general rule above verbatim; this special case applies only to the four steps named in `HEAD_DEPENDENT_STEPS`.

**Per-agent timeout wrapper**: Every Task agent dispatch in this loop runs under a per-agent timeout budget. If the dispatch does not return inside the budget, the wrapper logs an ERROR, marks the step `failed` via `manage-status mark-step-done`, and continues with the next step in the list (no abort, no re-throw). Inline-only steps are not timeout-wrapped because they execute in the main context where the host platform already manages call timeouts. Budgets:

| Step | Budget | Rationale |
|------|--------|-----------|
| `default:sonar-roundtrip` | 15 min (900s) | Full Sonar gate roundtrip plus optional fix-task creation |
| `default:automated-review` | 15 min (900s) | CI wait + review-bot buffer + comment triage |
| `default:lessons-capture` | 5 min (300s) | Bounded `manage-lessons add` + Write workflow |
| All other steps | no explicit budget | Fall under the host platform's default per-call ceiling |

For each step reference:

**Agent-suitable built-in steps** (self-contained, no user interaction) — each dispatches to `plan-marshall:execution-context-{level}` with the role-resolved workflow doc:

| Step reference | Resolver lookup | Workflow doc |
|----------------|-----------------|--------------|
| `default:create-pr` | `--phase phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/create-pr.md` |
| `default:lessons-capture` | `--phase phase-6-finalize --role post-run-review` | `plan-marshall:phase-6-finalize/workflow/lessons-capture.md` |
| `default:automated-review` | `--phase phase-6-finalize --role verification-feedback` (LLM core; outer wrapper tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/automated-review.md` |
| `default:sonar-roundtrip` | `--phase phase-6-finalize --role verification-feedback` (LLM core; outer wrapper tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/sonar-roundtrip.md` |

`automated-review` and `sonar-roundtrip` are orchestrator workflows — their LLM-judgement core is a single internal `verification-feedback` dispatch (with `producer=pr-comment` / `producer=sonar` runtime input). The outer wrapper resolves under `phase-6-finalize.default` since the body is mostly script execution and one sub-dispatch.

**Dispatch pattern** — resolve the target via the role resolver. Pass `--phase phase-6-finalize` for every dispatched step; add `--role <subkey>` only when the step has its own sub-key in the table above:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize [--role <subkey>]
```

Extract the `target` field from the TOON output. Use that value as `{target}` in the dispatch and the post-resolve log line below.

Emit the standardized post-resolve dispatch log line — see [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract. Substitute `{role}` with `default` when no `--role` flag was passed, otherwise the explicit sub-key value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role={role} workflow={workflow-doc-from-table} plan_id={plan_id}"
```

Dispatch:

```
Task: plan-marshall:{target}
  prompt: |
    name: <step-name>
    plan_id: {plan_id}
    skills[N]:
    - <step-specific skills>
    workflow: <workflow-doc-from-table>
    WORKTREE: {worktree_path}
```

The 5-field prompt-body contract (`name`, `plan_id`, `skills[]`, `workflow`, `WORKTREE`) is documented in [`plan-marshall:extension-api/standards/ext-point-execution-context-workflow`](../extension-api/standards/ext-point-execution-context-workflow.md). The variant resolution (canonical no-suffix for `inherit`/empty level; `execution-context-{level}` otherwise) lives in [`plan-marshall:plan-marshall/standards/effort-variants.md`](../plan-marshall/standards/effort-variants.md).

**Inline-only built-in steps** (require user interaction, sequential dependency, or are bounded polling primitives that fit comfortably under the host platform's per-call Bash ceiling):
- `architecture-refresh` (AskUserQuestion for Tier-1 prompt mode; consumes `architecture-pre/` snapshot from phase-1-init Step 5d), `branch-cleanup` (AskUserQuestion), `record-metrics` (must run immediately before `archive-plan` on the still-live plan directory), `archive-plan` (must be last, moves plan files). Note: `commit-push` is also inline-only but is HEAD-dependent (see § HEAD-dependent steps below), so it appears in `HEAD_DEPENDENT_STEPS` rather than here.

Per-step agent `<usage>` totals are persisted on disk by `manage-metrics accumulate-agent-usage` (called from step 5b below). The on-disk file `.plan/plans/{plan_id}/work/metrics-accumulator-6-finalize.toon` survives context compaction and is read by `default:record-metrics` at `end-phase` time. Do NOT maintain a parallel tally in model context — the on-disk file is authoritative.

**Initialise the `loop_back_iteration` counter to 0 BEFORE entering the FOR loop** (i.e., here, at the start of Step 3 — outside the loop body). The counter persists across FOR-loop re-entries triggered by the loop-back continuation hook (step 7b below), so that the `max_iterations` ceiling is enforced across the entire dispatch. Initialising the counter inside the FOR loop body (e.g., on each entry into the loop) would reset it on every loop-back BREAK + RE-ENTER, defeating the ceiling. The counter is held in model context for the duration of the dispatch — it is NOT persisted to status.json; a fresh phase-6-finalize entry (e.g., after a session restart) starts the counter back at 0.

```
loop_back_iteration = 0   # initialised once, before the FOR loop; persists across FOR-loop re-entries from the loop-back hook (step 7b)

FOR each step_id in manifest.phase_6.steps:
  # Resolve full step reference. Manifest entries may be:
  #   - bare names (e.g. `commit-push`) — built-in, prepend `default:`
  #   - already-prefixed (`default:foo`, `project:bar`, `bundle:skill`) — use verbatim
  # The composer preserves `project:` / `bundle:skill` prefixes from marshal.json;
  # only `default:` may be stripped. So presence of `:` in step_id => external step.
  IF step_id contains ':':
      step_ref = step_id                 # external step (`project:` / `bundle:skill`) — preserve verbatim
  ELSE:
      step_ref = "default:" + step_id    # built-in step — prepend `default:` prefix

  1. Resumable re-entry check:
     Read status.metadata.phase_steps["6-finalize"][step_id]:
       - IF step_id IN HEAD_DEPENDENT_STEPS (the HEAD-dependent special-case set; see "HEAD-dependent step set" note below):
           Resolve the live worktree HEAD via `git -C {worktree_path} rev-parse HEAD`.
           Read this fresh per iteration; do NOT cache across the loop.
             - IF outcome == "done" AND head_at_completion == live HEAD: SKIP this step
             - IF outcome == "done" AND head_at_completion != live HEAD: RE-FIRE (treat as no record — dispatch as fresh run)
             - IF outcome == "done" AND head_at_completion is absent: RE-FIRE (record is incomplete without a SHA; dispatch as fresh run)
             - IF outcome == "failed": RETRY (proceed to dispatch as fresh run)
             - IF outcome == "loop_back": RE-FIRE (treat as no record — dispatch as fresh run)
             - IF no record OR any other value: dispatch normally
       - ELSE (every other step keeps the general rule):
           - IF outcome == "done": SKIP this step (continue to next iteration)
           - IF outcome == "failed": RETRY (proceed to dispatch as fresh run)
           - IF outcome == "loop_back": RE-FIRE (treat as no record — dispatch as fresh run)
           - IF no record OR any other value: dispatch normally
     Log skip/retry/re-fire decisions at INFO level so the work.log reflects the re-entry path.

     **HEAD-dependent step set**: `HEAD_DEPENDENT_STEPS = {"pre-push-quality-gate", "automated-review", "sonar-roundtrip", "commit-push"}`. The first three validate the live worktree tree via local quality-gate, PR-comment, and Sonar infrastructure respectively. A loop-back commit (typically produced by `automated-review` or `sonar-roundtrip` opening a fix task that produces a new commit) advances HEAD past the previously-validated SHA, and a stale `done` record on any of these three steps would produce a false-clean result on re-entry. `commit-push` enters the HEAD-dependent set because a loop-back fix task may produce a fresh commit *after* `commit-push` recorded `outcome=done` against the prior HEAD; without HEAD-comparison the dispatcher would skip `commit-push` on re-entry and leave the fix-task changes staged-but-uncommitted. The same `head_at_completion` comparison applies to all four. The companion `CONDITIONAL_HEAD_DEPENDENT_STEPS = {"project:finalize-step-deploy-target", "project:finalize-step-sync-plugin-cache"}` set carries the same HEAD-dependency semantics but membership is re-evaluated per iteration: a step in this set is HEAD-dependent IFF `references.modified_files` (at the step's previous `done` mark) intersects `marketplace/bundles/**`. Both deploy steps produce derived artifacts (`target/claude/`, plugin cache) from source bundles — loop-back fix tasks that touch only test/doc paths leave the prior derived output still valid; loop-back fix tasks that touch any `marketplace/bundles/**` path require a re-fire. Other inline-only steps (`architecture-refresh`, `branch-cleanup`, `record-metrics`, `archive-plan`) and pure-administrative agent steps (`create-pr`, `lessons-capture`) are NOT HEAD-dependent — their effect is captured by side-effect (a created PR, recorded lessons) and is idempotent against HEAD advances; the general rule above applies to them. CI completion is resolved as a separate dispatcher-side precondition (`requires: [ci-complete]`) — its cache key is the same `git rev-parse HEAD` SHA, so a HEAD advance also invalidates the precondition cache.

  2. Log step start:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Executing step: {step_ref}"

  3. Determine step type:
     - IF step_ref starts with "default:" -> BUILT-IN type (use step_id for dispatch table lookup)
     - ELSE IF step_ref starts with "project:" -> PROJECT type (manifest may someday include extension steps)
     - ELSE IF step_ref contains ":" -> SKILL type

  4. Pre-archive snapshot hook (run BEFORE dispatching the step if step_id == "archive-plan"):
     See "Pre-Archive Snapshot Hook" subsection below. Capture the snapshot into model context, then proceed to step 5 to dispatch archive-plan normally.

  5. Dispatch with timeout wrapper:
     Resolve the per-agent timeout budget from the table above (15 min for sonar/automated-review, 5 min for knowledge/lessons; no explicit budget for other steps).

     - BUILT-IN (agent-suitable) — route each step_ref to the generic `execution-context-{level}` dispatcher via the Task tool, passing the step's workflow doc and role key through the prompt body, wrapped with the resolved timeout. The workflow-doc-bearing dispatch carries the step's enforcement envelope (input contract, required skill loads, prohibited actions) inside the subagent context via the loaded skills + workflow; a generic unscoped dispatch with no workflow doc is NOT valid.

       **Role-aware dispatch** (applies to all four built-in agent-suitable steps):

       (1) Resolve the level-bound target via the resolver:
           ```
           target = python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
             effort resolve-target --phase phase-6-finalize [--role <subkey>]
           ```
           Returns `execution-context-{level}` (variant), or canonical `execution-context` for `inherit`/empty.
       (2) Dispatch via `Task(subagent_type: plan-marshall:<target>, …)` with prompt body `name`, `plan_id`, `skills[]`, `workflow: plan-marshall:phase-6-finalize/workflow/{name}.md`, `WORKTREE`.

       Per-step workflow docs and resolver lookups:
         * default:create-pr        -> workflow: workflow/create-pr.md        | --phase phase-6-finalize                              (no --role)
         * default:automated-review -> workflow: workflow/automated-review.md | --phase phase-6-finalize                              (outer wrapper; inner verification-feedback dispatch uses --role verification-feedback) | timeout: 900s
         * default:sonar-roundtrip  -> workflow: workflow/sonar-roundtrip.md  | --phase phase-6-finalize                              (outer wrapper; inner verification-feedback dispatch uses --role verification-feedback) | timeout: 900s
         * default:lessons-capture  -> workflow: workflow/lessons-capture.md  | --phase phase-6-finalize --role post-run-review       | timeout: 300s

       The subagent's body loads `dev-general-practices` + the prompt's `skills[]`, then `Read`s the workflow doc and executes its steps inside the dispatch envelope. Pass `--plan-id {plan_id}` and, when an `{iteration}` counter applies, `--iteration {iteration}` as workflow-specific runtime inputs in the prompt body. The Worktree Header is conveyed via the always-required `WORKTREE` prompt-body field; the subagent resolves the worktree path internally and propagates it into any further dispatches it issues.

       **On timeout** (the dispatch does not return within the budget):
         a. Log ERROR:
            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Step {step_ref} timed out after {budget}s — marking failed and continuing"
         b. Mark step failed:
            python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
              --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome failed \
              --display-detail "timed out after {budget}s"
         c. Continue to the next step in the loop — DO NOT abort the pipeline.

     - BUILT-IN (inline-only: commit-push, architecture-refresh, branch-cleanup, record-metrics, archive-plan):
       Read the standards document from dispatch table and follow all steps in main context. Inline steps are not wrapped by the per-agent timeout block above — they execute under the host platform's standard per-call ceiling.

     - PROJECT/SKILL: Load the skill with interface contract:
       Skill: {step_ref}
         Arguments: --plan-id {plan_id} --iteration {iteration} [--session-id {session_id}]

       Append `--session-id {session_id}` ONLY when `step_ref` is on the
       Session-id forwarding whitelist documented under "Interface Contract
       for External Steps" above (the table at that section is the single
       source of truth — do not re-list its entries here). Off-whitelist
       external steps receive `--plan-id` and `--iteration` only —
       appending `--session-id` to a step that does not declare it risks a
       "rejected unknown flag" failure.

  5b. Accumulate agent usage (only when the dispatched step ran as a Task agent and did NOT time out):
      Extract total_tokens, tool_uses, duration_ms from the agent's <usage> tag, then persist them on disk via:

         python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics accumulate-agent-usage \
           --plan-id {plan_id} --phase 6-finalize \
           --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}

      The script reads `.plan/plans/{plan_id}/work/metrics-accumulator-6-finalize.toon` (initialising it on first call), sums in the supplied values, increments the `samples` counter, and writes the file back. Inline steps and timed-out steps skip this call — the timeout path's cost is captured by the `manage-metrics enrich` transcript sweep inside `default:record-metrics`. Step 5b runs at most once per dispatched agent return; do NOT also append the totals to a model-context variable.

  6. Capture archive result (only when step_id == "archive-plan"):
     Record the returned `archive_path` into model context alongside the pre-archive snapshot — it is consumed by Step 4 (Render Final Output Template).

  7. Log step completion:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"

  ### Loop-back Target Contract

  Two invariants govern every loop-back outcome emitted by a phase-6-finalize step. Both are structural: a violation is a contract bug, not a degraded run.

  - **Target phase invariant**: every loop-back-emitting finalize step MUST persist a `loop_back_target` value on its `mark-step-done --outcome loop_back` call. The persisted target MUST be one of `5-execute` or `6-finalize` — no other phases (notably `2-refine`, `3-outline`, or `4-plan`) are legal targets. The two-value enumeration is structural: `5-execute` denotes a full-phase rollback for fix-task-required dispositions (FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`); `6-finalize` denotes inline replay of the same finalize step for inline-fixable dispositions (SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX). The continuation hook (§ 7b below) routes deterministically on the field value — when target is `5-execute`, the loop-back-emitting step also persists `current_phase: 5-execute` via `manage-status set-phase --phase 5-execute` BEFORE its terminal `mark-step-done` call; when target is `6-finalize`, the persisted `current_phase` stays at `6-finalize` (no `set-phase` call) and the continuation hook replays the loop-back-marked step via the resumable re-entry check. Authoritative call sites: `workflow/automated-review.md` and `workflow/sonar-roundtrip.md` — each carries an inline "Loopback target invariant" marker above its `set-phase` block (or, when target is `6-finalize`, above the conditional that suppresses the `set-phase` call) as the structural guard against silent drift. The dispatcher-level enforcement of this invariant lives in `plan-marshall/workflow/execution.md` § "Loop-back continuation" → ELSE branch (the persisted-phase assertion that fires before any user-facing prompt).

  - **Granularity invariant**: loopback granularity is the **triage workflow's responsibility**, encoded in the `loop_back_target` field on the `mark-step-done --outcome loop_back` call. Two granularity tiers govern every loop-back iteration: `5-execute` denotes a **full-phase rollback** for fix-task-required dispositions (FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`) — the continuation hook (§ 7b) re-enters `phase-5-execute` from the top of its `manage-tasks next` loop, the execute pipeline drives the freshly-allocated fix tasks to done, then transitions `5-execute → 6-finalize` via the standard `phase-5-execute.finalize_without_asking` gate. `6-finalize` denotes an **inline replay** of the same finalize step for inline-fixable dispositions (SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX with no fix-task allocation) — the continuation hook stays in `6-finalize`, does NOT call `set-phase`, and re-fires the loop-back-marked step via the resumable re-entry check. **The dispatcher MUST honour the `loop_back_target` field; it MUST NOT decide granularity itself.** This replaces the prior "all loopbacks are full phase rollbacks" invariant: the answer to the canonical user question "are all loopback-triggered changes done as full phase changes, or are inline changes done as well?" is now **both, depending on the triage classification — fix-task-required dispositions roll back the phase; inline-fixable dispositions replay the same finalize step in place**.

  Cross-references: `workflow/automated-review.md` § "Handle findings (loop-back)" and Branch D, `workflow/sonar-roundtrip.md` § "Handle findings (loop-back)" and Branch D — each carries the conditional `set-phase` / `mark-step-done --loop-back-target` shape described above. `plan-marshall/workflow/triage.md` § Step 7 owns the granularity classification rule (the table that maps disposition types to the two `loop_back_target` values). The dispatcher-level enforcement of the invariant lives in `plan-marshall/workflow/execution.md` § "Loop-back continuation" → ELSE branch (the persisted-phase assertion). The four-corner truth table for the `finalize_without_asking` × `loop_back_without_asking` flag combinations is documented in § 7b below.

  7b. Loop-back continuation hook (consult the just-recorded outcome):
      Read the step's recorded outcome from `status.metadata.phase_steps["6-finalize"][step_id]` (the dispatched agent's `mark-step-done` call wrote it). When `outcome == "loop_back"`, also read the persisted `loop_back_target` field from the same record — it is structurally guaranteed to be present on every `loop_back` outcome (the manage-status `--loop-back-target` validation contract enforces this; absence is a dispatcher contract bug, not a routing case to handle). The two legal values are `5-execute` (full-phase rollback) and `6-finalize` (inline replay).

      **Symmetric-knob and ceiling check (BEFORE the granularity branch)** — the `loop_back_without_asking` knob and the `max_iterations` ceiling apply uniformly to BOTH granularity tiers. They gate whether the chosen dispatch shape executes inline or halts and prompts. The `loop_back_target` value selects the dispatch shape AFTER these gates pass.

      Consult the symmetric auto-continuation knob to decide whether to halt or re-enter inline:

         python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
           plan phase-6-finalize get --field loop_back_without_asking --audit-plan-id {plan_id}

      Read the returned `value`:

      - IF `value == false` (default): halt the FOR loop, mark the finalize phase as needing a re-entry, and emit the user-facing prompt (named for the persisted `loop_back_target`):
          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
            work --plan-id {plan_id} --level INFO \
            --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back signalled by {step_ref} (target={loop_back_target}): returning control to user (loop_back_without_asking=false)"
        IF `loop_back_target == "5-execute"`:
          Display: "Loop-back signalled. Run '/plan-marshall action=execute plan={plan_id}' when ready to dispatch the fix tasks."
        IF `loop_back_target == "6-finalize"`:
          Display: "Loop-back signalled (inline replay). Run '/plan-marshall action=finalize plan={plan_id}' to replay the finalize step."
        STOP.

      - IF `value == true`: increment the in-memory `loop_back_iteration` counter (initialised to 0 at the start of Step 3, BEFORE the FOR loop — see the `loop_back_iteration = 0` line above the `FOR each step_id` header. The counter persists across FOR-loop re-entries triggered by step 7b, so the `max_iterations` ceiling is enforced across the entire dispatch rather than reset per re-entry — counted across BOTH granularity tiers) and consult the ceiling:

         (a) Compare against `phase-6-finalize.max_iterations` (default 3, read in Step 2). When `loop_back_iteration > max_iterations`, halt with a user-facing prompt — even with the flag set, the ceiling is the structural safety valve. This applies to BOTH granularity tiers:
             python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
               work --plan-id {plan_id} --level WARNING \
               --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back ceiling reached ({loop_back_iteration}/{max_iterations}) — halting and returning control to user"
             Display: "Loop-back iteration ceiling reached. Inspect pending fix tasks via 'manage-tasks list --status pending --plan-id {plan_id}' and re-run when ready."
             STOP.

         (b) Otherwise, emit the canonical iteration log line:
             python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
               work --plan-id {plan_id} --level INFO \
               --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back iteration {loop_back_iteration}/{max_iterations}"

      **Granularity branch (AFTER the symmetric-knob and ceiling gates have passed)** — the `loop_back_target` value selects only the dispatch shape. Both branches share the same iteration counter and ceiling.

      - IF `loop_back_target == "6-finalize"` (inline replay for inline-fixable dispositions): the calling step did NOT issue a `manage-status set-phase --phase 5-execute` call, so the persisted `current_phase` is still `6-finalize`. The continuation hook **skips the phase-5-execute re-dispatch entirely** — do NOT call `manage-status set-phase`, do NOT load `Skill: phase-5-execute`. Just BREAK out of the current FOR iteration and RE-ENTER the FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check (item 1 above) sees the `loop_back`-marked step and re-fires it directly.

      - IF `loop_back_target == "5-execute"` (full-phase rollback for fix-task-required dispositions): the calling step issued `manage-status set-phase --phase 5-execute` before its terminal `mark-step-done`, so the persisted `current_phase` is `5-execute`. Dispatch the inline execute pipeline. The inline re-entry mirrors the forward `phase-5-execute.finalize_without_asking` path (`workflow/execution.md` § Execute Phase Completion) — it runs the execute pipeline against the freshly-allocated fix tasks, transitions back to `6-finalize`, and re-enters this FOR loop:

             1. Set the plan back to phase-5-execute (the loop-back-emitting step typically did this already via `manage-status set-phase`; idempotent re-issue is safe):
                python3 .plan/execute-script.py plan-marshall:manage-status:manage_status set-phase \
                  --plan-id {plan_id} --phase 5-execute

             2. Dispatch the execute pipeline inline by re-loading `phase-5-execute`:
                Skill: plan-marshall:phase-5-execute
                  Arguments: --plan-id {plan_id}

                The execute pipeline picks up the freshly-allocated fix tasks (created by the FIX disposition or by the overflow-handling path) via the standard `manage-tasks next` loop, drives them to done, then transitions `5-execute → 6-finalize` via the existing `phase-5-execute.finalize_without_asking` gate. When `finalize_without_asking == false`, the inline re-entry halts at the standard prompt — symmetric loop-back is gated by both knobs in series, so a project can opt into automated forward continuation without also opting into automated loop-back continuation.

             3. After phase-5-execute returns, BREAK out of the current FOR loop iteration position and RE-ENTER the FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check (item 1 above) skips already-`done` steps, retries `failed` steps, and re-fires the `loop_back`-marked step now that its preconditions have been addressed.

             Note: the BREAK + RE-ENTER above is a control-flow construct, not a per-step skip. The FOR loop re-iteration uses the same manifest list and the same per-step resumable check; the only state that changes is the `phase_steps["6-finalize"][step_id]` records (the dispatched agent will record a fresh outcome on its next run).

      The `loop_back_iteration` counter is held in model context for the duration of the dispatch — it is NOT persisted to status.json. A fresh phase-6-finalize entry (e.g., after a session restart) starts the counter back at 0; the manifest's resumable re-entry check still skips already-`done` steps, so re-entering after a restart re-runs only the steps that recorded `loop_back` or `failed` on the previous invocation.
END FOR
```

**Critical invariant**: This loop iterates **only** the manifest list. A step that is NOT in `manifest.phase_6.steps` MUST NOT fire under any circumstance — there is no fallback to a "default" step set, no inference from config booleans, no per-step skip logic. The manifest is the contract. If a deployment requires a different step set, recompose the manifest at outline time.

**Lessons-capture unconditionality**: When `lessons-capture` IS in `manifest.phase_6.steps` (the composer includes it for every non-trivial change-type), this loop dispatches it on every Phase 6 entry. It is not gated on PR state, CI state, or earlier step outcomes — reaching Phase 6 is itself the trigger.

**Symmetric auto-continuation invariant**: The `loop_back_without_asking` flag is the structural counterpart to `phase-5-execute.finalize_without_asking`. The two knobs together define the four corners of the unattended-vs-interactive matrix:

| `finalize_without_asking` | `loop_back_without_asking` | Behaviour |
|---------------------------|----------------------------|-----------|
| `false` (default) | any | The forward `5-execute → 6-finalize` transition halts and prompts the user. Loop-back never fires inline because finalize is not entered in the same orchestration cycle. |
| `true` | `false` (default) | Forward auto-continuation; loop-back halts at the inline execute re-entry point and prompts the user. (This is the conservative shape: forward is automated, reverse is interactive.) |
| `true` | `true` | Full unattended cycle. A loop_back outcome re-dispatches execute inline up to `max_iterations` times, then halts even with the flag set. |
| `false` | `true` | Effectively `false`/`false` from the user's perspective: forward halts and prompts before phase-6-finalize ever runs, so the loop-back hook is unreachable in the same orchestration cycle. |

The conservative default (`loop_back_without_asking=false`) ships an interactive shape so existing plans behave the same as before this knob was added. Projects that want full unattended execution must opt into both knobs.

#### Pre-Archive Snapshot Hook

When the NEXT step to dispatch is `default:archive-plan` (always the last CONFIGURED step), capture a snapshot of plan state BEFORE dispatching archive-plan. The archive step moves `.plan/plans/{plan_id}/` to `.plan/archived-plans/{date}-{plan_id}/` and invalidates subsequent `manage-status read` calls against the live path, so the renderer (Step 4) would be unable to read state after archive returns.

The snapshot is held in **model context (in-memory)** — do NOT write a work file to disk. It flows directly from this hook into Step 4's render procedure.

Capture the following values:

1. **`status.metadata.phase_steps["6-finalize"]`** — dict of `{step_name: {outcome, display_detail}}` from `manage-status read --plan-id {plan_id}`.
2. **Deliverables list** — from `manage-solution-outline read --plan-id {plan_id}` (ordered list of titles and per-deliverable state).
3. **Manifest `phase_6.steps` list** — from `manage-execution-manifest read --plan-id {plan_id}` (already fetched in Step 2; capture the bare-name list for renderer ordering).
4. **Repository state** — branch via `git -C {main_checkout} branch --show-current`, porcelain via `git -C {main_checkout} status --porcelain`.
5. **PR state + number** — via `ci pr view --plan-id {plan_id}` (preferred) or `ci pr view --project-dir {main_checkout}` (escape hatch). Treat error (no PR for branch) as `state=n/a, number=n/a`.
6. **Solution outline Summary** — the 2-3 sentence Summary body that feeds the Goal block. Fetch via `manage-solution-outline read --plan-id {plan_id} --section summary` and extract the `content` field. On `section_not_found` or empty content, store the sentinel value `None`; the emission procedure substitutes the defensive placeholder `(no summary recorded)`.
7. **Plan `short_description`** — the compact label used by Step 6's terminal `done` emission. Extract `plan.short_description` from `manage-status read --plan-id {plan_id}` (already fetched in item 1). Store the raw string, or `None` when the field is absent/empty. This value is captured **before** archive so it remains available after `status.json` is moved.

See [standards/output-template.md#snapshot-procedure](standards/output-template.md#snapshot-procedure) for exact commands and field extraction.

After the snapshot is captured, dispatch `default:archive-plan` normally (step 5 in the FOR body above) and capture its returned `archive_path` (step 6). Both the snapshot and `archive_path` flow into Step 4 "Render Final Output Template".

**Built-in step notes**:
- `default:branch-cleanup`: Do NOT preemptively skip based on PR state. The `standards/branch-cleanup.md` standard has its own `AskUserQuestion` confirmation gate.
- `default:record-metrics`: MUST immediately precede `default:archive-plan`. This step finalizes the `6-finalize` phase with two `manage-metrics` writes (`end-phase` for the closing phase + `generate` for `metrics.md`) and a separate `enrich` for session token capture. Plan finalization has no "next phase" so the fused `phase-boundary` subcommand does not apply here — see `standards/record-metrics.md` for the authoritative sequence. All writes MUST land on the live plan directory; if archive runs first, the target directory no longer exists and each command would recreate a post-archive orphan under `.plan/local/plans/{plan_id}/`.
- `default:archive-plan`: This step MUST be last in the default order because it moves plan files (including status.json), which breaks manage-* scripts. All plan operations must complete before archive.

Do NOT add any further `manage-metrics` invocations after `default:archive-plan` or after `Skill: plan-marshall:phase-6-finalize` returns to its caller. The plan-finalization bookkeeping (`end-phase` + `enrich` + `generate`) is fully contained by `default:record-metrics`.

### Step 4: Render Final Output Template

`default:archive-plan` in Step 3 atomically marks the active phase done and sets `current_phase: complete` on the live status.json BEFORE moving the plan directory — see `manage-status:_cmd_lifecycle.py cmd_archive`. A separate `manage-status transition --completed 6-finalize` call MUST NOT be issued from this phase; it would fail with `file_not_found` because archive has already invalidated the live path.

**This step ALWAYS runs** — it is NOT configurable via the `steps` list. It is the terminal action of the phase, invoked after `default:archive-plan` returns in Step 3.

Load the renderer specification:

```
Skill: plan-marshall:phase-6-finalize
  Standards: standards/output-template.md
```

**Inputs** (both already in model context from Step 3):

- **Pre-archive snapshot** — captured by the Pre-Archive Snapshot Hook before `default:archive-plan` dispatched. Contains `phase_steps` map, deliverables list, configured `steps` list, repository branch/porcelain, PR state/number, and the solution outline Summary text captured via `manage-solution-outline read --section summary`.
- **`archive_path`** — returned by `default:archive-plan` in Step 3.

**Procedure:** Follow the emission procedure in [standards/output-template.md#emission-procedure](standards/output-template.md#emission-procedure). The renderer is a pure assembler:

1. Resolve the headline token (`MERGED` / `OPEN` / `LOOP_BACK` / `SKIPPED` / `FAILED`) via the precedence chain.
2. Build the headline.
3. Build the Goal block (literal `Goal` header, blank line, Summary text wrapped to ~78 chars with 2-space indent; defensive `(no summary recorded)` fallback when Summary is `None` or empty).
4. Build the Deliverables block (one row per deliverable, icon by outcome).
5. Build the Finalize steps block (one row per configured step, padded 33-char name + `display_detail`).
6. Build the Repository trailer (main state | worktree token | working tree state).
7. Emit the five blocks separated by blank lines as a plain-text, user-facing output.

**No additional script calls are needed for this step** — the renderer consumes only the in-memory snapshot plus `archive_path`. It performs no `manage-status` / `manage-solution-outline` / `ci pr view` reads of its own.

The emitted template is a **user-facing text block printed to the model's output**, not a log entry. It is the primary surface reported to the user at the end of the finalize phase.

### Step 5: Log Phase Completion

Final metrics are already recorded inside the Step 3 pipeline by `default:record-metrics` (which runs immediately before `default:archive-plan`). This step only logs phase completion to work.log.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan completed: {steps_count} steps executed"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

**Note**: `manage-logging` operates on log files, not the plan directory, so these calls remain valid after `default:archive-plan` has moved the plan state.

### Step 6: Emit Done Terminal Title

**This step ALWAYS runs** when a `short_description` was captured in the pre-archive snapshot — it is NOT configurable via the `steps` list.

Emit a one-shot `✓ pm:done:{short_description}` OSC escape to the terminal so the session tab reflects plan completion. The emission is stateless: the OSC write sticks until the next terminal-title hook fires and overwrites it (the host platform's hook lifecycle owns that — see [`../plan-marshall/references/terminal-title.md`](../plan-marshall/references/terminal-title.md) for the underlying mechanism). No session state file, clearing hook, or TTL is required.

**Why this runs AFTER `default:archive-plan`**: archive has already moved the live plan directory, so the normal cwd/status.json resolution chain would return `◯ claude`. The `--plan-label` argument bypasses that chain by accepting the label directly from the caller. The label value comes from item 7 of the pre-archive snapshot, captured while `status.json` was still live.

**If `short_description` is `None` or empty**: skip this step (log at INFO and continue to return). A plan created before the `short_description` field existed, or one whose derivation produced an empty string, cannot produce a meaningful `pm:done:` label; in that case the title stays at whatever the last hook emitted (typically `◯ claude` via Stop).

**If `short_description` is set**: invoke the terminal-title script via the canonical executor notation, passing the captured label. The executor mapping resolves the deployed cache path at generation time, so future bundle-version bumps flow through automatically and the invocation matches every other phase-6-finalize step:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:set_terminal_title done --plan-label "{short_description}"
```

The user-side hook entries in `./.claude/settings.json` (written by `/marshall-steward`) are unaffected — they continue to invoke the script via absolute path because the host-platform hook runner does not load the marketplace executor; that absolute-path duplication is required by external constraint and `/marshall-steward` remains the single source of truth for it.

**Advisory**: this step is best-effort. On any error (script missing, non-zero exit, `/dev/tty` unavailable), log a WARNING and continue. A missing terminal emission is cosmetic and MUST NOT block finalize from returning success — the plan has already archived, all state transitions are committed, and the user can still read the Step 4 output template in their scrollback:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING --message "[WARNING] (plan-marshall:phase-6-finalize) Terminal done-title emission failed: {error}"
```

---

## Output

**Success** (user-facing):

The primary output is the five-block template rendered by Step 4. It is a plain-text, user-facing block — not TOON — assembled from the pre-archive snapshot plus `archive_path`. See [standards/output-template.md](standards/output-template.md) for the full renderer specification.

Example:

```
[MERGED] PR #212 -- 5 deliverable(s) shipped, all green

Goal
  Enrich the phase-6-finalize output with a terminal-rendered three-block
  template so the user sees a single at-a-glance summary of the plan's
  outcome, deliverables, and finalize-step results.

Deliverables (5/5)
  [OK]  1. Extend manage-status mark-step-done with --display-detail
  [OK]  2. Create standards/output-template.md
  [OK]  3. Wire renderer into phase-6-finalize/SKILL.md
  [OK]  4. Simplify standards/record-metrics.md
  [OK]  5. Add display_detail to 9 step standards docs

Finalize steps (10/10 done)
  [OK]  commit-push                       -> a1b2c3d
  [OK]  create-pr                         #212
  [OK]  automated-review                  3 comment(s) resolved (no loop-back)
  [OK]  sonar-roundtrip                   quality gate passed
  [OK]  lessons-capture                   no lessons recorded
  [OK]  validation                        all required steps done
  [OK]  record-metrics                    1591s / 209327 tokens
  [OK]  branch-cleanup                    main pulled, branch deleted (local+remote), worktree removed
  [OK]  archive-plan                      -> .plan/archived-plans/2026-04-17-lesson-2026-04-17-005

Repository: main up-to-date | worktree removed | working tree clean
```

**Success** (machine-facing minimal TOON — retained for callers that parse phase output):

```toon
status: success
plan_id: {plan_id}
archive_path: .plan/archived-plans/{date}-{plan_id}
next_state: complete
```

**Loop Back** (PR issues found, iteration < 3):

```toon
status: loop_back
plan_id: {plan_id}
iteration: {current_iteration}
reason: {ci_failure|review_comments|sonar_issues}
next_phase: 5-execute
fix_tasks_created: {count}
```

**Error**:

```toon
status: error
plan_id: {plan_id}
step: {commit|push|pr|automated_review|sonar}
message: {error_description}
recovery: {recovery_suggestion}
```

---

## Error Handling

On any error, **first log the error** to work-log:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) {step} failed - {error_type}: {error_context}"
```

See `standards/validation.md` for specific error scenarios and recovery actions.

---

## Resumability

Step activation is determined by presence in `manifest.phase_6.steps` — absent steps are NEVER executed under any circumstance.

The Step 3 dispatch loop is fully resumable across re-entries: each step's `status.metadata.phase_steps["6-finalize"][step_id].outcome` drives the per-step decision on a fresh phase-6-finalize invocation:

| Outcome on re-entry | Action |
|---------------------|--------|
| `done` | Skip dispatch entirely. The step ran successfully on a previous invocation; do not re-execute. |
| `failed` | Retry from scratch. The previous run produced a `failed` record (typically a timeout or step-internal abort); the new invocation gets exactly one fresh attempt. |
| `loop_back` | Re-fire (treat as no record — dispatch as fresh run). The previous run recorded a deliberate loop-back iteration and signalled that the dispatcher should re-execute the step on next phase entry. |
| (no record) | Dispatch as a first-time run. |
| any other value | Dispatch as a first-time run (treat as a degraded record). |

**Special case — `pre-push-quality-gate`**: this step's resumable check is augmented with a worktree-HEAD comparison so a loop-back commit re-fires the gate instead of skipping it on a stale `done`. The augmented rule applies ONLY when `step_id == "pre-push-quality-gate"`; every other step uses the general table above verbatim.

| Outcome on re-entry | `head_at_completion` vs live HEAD | Action |
|---------------------|-----------------------------------|--------|
| `done` | matches live `git -C {worktree_path} rev-parse HEAD` | Skip dispatch entirely (steady-state — gate already validated this exact tree). |
| `done` | differs from live HEAD | Re-fire (treat as no record — HEAD has advanced past the validated SHA, e.g., after a loop-back commit). |
| `done` | `head_at_completion` field absent | Re-fire (record is incomplete without a SHA; safe default is to re-run). |
| `failed` | n/a | Retry from scratch (unchanged). |
| (no record) | n/a | Dispatch as a first-time run (unchanged). |
| any other value | n/a | Dispatch as a first-time run (unchanged). |

The live HEAD MUST be resolved fresh per iteration via `git -C {worktree_path} rev-parse HEAD` — do NOT cache across the loop, so a step that advances HEAD mid-loop is observed correctly by every later check. Cross-reference: `standards/pre-push-quality-gate.md` "Mark Step Complete" Branch A, which persists `head_at_completion` on the success path.

This makes finalize safe to interrupt and re-enter — completed work is preserved, failed work gets a retry, never-run work runs for the first time, and the HEAD-dependent quality gate re-fires whenever the tree it validated has been superseded. There is no separate "resume" mode; every Phase 6 entry is implicitly resumable.

In-step state checks (consulted by individual standards docs after dispatch — these guard idempotent operations, not skip activation):

1. **Uncommitted changes?** `git status --porcelain` — empty → `commit-push` records "no changes" and marks done.
2. **PR exists?** `ci pr view` — `status: success` → `create-pr` re-uses the existing PR.
3. **Plan complete?** `manage-status read` — `current_phase: complete` → finalize has nothing to do; return immediately.

---

## Standards (Load On-Demand)

| Standard | Step Name | Purpose |
|----------|-----------|---------|
| `workflow/pre-submission-self-review.md` | `default:pre-submission-self-review` | Deterministic helper (resolved via `ext-self-review-{domain}` ext-point) + LLM cognitive review for symmetric-pair / regex-overfit / wording / duplication / contract-drift defects (hard-fail) |
| `standards/commit-push.md` | `default:commit-push` | Commit strategy, git status, workflow-integration-git delegation |
| `standards/create-pr.md` | `default:create-pr` | PR existence check, body generation, CI pr create |
| `standards/architecture-refresh.md` | `default:architecture-refresh` | Tier-0 deterministic `architecture discover --force` + `diff-modules --pre` driven `chore(architecture)` commit; Tier-1 LLM re-enrichment with `prompt`/`auto`/`disabled` modes; respects `architecture_refresh.tier_0` / `tier_1` run-config knobs and `change_type ∈ {bug_fix, verification}` shortcut |
| `standards/automated-review.md` | `default:automated-review` | Consume completed-CI signal, then consumer dispatch (FIX / SUPPRESS / ACCEPT / AskUserQuestion); loop-back on FIX or pr-comment-overflow. Architectural flow: [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) |
| `standards/sonar-roundtrip.md` | `default:sonar-roundtrip` | Sonar consumer dispatch (FIX / SUPPRESS / ACCEPT / AskUserQuestion); loop-back on FIX. Architectural flow: [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) |
| `standards/lessons-capture.md` | `default:lessons-capture` | manage-lesson add command |
| `standards/branch-cleanup.md` | `default:branch-cleanup` | Branch cleanup with user confirmation — PR mode (merge + CI) or local-only (switch + pull) |
| `standards/record-metrics.md` | `default:record-metrics` | Record final plan metrics before archive |
| `standards/finalize-step-print-phase-breakdown.md` | `default:finalize-step-print-phase-breakdown` | Optional override mode: capture Phase Breakdown table for the renderer (replaces per-step [OK] block) |
| `standards/archive-plan.md` | `default:archive-plan` | Archive the completed plan |
| `standards/output-template.md` | — | Renderer specification for the five-block final output template (Step 4) |
| `standards/required-steps.md` | — | Canonical list of steps enforced by the `phase_steps_complete` handshake invariant |
| `standards/validation.md` | — | Configuration requirements, error scenarios |
| `standards/lessons-integration.md` | — | Conceptual guidance on lesson capture |

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/pr-template.md` | PR body format |

---

## Related

| Resource | Purpose |
|----------|---------|
| [references/workflow-overview.md](references/workflow-overview.md) | Visual diagrams: 6-Phase Model and Shipping Pipeline |
| `plan-marshall:dev-general-practices` | Bash safety rules, tool usage patterns |
| `plan-marshall:workflow-integration-git` | Commit, push workflow |
| `plan-marshall:tools-integration-ci` | PR operations, CI status |
| `plan-marshall:workflow-integration-github` | CI monitoring, review handling (GitHub) |
| `plan-marshall:workflow-integration-sonar` | Sonar quality gate |
| `plan-marshall:phase-5-execute` | Loop-back target for fix task execution |
| `plan-marshall:manage-lessons` | Lessons capture |

### Phase-boundary metric bookkeeping

Phase finalization has no "next phase" — it closes the plan. The fused
`manage-metrics phase-boundary` subcommand therefore does NOT apply at this
boundary. The closing sequence (`end-phase 6-finalize` → `enrich` →
`generate`) lives in `standards/record-metrics.md` and remains a three-call
sequence by design. The fused `phase-boundary` call is only used at
inter-phase transitions (`1-init → 2-refine` … `5-execute → 6-finalize`),
recorded by the orchestrator workflows.
