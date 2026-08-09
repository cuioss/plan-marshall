---
lane:
  class: core
  cost_size: M
name: phase-6-finalize
description: Complete plan execution with git workflow and PR management
user-invocable: false
mode: workflow
---

# Phase Finalize Skill

**Role**: Finalize phase skill. Handles shipping workflow (assert clean tree, push, PR) and plan completion. Under the unconditional per-deliverable commit model, every deliverable was already committed on the feature branch during phase-5-execute, so finalize produces NO plan-level commit — it asserts a clean tree and ships (push + PR). Verification tasks have already been executed within phase-5-execute.

**Key Pattern**: Shipping-focused execution. No verification steps—all quality checks run as verification tasks within phase-5-execute before reaching this phase. Per-deliverable commits live on the feature branch; `main` receives the squash at merge — the squash-merge convention is unchanged.

**Required steps declaration**: This skill opts in to the `phase_steps_complete` handshake invariant. The canonical list of steps that MUST be marked done on `status.metadata.phase_steps["6-finalize"]` before the phase transitions is maintained in [standards/required-steps.md](standards/required-steps.md). Each built-in step's standards document terminates with a `manage-status mark-step-done` call whose `--step` value matches an entry in that file.

## Enforcement

> **Shared lifecycle patterns**: See [phase-lifecycle.md](../ref-workflow-architecture/standards/phase-lifecycle.md) for entry protocol, completion protocol, and error handling convention.

**Execution mode**: Follow workflow steps sequentially, respecting config gates. Each config-gated step dispatches to a standards/ document.

**Required skill load** (before any operation):
```text
Skill: plan-marshall:persona-plan-marshall-agent
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
- Never invoke a build, CI, Sonar, or GitHub/GitLab script (`ci`, `pyproject_build`, `sonar`, `workflow-integration-*`) without an explicit routing flag. Forward `--plan-id {plan_id}` (preferred — auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir {worktree_path}` / `--project-dir {main_checkout}` (escape hatch / explicit override after worktree removal). The two flags are mutually exclusive. The executor is cwd-pass-through; routing must be explicit at every call site.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

Step-level exceptions — calls whose non-zero exit is itself the signal (e.g., `manage-files exists` returning `exists: false`, `manage-status get-worktree-path` returning an empty `worktree_path`) — are documented inline in the step that issues them.

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
| `session_id` | string | Yes | Current host-platform session id — forwarded to `default:record-metrics` for `manage-metrics enrich`, which hands it to the platform-runtime `metrics normalized-tokens` op to capture main-context token usage. Without it, the runtime op cannot locate the session and session tokens are lost from the final report. |

### How to obtain session_id

**session_id**: the platform-runtime `session capture` operation stores the session id in the plan's `status.json` at plan-init time. Read it back via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field session_id
```

Parse `value` from the TOON output. On `status: error` or empty `value`, the orchestrator's `session_id` resolver (in `plan-marshall/workflow/execution.md`) does NOT abort immediately — it first attempts exactly one `platform-runtime session capture --plan-id {plan_id}` retry and re-reads the metadata field. An absent `session_id` at finalize entry is therefore recoverable as long as the platform session is still live. Only when that single late capture also fails (`status: error` or `value` still empty) does the resolver abort finalize with a clear message — do **not** invent a filler value.

**token enrichment**: `manage-metrics enrich` never parses a session transcript itself — it forwards the `session_id` (and the plan's phase windows) to the platform-runtime `metrics normalized-tokens` op, which owns the entire transcript engine for the active target. On Claude the op walks the session transcript and returns the normalized per-phase token categories; on OpenCode (no transcript) it returns a `no-op` with `transcript_not_found`. `enrich` degrades gracefully on that `no-op` — it skips enrichment and the final report simply carries no transcript-sourced session tokens.

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
| `phase_6.steps` | list | Ordered list of bare step IDs to execute (e.g., `push`, `create-pr`, …). Authoritative. |

**Cross-phase config from `marshal.json`** (read in Step 2 alongside the manifest):

| Field | Type | Description |
|-------|------|-------------|
| `phase-6-finalize.max_iterations` | integer | Maximum finalize-verify loops (default: 3) |
| `phase-6-finalize.loop_back_without_asking` | bool | Symmetric counterpart to `phase-6-finalize.finalize_without_asking`. When `true`, a `loop_back` outcome from any phase-6-finalize step (FIX disposition, `pr-comment-overflow`, sonar-roundtrip FIX) auto-dispatches the execute pipeline inline and re-enters the finalize loop, capped by `max_iterations`. When `false` (default), the dispatcher halts and returns control to the user. Read at runtime via `manage-config plan phase-6-finalize get --field loop_back_without_asking`. See Step 3 § "Loop-back continuation" for the dispatch shape. |
| `phase-5-execute.commit_and_push` | bool | When `true` (default), the unconditional per-deliverable commits made in phase-5 are pushed and a PR is created. When `false`, the run is local-only — the manifest's `commit_push_disabled` pre-filter strips `push`, `pre-push-quality-gate`, and `pre-submission-self-review` so no push happens. |
| `phase-6-finalize.finalize_without_asking` | bool | Forward-direction auto-continuation: when `true`, after `5-execute → 6-finalize` transition the orchestrator dispatches `phase-6-finalize` inline rather than halting and prompting the user. Read at runtime via `manage-config plan phase-6-finalize get --field finalize_without_asking`. The reverse-direction symmetric counterpart is `phase-6-finalize.loop_back_without_asking`. |
| `phase-1-init.branch_strategy` | string | feature / direct |

**Per-step params from the plan-local manifest snapshot.** Step-owned params (`review_bot_buffer_seconds` under `plan-marshall:automatic-review`; `touched_file_cleanup` / `do_transition` / `ce_wait_timeout_seconds` under `default:sonar-roundtrip`; `pr_merge_strategy` / `final_merge_without_asking` / `auto_rebase_threshold` under `default:branch-cleanup`) are NOT flat `marshal.json` fields. The dispatcher resolves each step's params via a single one-stop `manage-execution-manifest step-params get --plan-id {plan_id} --phase 6-finalize --step-id {step_id}` call keyed by step id, reading the param object snapshotted into the plan-local manifest body at compose time (with per-plan overrides via `step-params set`). The owning step's standards/workflow doc performs that read at the point it needs the param; this skill does NOT read step params from `marshal.json`.

A step is active if and only if it appears in `manifest.phase_6.steps`. Absent steps are NEVER executed. The order of steps in the manifest list is the execution order. The `plan.phase-6-finalize.steps` field in `marshal.json` is the *candidate set* — the input list `phase-4-plan` Step 8b passes to `manage-execution-manifest compose --phase-6-steps`. The manifest's `phase_6.steps` is the *resolved per-plan instance* of that candidate set and is the only authority this skill consults at dispatch time. The candidate set drives dispatch transitively; this skill itself never reads `marshal.json` for step selection.

---

## Dispatched workflows vs inline steps

Every default + project finalize step registered in `plan.phase-6-finalize.steps` is classified as either **dispatched** (run under `Task: execution-context-{level}`) or **inline** (pure scripts / trivial orchestration that earn no envelope) — exactly one classification per step, with no count claim to drift against a growing registry. Every dispatched step resolves under the phase-scoped registry `manage-config effort resolve-target --phase phase-6-finalize [--role <subkey>]`. `ci-verify` is a deterministic inline classifier whose green pass-through marks the step done with ZERO dispatch and only red CI routes one taxonomy finding per failing check to `verification-feedback`; CI completion itself is a dispatcher-resolved precondition (`requires: [ci-complete]`), not a sibling step (see Step 3 § "Precondition resolution"). The full per-step dispatched/inline classification, the step→role map, and the rationale live in [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) — the single source of truth the Execute Step Pipeline dispatch branch consumes.

**Record-before-return binds every dispatched step body — built-in included.** A dispatched step's body MUST land its terminal `manage-status mark-step-done` call BEFORE it composes its return TOON, never as a trailing action after the payload is assembled; a `status: done` return is not a substitute for the record, because the item-5d completion guard reads `status.metadata.phase_steps`, not the return. The governing invariant is [`../ref-workflow-architecture/standards/agents.md`](../ref-workflow-architecture/standards/agents.md) § the record-before-return corollary, which binds every dispatched leaf. This paragraph is the reach-point for **built-in** (`default:`) dispatched steps, whose bodies live in `standards/{name}.md` / `workflow/{name}.md` and have no shared authoring contract of their own; **external** (`project:` / `bundle:skill`) dispatched steps reach the same invariant through [`standards/external-step-contract.md`](standards/external-step-contract.md) § "Required termination". Both partitions of the dispatched roster are therefore bound, and neither reach-point restates the invariant it points at.

## Step Types

Four step types are supported, distinguished by prefix notation:

| Type | Notation | Resolution |
|------|----------|------------|
| **built-in** | `default:` prefix (e.g., `default:push`) | Strip prefix, read `standards/{name}.md` and follow all steps |
| **project (dispatched)** | `project:` prefix classified DISPATCHED (e.g., `project:finalize-step-plugin-doctor`) | `Task: execution-context-{level}` with `workflow: {step's own SKILL.md notation}` — see the Execute Step Pipeline step's DISPATCHED-step dispatch branch |
| **project (inline)** | `project:` prefix classified INLINE (e.g., `project:finalize-step-deploy-target`) | `Skill: {notation}` with interface contract parameters |
| **skill** | fully-qualified `bundle:skill` (e.g., `pm-dev-java:java-post-pr`) | DISPATCHED → `Task: execution-context-{level}`; INLINE → `Skill: {notation}` with interface contract parameters, per the same classification |

**Type detection logic**:
- Starts with `default:` -> built-in type (strip prefix, validate against dispatch table)
- Starts with `project:` -> project type; further classified DISPATCHED vs INLINE per the "Dispatched workflows vs inline steps" section
- Contains `:` (other) -> fully-qualified skill type; classified DISPATCHED vs INLINE the same way

The dispatched-vs-inline classification (which project/skill steps dispatch under `Task: execution-context-{level}` vs load inline via `Skill:`) is owned by the "Dispatched workflows vs inline steps" section above — it is the single source of truth, and the "Interface Contract for External Steps" section's `Skill:` template applies only to INLINE external steps.

Each step declares an `order: <int>` value in its authoritative source — frontmatter on built-in standards docs (`standards/{name}.md`), frontmatter on project-local `SKILL.md` for `project:` steps, and the return-dict `order` field for extension-contributed skills. `marshall-steward` sorts the `steps` list by this value when writing it to `marshal.json`. This skill iterates the list as written and does NOT re-sort or validate `order` at runtime — the persisted order is the runtime order.

The materialized keyed-map step roster, each step's explicit `lane` (exclusion = `lane: off`; core / derived-state classes are immune to a weakening `off`), and the frontmatter-`order`-governed sequence — resolved through the single choke-point `_manifest_validation._sort_steps_by_frontmatter_order`, consumed by both the plan-local manifest composer and `manage-config steps-sort` — are the CURRENT (post-#895/#896/#898) model. The central lane / order / preset contract is [`extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md); this skill documents the roster and consumes the resolved order, it does not re-specify the lane/order authority. There is no compose-layer `order` field and no `run_at_all` boolean — a step is present iff it is in the manifest, and its position is its `order:` frontmatter.

### Built-in Step Dispatch Table

**This table is a restatement, not a source.** The authoritative built-in step set is each step doc's own frontmatter, discovered via `find_implementors('plan-marshall:extension-api/standards/ext-point-finalize-step')` and filtered to `source: built-in`; the table below routes exactly that set and must name each step's real doc path. Because the table is hand-maintained, the alignment is **pinned by a test rather than trusted**: `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` § `TestBuiltInStepDispatchTableMatchesDiscovery` asserts the row SET equals the discovered built-in set (both directions) and that every row's document path IS the discovered doc — so a row naming a doc that MOVED fails at quality-gate instead of silently at dispatch. Its sibling `TestDefaultPhase6StepsMatchesDiscovery` pins the same source's other restatement, `_manifest_core.DEFAULT_PHASE_6_STEPS`. When a built-in step is added, removed, or its doc relocated, update this table in the SAME change.

The compose-time step-resolution gate is the complementary guard, not a substitute: it fails loud with `unresolvable_step` for a built-in whose standards doc is MISSING, so a deleted doc can never reach dispatch. It says nothing about a row that points at a real but wrong document, which is precisely what the test above covers.

| Step Name | Standards Document | Description |
|-----------|-------------------|-------------|
| `default:finalize-step-sync-baseline` | `standards/finalize-step-sync-baseline.md` | Early baseline rebase — rebase the worktree feature branch onto `origin/{base_branch}` at the start of finalize so the downstream local gates and CI validate the actual to-be-landed tree (no force-push, no `ci wait` at this order) |
| `default:pre-push-quality-gate` | `standards/pre-push-quality-gate.md` | Inline last gate before push — `quality-gate` once per unique bundle derived from the live footprint by the `derive_gate_bundles` seam, then a whole-tree module-tests gate that escalates only on scoped-vs-whole-tree divergence risk |
| `default:pre-submission-self-review` | `workflow/pre-submission-self-review.md` | Pre-submission structural self-review (symmetric pairs, regex, wording, duplication, contract drift) |
| `default:finalize-step-simplify` | `standards/finalize-step-simplify.md` | Holistic post-implementation simplification sweep — collapse accidental complexity introduced across the plan's diff (dispatches under `--phase phase-6-finalize`, no `--role`) |
| `default:finalize-step-security-audit` | `standards/finalize-step-security-audit.md` | Proactive security-audit sweep — runs the shared five-stage engine over the plan footprint with each affected domain's `skills_by_profile.security` skills layered on; hardening edits are applied to the worktree and committed by the dispatcher's commit instrumentation after `done` (`persona: persona-security-expert`) |
| `default:push` | `standards/push.md` | Push the converged branch (pure barrier; the dispatcher's commit instrumentation owns all commits) |
| `default:create-pr` | `workflow/create-pr.md` | Create pull request |
| `default:ci-verify` | `standards/ci-verify.md` | Inline deterministic executor (`scripts/ci_verify.py`) — green CI marks the step done with zero dispatch; red CI classifies failures into the multi-failure-mode taxonomy, files one structured triage finding per failing check, and returns a per-producer needs-triage signal (`requires: [ci-complete]` in consume-failures mode) |
| `default:architecture-refresh` | `standards/architecture-refresh.md` | Refresh architecture descriptors (tier-0 deterministic discover + diff, tier-1 LLM re-enrichment) |
| `plan-marshall:automatic-review` | `../automatic-review/SKILL.md` | CI automated review — **FIND-only**: files PR comments via `github_pr fetch_findings`, then marks done; dispatches no triage of its own. Once both wait-region producers have filed, the dispatcher runs ONE unified triage over the union (see Step 3 item 7c below, `verification-feedback` `producer=finalize-feedback`; see [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) for the architectural flow) |
| `default:sonar-roundtrip` | `workflow/sonar-roundtrip.md` | Sonar analysis roundtrip — **FIND-only**: files new-code issues via `sonar fetch_findings`, then marks done; dispatches no triage of its own. Triage runs via the same dispatcher-owned unified pass (Step 3 item 7c, `producer=finalize-feedback`) |
| `default:lessons-capture` | `workflow/lessons-capture.md` | Record lessons learned |
| `default:adr-propose` | `workflow/adr-propose.md` | Propose ADRs from the plan's architectural decisions — advisory, dispatcher-gated on a decision-shape Signal Gate (see Step 3 § "Adr-propose Signal Gate") |
| `default:branch-cleanup` | `standards/branch-cleanup.md` | Branch cleanup — adapts to PR mode or local-only based on create-pr step presence |
| `default:finalize-step-preference-emitter` | `standards/finalize-step-preference-emitter.md` | Inline per-plan preference-learning sweep — aggregates recurring `(module, finding-class, disposition)` patterns in the just-finished plan and files the threshold-passing ones as owed durable architecture hints (post-merge-ordered, so it names the owed `architecture enrich` calls rather than writing them) |
| `default:record-metrics` | `standards/record-metrics.md` | Record final plan metrics before archive |
| `default:finalize-step-print-phase-breakdown` | `standards/finalize-step-print-phase-breakdown.md` | Optional override mode: capture the Phase Breakdown table from metrics.md so the renderer emits it in place of the per-step [OK] block |
| `default:archive-plan` | `standards/archive-plan.md` | Archive the completed plan |

### Interface Contract for External Steps

External steps split by the dispatched-vs-inline classification in the
"Dispatched workflows vs inline steps" section.

**INLINE external steps** (e.g., `project:finalize-step-deploy-target`,
`project:finalize-step-sync-plugin-cache`) load in the main context and receive
these parameters:

```text
Skill: {step_reference}
  Arguments: --plan-id {plan_id} --iteration {iteration} [--session-id {session_id}]
```

**DISPATCHED external steps** (e.g., `project:finalize-step-plugin-doctor`) do NOT use the `Skill:` template above —
they dispatch under `Task: execution-context-{level}` with the step's own SKILL.md
as the `workflow` prompt-body field. Their input contract is the 5-field
prompt-body shape (`name`, `plan_id`, `skills[]`, `workflow`, `WORKTREE`) plus any
workflow-specific runtime inputs (`--iteration`, `producer`, whitelisted
`--session-id`). See the Execute Step Pipeline step § "DISPATCHED project/skill step" for the
dispatch shape.

In both cases the step body can access the plan's context via manage-* scripts (references, status, config).

#### Session-id forwarding and required termination

`--session-id {session_id}` is forwarded ONLY to external steps on a per-step opt-in whitelist (currently just `plan-marshall:plan-retrospective`), and every external step MUST terminate with a `manage-status mark-step-done --phase 6-finalize --step {step_name} --outcome {done|skipped|failed} --display-detail "{≤80-char, no-trailing-period, ASCII, single-line summary}"` call — a missing `display_detail` surfaces the `<missing display_detail>` placeholder and forces a `[FAILED]` headline. The whitelist, the how-to-apply steps, the full mark-step-done template with per-argument MANDATORY annotations, and the `display_detail` constraint list live in [`standards/external-step-contract.md`](standards/external-step-contract.md). The orchestrator resolves `session_id` (see "How to obtain session_id" earlier in this file) and forwards it verbatim to whitelisted steps.

---

## Mutation-settling stage (settle → push once → wait)

The finalize pipeline is a **mutation-settling stage**: every LOCAL, HEAD-changing step settles BEFORE the single push, and the wait region runs AFTER it off one settled HEAD. The stages, by `order:`:

- **SETTLE (local HEAD-changing, `order < 10`)** — `finalize-step-sync-baseline` (3, rebase→HEAD), `pre-push-quality-gate` (5, gate), `project:finalize-step-plugin-doctor` / `pre-submission-self-review` / `finalize-step-simplify` / `finalize-step-security-audit` (fixes→HEAD), and `architecture-refresh` (9, derived-state — sorts LAST in the settle band so the descriptor refresh captures the code-mutating settle edits). Each mutating step's edits are committed on the feature branch by the dispatcher's commit instrumentation (Step 3 item 5f) before the barrier runs.
- **PUSH (`order: 10`)** — the single `default:push` barrier ships the fully-settled HEAD. There is exactly ONE push.
- **WAIT (post-push, `order > 10`)** — `create-pr`, `ci-verify`, `automatic-review`, `sonar-roundtrip` are the D4 **concurrent WAIT barrier** off that one settled HEAD (see § the wait-region narrative for the barrier mechanics — this section does not restate it). Post-push HEAD mutations that structurally REQUIRE the remote PR (era-stamp-fill's PR-number resolution, sonar/review fix application) are NOT pulled before the push — they are absorbed by the D4 bounded re-settle mutation-fixpoint. `adr-propose` (62) then runs before `branch-cleanup` (70) merges.
- **POST-RUN REVIEW (post-merge, `order > 70`)** — every step declaring `post_run_review: true` runs after the merge gate, because at least one input it reads is only determined at or after that gate (the merge outcome, the post-merge base-branch state, or the re-review barrier's bot comments and triage dispositions). Membership is the declared fact, never a list here — see [`../extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter" for the P1 ∧ P2 discriminator. Such a step writes no tracked source (`mutates_source: false` is mandatory for it, and the mutual exclusion falls out of P2), so the post-merge band mutates nothing and needs no push.

**Ordering authority.** The settle-before-push-before-wait sequence is NOT a compose-layer `order` field and NOT a `run_at_all` boolean — it is governed entirely by each step doc's `order:` frontmatter, resolved through the single choke-point `_manifest_validation._sort_steps_by_frontmatter_order` (consumed by BOTH the plan-local manifest composer AND `manage-config steps-sort`). To move a step between the settle stage and the wait region, edit its `order:` frontmatter (settle `< 10`, wait `> 10`); the composer and `steps-sort` re-materialize the roster and the ascending-order validator asserts the barrier holds. See the roster block above and [`extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md) for the lane/order contract.

## Wait-region: the concurrent barrier off one settled HEAD

The post-push wait region awaits three EXTERNAL-latency signals — CI checks, review-bot comments, and the Sonar compute-engine — that all run against the single HEAD the settle stage pushed. They were historically awaited **serially**: `ci-verify` blocked for green CI, THEN `automatic-review` blocked for the review buffer + comments, THEN `sonar-roundtrip` blocked for the CE. Because the three processes run **concurrently on the remote** the moment the push lands, serial awaiting paid `sum(signal)` wall-clock for work that completes in `max(signal)`.

The wait region is now **one concurrent barrier**: all three signals are polled off the one settled HEAD at once, and the barrier **proceeds per-signal** — as each signal reaches a terminal state, the pipeline advances past it independently, rather than blocking the other two behind the slowest. The three signals remain **three distinct materialized steps** — `default:ci-verify` (`lane: minimal`), `plan-marshall:automatic-review` (`lane: minimal`), and `default:sonar-roundtrip` (`lane: full`) — each keeping its own `lane` and `order:` frontmatter. The barrier is a *concurrency pattern over how those three steps' waits are awaited*; it does NOT merge, drop, or re-lane any step, and it adds no compose-layer grouping (see deliverable-4 § "Section partition").

**Per-signal ratchets are reused, not replaced.** Each arm awaits through its own existing ratchet: the CI arm through the p50-seeded terminal-state `ci wait` (the #849 ratchet `ci_complete_precondition` drives), the review arm through the completion-aware bot-comment poll (plan-17 #884 D2), and the Sonar arm through the CE wait. The barrier layers **coordination** over those independent waits; it introduces no competing wait subsystem.

**Coordinator verb.** The provider-agnostic per-signal-proceed / re-settle decision is computed by the router-level `ci barrier` verb (implemented in `tools-integration-ci/scripts/_ci_barrier.py`; canonical surface in [`tools-integration-ci/SKILL.md`](../tools-integration-ci/SKILL.md) § Canonical invocations). Given the one `--settled-head` and one `--signal NAME:STATE[:HEAD]` per barrier signal, it returns `barrier_status` ∈ `{complete, waiting, failed, re_settle}` plus the per-bucket signal lists (`proceed` / `pending` / `failed` / `affected`). `waiting` means keep awaiting the `pending` arms; `complete` means all three settled at the settled HEAD; `failed` means a signal terminally failed at that HEAD (route it through the existing per-step triage); `re_settle` means HEAD advanced past where a settled signal was observed and the `affected` arms must be re-entered.

**Bounded re-settle (mutation-fixpoint).** A finding can post AFTER the barrier is entered (a bot comments, or Sonar surfaces a new-code issue) — a check-then-act window. The mitigation is a **bounded re-settle**: apply the fix → commit + push (advancing HEAD) → re-enter the barrier for the **affected signals only** (the `ci barrier` `affected` set), NOT a full finalize replay (the settle-stage gates — quality-gate, plugin-doctor, simplify, security-audit — are NOT re-run). Because a push re-runs every arm that validates against HEAD, the affected set is the barrier's own signals, and a clean re-entry (no new finding lands) settles them all at the new HEAD. The common case therefore **converges in ≤1–2 iterations**: iteration 1 applies-and-pushes the fix, iteration 2 observes all arms settled at the new HEAD → `complete`. This is the check-then-act / TOCTOU mitigation menu applied to the wait region — see [`ref-code-quality/standards/code-organization.md`](../ref-code-quality/standards/code-organization.md).

The barrier poll runs off resident context via the `await-long-running` detach seam so the large orchestrator context is not held during the wall-clock wait — that routing is documented in § "Barrier-detach routing" immediately below, and does not change any step's `lane` or `order:`.

### Barrier-detach routing (off resident context)

The wait-region barrier is a long-running orchestrator-tier wait, so it is **detached** through the shared [`await-long-running`](../plan-marshall/workflow/await-long-running.md) seam (as the `finalize-barrier` consumer) rather than blocked on synchronously. Detaching keeps the poll **off resident context**: the large orchestrator context is not held resident across the CI/review/Sonar wall-clock wait — the seam backgrounds the per-signal arms and the orchestrator wakes only on a notification, reading the compact `ci barrier` decision TOON, never the raw poll flood.

**Wake-on-transition contract.** The seam wakes the orchestrator on ANY barrier signal's **state transition** — a signal reaching a terminal state — so the pipeline proceeds past that arm the moment it settles (per-signal-proceed), NOT only when all three settle. It also wakes on **budget exhaustion**. On each wake the orchestrator reads the `ci barrier` decision (`barrier_status` + the `proceed` / `pending` / `affected` buckets) and advances the settled arms while continuing to await the `pending` ones. A `re_settle` decision re-detaches only the `affected` arms against the new settled HEAD (the D4 bounded re-settle), never a full finalize replay.

**Synchronous fallback preserved.** When the background primitive is unavailable (a non-Claude runtime, or `run_in_background` not honoured), the seam degrades to `await-long-running` step (g): the barrier awaits each arm's wait **inline** at its resolved timeout — the pre-detach serial blocking behaviour — still correct, only resident. The Claude-specific wake primitive stays contained behind the seam.

This is a **routing/narrative change only**: the three WAIT steps (`default:ci-verify`, `plan-marshall:automatic-review`, `default:sonar-roundtrip`) keep their own `lane` and `order:` frontmatter, and no materialized step is added or removed. Detaching governs *where the poll runs* (off resident context), never *which steps run or how they are laned*.

## Operation: finalize

**Input**: `plan_id`

### Step 0: Resolve Worktree and Main Checkout Paths

**This step runs before any other finalize step** and makes `{worktree_path}` and `{main_checkout}` available to every subsequent step and standards document. All git Bash calls and all build/CI/sonar/github/gitlab script invocations in the finalize workflow depend on these two values — no standards document may resolve them independently.

Read the plan status and extract the worktree path from metadata:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
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

#### Return-to-main ordering

Per ADR-002, the orchestrator enters finalize still cwd-pinned to the worktree (the pin established at phase-5 entry by `prepare_execute.py` — see `plan-marshall/workflow/execution.md` § "Orchestrator cwd-pinning (phase-5+)"). The finalize phase ends that pin, but the move-back and the worktree removal are SEQUENCED, not simultaneous:

1. **Move-back while the worktree is still present.** The atomic move-back script (deliverable 5) folds the plan's own global logs into the plan directory, moves the plan directory back to main, and runs under the merge lock — all while the worktree still exists:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-git:integrate_into_main integrate \
     --plan-id {plan_id}
   ```

   `integrate_into_main.py` resolves its SOURCE (the worktree-resident plan dir, via `manage-status get-worktree-path`) and its DESTINATION (main's plan dir, via the sanctioned main-anchored resolver) **cwd-independently**, so it is correct whether invoked before or after the cwd return — it does NOT require any particular working directory. It also does NOT change the caller's working directory, does NOT remove the worktree, and does NOT regenerate the executor. On-main executor regeneration is performed later by the project-level `project:finalize-step-sync-plugin-cache` step (meta-project-only) after the cache sync — the executor stays a per-tree derived artifact (ADR-002), never file-moved onto main.

2. **Return cwd to main.** After the move-back returns, the orchestrator returns its own working directory to `{main_checkout}`. The plan directory and executor now live on main again, so the uniform cwd rule resolves them on main from this point. Because `integrate_into_main` is cwd-independent, the cwd return is not a precondition of the move-back — the only hard ordering constraint is the worktree-removal sequencing in step 3.

3. **Resume the remaining finalize steps, then remove the worktree.** With cwd back on main, the orchestrator resumes the remaining finalize pipeline; the worktree is removed last, by the `branch-cleanup` step. Removing the worktree before the move-back completes would strand the authoritative plan-state copy, so the move-back MUST precede worktree removal. That sequencing — move-back → resume → worktree removal — is the load-bearing constraint; the cwd return is independent of it.

The worktree-lifecycle and dispatch contract is the central standard at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md`; this section documents only the finalize-side return-to-main ordering and does not re-inline that contract.

### Step 1: Check Q-Gate Findings and Log Start

#### Log Phase Start

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Starting finalize phase"
```

#### Query Unresolved Findings

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --phase 6-finalize --resolution pending
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

Extract `phase_6.steps` — the ordered list of step IDs (e.g., `push`, `create-pr`, `plan-marshall:automatic-review`, …) to execute. Step IDs in the manifest are **bare names** (no `default:` prefix). The dispatcher in Step 3 prepends `default:` when looking up built-in steps, but otherwise iterates the list verbatim.

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

Read the flat config blocks for `max_iterations`, `commit_and_push`, and `branch_strategy` from `marshal.json`. The `review_bot_buffer_seconds` param is NOT flat — it is a step-owned param of `plan-marshall:automatic-review`, resolved at the point of use via the one-stop `manage-execution-manifest step-params get --phase 6-finalize --step-id plan-marshall:automatic-review` call (see the per-step-params convention above and `../automatic-review/SKILL.md`). **Do not** read the `steps` field from `marshal.json` here — that field is the candidate set consumed by `phase-4-plan` Step 8b, not by this skill. The manifest's `phase_6.steps` list is the only valid source for runtime dispatch.

Also read references context for branch and issue information:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

**After reading configuration**, log the finalize strategy decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize) Finalize strategy: commit_and_push={commit_and_push}, manifest_steps={steps_count}, branch={branch_strategy}"
```

### Step 3: Execute Step Pipeline (Manifest-Driven, Resumable, Timeout-Wrapped)

Iterate over `manifest.phase_6.steps` (read in Step 2). The list is the manifest's authoritative ordering — neither this skill nor any standards document re-orders, filters, or skip-conditional any step.

#### Plugin cache freshness

In meta-projects that own marketplace bundles (notably the
plan-marshall repo itself), the project-local Phase 6 ordering pairs
`project:finalize-step-deploy-target` (order 81) with
`project:finalize-step-sync-plugin-cache` (order 85), placing both
**after** `default:branch-cleanup`, against the main checkout
post-merge. The cache mirrors the `target/claude/` content from the
merged source tree, so the next session-boot re-derivation reads the
same authoritative tree the dispatcher just wrote to. On-main executor
regeneration is performed by the project-level
`project:finalize-step-sync-plugin-cache` step (order 85) immediately
after the cache sync, in both worktree and no-worktree finalize flows;
`integrate_into_main` performs the move-back only and does NOT regenerate
the executor.

Meta-project finalize agents dispatched between `create-pr` and
`branch-cleanup` see pre-plan skill bodies in the host cache (the cache
sync now runs later, post-merge). This is acceptable — see the
`what_this_gives_up` analysis in the originating lesson for the
deliberate-trade-off rationale: tool calls resolve against worktree
absolute paths and the executor reads notation paths fresh per
subprocess, so only `Skill:` dispatches consume the in-process
registry, and the meta-project case is explicitly accepted.

Consumer projects do not own bundle sources, so they do not register
either step. Their finalize dispatches load whatever the host plugin
cache holds, which is exactly the published bundle definitions.

**Resumable re-entry semantics**: Before dispatching each step, read the current step record from `status.metadata.phase_steps["6-finalize"]`. If the step is already marked `done`, skip dispatch entirely (no re-run, no log noise — the previous run completed it). If the step is marked `failed`, retry it from scratch. If the step has no record (or any other outcome), dispatch it as a fresh run. This makes finalize safe to re-enter after a partial run, a crash, or an explicit retry — completed steps stay completed, failed steps get exactly one retry per invocation.

**Precondition resolution**: before dispatching any step in the FOR loop, parse the step's frontmatter `requires:` list (if present) and resolve each entry against its mapped resolver. The only precondition currently defined is `ci-complete`, mapped to the dispatcher-internal helper `scripts/ci_complete_precondition.py` (notation `plan-marshall:phase-6-finalize:ci_complete_precondition`). The resolver is invoked inline through the executor proxy (no Task agent dispatch — the helper clamps its inner `ci wait --timeout` so the outer subprocess call stays strictly below the host platform's per-call Bash ceiling, and past that bound returns a structured `deadline_exceeded` envelope for the dispatcher to re-poll on re-entry rather than being killed mid-call).

The resolver's **resolution mode** is selected per consumer step. Two dimensions govern it: the `--signal-arm` (which barrier arm the FIND gates on) and, for the `ci` arm only, the `--mode` flag (`strict` | `consume-failures`). The dispatcher MUST pass the resolution below per consumer step — it depends on which consumer the precondition is being resolved for, NOT on the resolver itself:

| Consumer step | Resolution | Why |
|---------------|------------|------|
| `default:ci-verify` | `--signal-arm ci --mode consume-failures` (global `ci-complete`) | The step's whole purpose is to classify CI failures into the multi-failure-mode taxonomy and emit one structured finding per failing check. `consume-failures` threads `wait_failed` through to the body rather than short-circuiting, so the classify → file-findings → verification-feedback → loop_back machinery stays reachable on red CI. Unchanged. |
| `plan-marshall:automatic-review` | `--signal-arm review` (per-signal FIND gate) | Gate the comment FIND on the **review arm's own terminal state**, not global CI colour. A terminal (`settled`\|`failed`) arm proceeds to FIND; a red CI unrelated to the review signal no longer skips the comment fetch. |
| `default:sonar-roundtrip` | `--signal-arm sonar` (per-signal FIND gate) | Gate the Sonar FIND on the **sonar arm's own terminal state**. A `failed` sonar arm STILL proceeds to FIND — a red Sonar gate is exactly when its new-code findings exist (the TokenSheriff-572 deadlock fix). |
| _Future consumers_ | Default to `--signal-arm ci --mode strict` unless the consumer's body explicitly handles a per-signal (`arm_proceed`/`arm_pending`) or `consume-failures` envelope. |

The dispatcher resolves the value by mapping the consumer step id (`step.name` from frontmatter) to the table above. When a step declares `requires: [ci-complete]` but does not appear in the table, the default is `--signal-arm ci --mode strict`.

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_complete_precondition \
  resolve --plan-id {plan_id} --worktree-path {worktree_path} --pr-number {pr_number} \
  [--signal-arm {ci|review|sonar}] [--mode {strict|consume-failures}] [--timeout TIMEOUT]
```

The helper returns a TOON envelope whose shape depends on the resolution mode. For the **`ci` arm** (`--signal-arm ci` / absent) it returns `status` (`satisfied`\|`wait_succeeded`\|`wait_failed`), `head_sha`, `ci_final_status`, and (on `wait_failed`) `failing_checks`, `wait_outcome`, and `mode` (the value passed in). For a **per-signal producer arm** (`--signal-arm review|sonar`) it returns `status` (`arm_proceed`\|`arm_pending`), `signal_arm`, `arm_state` (`settled`\|`failed`\|`pending`), `head_sha`, and `ci_final_status`. The underlying `ci wait` envelope partitions GitHub check conclusions per the canonical table (`success | skipped | neutral` → non-failing; `failure | timed_out | cancelled | action_required | stale` → failing; `null | in_progress | queued` → wait); the previous `mixed` outcome is no longer returned by any github_ops function.

**Ci-arm outcome mapping** (`--signal-arm ci`, consumed by `default:ci-verify`):

| Resolver `status` | `ci_final_status` | `--mode` | Dispatcher action |
|-------------------|--------------------|----------|--------------------|
| `satisfied` | `success` | _any_ | Cache hit — proceed to dispatch the consumer step normally. |
| `wait_succeeded` | `success` | _any_ | Cache miss → fresh `ci wait` returned success — proceed to dispatch. |
| `wait_failed` | `failure` | `strict` | CI ran to completion and at least one check is in the failing partition. SKIP the consumer step's body and mark the step's outcome `failed` via `manage-status mark-step-done … --outcome failed --display-detail "ci_failure (precondition): {failing_check_names}"`. The `failing_checks[]` list is forwarded into the `display_detail` so the work-log line names the specific checks that drove the verdict rather than the opaque "mixed" phrasing the pre-fix code emitted. |
| `wait_failed` | `timeout` | `strict` | `ci wait` exhausted its `--timeout` budget; `wait_outcome: deadline_exceeded` and `failing_checks[]` enumerates the still-running checks at the deadline. Same skip-and-mark action as `failure`; downstream consumers route this to `ci-verify-timeout`. |
| `wait_failed` | `no_checks` | `strict` | CI never produced any checks (`final_status: none` from `ci wait`). Distinct from real failure so the dispatcher can surface "no CI configured for this branch" rather than "CI ran red". Same skip-and-mark action; downstream consumers route this to `ci-verify-missing`. |
| `wait_failed` | `failure` \| `timeout` \| `no_checks` | `consume-failures` | Do NOT skip the consumer step. Thread `failing_checks[]`, `wait_outcome`, and `ci_final_status` into the consumer step's runtime inputs and run it normally; the consumer (currently only `default:ci-verify`, an inline deterministic script) classifies the failures into structured findings and returns a per-producer needs-triage signal. The structured-finding emission below STILL fires so the precondition decision remains audit-traceable; the difference vs `strict` is purely "skip step" → "run the deterministic classifier with the envelope". |

**Per-signal arm outcome mapping** (`--signal-arm review|sonar`, consumed by `plan-marshall:automatic-review` / `default:sonar-roundtrip`):

| Resolver `status` | `arm_state` | Dispatcher action |
|-------------------|-------------|-------------------|
| `arm_proceed` | `settled` | The arm settled cleanly (CI green) — dispatch the consumer step's FIND body normally. |
| `arm_proceed` | `failed` | The arm reached a terminal-but-red state — STILL dispatch the FIND body. A red gate is exactly when that producer's findings exist; the step FINDs and files them for the unified triage. Do NOT skip and do NOT mark the step `failed`. |
| `arm_pending` | `pending` | The underlying `ci wait` did not reach a terminal state within the budget (`ci_final_status: timeout`) — the arm has not settled. SKIP the consumer step this round WITHOUT marking it `failed` and WITHOUT emitting a finding; leave the step record absent so the resumable re-entry check re-fires it on the next finalize entry (the arm re-polls against the same HEAD). |

The per-signal path emits NO structured `triage` finding — a red arm PROCEEDS to FIND (its findings are filed by the FIND body, not lost), and a pending arm simply re-polls on re-entry, so there is no skip-verdict to audit. The structured finding emission below is therefore ci-arm-only.

**Structured finding emission on `wait_failed`** (ci arm only): in addition to the `mark-step-done … --outcome failed --display-detail "ci_failure (precondition): {failing_check_names}"` call above, the dispatcher MUST also persist a structured `triage` finding so the precondition decision survives outside the work-log. Emit exactly one finding per `wait_failed` resolution (NOT one per failing check — the failing-check enumeration lives in the message body). Invoke immediately after the `mark-step-done … --outcome failed` call:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type triage --severity warning \
  --title "CI failure (precondition) at HEAD {head_sha}" \
  --component "plan-marshall:phase-6-finalize" \
  --detail "ci_failure (precondition) at HEAD {head_sha}: failing=[{comma-joined failing check names}] / reason={failure|timeout|no_checks}" \
  --file-path "marketplace/bundles/plan-marshall/skills/workflow-integration-{github|gitlab}/scripts/{github|gitlab}_ops.py"
```

Field-by-field:

- `--type triage` — the precondition decision is a triage event (the operator decides between retry / suppress / accept / taken_into_account between finalize boundaries). Re-using the existing `triage` finding-type keeps the 14-type taxonomy stable; no new type is introduced.
- `--title "..."` — a one-line summary anchored to the failing HEAD; `add` requires it. Substitute `{head_sha}` from the resolver's return envelope.
- `--severity warning` — a CI failure that blocks the dispatcher is not itself a code defect; the underlying failing checks are the defect. `warning` matches the `[WARNING]` work-log convention this finding complements.
- `--component "plan-marshall:phase-6-finalize"` — the precondition resolver belongs to phase-6-finalize even though it consults `workflow-integration-{github,gitlab}`.
- `--detail "..."` — substitute `{head_sha}` from the resolver's return envelope, `{comma-joined failing check names}` from `failing_checks[].name` (use the empty string when `failing_checks` is empty; this occurs, for example, when `ci_final_status` is `no_checks`), and `{failure|timeout|no_checks}` from the `ci_final_status` value. The detail body carries enough context for `manage-findings list --type triage` to reproduce the verdict without re-fetching CI.
- `--file-path` — resolve to the provider script that produced the verdict: `github_ops.py` when the active CI integration is GitHub, `gitlab_ops.py` when GitLab. The dispatcher already knows the active provider via the `tools-integration-ci` abstraction.

The finding is filed as `triage`, which is **not** in the hardcoded ACTIONABLE blocking set (`build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `qgate`, `pr-comment`), so it does not gate the phase boundary. The ci_failure precondition already blocks the consumer step (the step records `failed` outcome and the dispatcher honours `failed_outcome_strategy`); having the finding also block the transition would double-block it and prevent the operator from explicitly resolving the finding as `accepted` between runs. The finding surfaces in retrospectives via `manage-findings list --type triage`; the blocking invariant does not need to know about it.

This step fires ONLY on `wait_failed`. `satisfied` and `wait_succeeded` resolutions emit no finding (CI passed — nothing to triage).

**Cache lifecycle**: The helper persists successful outcomes to `.plan/local/plans/{plan_id}/work/ci-precondition-cache.toon`, keyed by the current `git -C {worktree_path} rev-parse HEAD` SHA. The cache is alive for one dispatcher iteration; a loop-back commit that advances HEAD invalidates the entry implicitly (the next resolve sees a fresh SHA, the stored SHA no longer matches, and the resolver re-polls CI against the new tree). Failed outcomes are NOT cached — re-entry always re-polls so a transient CI failure resolves on the next attempt. Multiple consumer steps in the same dispatcher pass share the cache: the first `requires: [ci-complete]` lookup runs the wait, and subsequent lookups at the same HEAD return `satisfied` without re-polling.

The precondition resolver is dispatcher-internal — it produces no `phase_steps["6-finalize"]` record of its own (the precondition is not itself a finalize step). The dispatcher bears responsibility for the `wait_failed → ci_failure (precondition)` outcome mapping on the consumer step. Consumer step bodies (under `workflow/`) MUST declare `requires: [ci-complete]` in their YAML frontmatter to opt into the precondition; absent the declaration, the dispatcher proceeds directly to the step body and does not invoke the resolver.

**Commit instrumentation contract**: the dispatcher owns every commit a finalize step's edits produce. A step states whether it mutates source via the `mutates_source: true|false` frontmatter fact on its authoritative doc (the `standards/{name}.md` or `workflow/{name}.md` that declares the step's `order:`). After a `mutates_source: true` step records its terminal `done`/`skipped` outcome, the dispatcher runs `git -C {worktree_path} status --porcelain`; if non-empty, it commits the changes on the feature branch via `Skill: workflow-integration-git` Commit Changes (`push: false`), using the step's returned `commit_message` field, falling back to `chore(finalize): apply {step_id} changes`. Read-only (`mutates_source: false`) steps are never instrumented. The per-step instrumentation runs at item 5f of the FOR loop (see below). Every mutating step's output is committed before the dispatcher advances, so a mutating step can never leave uncommitted edits that a later step silently drops; the correct ordering — push only once the mutating quality steps have converged — falls out of plain `order:` values with no special placement invariant.

**Post-rebase step-doc re-resolution contract**: a step states whether a successful run advances `main` via the `advances_main_via_rebase: true|false` frontmatter fact on its authoritative doc (a sibling of `mutates_source`, declared by `finalize-step-sync-baseline` at `order: 3` and `branch-cleanup` at `order: 70` — the two steps that rebase the feature branch onto the freshly-fetched `origin/{base_branch}` tip). After a step whose authoritative doc declares `advances_main_via_rebase: true` records a terminal outcome AND actually advanced `main` (a **non-noop rebase** — the step's own return distinguishes a real replay from an `action: noop`; a noop advanced nothing and arms nothing), the dispatcher MUST, for every **subsequent** step in the FOR loop, re-read that step's authoritative `standards/{name}.md` / `workflow/{name}.md` doc **from the just-rebased `{worktree_path}` at the point of dispatch** rather than trusting the copy loaded into context at session start. The session-start context copy predates the rebase; the worktree now holds the post-rebase tree, and the two can disagree.

The dispatcher MUST additionally treat a subsequent `workflow_not_found` (or a missing dispatch target / unresolved standards path) as the **FIRST-hypothesis signal of post-rebase version skew**, not as proof the doc is genuinely absent: before concluding the step is unrunnable, re-resolve the target from the just-rebased `{worktree_path}` (re-read the standards/workflow doc at its worktree path, re-derive the dispatch target) and only surface a genuine "missing" error when the worktree copy is also absent.

The version-skew failure mode this contract closes is behavioural: between session start and the rebase, a PR that landed on `origin/{base_branch}` can have converted a step's dispatched `workflow/` doc into an inline executor (removing the `workflow` target the session-start copy still names), or moved/renamed the step's authoritative doc. After the rebase folds that upstream change into the worktree, a dispatcher that trusted the stale session-start copy would dispatch a `workflow` that no longer exists (→ `workflow_not_found`) or execute a superseded step body; re-reading from the just-rebased worktree at dispatch time resolves the current shape instead.

**Special case — HEAD-dependent steps**: a step is **head-dependent** iff its authoritative doc declares `head_dependent: true` in frontmatter — a sibling of `mutates_source`, governed by the discriminator *"would this verdict change if HEAD changed?"*. The contract, the discriminator's exact scoping, and the per-step vs whole-set consumption rule live in [`../extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter". **This sentence is the single authoritative statement of head-dependence in this document — every other site below cross-references it, and none restates the membership or its size.** Two shapes qualify: a step that records a pass/fail verdict over the live worktree tree or over the remote state of that tree (local quality gates, structural-lint gates, diff reviews, and PR-comment / Sonar / CI verdicts), and a settle-stage step whose edits land directly in the worktree (the dispatcher's commit instrumentation — not a self-commit — commits those edits, advancing HEAD). A step matching **neither** shape — one that records *an action performed* and leaves no edits of its own in the worktree — has no verdict to go stale and is not head-dependent. The exclusion applies only to steps outside both shapes: a settle-stage editing step matches shape 2 and IS head-dependent even though its record describes an action, because a later HEAD advance means its edits were computed against a superseded tree. The general rule above is augmented for a head-dependent step with a worktree-HEAD comparison so a loop-back commit (produced when the dispatcher-owned unified triage — Step 3 item 7c, `producer=finalize-feedback` — opens a fix task off `plan-marshall:automatic-review`'s or `sonar-roundtrip`'s filed findings) re-fires each gate against the newer code instead of skipping it on a stale `done` record:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — gate already validated this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD is no longer the SHA the verdict was computed against) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE **and report the prior verdict UNVERIFIED** (see below) — a record with no SHA was never anchored to a tree |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| `outcome == loop_back` | n/a | RE-FIRE (treat as no record — same as the general rule for loop_back) |
| no record OR any other value | n/a | DISPATCH (unchanged — same as the general rule) |

**A head-dependent verdict is never left standing as green for a HEAD it was not computed against.** That is the governing rule the table encodes, and the two RE-FIRE rows are its two halves: a superseded SHA re-fires, and an absent SHA re-fires AND is reported UNVERIFIED. On the absent-SHA row the dispatcher MUST log the prior verdict as unverified rather than discarding it silently, so a `done` record that was never anchored to a SHA stays visibly distinguishable from one that was genuinely validated and later superseded — the two are different facts, and collapsing them hides which gate never ran at all.

The `!= HEAD` comparison covers **all three supersession mechanisms in scope**: a loop-back commit, a force-push, and a rebase. Each one replaces the SHA the verdict was computed against, so a plain SHA inequality is sufficient for all three — no separate force-push detector and no rebase detector is introduced. (A rebase additionally arms the post-rebase step-doc re-resolution contract above; that is a different obligation on the same event, not a second membership test.)

The comparison consults HEAD-advance only — there is no dirty-tree re-fire branch. The dispatcher's commit instrumentation (item 5f) commits every `mutates_source: true` step's output before the dispatcher advances, so no head-dependent step can leave an uncommitted tree at re-entry. A dirty tree at any re-entry indicates an upstream contract violation rather than a re-fire trigger; every head-dependent step follows the HEAD-only table.

Membership is **declared, never listed** — see the authoritative statement above. Each head-dependent step MUST persist `head_at_completion` on its terminal `--outcome done` `mark-step-done` call so the comparison above is meaningful, and each step's own authoritative doc carries the per-step instruction for capturing `git rev-parse HEAD` immediately before the `mark-step-done` invocation and forwarding it via `--head-at-completion {sha}`. Branches that mark `loop_back` or `failed` do not need to persist the SHA — the dispatcher's general resumability handling for those outcomes does not consult it. CI completion is a separate dispatcher-resolved precondition (`requires: [ci-complete]`) — its cache key is the same `git rev-parse HEAD` SHA, so the same HEAD-advance signal that invalidates a stale `done` record also invalidates the precondition cache.

The `push` step is a pure push barrier and is deliberately NOT head-dependent (its doc declares no `head_dependent` fact): its skip/re-fire decision at re-entry is **parity-driven, not done-record-driven** — the item-1 re-entry check consults `branch-sync-state` (remote-comparison: `ahead`/`no_remote` → re-fire, `synced` → skip) instead of trusting a recorded `done`. The dispatcher additionally re-invokes it explicitly after a post-PR `mutates_source` step commits (item 5f § "Post-PR re-push") as the fast path. The freshness precondition that validates *that a `verify` was actually performed against this version of the code* (`pre-commit-verify-freshness`, see `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness") is retained on the `push` step itself — see `standards/push.md` § "Freshness precondition".

Resolve the comparison HEAD inside the dispatcher block at the moment of the per-step check:

```bash
git -C {worktree_path} rev-parse HEAD
```

Do NOT cache the live HEAD across loop iterations — read it fresh per step so a step that advances HEAD mid-loop (e.g., a commit the dispatcher's instrumentation produced for a loop-back fix) is observed correctly by every later step's check. All other finalize steps keep the general rule above verbatim; this special case applies only to steps declaring `head_dependent: true`.

**Per-agent timeout wrapper**: Every Task agent dispatch in this loop runs under a per-agent timeout budget. If the dispatch does not return inside the budget, the wrapper logs an ERROR, marks the step `failed` via `manage-status mark-step-done`, and continues with the next step in the list (no abort, no re-throw). Inline-only steps are not timeout-wrapped because they execute in the main context where the host platform already manages call timeouts. Budgets:

| Step | Budget | Rationale |
|------|--------|-----------|
| `default:sonar-roundtrip` | 15 min (900s) | Full Sonar gate roundtrip plus optional fix-task creation |
| `plan-marshall:automatic-review` | 15 min (900s) | CI wait + review-bot buffer + comment triage |
| `default:lessons-capture` | 5 min (300s) | Bounded `manage-lessons add` + Write workflow |
| `default:adr-propose` | 5 min (300s) | Bounded `manage-adr create` + Write workflow; advisory, never blocks |
| All other steps | no explicit budget | Fall under the host platform's default per-call ceiling |

For each step reference:

**Agent-suitable built-in steps** (self-contained, no user interaction) — each dispatches to `plan-marshall:execution-context-{level}` with the role-resolved workflow doc:

| Step reference | Resolver lookup | Workflow doc |
|----------------|-----------------|--------------|
| `default:create-pr` | `--phase phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/create-pr.md` |
| `default:lessons-capture` | `--phase phase-6-finalize --role post-run-review` (derived — declares `post_run_review: true`) | `plan-marshall:phase-6-finalize/workflow/lessons-capture.md` |
| `default:adr-propose` | `--phase phase-6-finalize` (no `--role`; tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/adr-propose.md` |
| `plan-marshall:automatic-review` | `--phase phase-6-finalize` (FIND-only; tracks `phase-6-finalize.default`) | `plan-marshall:automatic-review/SKILL.md` |
| `default:sonar-roundtrip` | `--phase phase-6-finalize` (FIND-only; tracks `phase-6-finalize.default`) | `plan-marshall:phase-6-finalize/workflow/sonar-roundtrip.md` |

**The `post-run-review` sub-key is DERIVED, not listed.** A dispatched step resolves under `--role post-run-review` **iff** its own authoritative doc declares `post_run_review: true`; every other dispatched step resolves under `phase-6-finalize.default`. Read the ONE step's fact at the point of dispatch — a per-step membership test, never a whole-set materialisation (see [`../extension-api/standards/ext-point-finalize-step.md`](../extension-api/standards/ext-point-finalize-step.md) § "Implementor Frontmatter"). Deriving the sub-key is what keeps the role key and the post-merge ordering obligation on ONE source: a step cannot be ordered as a post-run review and dispatched as something else, or vice versa. `default:adr-propose` is the discriminator's one near-miss and is recorded here so its lookup is not read as an oversight — it looks back at the plan's history (P1) but the decisions it records are settled at outline/execute time, not at or after the merge gate (P2 fails), so it is NOT a `post_run_review` member and tracks `phase-6-finalize.default`.

`plan-marshall:automatic-review` and `sonar-roundtrip` are the two wait-region producers, each **FIND-only**: gated on its own `_ci_barrier` arm (the per-signal precondition — `review` / `sonar` arm respectively), the step fetches its provider's feedback and files `pr-comment` / `sonar-issue` findings to the store, then marks done. Neither step dispatches its own triage any more. The per-finding LLM triage runs ONCE at the dispatcher level as the **Wait-region unified triage** (§ item 7c below), a single `verification-feedback` dispatch with `producer=finalize-feedback` over the union of both producers' pending findings. The outer FIND wrappers resolve under `phase-6-finalize.default` since each body is now pure script execution (fetch + file), no sub-dispatch.

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

**The emit and the spawn are ONE indivisible pair.** The `[DISPATCH]` write above and the `Task:` spawn below are two halves of a single action, not an instruction followed by an optional adjacent one — the same pairing item 5c states for its metrics row. Spawning the step without having written the line is a **contract violation**, not a cosmetic omission: the work-log then carries no record that the dispatch happened, so the dispatch-audit chain cannot attribute the step's cost, its target, or its role. Never emit the line after the spawn, and never skip it because the dispatch "obviously" happened.

Dispatch:

```text
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

**Inline-only built-in steps** — membership is every step classified under [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) § "Inline steps", the single source of truth; that roster also carries each step's own inline rationale (user interaction, sequential dependency, or a bounded polling primitive that fits comfortably under the host platform's per-call Bash ceiling). Do NOT re-list the membership here. The notes below add only the dispatcher-local sequencing detail the roster does not carry:
- `record-metrics` is the last token-accounting step — it runs after all token-consuming steps and before the read-only `print-phase-breakdown`/`archive-plan` tail, on the still-live plan directory.
- `archive-plan` must be last — it moves plan files.
- `push` is a pure push barrier and is NOT HEAD-dependent; its re-entry skip/re-fire decision is parity-driven via `branch-sync-state`, and the dispatcher also re-invokes it explicitly after a post-PR `mutates_source` step commits.
- `architecture-refresh` extracts `origin/main`'s committed `.plan/project-architecture/` tree as the pre-baseline.

Per-step agent `<usage>` totals are persisted on disk by `manage-metrics accumulate-agent-usage` (called from step 5b below). The on-disk file `.plan/plans/{plan_id}/work/metrics-accumulator-6-finalize.toon` survives context compaction and is read by `default:record-metrics` at `end-phase` time. Do NOT maintain a parallel tally in model context — the on-disk file is authoritative.

**Read the persisted `loop_back_iteration` count BEFORE entering the FOR loop** (i.e., here, at the start of Step 3 — outside the loop body). The count lives in `status.metadata.loop_back_iteration`, so it survives FOR-loop re-entries from the loop-back continuation hook (step 7b below), phase re-entries, session restarts, AND the halt-and-prompt cycle of the default `loop_back_without_asking: false` configuration. That durability is what makes the `max_iterations` ceiling enforceable across the plan's whole review chain rather than across one uninterrupted dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field loop_back_iteration
```

An absent field reads as `0`. Item 7b re-reads the persisted value at its admission gate and writes the incremented value back on every admitted iteration, so this read is the loop's starting view, never the authority — do NOT carry a model-context counter forward as a substitute for the re-read.

```text
loop_back_iteration = <status.metadata.loop_back_iteration, or 0 when absent>   # re-read and re-written at the item-7b admission gate

FOR each step_id in manifest.phase_6.steps:
  # Resolve full step reference. Manifest entries may be:
  #   - bare names (e.g. `push`) — built-in, prepend `default:`
  #   - already-prefixed (`default:foo`, `project:bar`, `bundle:skill`) — use verbatim
  # The composer preserves `project:` / `bundle:skill` prefixes from marshal.json;
  # only `default:` may be stripped. So presence of `:` in step_id => external step.
  IF step_id contains ':':
      step_ref = step_id                 # external step (`project:` / `bundle:skill`) — preserve verbatim
  ELSE:
      step_ref = "default:" + step_id    # built-in step — prepend `default:` prefix

  1. Resumable re-entry check:
     Read status.metadata.phase_steps["6-finalize"][step_id]:
       - IF the step's authoritative doc declares head_dependent: true (resolve this ONE step's
         own fact — a membership test, not a whole-set materialisation; see "HEAD-dependent step set"
         note below):
           Resolve the live worktree HEAD via `git -C {worktree_path} rev-parse HEAD`.
           Read this fresh per iteration; do NOT cache across the loop.
             - IF outcome == "done" AND head_at_completion == live HEAD: SKIP this step
             - IF outcome == "done" AND head_at_completion != live HEAD: RE-FIRE (treat as no record — dispatch as fresh run)
             - IF outcome == "done" AND head_at_completion is absent: RE-FIRE and report the prior
               verdict UNVERIFIED (a record with no SHA was never anchored to a tree; dispatch as fresh run)
             - IF outcome == "failed": RETRY (proceed to dispatch as fresh run)
             - IF outcome == "loop_back": RE-FIRE (treat as no record — dispatch as fresh run)
             - IF no record OR any other value: dispatch normally
       - ELSE IF step_id == "push" (parity-driven barrier re-entry):
           - IF outcome == "done": invoke the remote-parity probe
             `git-workflow branch-sync-state --plan-id {plan_id}`
             (see `workflow-integration-git` Canonical invocations → `branch-sync-state`) and branch on `state`:
               - `state == "ahead"` OR `state == "no_remote"`: RE-FIRE (treat as no record — local commits
                 are not on origin, so the `done` record is stale; dispatch the push step as a fresh run)
               - `state == "synced"`: SKIP this step (local HEAD already on origin)
               - `status: error`: RE-FIRE (fail toward pushing — the push step's own freshness
                 precondition still guards the actual push)
           - IF outcome == "failed": RETRY (proceed to dispatch as fresh run)
           - IF outcome == "loop_back": RE-FIRE (treat as no record — dispatch as fresh run)
           - IF no record OR any other value: dispatch normally
       - ELSE (every other step keeps the general rule):
           - IF outcome == "done": SKIP this step (continue to next iteration)
           - IF outcome == "failed": RETRY (proceed to dispatch as fresh run)
           - IF outcome == "loop_back": RE-FIRE (treat as no record — dispatch as fresh run)
           - IF no record OR any other value: dispatch normally
     Log skip/retry/re-fire decisions at INFO level so the work.log reflects the re-entry path.

     **Named exemption — a re-entry SKIP intentionally emits NO completion line.** Every SKIP
     branch above (the HEAD-dependent `head_at_completion == live HEAD` skip, the `push`
     parity-driven `state == "synced"` skip, and the general `outcome == "done"` skip) is exempt
     from the item-7 pairing, because a SKIP records NO outcome — it observes a terminal record
     an EARLIER entry already wrote, and that entry already emitted the step's
     `[STEP] ... Completed step:` line. The pairing binds a step's outcome RECORDING to its
     completion emission; with no recording there is nothing to pair, and emitting here would
     double-count the step as completed once per re-entry. The INFO skip-decision line above is
     the audit record for this path.

     **HEAD-dependent step set**: membership is the derived `head_dependent: true` frontmatter fact — see § "Special case — HEAD-dependent steps" above for the single authoritative statement and the governing discriminator; do NOT re-list or count the members here. A loop-back commit (typically produced by `plan-marshall:automatic-review` or `sonar-roundtrip` opening a fix task that produces a new commit) advances HEAD past the previously-validated SHA, and a stale `done` record on any head-dependent step would produce a false-clean result on re-entry. The same `head_at_completion` comparison applies to every member. The `push` step is NOT head-dependent — it is a pure push barrier whose re-entry skip/re-fire decision is parity-driven, not done-record-driven: the item-1 push-specific branch consults `branch-sync-state` (`ahead`/`no_remote` → re-fire, `synced` → skip) instead of a HEAD-comparison, and the dispatcher additionally re-invokes it explicitly after a post-PR `mutates_source` step commits (item 5f § "Post-PR re-push") as the fast path. Every other step whose authoritative doc declares no `head_dependent` fact is likewise not head-dependent — their effect is captured by side-effect (a created PR, recorded lessons, regenerated `target/claude/` from the post-merge source tree) and is idempotent against HEAD advances; the general rule above applies to them. Note that head-dependence is **orthogonal to the dispatched/inline split** — do NOT infer non-head-dependence from a step's presence on the [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) § "Inline steps" roster. Some steps on that roster declare `head_dependent: true` and some do not, so resolve each step's own frontmatter fact rather than inferring from its roster placement. CI completion is resolved as a separate dispatcher-side precondition (`requires: [ci-complete]`) — its cache key is the same `git rev-parse HEAD` SHA, so a HEAD advance also invalidates the precondition cache.

  2. Log step start:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Executing step: {step_ref}"

  3. Determine step type:
     - IF step_ref starts with "default:" -> BUILT-IN type (use step_id for dispatch table lookup)
     - ELSE IF step_ref starts with "project:" -> PROJECT type (manifest may someday include extension steps)
     - ELSE IF step_ref contains ":" -> SKILL type

  4. Pre-archive snapshot hook (run BEFORE dispatching the step if step_id == "archive-plan"):
     See "Pre-Archive Snapshot Hook" subsection below. Capture the snapshot into model context, then proceed to step 5 to dispatch archive-plan normally.

  4b. Lessons-capture Signal Gate (B4 — run BEFORE dispatching the step if step_id == "lessons-capture"):

      The deterministic three-signal Signal Gate is evaluated at dispatcher level so the envelope spawn cost is avoided when all three signals are zero. The dispatcher computes the precondition; the LLM workflow body is the recording loop only. When all three signals are zero AND the run is not orchestrated, short-circuit and record `outcome=skipped` — an orchestrated run is dispatched even at zero signals, per the orchestration carve-out in item 4b.b below.

      a0. Resolve orchestration context (runs BEFORE the three-zero short-circuit):

         An orchestrated plan — one launched from an epic's staged plan spec — routes its lesson-shaped output to the epic's `inbox/` OUTBOX instead of the global lessons store. The verdict is resolved ONCE per finalize run, here, and consumed by EVERY step whose body emits lesson-shaped output. That set is currently **three** steps: `default:lessons-capture`, `plan-marshall:plan-retrospective` (Step 5b), and `default:finalize-step-preference-emitter` (Step 4). A future step that gains a `manage-lessons add` call site MUST be added to this list and receive the same two runtime inputs.

         The two dispatched consumers receive the verdict as prompt-body runtime inputs (item c below); `default:finalize-step-preference-emitter` is an inline step, so it reads the values the dispatcher already holds — it MUST NOT re-issue either resolution call. All three run at or after `order: 991`, so the verdict resolved here is available to each of them.

         Read the plan's spec pointer through its canonical owner:

            python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
              request read --plan-id {plan_id} --section source_id

         Classify it through the single detection seam (no second detector, no new persisted metadata field):

            python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox detect \
              --source-id "{source_id}"

         Parse `orchestrated`, `epic`, and `detection` from the TOON output. `detection` names WHY the verdict came out the way it did, over the seam's closed four-token vocabulary (`orchestrated`, `not_orchestrator_pointer`, `unrecognised_id`, `unsafe_slug`). Log the verdict, mirroring the Signal-Gate skip log line:

            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              decision --plan-id {plan_id} --level INFO \
              --message "(plan-marshall:phase-6-finalize:lessons-capture) Orchestration context: orchestrated={orchestrated} epic={epic} detection={detection}"

         When `detection == unrecognised_id`, ALSO emit one work-log WARNING naming the pointer. That token means the `source_id` IS an orchestrator plan-spec path but its id segment matched none of the accepted forms — the plan looks orchestrated, yet no inbox message will be written for it:

            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              work --plan-id {plan_id} --level WARNING \
              --message "[VERIFY] (plan-marshall:phase-6-finalize:lessons-capture) Unrecognised orchestrator pointer {source_id} - the plan looks orchestrated but its id segment was not recognised, so no inbox message will be written"

         The WARNING changes the SILENCE, not the branch: the verdict stays `orchestrated: false` and the run proceeds down the non-orchestrated path exactly as before. All three consumers (`default:lessons-capture`, `plan-marshall:plan-retrospective` Step 5b, and `default:finalize-step-preference-emitter` Step 4) keep receiving `orchestrated` and `epic` unchanged — `detection` is read here and is not added to their runtime inputs. Emit the WARNING for `unrecognised_id` only: `orchestrated` and `not_orchestrator_pointer` are the ordinary paths and stay quiet.

      a. Compute three signal counts:

         **Signal 1 — Q-Gate findings, pending OR resolved-in-run (sum across five phases)**:
         For each phase in `{2-refine, 3-outline, 4-plan, 5-execute, 6-finalize}`, invoke the pending query:

            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              qgate list --plan-id {plan_id} --phase {phase} --resolution pending

         Parse `filtered_count` from each TOON output — this is the per-phase pending count. (`total_count` is the unfiltered cardinality of the entire findings store and MUST NOT be used as the pending-count signal — the call filters by `--resolution pending`, so the matching count lives in `filtered_count`.) Sum the five `filtered_count` values into `pending_subtotal`.

         Then, for each of the same five phases, count the Q-Gate findings the run RESOLVED. The Q-Gate facet shares the same resolved-in-run blind spot as Signals 2 and 3: a finding that was raised AND resolved (`fixed` / `suppressed` / `accepted` / `taken_into_account`) within the run is a slipped-then-caught defect — the highest-value lesson class — yet a pending-only count contributes zero for it. For each phase, invoke the four non-pending resolution filters and sum their `filtered_count` values:

            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              qgate list --plan-id {plan_id} --phase {phase} --resolution fixed
            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              qgate list --plan-id {plan_id} --phase {phase} --resolution suppressed
            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              qgate list --plan-id {plan_id} --phase {phase} --resolution accepted
            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              qgate list --plan-id {plan_id} --phase {phase} --resolution taken_into_account

         Parse `filtered_count` from each (NOT `total_count`) and sum all twenty values (five phases × four non-pending resolutions) into `resolved_subtotal`. `signal_1_count = pending_subtotal + resolved_subtotal`, so Signal 1 fires on EITHER pending OR resolved-in-run Q-Gate findings — symmetric with the remediated-in-run triggers added to Signals 2 and 3.

         **Signal 2 — plan-marshall:automatic-review outcome (outstanding OR remediated-in-run)**:

            python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
              read --plan-id {plan_id}

         Locate the `plan-marshall:automatic-review` step under `metadata.phase_steps["6-finalize"]`. Then query the count of review-bot findings the run REMEDIATED:

            python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
              list --plan-id {plan_id} --type pr-comment --resolution fixed

         Parse `filtered_count` from that TOON output (the `--resolution fixed` filter narrows the `artifacts/findings/pr-comment.jsonl` store to the in-run-fixed entries). `signal_2_count = 1` when ANY of the following holds; `0` otherwise: (a) `outcome` is anything other than `done`, (b) `display_detail` reports a non-zero promoted-comment count (e.g. `"3 comments promoted"`), (c) the `manage-findings list --type pr-comment --resolution fixed` query returns one or more findings (`filtered_count >= 1`). Trigger (c) is the remediated-in-run facet: a review-bot finding caught-and-fixed within the same run resolves to zero outstanding comments and leaves the step `outcome=done`, so triggers (a) and (b) both report zero — yet the run carried a lesson-bearing slipped-then-caught defect (the originating `hash_id=d9c3c7` case). Counting `resolution=fixed` pr-comment findings fires the signal for exactly that class. Triggers (a) and (b) are preserved unchanged.

         **Signal 3 — script-failure clusters (three marker classes)**:

            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              read --plan-id {plan_id} --type work

         Scan the returned log lines for THREE marker classes and bucket each by the distinct failing script notation (the `bundle:skill:script` token in the line):

         - **`[FAILED]`** lines — explicit failure markers.
         - **`[ERROR] ... script_failure`** lines — the canonical per-call non-zero-exit marker emitted by the phase Error Handling sections (argparse rejections, internal errors, "Unknown notation" failures). These never carry a `[FAILED]` token.
         - **`voluntary_checkpoint → error`** reclassifications — the dispatch-boundary no-progress reclassification (B7); the failing notation is the dispatched workflow/agent whose dispatch was reclassified.

         `signal_3_count` is the number of distinct notations across the UNION of all three marker classes (a notation that fails under more than one class counts once). The motivating case: a long build lost across the dispatch boundary, logged as `[ERROR] script_failure` plus a `voluntary_checkpoint → error` reclassification but never a `[FAILED]` line. This marker set is kept consistent with the retrospective analyzer's failure-marker set so the Signal-Gate count and the retrospective's script-failure cluster count stay aligned.

      b. Three-zero short-circuit:

         **Orchestration carve-out**: when `orchestrated: true` (from a0) the three-zero short-circuit does NOT fire — the body is dispatched even at zero signals, because an orchestrated plan owes its epic a `kind: landing` message regardless of whether it produced lesson-bearing signals. Skip straight to item c. When `orchestrated: false` the short-circuit below is unchanged, byte for byte.

         When `orchestrated == false AND signal_1_count == 0 AND signal_2_count == 0 AND signal_3_count == 0`:
            - Mark the step done with `outcome=skipped` directly from the dispatcher (do NOT dispatch the envelope):

              python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
                --plan-id {plan_id} --phase 6-finalize --step lessons-capture --outcome skipped \
                --display-detail "no lesson-bearing signals"

            - Log the skip decision:

              python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
                decision --plan-id {plan_id} --level INFO \
                --message "(plan-marshall:phase-6-finalize:lessons-capture) Signal Gate skip — all three signals zero (qgate=0, plan-marshall:automatic-review=0, script-failures=0)"

            - Emit the step-completion line — the `outcome=skipped` recording above and this
              emission are ONE indivisible pair (see item 7). A Signal-Gate skip settles the
              step's outcome, so it owes the same completion line as a dispatched run:

              python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
                work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"

            - CONTINUE the FOR loop (skip item 5 dispatch entirely for this step).

      c. Forward gate counts and orchestration context on dispatch (when at least one signal is non-zero, OR `orchestrated: true`):

         The envelope no longer re-computes the three signals — the dispatcher forwards them as runtime inputs so the body skips its (now-removed) Signal Gate step. It likewise forwards the a0 orchestration verdict so no body re-issues the detection. Add all five fields verbatim into the prompt body's runtime-inputs block alongside `plan_id` (see item 5 below):

            signal_qgate_pending_count: {signal_1_count}
            signal_automated_review_count: {signal_2_count}
            signal_script_failure_clusters_count: {signal_3_count}
            orchestrated: {true|false}
            epic: {slug|""}

         The same two orchestration fields are ALSO forwarded on the `plan-marshall:plan-retrospective` dispatch (the DISPATCHED roster entry under `--phase phase-6-finalize --role post-run-review`, and the sole whitelisted `--session-id` recipient), so every lesson-emitting write-site sees one verdict resolved once:

            orchestrated: {true|false}
            epic: {slug|""}

         `default:finalize-step-preference-emitter` (Step 4) is the third write-site and is INLINE, so it takes no prompt body — carry the same two values into it directly when the FOR loop reaches it at `order: 992`. It MUST NOT re-issue `request read --section source_id` or `orchestrator inbox detect`.

         Continue to item 5 (Dispatch with timeout wrapper).

  4c. Adr-propose Signal Gate (run BEFORE dispatching the step if step_id == "adr-propose"):

      The deterministic decision-shape Signal Gate is evaluated at dispatcher level so the envelope spawn cost is avoided when the plan carries no decision-shape signal. The dispatcher computes a coarse decision-shape precondition; the LLM workflow body applies the fine-grained decision-shape criteria and authors the proposals. When no decision-shape signal is present, short-circuit and record `outcome=skipped`. The decision-shape signal taxonomy is owned by `standards/adr-integration.md` § "Decision-shape signals" — do NOT inline-copy the pre-filter decision table; the deterministic precondition below is the coarse gate, not the full taxonomy.

      a. Compute the coarse decision-shape signal. A plan that settled an architectural decision leaves at least one of the following deterministic markers:

         **Marker 1 — a compatibility decision in the solution outline**:

            python3 .plan/execute-script.py plan-marshall:manage-files:manage-files read \
              --plan-id {plan_id} --file solution_outline.md

         The `compatibility:` line (e.g. `breaking`, `deprecation`, `smart_and_ask`) is a chosen-approach-with-rationale marker — a rejected-alternative signal. `marker_1 = 1` when the outline carries a non-empty `compatibility` value; `0` otherwise.

         **Marker 2 — decision-log entries**:

            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              read --plan-id {plan_id} --type decision

         `marker_2 = 1` when the decision log carries at least one entry (a recorded fork-with-rationale during the plan); `0` otherwise.

         `signal_decision_shape_count = marker_1 + marker_2`.

      b. Zero short-circuit:

         When `signal_decision_shape_count == 0`:
            - Mark the step done with `outcome=skipped` directly from the dispatcher (do NOT dispatch the envelope):

              python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
                --plan-id {plan_id} --phase 6-finalize --step adr-propose --outcome skipped \
                --display-detail "no decision-shape signals"

            - Log the skip decision:

              python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
                decision --plan-id {plan_id} --level INFO \
                --message "(plan-marshall:phase-6-finalize:adr-propose) Signal Gate skip — no decision-shape signal (compatibility=0, decision-log=0)"

            - Emit the step-completion line — the `outcome=skipped` recording above and this
              emission are ONE indivisible pair (see item 7). A Signal-Gate skip settles the
              step's outcome, so it owes the same completion line as a dispatched run:

              python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
                work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"

            - CONTINUE the FOR loop (skip item 5 dispatch entirely for this step).

      c. Forward gate count on dispatch (when the signal is non-zero):

         When `signal_decision_shape_count >= 1`, dispatch the `adr-propose.md` workflow body. Reaching the body PROVES at least one decision-shape signal was present, so the body proceeds straight into ADR proposal without re-evaluating the gate (see `workflow/adr-propose.md` § "Dispatch contract"). Add the count field verbatim into the prompt body's runtime-inputs block alongside `plan_id`:

            signal_decision_shape_count: {signal_decision_shape_count}

         Continue to item 5 (Dispatch with timeout wrapper).

  5. Dispatch with timeout wrapper:
     Resolve the per-agent timeout budget from the table above (15 min for sonar/plan-marshall:automatic-review, 5 min for knowledge/lessons; no explicit budget for other steps).

     - BUILT-IN (agent-suitable) — route each step_ref to the generic `execution-context-{level}` dispatcher via the Task tool, passing the step's workflow doc and role key through the prompt body, wrapped with the resolved timeout. The workflow-doc-bearing dispatch carries the step's enforcement envelope (input contract, required skill loads, prohibited actions) inside the subagent context via the loaded skills + workflow; a generic unscoped dispatch with no workflow doc is NOT valid.

       **Role-aware dispatch** (applies to all five built-in agent-suitable steps):

       (1) Resolve the level-bound target via the resolver:
           ```
           target = python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
             effort resolve-target --phase phase-6-finalize [--role <subkey>]
           ```text
           Returns `execution-context-{level}` (variant), or canonical `execution-context` for `inherit`/empty.
       (2) Dispatch via `Task(subagent_type: plan-marshall:<target>, …)` with prompt body `name`, `plan_id`, `skills[]`, `workflow: plan-marshall:phase-6-finalize/workflow/{name}.md`, `WORKTREE`.

       Per-step workflow docs and resolver lookups:
         * default:create-pr        -> workflow: workflow/create-pr.md        | --phase phase-6-finalize                              (no --role)
         * plan-marshall:automatic-review -> workflow: ../automatic-review/SKILL.md | --phase phase-6-finalize                              (FIND-only producer; triage is the dispatcher-owned unified pass — item 7c) | timeout: 900s
         * default:sonar-roundtrip  -> workflow: workflow/sonar-roundtrip.md  | --phase phase-6-finalize                              (FIND-only producer; triage is the dispatcher-owned unified pass — item 7c) | timeout: 900s
         * default:lessons-capture  -> workflow: workflow/lessons-capture.md  | --phase phase-6-finalize --role post-run-review       | timeout: 300s
         * default:adr-propose      -> workflow: workflow/adr-propose.md      | --phase phase-6-finalize                              (no --role; P2 fails — not a post_run_review member) | timeout: 300s

       The `--role post-run-review` values above are NOT a hand-maintained list: each is the
       derived consequence of that step's own `post_run_review` frontmatter fact (see the
       "The `post-run-review` sub-key is DERIVED, not listed" note under the resolver table
       above). Resolve the fact for the step being dispatched rather than reading the sub-key
       off this table.

       The subagent's body loads `persona-plan-marshall-agent` + the prompt's `skills[]`, then `Read`s the workflow doc and executes its steps inside the dispatch envelope. Pass `--plan-id {plan_id}` and, when an `{iteration}` counter applies, `--iteration {iteration}` as workflow-specific runtime inputs in the prompt body. The Worktree Header is conveyed via the always-required `WORKTREE` prompt-body field; the subagent resolves the worktree path internally and propagates it into any further dispatches it issues.

       **On timeout** (the dispatch does not return within the budget):
         a. Log ERROR:
            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              work --plan-id {plan_id} --level ERROR --message "[ERROR] (plan-marshall:phase-6-finalize) Step {step_ref} timed out after {budget}s — marking failed and continuing"
         b. Mark step failed:
            python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
              --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome failed \
              --display-detail "timed out after {budget}s"
         c. Emit the step-completion line — the (b) `outcome=failed` recording and this
            emission are ONE indivisible pair (see item 7). The timeout path leaves the
            iteration without reaching item 7, so the line is emitted here or not at all:
            python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
              work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"
         d. Continue to the next step in the loop — DO NOT abort the pipeline.

     - BUILT-IN (inline-only — every `default:` step classified under
       [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) § "Inline steps",
       the single source of truth for inline membership; do NOT re-list it here):
       Read the standards document from dispatch table and follow all steps in main context. Inline steps are not wrapped by the per-agent timeout block above — they execute under the host platform's standard per-call ceiling. `ci-verify` runs the deterministic `scripts/ci_verify.py` executor: the dispatcher threads the `consume-failures` precondition envelope (`ci_final_status` → `--final-status`, `wait_outcome` → `--wait-outcome`, `head_sha` → `--head-sha`) into the script, which marks the step done on green (zero dispatch) or returns a per-producer needs-triage signal on red CI so the dispatcher runs `verification-feedback` — see `standards/ci-verify.md`.

     - PROJECT/SKILL: Branch on the dispatched-vs-inline classification from the
       "Dispatched workflows vs inline steps" section, which points at
       [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md)
       as the single source of truth. A `project:` / `bundle:skill` step is
       DISPATCHED when it appears under that document's `## Dispatched steps`
       roster; every step under `## Inline steps` is INLINE. Look the step up in
       the roster — do NOT infer the class from any example named in this branch,
       and do NOT assume the dispatched class is a single member: the roster
       carries multiple external dispatched steps and grows as steps are added.

       **DISPATCHED project/skill step** — route through the generic
       `execution-context-{level}` dispatcher exactly like an agent-suitable
       built-in, wrapped with the resolved per-agent timeout:

       (1) Resolve the level-bound target via the resolver:
           ```
           target = python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
             effort resolve-target --phase phase-6-finalize [--role <subkey>]
           ```text
           Use the step's own resolver lookup as declared on its row in
           [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md)
           § "Dispatched steps" — that roster's resolver-lookup column is the
           authoritative per-step source for the `--phase` value, the `--role`
           sub-key (or its documented absence), and any `producer` runtime input.
           Read the lookup off the step's row; do not generalise one step's role to
           the rest of the dispatched class.
       (2) Emit the standardized `[DISPATCH]` work-log line (see
           [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md)
           § Emission contract). Substitute `{role}` with `default` when no `--role`
           flag was passed, otherwise the explicit sub-key value:
           ```bash
           python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
             work --plan-id {plan_id} --level INFO \
             --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role={role} workflow={step's own SKILL.md notation} plan_id={plan_id}"
           ```
           **This emit and the item-(3) spawn are ONE indivisible pair.** The
           `[DISPATCH]` write and the `Task:` spawn are two halves of a single
           action, not an instruction followed by an optional adjacent one — the
           same pairing item 5c states for its metrics row. Spawning the step
           without having written the line is a **contract violation**, not a
           cosmetic omission: the work-log then carries no record that the
           dispatch happened, so the dispatch-audit chain cannot attribute the
           step's cost, its target, or its role. Never emit the line after the
           spawn, and never skip it because the dispatch "obviously" happened.
       (3) Dispatch via the Task tool. The workflow doc for a dispatched project/skill
           step is the project skill's own SKILL.md (e.g.
           `project:finalize-step-plugin-doctor/SKILL.md`):
           ```text
           Task: plan-marshall:{target}
             prompt: |
               name: {step_name}
               plan_id: {plan_id}
               skills[N]:
               - <step-specific skills>
               workflow: {step's own SKILL.md notation}
               WORKTREE: {worktree_path}
           ```
           Forward `--plan-id {plan_id}`, `--iteration {iteration}`, and any
           `producer` runtime input as workflow-specific prompt-body inputs. The
           `[--session-id {session_id}]` runtime input follows the same whitelist
           rule documented under "Interface Contract for External Steps".

       The DISPATCHED branch obeys the same "On timeout" handling as the
       agent-suitable built-in branch (item 5 above): log ERROR, mark the step
       `failed`, continue to the next step.

     - INLINE project/skill step — load the skill with interface contract in the
       main context:
       Skill: {step_ref}
         Arguments: --plan-id {plan_id} --iteration {iteration} [--session-id {session_id}]

       The INLINE branch is reserved for genuinely-inline external steps
       (`project:finalize-step-deploy-target`, `project:finalize-step-sync-plugin-cache`).
       Append `--session-id {session_id}` ONLY when `step_ref` is on the
       Session-id forwarding whitelist documented under "Interface Contract
       for External Steps" above (the table at that section is the single
       source of truth — do not re-list its entries here). Off-whitelist
       external steps receive `--plan-id` and `--iteration` only —
       appending `--session-id` to a step that does not declare it risks a
       "rejected unknown flag" failure.

  5b. Accumulate agent usage (only when the dispatched step ran as a Task agent and did NOT time out):
      Extract total_tokens, tool_uses, duration_ms from the agent's <usage> tag, then persist them on disk via:

         python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
           --plan-id {plan_id} --phase 6-finalize \
           --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}

      The script reads `.plan/plans/{plan_id}/work/metrics-accumulator-6-finalize.toon` (initialising it on first call), sums in the supplied values, increments the `samples` counter, and writes the file back. Inline steps and timed-out steps skip this call — the timeout path's cost is captured by the `manage-metrics enrich` transcript sweep inside `default:record-metrics`. Step 5b runs at most once per dispatched agent return; do NOT also append the totals to a model-context variable.

      **Retrospective-tokens forwarding (producer side)**: when — and ONLY when — the just-returned dispatched step is the opt-in **retrospective** step (`plan-marshall:plan-retrospective`, dispatched under `phase-6-finalize --role post-run-review`), ALSO pass `--retrospective-tokens {total_tokens}` on the SAME `accumulate-agent-usage` call. The retrospective dispatches inside the `6-finalize` phase window, so its `<usage>` `total_tokens` IS the full retrospective spend; forwarding it here is the producer side of the `retrospective_tokens` attribution that `default:record-metrics`'s `end-phase` reads back from the accumulator (no `--retrospective-tokens` flag is added at the `end-phase` call site — it picks the value up from this accumulator). For the retrospective step the combined call is:

         python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics accumulate-agent-usage \
           --plan-id {plan_id} --phase 6-finalize \
           --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms} \
           --retrospective-tokens {total_tokens}

      No other finalize step forwards `--retrospective-tokens` — every non-retrospective dispatched step omits it so the accumulator's `retrospective_tokens` total stays equal to the retrospective spend alone.

  5c. Record dispatch-boundary row for the just-returned step (per-step, only when 5b also ran):
      Apply the SAME gate as 5b — fire only when the step ran as a Task agent and did NOT time out. Every step classified under [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) § "Inline steps" — the single source of truth for inline membership, not re-listed here — skips this call uniformly, mirroring the 5b gate. The call fires per-step — once for each dispatched finalize step return — NOT once per phase entry.

      Classify the step's return into exactly one of the four phase-6-finalize termination causes:

      | Cause | Detection rule |
      |-------|----------------|
      | `step_complete` | The dispatched step returned cleanly (its `mark-step-done` call recorded `outcome: done`). |
      | `blocked_user_review` | The dispatched step raised an `AskUserQuestion` review gate that halted dispatch (e.g., branch-cleanup confirmation, or a `plan-marshall:automatic-review` `escalate_ask{reason: re_review_timeout}` return whose `ask` policy made the dispatcher fire the re-review-timeout `AskUserQuestion` — see item 7a). |
      | `blocked_session_restart` | The dispatch was cut short by a session restart, harness cancellation, or the per-agent timeout budget firing (timeout block at item 5 above). |
      | `error` | The dispatched step's `mark-step-done` call recorded `outcome: failed`. |

      **Ordering note for the `escalate_ask` path** — classification at 5c reads the return TOON; it does NOT itself fire the `AskUserQuestion`. When the just-returned step carries `status: escalate_ask{reason: re_review_timeout}`, the three subsequent items run in a fixed order: **5c classifies** the return (this `blocked_user_review` row applies only once item 7a actually fires the `ask`-policy prompt) → **5d skips** the completion guard for the `escalate_ask` return (its dedicated carve-out — terminality is NOT asserted, see 5d) → **7a consumes** the escalation envelope (reads `re_review_on_timeout`, branches on `action`/`reason`, and fires the `AskUserQuestion` for the `ask` policy). 5d does NOT assert terminality on the `escalate_ask` path; the `step_record_missing` halt the guard would otherwise raise is precisely the bug the 5d carve-out removes, which is what keeps item 7a reachable.

      Forward the `<usage>` totals captured by 5b (total_tokens, tool_uses, duration_ms):

         python3 .plan/execute-script.py plan-marshall:manage-metrics:manage-metrics record-dispatch-boundary \
           --plan-id {plan_id} --phase 6-finalize --termination-cause {step_complete|blocked_user_review|blocked_session_restart|error} \
           --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}

      The accumulating artifact at `work/metrics-dispatch-boundaries-6-finalize.toon` is the per-step audit trail that `plan-retrospective` correlates with finalize-step `[STEP]` log coverage; the same shape as the phase-5-execute boundary artifact, generalised to per-phase keying.

  5d. Post-dispatch completion guard (only when the dispatched step ran as a Task agent, did NOT time out, and did NOT return `status: escalate_ask`):
      Apply the SAME gate as 5b/5c, extended with a third carve-out. The guard fires ONLY when the step ran as a Task agent AND did NOT time out AND its return TOON does NOT carry `status: escalate_ask`. Three classes of step SKIP this guard uniformly:

      - **Inline-only steps** — every step classified under [`standards/dispatch-inline-split.md`](standards/dispatch-inline-split.md) § "Inline steps" (the single source of truth for inline membership; do NOT re-list it here) — they record their own mark synchronously in the main context.
      - **Timed-out steps** — the timeout path at item 5 already recorded `outcome=failed` before continuing.
      - **`escalate_ask`-returning steps** — a `plan-marshall:automatic-review` step that returns `status: escalate_ask` legitimately left NO terminal `mark-step-done` record, because the continuation is owned by item 7a (the escalate-ask continuation hook), NOT by the leaf. The carve-out keys on `status: escalate_ask` alone and therefore generalizes over the `reason` field — it covers **both** escalation reasons uniformly: `reason: re_review_timeout` (trigger B re-review await timeout under an `ask` or `defer` policy) and `reason: rate_window_timeout` (the rate-window await loop exhausting its budget while the bot is still rate-limited). A dispatched leaf cannot fire the `AskUserQuestion` and cannot mark the step terminal — it returns the escalation envelope and item 7a consumes it. Asserting terminality for such a step is a FALSE POSITIVE that would halt the pipeline with `step_record_missing` BEFORE item 7a can run, leaving 7a unreachable. The dispatcher already has the return TOON in context (it read the same TOON to classify the termination cause under item 5c), so detecting `status: escalate_ask` adds no new read. This carve-out is the symmetric dispatcher-side counterpart of the leaf's no-mark contract documented in [`../automatic-review/SKILL.md`](../automatic-review/SKILL.md) § "`escalate_ask` return (timeout escalations)".

      See the "Post-dispatch completion guard" subsection below for the placement contract.

      When the guard fires (the step is not in any of the three skip classes above), assert that the just-returned step actually recorded a terminal outcome on `status.metadata.phase_steps["6-finalize"][step_id]`. A dispatched step is contractually required to terminate with a `manage-status mark-step-done` call; an agent that returns `status: success` but omits that side-effect leaves NO record, which silently deadlocks the `phase_steps_complete` handshake at the phase transition with no per-step attribution. The guard converts that silent gap into an attributed failure at per-step granularity.

      **Missing-record taxonomy — two independent causes.** The recurrences this guard detects resolve into exactly two causes, not one: **cause A, key-form split** (the step authored `--step` in a different key form than the composed manifest key) — absorbed for bare and `default:`-prefixed keys by the canonical step-key seam that normalises them on write, and still live for `bundle:skill` ids whose prefix that seam preserves verbatim by design; and **cause B, omitted call** (the step did its work and returned `status: success` without ever calling `mark-step-done`) — addressed by the record-before-return ordering invariant on the authoring side. Key normalisation cannot fix a write that never happens, so the two causes need different remedies: cause A surfaces here as `step_record_mismatched_key`, cause B as `step_record_missing`. This guard is the **detector** for both, and the backstop rather than the fix — the authoring-side rules for both causes live in [`standards/external-step-contract.md`](standards/external-step-contract.md) § "Required termination" (the `--step` catalog-key contract and the record-before-return ordering invariant). No behavioural change to the guard itself.

      Call the read-only verb with `--require-terminal` so a missing terminal record is escalated to a branchable error:

         python3 .plan/execute-script.py plan-marshall:manage-status:manage-status assert-step-recorded \
           --plan-id {plan_id} --phase 6-finalize --step {step_id} --require-terminal

      Branch on the returned TOON:

      - `status: success` (`recorded: true`) — the dispatched step recorded a terminal outcome (`done` / `skipped` / `loop_back` / `failed`). Continue normally to item 6/7.
      - `status: error, error: step_record_missing` (`recorded: false`) — the agent returned but left no terminal record: a contract violation. The dispatcher records the violation itself (the leaf cannot, having already returned), logs an attributed `[ERROR]` line, and halts the pipeline. Do NOT abort silently and do NOT advance to the next step — the resumable re-entry check (item 1) retries the `failed` step on the next finalize entry.

        a. Record the violation as a `failed` outcome attributed to the offending step:
           python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
             --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome failed \
             --display-detail "step-record-missing: agent returned no outcome"
        b. Log the attributed error:
           python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
             work --plan-id {plan_id} --level ERROR \
             --message "[ERROR] (plan-marshall:phase-6-finalize) Step {step_ref} returned without recording a terminal outcome — post-dispatch guard recorded failed and halted; resumable re-entry will retry the step"
        c. Emit the step-completion line, THEN HALT the FOR loop (return control to the
           orchestrator). Do NOT proceed to item 6/7 for this step. The emission comes first
           because the (a) `outcome=failed` recording and this line are ONE indivisible pair
           (see item 7), and the halt bypasses item 7 — so the line is emitted here or not at
           all, and a failed step that never appears as completed is invisible to per-step
           completion coverage:
           python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
             work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"

  5e. Record per-step execution outcome to the manifest (mirror of the phase-5-execute Step 8c record-step call):
      Append one execution-log row to the manifest so per-step finalize execution metadata is loggable per-plan deterministically — this is the consuming side of the `record-step` contract published by `manage-execution-manifest` (its Producers table names `phase-6-finalize` as a `record-step` producer). The call fires per dispatched finalize step return, mirroring the 5b accumulate-agent-usage call so the per-step execution log and the per-phase token accumulator stay aligned. Unlike 5b/5c/5d, this row is recorded for EVERY finalize step — dispatched OR inline — so a skipped or inline step still lands an `execution_log` row (with zero token attribution for inline steps that carry no `<usage>` tag):

         python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest record-step \
           --plan-id {plan_id} --step-id {step_id} --phase 6-finalize --outcome {executed|skipped|error} \
           --total-tokens {total_tokens} --tool-uses {tool_uses} --duration-ms {duration_ms}

      See `manage-execution-manifest` Canonical invocations → `record-step` for the authoritative argument surface. Contract:

      - `--phase` is always `6-finalize` in this phase; `--step-id` is the finalize step ID / notation (e.g. `push`, `create-pr`, `record-metrics`, or an external step's `project:` / `bundle:skill` notation).
      - `--outcome` is `executed` when the step ran, `skipped` when the resumable re-entry check (item 1) skipped an already-`done` step or a HEAD-comparison decided no re-run was needed, and `error` when the step's `mark-step-done` recorded `outcome: failed` (including the 5d post-dispatch-guard violation path at item 5d.b — record the `error` row BEFORE halting the FOR loop so the failed attempt is on the execution log).
      - The token-attribution triple is the SAME triple captured by 5b — forward the `<usage>` integers for dispatched steps, and `0` for inline steps that carry no `<usage>` tag (the manifest schema documents the `0` default, so an inline step records a row with zero token attribution rather than a missing column). 5b sums these into the per-phase accumulator that fills the `total_tokens` column; 5e records the per-step breakdown. The two are complementary, not redundant.
      - The manifest MUST already exist (composed by `phase-4-plan` Step 8b); `record-step` returns `file_not_found` otherwise. The append is atomic and one decision-log line is emitted per record.

      **Exec-blind contract (finalize side)**: the `6-finalize` row in `metrics.toon` is kept non-zero by `default:record-metrics`'s `end-phase` write, which reads the `metrics-accumulator-6-finalize.toon` accumulator that 5b fills on every dispatched step return — see § Phase-boundary metric bookkeeping below. 5e's per-step `execution_log[]` rows are the auditable per-step breakdown behind that aggregate, mirroring phase-5-execute Step 8c so neither phase has an exec-blind (`total_tokens==0`) path.

  5f. Commit instrumentation (after the step has recorded a terminal `done`/`skipped` outcome — see "Commit instrumentation contract" below):
      The dispatcher owns EVERY commit a finalize step's edits produce. Read the step's declared `mutates_source` AND `post_run_review` frontmatter facts from its authoritative doc (the `standards/{name}.md` or `workflow/{name}.md` that declares the step's `order:`) — one frontmatter read, two facts. When `mutates_source` is `false` (or absent — read-only is the safe default), run the post-run-band tracked-source guard at (0) below and then proceed to item 6. When `mutates_source` is `true`, skip (0) — a declared mutator's edits are exactly what (a)-(d) commit — and instrument the commit:

      (0) **Post-run-band tracked-source guard** (fires ONLY when `post_run_review` is `true`; the two facts are mutually exclusive, so this arm is reached only on the `mutates_source: false` path): the `mutates_source: false` declaration is the ONLY thing standing between a post-run-review step and an unpushable source edit, and a declaration cannot detect a branch that violates it. A post-run-review step runs AFTER the merge gate, so a tracked-source write one of its branches makes lands as an uncommitted diff with no remaining push path. Observe the main checkout once per such step return:

          ```bash
          python3 .plan/execute-script.py plan-marshall:phase-6-finalize:post_run_source_guard check \
            --step-id {step_id} --project-dir {main_checkout}
          ```

          **The tree to observe is `{main_checkout}`, never `{worktree_path}`.** Every
          `post_run_review: true` step is ordered after `default:branch-cleanup` (70), which
          merges and then REMOVES the worktree — so by the time this guard runs, `{worktree_path}`
          no longer exists on disk and a `git -C` against it fails outright, returning
          `status: error` with `clean: true`. Since (0)'s error branch records nothing, pointing
          the guard at the worktree would make its entire `clean: false` arm structurally
          unreachable: a guard that can never fire. `{main_checkout}` is also the correct tree on
          the merits — a post-run step's stray tracked write lands there, on the merged base
          branch, which is exactly the unpushable edit this guard exists to surface.

          The guard's three settled design decisions — do NOT re-derive them:

          - **Scope is the post-run band, not every step.** Before the merge gate an uncommitted tracked edit is still pushable, so the defect is reachable only after it. The guard is therefore consulted only for a step declaring `post_run_review: true`; every other `mutates_source: false` step proceeds to item 6 with no observation.
          - **The path predicate is dirty AND tracked AND outside `.plan/`.** Every finalize step legitimately writes plan state under `.plan/`, so a bare non-empty `git status --porcelain` test would fire on every post-run step. The script composes two filters — `--untracked-files=no` (git drops untracked paths) plus an explicit `.plan/` prefix exclusion — and only what survives both is reported.
          - **The failure action is loud and legible, but NEVER blocking.** The post-run band is advisory by design — its members are ordered after `default:branch-cleanup`, so the merge has already happened and there is nothing left for a hard failure to protect; blocking there would strand a merged branch rather than prevent a bad merge. A hard failure would therefore contradict the band's placement. The script exits `0` on every path, including `clean: false` and its own `status: error`.

          Branch on the returned TOON. On `clean: true` (the expected outcome) do nothing and proceed to item 6. On `clean: false`, take BOTH non-blocking actions, then proceed to item 6 anyway:

          a. Log an attributed WARNING naming the writing step and the offending tracked paths:

             ```bash
             python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
               work --plan-id {plan_id} --level WARNING \
               --message "[STATUS] (plan-marshall:phase-6-finalize) Post-run-review step {step_id} declares mutates_source: false but left dirty TRACKED source outside .plan/: {offending_paths} — the edit ran after the merge gate and has no push path; it is NOT committed and NOT blocking"
             ```

          b. Record the observation as a finding so it survives the run:

             ```bash
             python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
               --plan-id {plan_id} --phase 6-finalize --source qgate --type anti-pattern --severity warning \
               --component "plan-marshall:phase-6-finalize" \
               --title "post_run_review step wrote tracked source after the merge gate" \
               --detail "{step_id} declares mutates_source: false yet left these dirty tracked paths outside .plan/: {offending_paths}. A post-run-review step runs after the merge gate, so the edit is unpushable. Either the step must stop writing tracked source, or it does not belong in the post-run band."
             ```

          On `status: error` (the observation itself failed — not a git repository, git unavailable) the guard returns `clean: true` with an `error` field so an unusable observation never manufactures an offender. Log the `error` value at WARNING and proceed to item 6; do NOT record a finding, and do NOT treat it as a blocking failure.

      (a) Check the worktree for uncommitted changes the step produced:

          git -C {worktree_path} status --porcelain

      (b) IF the porcelain output is non-empty, commit the changes on the feature branch (no push — the `push` barrier owns the push). Use the step's returned `commit_message` field when the step supplied one in its return TOON; otherwise derive the conventional-commit fallback `chore(finalize): apply {step_id} changes`:

          Skill: plan-marshall:workflow-integration-git
          Parameters:
            - message: {step's returned commit_message, else "chore(finalize): apply {step_id} changes"}
            - push: false
            - create-pr: false

          **Re-stamp `head_at_completion` (mandatory for a head-dependent step)**: the instrumentation commit advances the feature-branch HEAD past the SHA the step recorded on its terminal `mark-step-done` call (the step captured `git rev-parse HEAD` BEFORE its edits were committed, because the dispatcher — not the step — owns the commit). For a `mutates_source: true` step that is ALSO head-dependent (resolve the step's own `head_dependent` fact — see § "Special case — HEAD-dependent steps"; do not consult an inline list), leaving the stale pre-commit SHA on the record makes the item-1 re-entry check observe `head_at_completion != live HEAD` and RE-FIRE the step on every resume — defeating the SKIP optimization. After the commit succeeds, resolve the new HEAD (`{new_commit_sha}`) and re-stamp the step's record so a converged-tree re-entry SKIPs correctly:

          ```bash
          git -C {worktree_path} rev-parse HEAD
          ```

          ```bash
          python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
            --plan-id {plan_id} --phase 6-finalize --step {step_id} --outcome done \
            --head-at-completion {new_commit_sha} \
            --display-detail "{the step's own display_detail, preserved}"
          ```

          This re-stamp is a no-op for a `mutates_source: true` step that is NOT head-dependent — skip it whenever the step's own `head_dependent` fact is absent or false. Resolve that fact per step rather than inferring it from any example: `mutates_source` and `head_dependent` are independent facts, and the pairing that makes the re-stamp load-bearing is a step declaring BOTH.

      (c) IF the porcelain output is empty, the mutating step produced no net change — record nothing and proceed to item 6. The step's pre-commit `head_at_completion` already equals the live HEAD (no commit was made), so no re-stamp is needed.

      (d) **Freshness reconciliation record** (emit ONLY after a non-empty commit was made at (b); skip on the (c) empty-porcelain path): the instrumentation commit is a finalize-internal `mutates_source` commit that advances the working-tree `worktree_sha` past the last `kind=build` ledger entry, which will make the downstream `push` step's freshness precondition report `stale` even though the source a `verify` already observed is unchanged (see `standards/push.md` § "Finalize-internal re-stale reconciliation"). Emit a legible reconciliation record so `push` reconciles the gate for a documented reason instead of a silent `--force`. Resolve the prior successful-build `worktree_sha` from the ledger:

          ```bash
          python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger query \
            --kind build
          ```

          Filter the returned entries to those whose `status` field is `success` (NOT `--exit-code 0` — the build wrapper exits 0 even on a `killed` / `timeout` / `error` outcome, so an exit-code filter can select a non-successful build and record an invalid `prior_build_worktree_sha` the push flow would then trust). Take the most-recent `status: success` entry's `worktree_sha` as `{prior_build_worktree_sha}`. When NO `status: success` entry exists, **fail closed**: skip emitting the reconciliation record entirely so the downstream push freshness gate stays `stale` rather than reconciling against an unverified build. `{new_commit_sha}` is the HEAD resolved at (b). Record the reconciliation decision naming the finalize-internal commit, the producing step, and the prior build sha:

          ```bash
          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
            decision --plan-id {plan_id} --level INFO \
            --message "(plan-marshall:phase-6-finalize:freshness-reconcile) commit_sha={new_commit_sha} step_id={step_id} prior_build_worktree_sha={prior_build_worktree_sha} — finalize-internal mutates_source commit advanced worktree_sha past the last successful build; the downstream push freshness gate is reconciled for this documented reason, not force-overridden."
          ```

          The `push` step's freshness precondition reads this record — matching `commit_sha` against the live HEAD — to distinguish the known-safe finalize-internal re-stale from genuine un-built source drift, which stays fail-closed. Genuine drift never produces this record (no finalize-internal commit authored it), so the fail-closed path is preserved.

      **Post-PR re-push**: when a `mutates_source: true` step that runs AFTER `create-pr` and BEFORE the merge gate (e.g. `plan-marshall:automatic-review` or `sonar-roundtrip` committing a loop-back fix) commits via this instrumentation, the dispatcher re-invokes the `push` step so the PR HEAD advances (and, for review-bearing steps, re-review fires) inside the normal settle band instead of at the merge gate. The `push` step is a pure barrier (it carries no commit logic and is not head-dependent); the dispatcher re-invokes it explicitly here rather than relying on a HEAD-comparison re-fire. This explicit re-invocation is the **fast path**; the item-1 `branch-sync-state` parity check is the **structural backstop** — even if this re-invocation is missed (crash, session loss), the next re-entry observes `state: ahead` and re-fires the push rather than trusting the stale `done` record. Read-only (`mutates_source: false`) steps never reach item 5f's instrumentation and never trigger a re-push.

  6. Capture archive result (only when step_id == "archive-plan"):
     Record the returned `archive_path` into model context alongside the pre-archive snapshot — it is consumed by Step 4 (Render Final Output Template).

  7. Log step completion:
     python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
       work --plan-id {plan_id} --level INFO --message "[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}"

     **Recording a step's terminal outcome and emitting its completion line are ONE indivisible pair.**
     The `mark-step-done` write (whatever its `--outcome`: `done` / `skipped` / `loop_back` / `failed`)
     and the `[STEP] (plan-marshall:phase-6-finalize) Completed step: {step_ref}` line above are two
     halves of a single action, exactly as the `[DISPATCH]` write and the `Task:` spawn are one pair.
     Recording the outcome without emitting the line is a **contract violation**, not a cosmetic
     omission: the work-log then carries no record that the step settled, so per-step completion
     coverage cannot be reconstructed and the retrospective reads the step as never having run.
     The pairing holds on EVERY path a step's outcome is recorded on — not only this happy path:
     the item-4b.b and item-4c.b Signal-Gate skips (`outcome=skipped`, then CONTINUE), the
     item-5 dispatch-timeout path (`outcome=failed`, then CONTINUE to the next step), and the
     item-5d.c post-dispatch-guard halt (`outcome=failed`, then HALT) each emit the line at their
     own recording site, and the item-1 re-entry SKIP and item-7a continuation hook each carry a
     named exemption. Emit the line immediately after the recording call, never before it, and
     never omit it because the step "obviously" completed.

  7a. Escalate-ask continuation hook (consult the dispatched step's return status):

      **Named exemption — this hook's terminal recordings emit NO completion line of their own.**
      Item 7a runs AFTER item 7, so the `[STEP] ... Completed step:` line for this
      iteration's `{step_ref}` has already been emitted by the time any branch below
      records an outcome. The "Merge anyway" branch's `mark-step-done --outcome done`
      is a post-emission resolution of an already-completed iteration, not a new
      terminal site, and emitting again here would double-count the step as completed.
      The `defer` branch records nothing at all by design.

      When the dispatched `plan-marshall:automatic-review` step returns `status: escalate_ask`, the leaf has returned an escalation envelope rather than firing an `AskUserQuestion` itself (a dispatched leaf cannot own the prompt — see the leaf/dispatch-topology contract in `ref-workflow-architecture/standards/agents.md`). The dispatcher owns the consumption. Four escalation reasons reach this hook, discriminated by the return TOON's `reason` field, and the hook handles them **identically at the AskUserQuestion layer** — the only difference is which policy knob (if any) is consulted first:

      - **`reason: re_review_timeout`** — a re-review await timed out at trigger B (see `../automatic-review/SKILL.md` § "On re-review timeout (trigger B)"). The `re_review_on_timeout` policy knob selects `action: defer` vs `action: ask` (or `proceed`, which never returns `escalate_ask`).
      - **`reason: rate_window_timeout`** — the rate-window expiry poll exhausted `review_rate_window_timeout_seconds` while the claimed window was still open.
      - **`reason: rate_window_not_awaitable`** — the refusing bot's `rate_limit_class` is `hard_quota` or `unknown`, so neither awaiting nor generating an event is productive; the leaf escalated without claiming a window.
      - **`reason: rate_window_exhausted`** — the recovery recursion cap for that bot on that PR is spent; the leaf escalated rather than re-triggering a bot it has already re-triggered `attempt_cap` times.

      The three rate-window reasons (see `../automatic-review/SKILL.md` § "Rate-limit refusal recovery (opt-in)") always carry `action: ask` and consult NO policy knob — they always fire the AskUserQuestion.

      The full field set of the `escalate_ask` return TOON (all four `reason` variants) is defined in [`../automatic-review/SKILL.md`](../automatic-review/SKILL.md) § "`escalate_ask` return (timeout escalations)" — read it there; do NOT restate the field set here.

      For `reason: re_review_timeout`, read the timeout policy from the `plan-marshall:automatic-review` step-params snapshot (the three rate-window variants skip this read — they have no policy knob):

         python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
           step-params get --plan-id {plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review

      Read `re_review_on_timeout` off the returned `params` object, then branch on the returned envelope's `action`/`reason`:

      - **`action: defer`** (policy `defer`): skip the merge for this run — do NOT advance to `branch-cleanup`'s merge. Decision-log the deferral, leave the `plan-marshall:automatic-review` step record ABSENT (do NOT call `mark-step-done` — the absent record is what makes the resumable re-entry check re-issue the step on the next finalize entry), and HALT the FOR loop returning control for re-entry. This is the deliberate inverse of the "Merge anyway" branch below: merge-anyway records a terminal `done` because the operator resolved the step, whereas defer intentionally records nothing so the step re-runs:

           python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
             decision --plan-id {plan_id} --level INFO \
             --message "(plan-marshall:phase-6-finalize) plan-marshall:automatic-review returned escalate_ask{action: defer} — skipping merge for unreviewed head_sha={head_sha}; re-enter finalize later"

      - **policy `proceed`** (the leaf already fell through to "Wait for review-bot comments" and the run terminated normally): the leaf does NOT return `escalate_ask` for `proceed` — no orchestrator branch is needed. This is the documented explicit non-escalating case; the unreviewed-HEAD WARNING was logged by the leaf.

      - **policy `ask` (any of the four `reason` values)**: fire an `AskUserQuestion` using the three options encoded in the returned `prompt_options[]`. All four reasons are handled identically here — the same three options, the same terminal-record contract — differing only in how the "merge anyway" branch resolves the SHA it stamps (the three rate-window envelopes carry no `head_sha`; see the sub-branch note below). Classify the halt under the existing `blocked_user_review` termination cause (item 5c) when it fires AskUserQuestion. Branch on the operator's selection:
        - **"Wait another {timeout_seconds}s"** → re-dispatch `plan-marshall:automatic-review` from scratch with a fresh budget (re-enter the Step 3 dispatch with the SAME role/level resolution — NOT a SendMessage resume; the harness cannot resume a spawned agent, see the harness-no-resume contract). For `reason: re_review_timeout` the fresh dispatch re-runs the re-review await against a new budget; for the three rate-window reasons it re-runs the refusal-recovery sequence against a fresh `review_rate_window_timeout_seconds` budget. Note that `rate_window_exhausted` is NOT reset by the re-dispatch — the recursion cap is stored per bot per PR and survives, so the fresh dispatch will re-escalate rather than silently re-triggering the bot a third time.
        - **"Merge anyway — proceed unreviewed"** → decision-log a WARNING, then record the terminal step outcome on the `plan-marshall:automatic-review` REQUIRED step BEFORE advancing, then continue the FOR loop (advance to `branch-cleanup`). The terminal record is mandatory: `plan-marshall:automatic-review` is head-dependent (its doc declares `head_dependent: true`) and a REQUIRED step in the `phase_steps_complete` handshake — without an `--outcome done` record on this branch the handshake deadlocks at the 6-finalize phase transition with a `step_record_missing` gap. `plan-marshall:automatic-review` requires a `--head-at-completion {sha}` on its terminal `done` record; resolve `{sha}` by reason:
           - `reason: re_review_timeout` → use the `{head_sha}` from the escalation envelope (the unreviewed commit the operator's decision applies to).
           - `reason: rate_window_timeout` / `rate_window_not_awaitable` / `rate_window_exhausted` → the envelope carries no `head_sha`; resolve the live worktree HEAD via `git -C {worktree_path} rev-parse HEAD` and stamp that.

             python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
               decision --plan-id {plan_id} --level WARNING \
               --message "(plan-marshall:phase-6-finalize) plan-marshall:automatic-review {reason}: user chose merge-anyway — advancing UNREVIEWED head_sha={head_sha}"

             python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
               --plan-id {plan_id} --phase 6-finalize --step plan-marshall:automatic-review --outcome done \
               --display-detail "proceeded unreviewed (head {head_sha})" \
               --head-at-completion {head_sha}

        - **"Defer merge"** → same as `action: defer` above (skip the merge, leave the step record absent so the resumable re-entry check re-issues `plan-marshall:automatic-review` on the next finalize entry, and HALT).

  ### Loop-back Target Contract

  Two invariants govern every loop-back outcome emitted by a phase-6-finalize step. Both are structural: a violation is a contract bug, not a degraded run.

  - **Target phase invariant**: every loop-back-emitting finalize step MUST persist a `loop_back_target` value on its `mark-step-done --outcome loop_back` call. The persisted target MUST be one of `5-execute` or `6-finalize` — no other phases (notably `2-refine`, `3-outline`, or `4-plan`) are legal targets. The two-value enumeration is structural: `5-execute` denotes a full-phase rollback for fix-task-required dispositions (FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`); `6-finalize` denotes inline replay of the same finalize step for inline-fixable dispositions (SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX). The continuation hook (§ 7b below) routes deterministically on the field value — when target is `5-execute`, the loop-back-emitting step also persists `current_phase: 5-execute` via `manage-status set-phase --phase 5-execute` BEFORE its terminal `mark-step-done` call; when target is `6-finalize`, the persisted `current_phase` stays at `6-finalize` (no `set-phase` call) and the continuation hook replays the loop-back-marked step via the resumable re-entry check. Authoritative call sites: `../automatic-review/SKILL.md` and `workflow/sonar-roundtrip.md` — each carries an inline "Loopback target invariant" marker above its `set-phase` block (or, when target is `6-finalize`, above the conditional that suppresses the `set-phase` call) as the structural guard against silent drift. The dispatcher-level enforcement of this invariant lives in `plan-marshall/workflow/execution.md` § "Loop-back continuation" → ELSE branch (the persisted-phase assertion that fires before any user-facing prompt).

  - **Granularity invariant**: loopback granularity is the **triage workflow's responsibility**, encoded in the `loop_back_target` field on the `mark-step-done --outcome loop_back` call. Two granularity tiers govern every loop-back iteration: `5-execute` denotes a **full-phase rollback** for fix-task-required dispositions (FIX with `fix_tasks_created > 0`, `overflow_deferred > 0`) — the continuation hook (§ 7b) re-enters `phase-5-execute` from the top of its `manage-tasks next` loop, the execute pipeline drives the freshly-allocated fix tasks to done, then transitions `5-execute → 6-finalize` via the standard `plan.phase-6-finalize.finalize_without_asking` gate. `6-finalize` denotes an **inline replay** of the same finalize step for inline-fixable dispositions (SUPPRESS, narrow-rationale ACCEPT, single-annotation FIX with no fix-task allocation) — the continuation hook stays in `6-finalize`, does NOT call `set-phase`, and re-fires the loop-back-marked step via the resumable re-entry check. **The dispatcher MUST honour the `loop_back_target` field; it MUST NOT decide granularity itself.** This replaces the prior "all loopbacks are full phase rollbacks" invariant: the answer to the canonical user question "are all loopback-triggered changes done as full phase changes, or are inline changes done as well?" is now **both, depending on the triage classification — fix-task-required dispositions roll back the phase; inline-fixable dispositions replay the same finalize step in place**.

  Cross-references: `../automatic-review/SKILL.md` § "Handle findings (loop-back)" and Branch D, `workflow/sonar-roundtrip.md` § "Handle findings (loop-back)" and Branch D — each carries the conditional `set-phase` / `mark-step-done --loop-back-target` shape described above. `plan-marshall/workflow/triage.md` § Step 7 owns the granularity classification rule (the table that maps disposition types to the two `loop_back_target` values). The dispatcher-level enforcement of the invariant lives in `plan-marshall/workflow/execution.md` § "Loop-back continuation" → ELSE branch (the persisted-phase assertion). The four-corner truth table for the `finalize_without_asking` × `loop_back_without_asking` flag combinations is documented in § 7b below.

  7b. Loop-back continuation hook (consult the just-recorded outcome):
      Read the step's recorded outcome from `status.metadata.phase_steps["6-finalize"][step_id]` (the dispatched agent's `mark-step-done` call wrote it). When `outcome == "loop_back"`, also read the persisted `loop_back_target` field from the same record — it is structurally guaranteed to be present on every `loop_back` outcome (the manage-status `--loop-back-target` validation contract enforces this; absence is a dispatcher contract bug, not a routing case to handle). The two legal values are `5-execute` (full-phase rollback) and `6-finalize` (inline replay).

      **(i) Ceiling admission gate — the FIRST thing item 7b evaluates, on BOTH knob branches.**

      The ceiling is evaluated BEFORE the `loop_back_without_asking` knob is even read, so it bounds the default configuration on the same terms as the auto-continue one. Placing it inside the `value == true` branch — as it was — left `loop_back_without_asking: false` (the DEFAULT) with a declared ceiling that could never be reached: each halt-and-prompt returned control, the operator re-ran finalize, and the count started again from zero, so `max_iterations` bounded only the configuration almost nobody runs. The knob decides HOW a loop-back continues; the ceiling decides WHETHER one is admitted at all, and the second question comes first.

      Read the persisted iteration count. It lives in `status.metadata.loop_back_iteration`, NOT in model context — an in-memory counter is reset by every session restart, every phase re-entry, and every halt-and-prompt cycle, which is exactly what made the declared ceiling unenforceable:

         python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
           --plan-id {plan_id} --get --field loop_back_iteration

      An absent field reads as `0` (no loop-back has been admitted for this plan yet). Capture the value as `{loop_back_iteration}`.

      **The comparison is an ADMISSION test over the iteration about to be spent, not a report on one already spent.** Admitting this loop-back would spend iteration `{loop_back_iteration} + 1`. Refuse to admit it when doing so would exceed the ceiling:

         WHEN `{loop_back_iteration} + 1 > max_iterations` (`phase-6-finalize.max_iterations`, default 3, read in Step 2):

             python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
               work --plan-id {plan_id} --level WARNING \
               --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back ceiling breached — {step_ref} requested iteration {loop_back_iteration + 1} against a ceiling of {max_iterations}; refusing to admit it. The findings this round raised have no remaining iteration in which their fixes could be reviewed."

             Display: "Loop-back ceiling reached: {loop_back_iteration} of {max_iterations} iterations already spent, and {step_ref} asked for another. The run is halting WITHOUT admitting it, so the findings this round raised are recorded but their fixes have NOT been reviewed — no iteration remains in which they could be. Inspect them via 'manage-findings qgate list --plan-id {plan_id} --phase 6-finalize --resolution pending' and the pending fix tasks via 'manage-tasks list --status pending --plan-id {plan_id}', then re-run when ready."

             STOP.

      **This refusal is a distinct terminal outcome**, not the ordinary halt-and-prompt of the `loop_back_without_asking: false` branch below. The two are reported separately on purpose: the knob halt means *"a loop-back is available and awaits your go-ahead"*, whereas this one means *"a loop-back was requested and REFUSED, and the work it would have reviewed is unreviewed"*. Collapsing them into one message would tell an operator the run merely paused where in fact the review chain ended one round short.

      Otherwise the iteration IS admitted. Persist the incremented count BEFORE continuing, so a session lost mid-iteration cannot silently return the plan a free round:

         python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
           --plan-id {plan_id} --set --field loop_back_iteration --value {loop_back_iteration + 1}

      Then emit the canonical iteration log line:

         python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
           work --plan-id {plan_id} --level INFO \
           --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back iteration {loop_back_iteration + 1}/{max_iterations}"

      `max_iterations` keeps its declared default — this gate makes the existing value load-bearing and does not change it.

      **(ii) Symmetric-knob check (AFTER the ceiling gate, BEFORE the granularity branch)** — the `loop_back_without_asking` knob applies uniformly to BOTH granularity tiers and gates whether the admitted loop-back executes inline or halts and prompts. The `loop_back_target` value selects the dispatch shape AFTER this gate passes.

      Consult the symmetric auto-continuation knob to decide whether to halt or re-enter inline:

         python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
           plan phase-6-finalize get --field loop_back_without_asking

      Read the returned `value`:

      - IF `value == false` (default): halt the FOR loop, mark the finalize phase as needing a re-entry, and emit the user-facing prompt (named for the persisted `loop_back_target`). The iteration has already been admitted and persisted, so the operator's re-run resumes against the incremented count rather than a fresh zero:
          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
            work --plan-id {plan_id} --level INFO \
            --message "[STATUS] (plan-marshall:phase-6-finalize) Loop-back signalled by {step_ref} (target={loop_back_target}), iteration {loop_back_iteration + 1}/{max_iterations} admitted: returning control to user (loop_back_without_asking=false)"
        IF `loop_back_target == "5-execute"`:
          Display: "Loop-back signalled. Run '/plan-marshall action=execute plan={plan_id}' when ready to dispatch the fix tasks."
        IF `loop_back_target == "6-finalize"`:
          Display: "Loop-back signalled (inline replay). Run '/plan-marshall action=finalize plan={plan_id}' to replay the finalize step."
        STOP.

      - IF `value == true`: proceed directly to the granularity branch below. The ceiling has already been evaluated and the iteration already persisted at (i), so this branch performs no counting of its own.

      **Granularity branch (AFTER the symmetric-knob and ceiling gates have passed)** — the `loop_back_target` value selects only the dispatch shape. Both branches share the same iteration counter and ceiling.

      - IF `loop_back_target == "6-finalize"` (inline replay for inline-fixable dispositions): the calling step did NOT issue a `manage-status set-phase --phase 5-execute` call, so the persisted `current_phase` is still `6-finalize`. The continuation hook **skips the phase-5-execute re-dispatch entirely** — do NOT call `manage-status set-phase`, do NOT load `Skill: phase-5-execute`. Just BREAK out of the current FOR iteration and RE-ENTER the FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check (item 1 above) sees the `loop_back`-marked step and re-fires it directly.

      - IF `loop_back_target == "5-execute"` (full-phase rollback for fix-task-required dispositions): the calling step issued `manage-status set-phase --phase 5-execute` before its terminal `mark-step-done`, so the persisted `current_phase` is `5-execute`. Dispatch the inline execute pipeline. The inline re-entry mirrors the forward `plan.phase-6-finalize.finalize_without_asking` path (`workflow/execution.md` § Execute Phase Completion) — it runs the execute pipeline against the freshly-allocated fix tasks, transitions back to `6-finalize`, and re-enters this FOR loop:

             1. Set the plan back to phase-5-execute (the loop-back-emitting step typically did this already via `manage-status set-phase`; idempotent re-issue is safe):
                python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
                  --plan-id {plan_id} --phase 5-execute

             2. Dispatch the execute pipeline inline by re-loading `phase-5-execute`:
                Skill: plan-marshall:phase-5-execute
                  Arguments: --plan-id {plan_id}

                The execute pipeline picks up the freshly-allocated fix tasks (created by the FIX disposition or by the overflow-handling path) via the standard `manage-tasks next` loop, drives them to done, then transitions `5-execute → 6-finalize` via the existing `plan.phase-6-finalize.finalize_without_asking` gate. When `finalize_without_asking == false`, the inline re-entry halts at the standard prompt — symmetric loop-back is gated by both knobs in series, so a project can opt into automated forward continuation without also opting into automated loop-back continuation.

             3. After phase-5-execute returns, BREAK out of the current FOR loop iteration position and RE-ENTER the FOR loop from the start of `manifest.phase_6.steps`. The resumable re-entry check (item 1 above) skips already-`done` steps, retries `failed` steps, and re-fires the `loop_back`-marked step now that its preconditions have been addressed.

             Note: the BREAK + RE-ENTER above is a control-flow construct, not a per-step skip. The FOR loop re-iteration uses the same manifest list and the same per-step resumable check; the only state that changes is the `phase_steps["6-finalize"][step_id]` records (the dispatched agent will record a fresh outcome on its next run).

      The `loop_back_iteration` counter is PERSISTED to `status.metadata.loop_back_iteration` and read back at (i) on every evaluation. It is deliberately NOT held in model context: a counter that lives only for the duration of one dispatch is reset by a session restart, by a phase re-entry, and — most importantly — by every halt-and-prompt cycle of the default `loop_back_without_asking: false` configuration, which is precisely the path that loops most. A fresh phase-6-finalize entry therefore resumes against the count the previous entry left behind rather than starting over at 0, so the ceiling bounds the plan's whole review chain instead of one uninterrupted dispatch. The manifest's resumable re-entry check is unchanged: it still skips already-`done` steps, so re-entering after a restart re-runs only the steps that recorded `loop_back` or `failed` on the previous invocation.

  7c. Wait-region unified triage hook (fires after the LATER wait-region producer completes):

      The two wait-region producers (`plan-marshall:automatic-review`, `default:sonar-roundtrip`) are FIND-only — each is gated on its own `_ci_barrier` arm (the per-signal precondition: `review` / `sonar` arm), files its `pr-comment` / `sonar-issue` findings, marks done, and dispatches NO triage of its own. After BOTH have FILED, the dispatcher runs ONE unified triage over the union of their pending findings, replacing the two retired per-producer triage dispatches (`producer=pr-comment`, `producer=sonar`) with a single pass via the `producer=finalize-feedback` mode — see [`../plan-marshall/workflow/verification-feedback.md`](../plan-marshall/workflow/verification-feedback.md) § "Producer modes".

      Fire this hook when the just-completed step is the LATER of the two producers present in `manifest.phase_6.steps` (canonically `default:sonar-roundtrip`, which the manifest orders after `plan-marshall:automatic-review`) AND every wait-region producer that IS in the manifest has recorded a terminal `done` outcome on `status.metadata.phase_steps["6-finalize"]`. When only one of the two producers is in the manifest, that one is the "later" producer and the union query naturally covers only its finding-type.

      (1) Resolve the level-bound target under the `verification-feedback` role:
          ```bash
          python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
            effort resolve-target --phase phase-6-finalize --role verification-feedback
          ```
      (2) Emit the standardized `[DISPATCH]` work-log line (see [`../ref-workflow-architecture/standards/dispatch-logging.md`](../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract). This hook's `role` is `verification-feedback` and its `workflow` is the unified-triage workflow doc:
          ```bash
          python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
            work --plan-id {plan_id} --level INFO \
            --message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=verification-feedback workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md plan_id={plan_id}"
          ```
          The emit and the item-(3) `Task:` spawn below are ONE indivisible pair, exactly as at the two dispatch-branch emit sites: dispatching this hook without first writing the line is a contract violation, not a cosmetic omission.
      (3) Dispatch ONE `verification-feedback` envelope with `producer=finalize-feedback` over the union — by reference (the subagent issues its own union `manage-findings list` as its first workflow step):
          ```text
          Task: plan-marshall:{target}
            prompt: |
              name: wait-region-unified-triage
              plan_id: {plan_id}
              skills[7]:
              - plan-marshall:manage-findings
              - plan-marshall:manage-tasks
              - plan-marshall:manage-architecture
              - plan-marshall:manage-config
              - plan-marshall:manage-execution-manifest
              - plan-marshall:workflow-integration-github
              - plan-marshall:workflow-integration-sonar
              workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md

              producer: finalize-feedback
              caller_phase: phase-6-finalize
              pr_number: {pr_number}

              WORKTREE: {worktree_path}
          ```
      (4) Consume the return. The unified triage owns the RESPOND loop (both `github_pr post_responses` for `pr-comment` thread-replies AND `sonar post_responses` for `sonar-issue` server-side dismissals, each keyed by `hash_id`). On `status: loop_back` (FIX dispositions created fix tasks OR overflow deferred), route it through the SAME continuation machinery as item 7b: read `loop_back_target` from the return, apply the symmetric `loop_back_without_asking` knob + the `max_iterations` ceiling, then re-enter per the granularity branch (`5-execute` full-phase rollback / `6-finalize` inline replay). A `6-finalize` re-entry re-fires the wait-region producers (they are HEAD-dependent — a fix commit advanced HEAD), which re-FIND against the new tree, and this hook runs the unified triage again. On `status: success`, every pending finding resolved with no loop-back — continue the FOR loop.

      This hook is dispatcher-owned and produces NO `phase_steps["6-finalize"]` record of its own (it is not a manifest step); the wait-region producer steps carry the `done` records. The single unified pass is the ONLY place `pr-comment` and `sonar-issue` findings are triaged in finalize — the retired per-producer `producer=pr-comment` and `producer=sonar` dispatches no longer run.
END FOR
```text

**Critical invariant**: This loop iterates **only** the manifest list. A step that is NOT in `manifest.phase_6.steps` MUST NOT fire under any circumstance — there is no fallback to a "default" step set, no inference from config booleans, no per-step skip logic. The manifest is the contract. If a deployment requires a different step set, recompose the manifest at outline time.

**Lessons-capture unconditionality**: When `lessons-capture` IS in `manifest.phase_6.steps` (the composer includes it for every non-trivial change-type), this loop dispatches it on every Phase 6 entry. It is not gated on PR state, CI state, or earlier step outcomes — reaching Phase 6 is itself the trigger.

**Adr-propose conditionality**: `adr-propose` is its sibling under the `post-run-review` role but is dispatcher-gated, not unconditional. When `adr-propose` IS in `manifest.phase_6.steps` (the composer includes it alongside `lessons-capture` for every non-trivial change-type), the loop evaluates the decision-shape Signal Gate (Step 3 § "Adr-propose Signal Gate") on every Phase 6 entry. The envelope is dispatched only when the plan carries a decision-shape signal; absent one, the dispatcher records `outcome=skipped` directly without spawning the envelope.

**Symmetric auto-continuation invariant**: The `loop_back_without_asking` flag is the structural counterpart to `plan.phase-6-finalize.finalize_without_asking`. The two knobs together define the four corners of the unattended-vs-interactive matrix:

| `finalize_without_asking` | `loop_back_without_asking` | Behaviour |
|---------------------------|----------------------------|-----------|
| `false` | any | The forward `5-execute → 6-finalize` transition halts and prompts the user. Loop-back never fires inline because finalize is not entered in the same orchestration cycle. |
| `true` (default) | `false` (default) | Forward auto-continuation; loop-back halts at the inline execute re-entry point and prompts the user. (This is the conservative shape: forward is automated, reverse is interactive.) Bounded by `max_iterations` exactly as the row below — the ceiling is evaluated before this knob is read, and the count is persisted, so the operator's re-run resumes against it instead of restarting at zero. |
| `true` | `true` | Full unattended cycle. A loop_back outcome re-dispatches execute inline up to `max_iterations` times, then refuses to admit a further one even with the flag set. |
| `false` | `true` | Effectively `false`/`false` from the user's perspective: forward halts and prompts before phase-6-finalize ever runs, so the loop-back hook is unreachable in the same orchestration cycle. |

**The ceiling binds both rows.** It is evaluated at the item-7b admission gate BEFORE `loop_back_without_asking` is consulted, and its count is persisted to `status.metadata.loop_back_iteration`. A ceiling evaluated inside the `value == true` branch, counting in model context, would leave the DEFAULT configuration unbounded in practice: every halt-and-prompt returns control, and a re-entry that restarted the count at zero would let a plan loop indefinitely one operator re-run at a time while `max_iterations` was nominally in force.

The conservative default (`loop_back_without_asking=false`) ships an interactive shape so existing plans behave the same as before this knob was added. Projects that want full unattended execution must opt into both knobs. Note the mechanics differ from the same-suffixed merge knob: `loop_back_without_asking=false` halts the dispatcher and *instructs* the operator via a Display + STOP prompt (no `AskUserQuestion` is fired — see § "Loop-back continuation hook" item 7b), whereas `final_merge_without_asking=false` fires a genuine inline pre-merge `AskUserQuestion` gate (see [standards/branch-cleanup.md](standards/branch-cleanup.md) § "Pre-Merge Confirmation Gate") — same suffix, opposite mechanics.

#### Post-dispatch completion guard

The post-dispatch completion guard sub-step above (the `assert-step-recorded` check inside the dispatch branch) is the deterministic completion guard. It calls the read-only `plan-marshall:manage-status:manage-status assert-step-recorded` verb with `--require-terminal` after every dispatched-step return and converts a missing terminal record into an attributed `failed` outcome plus a pipeline halt. Three placement facts govern its interaction with the rest of the Execute Step Pipeline step:

- **Placement relative to resumable re-entry**: the guard fires at the END of a FOR-loop iteration (after the dispatch and the metrics items 5b/5c), whereas the resumable re-entry check (item 1) runs at the START of each iteration. The `failed` record the guard writes is therefore retried by the start-of-iteration resumability check on the next finalize entry — the guard does not re-fire the step itself; it records the violation and halts, and the existing `failed`→retry path picks it up. This reuses the existing control flow with zero new branches.

- **Interaction with the HEAD-dependent table**: the guard is orthogonal to the HEAD-dependent re-fire table (the `head_at_completion` comparison in item 1 and § HEAD-dependent steps), which is consulted at iteration start to decide SKIP vs RE-FIRE for a head-dependent step. The guard only asserts that *some* terminal record exists; it does not read or compare `head_at_completion`. A `loop_back` record counts as terminal for guard purposes, so a loop-back-emitting step satisfies the guard and proceeds to item 7b unchanged.

- **Relationship to the `phase_steps_complete` handshake**: the guard is the earlier, attributed sibling of the existing `phase_steps_complete` handshake invariant (see [standards/required-steps.md](standards/required-steps.md)). The handshake catches a missing step record at the phase transition, but with no per-step attribution — it only reports that the phase is incomplete. The guard catches the same omission immediately after the offending step returns, names the step, and halts, so the violation surfaces at per-step granularity in the work-log and the Step 4 output template rather than as an opaque transition deadlock.

- **`escalate_ask` guard invariant**: `escalate_ask` is a legitimate non-terminal return owned exclusively by item 7a (the escalate-ask continuation hook). When `plan-marshall:automatic-review` returns `status: escalate_ask` — for EITHER `reason: re_review_timeout` (trigger B re-review await timeout under an `ask` or `defer` policy) or `reason: rate_window_timeout` (the rate-window await loop exhausting its budget) — the leaf legitimately recorded no terminal `mark-step-done` outcome because the continuation — firing the `AskUserQuestion`, or deferring the merge — belongs to item 7a, not to the leaf. The completion guard MUST NOT assert terminality for an `escalate_ask` return regardless of `reason`: doing so produces a false `step_record_missing` halt that fires BEFORE item 7a runs, leaving item 7a unreachable for the escalate-ask path. This is the dispatcher-side half of the symmetric no-mark contract — the leaf does not record terminality (see [`../automatic-review/SKILL.md`](../automatic-review/SKILL.md) § "`escalate_ask` return (timeout escalations)"), and the guard does not assert it.

The guard is scoped to dispatched (Task-agent) steps only, and within that scope it exempts three classes uniformly — inline steps record their mark synchronously in the main context, the item-5 timeout path already records `outcome=failed`, and `escalate_ask`-returning steps legitimately leave no terminal record because item 7a owns their continuation. All three are exempt under the same gate as items 5b/5c, extended in item 5d with the `escalate_ask` carve-out.

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
See [standards/output-template.md#snapshot-procedure](standards/output-template.md#snapshot-procedure) for exact commands and field extraction.

After the snapshot is captured, dispatch `default:archive-plan` normally (step 5 in the FOR body above) and capture its returned `archive_path` (step 6). Both the snapshot and `archive_path` flow into Step 4 "Render Final Output Template".

#### Issue-documentation mode — milestone (c): mirror the final completion block

After the merge has completed but BEFORE `default:archive-plan` runs (the plan directory must still be live so the `--plan-id` body store resolves), if the plan originated from a GitHub issue, post the final `[MERGED]` PR completion block to the originating issue as a comment so the issue thread records the shipped outcome. The hook is placed after the merge so the block reflects final state, and pre-archive so the body store is still resolvable via `--plan-id`. It is a clean no-op when the plan did not originate from an issue OR when the PR did not reach a merged state.

1. Read `source` and `source_id` from `request.md` (the plan dir is still live at this point):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
     --plan-id {plan_id}
   ```

   When `source != issue`, skip the entire hook — no comment is posted. When the pre-archive snapshot's PR `state != merged`, also skip (the block only mirrors a merged outcome).

2. Derive the issue number from `source_id` by splitting the issue URL on `/issues/` and taking the first path segment of the tail.

3. Render the same `[MERGED]` PR completion block that Step 4 emits (from the in-memory pre-archive snapshot — `standards/output-template.md` § Emission Procedure), then post it as a single comment via the path-allocate flow documented in [`tools-integration-ci/standards/issue-operations.md`](../tools-integration-ci/standards/issue-operations.md) § "Workflow: Comment on Issue" (`ci issue prepare-comment` → Write the block → `ci issue comment --issue {issue_number} --plan-id {plan_id}`). The canonical call shape is the `### issue` block in [`tools-integration-ci/SKILL.md`](../tools-integration-ci/SKILL.md) § Canonical invocations — do not inline-copy it here.

**Forbidden**: direct `gh` / `glab`. All issue interactions route through `plan-marshall:tools-integration-ci:ci`.

**Built-in step notes**:
- `default:branch-cleanup`: Do NOT preemptively skip based on PR state. The executor always runs to completion and records `outcome=done` — the dispatcher contract is unchanged. The standard's internal `AskUserQuestion` confirmation gate is now **conditional on a conflict-severity classifier** (`baseline-reconcile --no-emit`) per `standards/branch-cleanup.md` § "Conflict-Severity Classifier": clean / auto-resolvable rebases bypass the prompt under the default `no_overlap_only` threshold; genuine `overlap_with_content_conflict` cases still fire the prompt. Only the standard's internal user-interaction surface narrowed; the dispatcher continues to treat the step as a single inline run-to-completion.
- `default:record-metrics`: MUST be the last token-accounting step — it runs after all token-consuming finalize steps (`plan-marshall:plan-retrospective`, `project:finalize-step-lessons-housekeeping`) and before the read-only `default:finalize-step-print-phase-breakdown` / `default:archive-plan` tail, so its `end-phase` accumulator read folds the full phase token spend (including retrospective and lessons-housekeeping) into the closed `6-finalize` row. This step finalizes the `6-finalize` phase with two `manage-metrics` writes (`end-phase` for the closing phase + `generate` for `metrics.md`) and a separate `enrich` for session token capture. Plan finalization has no "next phase" so the fused `phase-boundary` subcommand does not apply here — see `standards/record-metrics.md` for the authoritative sequence. All writes MUST land on the live plan directory; if archive runs first, the target directory no longer exists and each command would recreate a post-archive orphan under `.plan/local/plans/{plan_id}/`.
- `default:archive-plan`: This step MUST be last in the default order because it moves plan files (including status.json), which breaks manage-* scripts. All plan operations must complete before archive.

Do NOT add any further `manage-metrics` invocations after `default:archive-plan` or after `Skill: plan-marshall:phase-6-finalize` returns to its caller. The plan-finalization bookkeeping (`end-phase` + `enrich` + `generate`) is fully contained by `default:record-metrics`.

### Step 4: Render Final Output Template

`default:archive-plan` in Step 3 atomically marks the active phase done and sets `current_phase: complete` on the live status.json BEFORE moving the plan directory — see `manage-status:_cmd_lifecycle.py cmd_archive`. A separate `manage-status transition --completed 6-finalize` call MUST NOT be issued from this phase; it would fail with `file_not_found` because archive has already invalidated the live path.

**This step ALWAYS runs** — it is NOT configurable via the `steps` list. It is the terminal action of the phase, invoked after `default:archive-plan` returns in Step 3.

Load the renderer specification:

```text
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
5. Build the Finalize steps block (one row per configured step, padded 33-char name + `display_detail`). When the Phase Breakdown override is active (see `standards/output-template.md § ## Phase Breakdown Override`), the per-step iteration substitutes the `record-metrics` row with the literal `Phase Breakdown` header + blank line + verbatim `phase_breakdown_override_content`. Every other step row emits unchanged.
6. Build the Repository trailer (main state | worktree token | working tree state).
7. Emit the five blocks separated by blank lines as a plain-text, user-facing output.

**No additional script calls are needed for this step** — the renderer consumes only the in-memory snapshot plus `archive_path`. It performs no `manage-status` / `manage-solution-outline` / `ci pr view` reads of its own.

The emitted template is a **user-facing text block printed to the model's output**, not a log entry. It is the primary surface reported to the user at the end of the finalize phase.

### Step 5: Log Phase Completion

Final metrics are already recorded inside the Step 3 pipeline by `default:record-metrics` (the last token-accounting step, which runs after all token-consuming steps and before the `print-phase-breakdown`/`archive-plan` tail). This step only logs phase completion to work.log.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan completed: {steps_count} steps executed"
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  separator --plan-id {plan_id} --type work
```

**Note**: `manage-logging` operates on log files, not the plan directory, so these calls remain valid after `default:archive-plan` has moved the plan state.

---

## Output

**Success** (user-facing):

The primary output is the five-block template rendered by Step 4. It is a plain-text, user-facing block — not TOON — assembled from the pre-archive snapshot plus `archive_path`. See [standards/output-template.md](standards/output-template.md) for the full renderer specification.

Example:

```text
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
  [OK]  push                              -> a1b2c3d
  [OK]  create-pr                         #212
  [OK]  plan-marshall:automatic-review                  3 comment(s) resolved (no loop-back)
  [OK]  sonar-roundtrip                   quality gate passed
  [OK]  lessons-capture                   no lessons recorded
  [OK]  adr-propose                       no ADRs proposed
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

**Special case — head-dependent steps** (`pre-push-quality-gate` is the canonical example): a head-dependent step's resumable check is augmented with a worktree-HEAD comparison so a loop-back commit re-fires the gate instead of skipping it on a stale `done`. The augmented rule applies to exactly the steps whose authoritative doc declares `head_dependent: true` — see § "Special case — HEAD-dependent steps" in Step 3 for the single authoritative statement of that membership and its governing discriminator. Every step that does not declare the fact uses the general table above verbatim.

| Outcome on re-entry | `head_at_completion` vs live HEAD | Action |
|---------------------|-----------------------------------|--------|
| `done` | matches live `git -C {worktree_path} rev-parse HEAD` | Skip dispatch entirely (steady-state — gate already validated this exact tree). |
| `done` | differs from live HEAD | Re-fire (treat as no record — HEAD has advanced past the validated SHA, e.g., after a loop-back commit). |
| `done` | `head_at_completion` field absent | Re-fire AND report the prior verdict UNVERIFIED — a record with no SHA was never anchored to a tree, so it is never left standing as green. |
| `failed` | n/a | Retry from scratch (unchanged). |
| (no record) | n/a | Dispatch as a first-time run (unchanged). |
| any other value | n/a | Dispatch as a first-time run (unchanged). |

The live HEAD MUST be resolved fresh per iteration via `git -C {worktree_path} rev-parse HEAD` — do NOT cache across the loop, so a step that advances HEAD mid-loop is observed correctly by every later check. Cross-reference: `standards/pre-push-quality-gate.md` "Mark Step Complete" Branch A, which persists `head_at_completion` on the success path.

This makes finalize safe to interrupt and re-enter — completed work is preserved, failed work gets a retry, never-run work runs for the first time, and the HEAD-dependent quality gate re-fires whenever the tree it validated has been superseded. There is no separate "resume" mode; every Phase 6 entry is implicitly resumable.

In-step state checks (consulted by individual standards docs after dispatch — these guard idempotent operations, not skip activation):

1. **Uncommitted changes?** `git status --porcelain` — the dispatcher's commit instrumentation (item 5f) commits any `mutates_source: true` step's output before the `push` barrier runs, so `push` asserts a clean tree and pushes.
2. **PR exists?** `ci pr view` — `status: success` → `create-pr` re-uses the existing PR.
3. **Plan complete?** `manage-status read` — `current_phase: complete` → finalize has nothing to do; return immediately.

---

## Standards (Load On-Demand)

| Standard | Step Name | Purpose |
|----------|-----------|---------|
| `standards/finalize-step-sync-baseline.md` | `default:finalize-step-sync-baseline` | Early baseline rebase — `baseline-reconcile --no-emit` classify + `worktree-rebase-to` onto `origin/{base_branch}` at the start of finalize (no force-push, no `ci wait` at this order); `auto_rebase_threshold`-gated |
| `workflow/pre-submission-self-review.md` | `default:pre-submission-self-review` | Deterministic helper (resolved via `ext-self-review-{domain}` ext-point) + LLM cognitive review for symmetric-pair / regex-overfit / wording / duplication / contract-drift defects (hard-fail) |
| `standards/push.md` | `default:push` | Pure push barrier — freshness precondition + workflow-integration-git push (no commit logic; the dispatcher's instrumentation owns commits) |
| `workflow/create-pr.md` | `default:create-pr` | PR existence check, body generation, CI pr create |
| `standards/ci-verify.md` | `default:ci-verify` | Inline deterministic executor (`scripts/ci_verify.py`) — green CI marks done with zero dispatch; red CI classifies failures into the multi-failure-mode taxonomy, files one triage finding per failing check, and returns a per-producer needs-triage signal |
| `standards/architecture-refresh.md` | `default:architecture-refresh` | Tier-0 deterministic `architecture discover --force` + `diff-modules --pre` driven `chore(architecture)` commit; Tier-1 LLM re-enrichment with `prompt`/`auto`/`disabled` modes; respects `architecture_refresh.tier_0` / `tier_1` run-config knobs and `change_type ∈ {bug_fix, verification}` shortcut |
| `../automatic-review/SKILL.md` | `plan-marshall:automatic-review` | Review-bot comment FIND (per-signal review-arm gate; file `pr-comment` findings); the unified wait-region triage consumes them. Architectural flow: [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) |
| `workflow/sonar-roundtrip.md` | `default:sonar-roundtrip` | Sonar FIND (fetch new-code issues, file `sonar-issue` findings); the unified wait-region triage consumes them. Architectural flow: [`findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md) |
| `workflow/lessons-capture.md` | `default:lessons-capture` | manage-lesson add command |
| `workflow/adr-propose.md` | `default:adr-propose` | manage-adr create command — propose ADRs from plan decisions (advisory, dispatcher-gated) |
| `standards/branch-cleanup.md` | `default:branch-cleanup` | Branch cleanup with user confirmation — PR mode (merge + CI) or local-only (switch + pull) |
| `standards/record-metrics.md` | `default:record-metrics` | Record final plan metrics before archive |
| `standards/finalize-step-print-phase-breakdown.md` | `default:finalize-step-print-phase-breakdown` | Optional override mode: capture Phase Breakdown table for the renderer (replaces per-step [OK] block) |
| `standards/archive-plan.md` | `default:archive-plan` | Archive the completed plan |
| `standards/output-template.md` | — | Renderer specification for the five-block final output template (Step 4) |
| `standards/required-steps.md` | — | Canonical list of steps enforced by the `phase_steps_complete` handshake invariant |
| `standards/source-edit-pushability.md` | — | General contract for finalize steps that edit source: a source-editing step MUST run pre-merge so its edit is pushable and CI-covered; a step that discovers an edit only post-merge MUST emit an explicit follow-up artifact, never silently revert. `project:finalize-step-era-stamp-fill` is the reference implementation |
| `standards/validation.md` | — | Configuration requirements, error scenarios |
| `standards/lessons-integration.md` | — | Conceptual guidance on lesson capture |

---

## Templates

| Template | Purpose |
|----------|---------|
| `templates/pr-template.md` | PR body format |

---

## Scripts

| Script | Notation | Purpose |
|--------|----------|---------|
| `scripts/ci_verify.py` | `plan-marshall:phase-6-finalize:ci_verify` | Inline deterministic `default:ci-verify` executor — green CI marks the step done with zero dispatch; red CI classifies failures and returns a per-producer needs-triage signal |
| `scripts/ci_complete_precondition.py` | `plan-marshall:phase-6-finalize:ci_complete_precondition` | Resolver for the `requires: [ci-complete]` frontmatter precondition, with a per-HEAD cache and a harness-ceiling clamp |
| `scripts/derive_gate_bundles.py` | `plan-marshall:phase-6-finalize:derive_gate_bundles` | Derives the unique bundle set the pre-push quality gate runs over, from the live footprint |
| `scripts/pr_intent_section.py` | `plan-marshall:phase-6-finalize:pr_intent_section` | Renders the distilled `## Intent` section into the generated PR body — owns the character budget and its visible truncation, and omits the section entirely (heading included) when the plan has no outline intent |
| `scripts/post_run_source_guard.py` | `plan-marshall:phase-6-finalize:post_run_source_guard` | Runtime tracked-source guard for the `post_run_review` band (item 5f sub-item 0) — reports dirty TRACKED paths outside `.plan/` left by a step that declared `mutates_source: false`; advisory and non-blocking (always exits 0) |

## Canonical invocations

The canonical argparse surface for `ci_complete_precondition.py`, `pr_intent_section.py` and `post_run_source_guard.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### ci_complete_precondition — resolve

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_complete_precondition resolve \
  --plan-id PLAN_ID --worktree-path WORKTREE_PATH --pr-number PR_NUMBER \
  [--timeout TIMEOUT] [--mode {strict,consume-failures}] [--signal-arm {ci,review,sonar}]
```

### pr_intent_section — render

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:pr_intent_section render \
  --plan-id PLAN_ID --draft-path DRAFT_PATH --body-path BODY_PATH
```

### post_run_source_guard — check

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:post_run_source_guard check \
  --step-id STEP_ID --project-dir MAIN_CHECKOUT
```

`--project-dir` is required and takes the MAIN CHECKOUT — it carries no default
because every caller runs after `default:branch-cleanup` removed the worktree,
so a cwd default would silently observe a deleted tree.

## Related

| Resource | Purpose |
|----------|---------|
| [references/workflow-overview.md](references/workflow-overview.md) | Visual diagrams: 6-Phase Model and Shipping Pipeline |
| `plan-marshall:persona-plan-marshall-agent` | Bash safety rules, tool usage patterns |
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
