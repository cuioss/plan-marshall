---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Verification-Feedback Workflow

Thin orchestrator that unifies the LLM-driven feedback flows under a single dispatch shape and enforces the consolidated **FIND → INGEST → TRIAGE → RESPOND** pipeline. Branches on the `producer` runtime input for the producer-side FIND work in Step 1, runs the single batched INGEST pass (Step 1.6) that promotes every quarantined `raw_input.{field}` value to the clean top-level fields, hands off to the canonical Steps 1-6 in [`triage.md`](triage.md) for the per-finding FIX / SUPPRESS / ACCEPT / AskUserQuestion loop (which reads TOP-LEVEL fields only, never `raw_input.*`), then transmits the decided dispositions back to the provider in the RESPOND loop (Step 8, `post_responses` / `sonar_rest transition`, keyed by `hash_id`). On GitHub, under `producer=finalize-feedback`, a `fixed` disposition is held there until its fix commit is stamped on the finding, and is transmitted by a second respond pass that the phase-6-finalize hook runs; under every other producer it is transmitted in Step 8 with the rest.

Dispatched under the **phase-scoped** `verification-feedback` role key — the resolver bubbles from `<caller-phase>.verification-feedback` to `<caller-phase>.default` to `effort`. Phase-5 dispatches use `--phase phase-5-execute --role verification-feedback`; every phase-6-finalize dispatch (finalize-feedback, plugin-doctor, pr-state) uses `--phase phase-6-finalize --role verification-feedback`. The standalone `sonar` and `pr-comment` producer modes are retired as finalize dispatch modes — `sonar-roundtrip` and `automatic-review` are now FIND-only and no longer dispatch this workflow themselves; the dispatcher-owned `finalize-feedback` mode triages the union of their filed findings instead (see the Producer modes table below).

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Producer modes

| `producer` | Caller surface | Producer-side work (Step 1) | Pre-flight gate |
|------------|----------------|-----------------------------|-----------------|
| `build-runner` | phase-5-execute Step 11 + Step 11b | Build-runner / quality-gate log parse → findings store. **Mechanical, pre-flight** — the orchestrator runs the build, captures findings via `manage-findings add`, dispatches this workflow only when `manage-findings list | count > 0`. Step 1 here is a store-only query. | Count > 0 |
| `sonar` | **Retired as a finalize dispatch mode.** `sonar-roundtrip` still runs `workflow-integration-sonar:sonar fetch_findings` to file its `sonar-issue` findings, but it no longer dispatches this workflow itself — it is FIND-only and marks done after filing. Superseded by `producer=finalize-feedback` below, which triages the union including these findings. | — |
| `pr-comment` | **Retired as a finalize dispatch mode.** `automatic-review` still runs `workflow-integration-github:github_pr fetch_findings` (or GitLab equivalent) to file its `pr-comment` findings, but it no longer dispatches this workflow itself — it is FIND-only and marks done after filing. Superseded by `producer=finalize-feedback` below, which triages the union including these findings. | — |
| `plugin-doctor` | `project:finalize-step-plugin-doctor` + `/plugin-doctor` slash command | Marketplace static analysis — **LLM-heavy**, runs inside this envelope as Step 1: iterate the plugin-doctor rule catalog in-context, scope-filter, emit one finding per violation to the store. | None — analysis IS the producer step. |
| `pr-state` | `/workflow-pr-doctor` slash command | Wait for CI checks; fetch build status, PR comments, and Sonar issues sequentially; emit each finding-type to the store. Step 1 here orchestrates the multi-source sweep, then the unified triage in Steps 3-6 processes the aggregated set. | None — the producer always runs; Steps 3-6 short-circuit on zero findings. |
| `finalize-feedback` | phase-6-finalize dispatcher (wait-region), after both `plan-marshall:automatic-review` and `default:sonar-roundtrip` have FILED | **No producer FIND** — the two wait-region producers already filed their `pr-comment` / `sonar-issue` findings via their own per-signal-gated FIND steps. Step 1 here is a single store-only union query over pending `pr-comment` ∪ `sonar-issue`. Collapses the retired per-producer `producer=pr-comment` and `producer=sonar` finalize triage dispatches into ONE pass over the union, mirroring the `pr-state` multi-source→one-triage precedent. | None — the producers already filed; Steps 3-6 short-circuit on zero findings. |

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `producer` | Yes | Single accept-set: one of `build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`, `finalize-feedback`. Selects the Step 1 branch and which `ext-triage-{domain}` skills are pre-loaded in Step 2. `ci-verify-timeout` is rejected on every producer path — it is a `default:ci-verify` taxonomy producer string (row h, Timeout), not a `producer` value; the owning producer of the rejection is `default:ci-verify`. |
| `plan_id` | Yes | Forwarded to every `manage-findings` / `manage-tasks` / `tools-integration-ci` call. |
| `WORKTREE` | Yes | Used verbatim for `git -C {WORKTREE}` and as the root for every Edit/Write/Read. |
| `pr_number` | Conditional | Required for `pr-comment` (thread replies) and for `pr-state` (CI wait + multi-source fetch). |
| `caller_phase` | Optional | Explicit caller-phase override the main-context orchestrator passes when dispatching this phase-agnostic workflow, so the level resolver tracks the caller's phase. See `ext-point-execution-context-workflow.md` § Phase-context propagation for phase-agnostic workflows. |
| `iteration` | No | The requesting source's own loop-back round number, forwarded by the dispatcher. It counts that source's rounds only and has no fixed upper bound. Surfaced in `display_detail` on `loop_back` outcomes. |

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
- `producer=finalize-feedback` — also forward BOTH RESPOND-loop providers `plan-marshall:workflow-integration-github` (or `…-gitlab`) and `plan-marshall:workflow-integration-sonar`, since the unified pass responds to both `pr-comment` thread-replies and `sonar-issue` server-side dismissals (mirroring `pr-state`).
- `producer=plugin-doctor` — also forward `pm-plugin-development:plugin-doctor` (rule catalog + references) and `pm-plugin-development:tools-marketplace-inventory`.

Domain-triage extensions (`{bundle}:ext-triage-{domain}`) are loaded on demand inside Steps 3-6 — they are NOT pre-loaded by the caller.

## Step 1: Producer-mode branch

### Guard: `producer` input validation (input boundary)

Validate the `producer` runtime input against the accept-set (`build-runner`, `sonar`, `pr-comment`, `plugin-doctor`, `pr-state`, `finalize-feedback`) BEFORE entering any Step 1 branch. When the value is outside the accept-set, STOP — do not enter the shared ingestion/triage flow — and return:

```toon
status: error
error: unknown_producer
producer: {received value}
display_detail: "unknown producer: {received value}"
```

`ci-verify-timeout` is rejected here on every producer path — it is a `default:ci-verify` taxonomy producer string, not a `producer` value; the owning producer of the rejection is `default:ci-verify` (see the Inputs table note).

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

   On `status: success`, read `pr_number` from the TOON output. A `status: error` is NOT a no-PR signal: one envelope covers several materially different causes and its `error` message is hard-coded to the no-PR wording, so only the `error_cause: no_pr_found` arm establishes that the branch genuinely has no PR — that arm alone returns `status: success`, `display_detail: "no PR available — nothing to triage"`. Every other cause, and an absent `error_cause`, leaves the question UNANSWERED rather than answered "no"; STOP and return an error TOON preserving the stdout error envelope as emitted. The discriminator's vocabulary and its per-arm field sets are owned by [`tools-integration-ci/standards/api-contract.md`](../../tools-integration-ci/standards/api-contract.md) § "`pr view` and the `error_cause` discriminator" and are deliberately not restated here.

3. **Wait for CI** (when `wait=true`, default). Pass `--adaptive` so this wait seeds its ceiling from — and records its observed duration back into — the persisted `ci:wait` budget (the same #849 ratchet `ci_complete_precondition` drives), instead of the fixed `DEFAULT_CI_TIMEOUT`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
     --project-dir {worktree} checks wait --pr-number {pr_number} --adaptive
   ```

   Bash tool timeout: pass the seam-resolved host cap (`harness bash-timeout-ceiling` — 600s on the Claude target); `--adaptive` seeds the inner `ci:wait` budget from the persisted budget so the wait converges on observed CI durations rather than a fixed baseline. On timeout, `AskUserQuestion` (continue / skip / abort).

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

### Branch: `producer=finalize-feedback` (store-only union over pr-comment ∪ sonar-issue)

This is the finalize-scoped store-only sibling of `pr-state`: it does NO producer FIND. Both wait-region producers have already FILED their findings before this dispatch — `plan-marshall:automatic-review` filed the `pr-comment` findings and `default:sonar-roundtrip` filed the `sonar-issue` findings, each gated on its own `_ci_barrier` arm reaching a terminal state (the per-signal FIND gate). This mode collapses the two retired per-producer triage dispatches (`producer=pr-comment` and `producer=sonar`) into ONE triage pass over the union.

Query the store for the union of pending `pr-comment` and `sonar-issue` findings — `--include-qgate` merges the pending per-phase Q-Gate findings into the per-plan read so the union is a single unified query (see `manage-findings` Canonical invocations → `list`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id {plan_id} --resolution pending --include-qgate
```

If empty, return `status: success`, `display_detail: "0 finding(s) — nothing to triage"`, `loop_back_needed: false`. Otherwise continue to Step 1.4 — the pass then falls through the shared pipeline unchanged: Step 1.4 batched INGEST, Step 2 extension load (BOTH the `pr-comment` and `sonar` triage extensions load, one per finding-type present), Steps 3-6 TRIAGE with smart-grouping (a defect flagged by both CodeRabbit and Sonar is co-located into one batched LLM decision by the pre-group step), and Step 8 unified RESPOND (BOTH `github_pr post_responses` for the `pr-comment` thread-replies AND `sonar post_responses` for the `sonar-issue` server-side dismissals, each keyed by its own `hash_id`).

**Cross-producer dedup is intentionally deferred.** A defect flagged by BOTH CodeRabbit and Sonar lands as two findings (one `pr-comment`, one `sonar-issue`); this mode does NOT hard-merge them. The Step 2 smart-grouping (`triage.md` § Step 2 pre-group) already co-locates the related findings into one batched LLM decision, so the doubly-flagged defect is triaged coherently WITHOUT a hard dedup, and each finding keeps its own provider RESPOND surface (a `pr-comment` thread-reply vs a `sonar-issue` server-side dismissal keyed by `hash_id`) — merging to one finding would strand one provider's response. A future plan may add dedup against a concrete measured need.

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

`loop_back_needed: true` when any decision in any group resolved to FIX, as a task fix or as an inline fix, when any group deferred via overflow, or when any decision resolved to another inline-fixable disposition that needs the calling step replayed — SUPPRESS, or a narrow-rationale ACCEPT. A SUPPRESS annotation edits a file in the worktree, so a run whose only dispositions are SUPPRESS returns `status: loop_back` too. The rule and its granularity tiers are stated once in [`triage.md`](triage.md) § Step 7. The calling manifest step (or slash command body) handles the actual re-fire — this workflow does NOT call `manage-status set-phase` directly.

## Step 8: Respond loop — transmit dispositions to the provider (RESPOND)

Triage (Steps 3-6) RECORDED a disposition and a reviewer-ready `resolution_detail` on each finding via `manage-findings resolve`; it did NOT talk to the provider. This RESPOND loop transmits those already-decided dispositions back to the provider after all triage has settled — keyed by each finding's own `hash_id`, never by positional pairing (the store-keyed pairing is the structural fix for the historical positional respond mis-pairing defect). Each disposition is transmitted once; under `producer=finalize-feedback` a `fixed` disposition is transmitted by a later pass than the others, as the ordering below states. It runs for the PR / Sonar producers only; `test-failure` / `lint-issue` / `plugin-doctor` findings have no external provider surface and skip this step.

The respond verbs are the pure zero-LLM provider surface (D3) — they apply dispositions, they never decide them:

1. **PR providers (`pr-comment`, and `sonar-issue` when `pr_number` is set for thread context)** — one `post_responses` call transmits every terminal-disposition finding that carries a `resolution_detail` and is not held: a thread-bearing finding gets a thread-reply then a resolve-thread; the thread-less ones (a `review_body` finding from any bot, or a bot that posts only issue comments) go out together in ONE batched PR-level comment anchored on each source `comment_id`. A finding with no `resolution_detail` is skipped — there is genuinely nothing to transmit. The GitHub call has two forms, and the `producer` decides which one this step issues:

   | `producer` | GitHub call | A `fixed` finding with no stamped fix commit |
   |------------|-------------|----------------------------------------------|
   | `finalize-feedback` | WITHOUT `--send-unstamped-fixed` | Held and reported `deferred_until_commit`. The phase-6-finalize hook that dispatched this workflow transmits it in a second respond pass (see "Ordering" below). |
   | every other producer that reaches this step with a PR provider — `pr-state`, and the standalone `pr-comment` mode | WITH `--send-unstamped-fixed` | Transmitted in this pass with the other dispositions. No later respond pass exists for these producers, so a held reply would never be sent. |

   `producer=finalize-feedback`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
     post_responses --pr-number {pr_number} --plan-id {plan_id}
   ```

   Every other producer:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
     post_responses --pr-number {pr_number} --plan-id {plan_id} --send-unstamped-fixed
   ```

   On a GitLab project the call is `workflow-integration-gitlab:gitlab_pr post_responses` instead, in the first form under every producer — one provider per host. `--send-unstamped-fixed` is a flag of the GitHub verb only; the GitLab verb does not declare it and holds nothing.

   **What the flag costs the reviewer.** With `--send-unstamped-fixed` the reviewer is told "fixed", and a thread-bearing finding's thread is resolved, when the fix is decided. For a task fix no commit carries the fix at that point. For an inline fix the edit is in the worktree and may not be committed yet. The reply is the stored `resolution_detail` and names no commit. The flag reaches a finding with no stamp only: a `fixed` finding that already carries a `fix_commit_sha` is checked against the pull request head as in "Ordering" below, whichever form is issued.

   **Read the returned `status`, not just the exit code.** `status: partial` with a non-zero `count_untransmitted` means at least one disposition had something to say and could NOT be delivered; every such finding is enumerated in `untransmitted[]` with a reason. Surface that to the operator rather than treating the RESPOND loop as clean. See [`workflow-integration-github` SKILL.md](../../workflow-integration-github/SKILL.md) § Workflow 2 step 4 for the full three-way transmit table and the `transmit_mode` / `resolved_on_provider` fields.

   **Ordering under `producer=finalize-feedback` — a `fixed` reply waits for its fix commit.** Triage resolves a finding `fixed` when it decides the fix: when it allocates the fix task, or when it applies the one inline edit. No commit carries the fix at that point. Called without `--send-unstamped-fixed`, the GitHub verb therefore does not transmit a `fixed` finding until the finding carries a stamped fix commit (`fix_commit_sha`, written by `manage-findings stamp-fix-commit`) and that commit is on the pull request head. Until then:

   - the finding is reported in `deferred_until_commit[]` and counted in `count_deferred_until_commit`, with the reason;
   - it gets no thread reply and no resolve-thread call;
   - it is not untransmitted and does not make the run `partial`.

   A task fix and an inline fix are held alike: the verb reads the stamp, not how the fix was made. The other four dispositions (`suppressed`, `accepted`, `taken_into_account`, `rejected`) are transmitted in this pass. Under `producer=finalize-feedback` the held replies go out in a second respond pass, which the phase-6-finalize hook runs after the fix commit is pushed and stamped — see [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) Step 3 item 7c. The transmitted reply is then the stored `resolution_detail` with the short commit id added, and the thread is resolved in the same call. A non-empty `deferred_until_commit[]` after this pass is the expected state while a fix is still on its way; report the count, do not treat it as a failure. The hook stamps at three points, in this order: before its first respond pass it stamps a task fix whose task is `done`, and an inline fix a stopped firing left unstamped for which it finds the one commit that holds inline edits to the finding's file; after that pass it stamps again each finding the pass reported as `fix_commit_not_on_pr_head` for which it finds the one commit that carries the replaced commit's change to the finding's file, and runs the pass once more when it stamped at least one; and after it has committed and pushed the triage's own edits it stamps the inline fixes of that firing and runs the pass again.

   No other producer has that hook. `pr-state` and the standalone `pr-comment` mode stamp nothing and run no second respond pass, which is why they pass `--send-unstamped-fixed`: their `fixed` replies go out in this pass, before the fix is known to be on the pull request, and a `deferred_until_commit[]` row can then only name a finding that already carried a stamp.

   **Which commit the hook stamps.** For an inline fix it is the commit that holds the edit, stamped by the firing that commits the edit. For a task fix it is the pushed head of the branch, read once the fix task is `done` and `branch-sync-state` reports `synced`. That commit contains the fix and may be later than the commit that made it, so the short commit id in the reply names a commit as of which the fix is on the pull request, not necessarily the commit that changed the lines. A pushed head is the pull request head, and stays an ancestor of it when further commits are pushed on top, so such a stamp keeps satisfying the condition above; it stops satisfying it only when a rebase or a force-push replaces the stamped commit.

   The hook stamps an evidence commit in two further cases, each only while `branch-sync-state` reports `synced`. In neither does it stamp the pushed head: a stamp is written only with the one commit that is shown to carry the change, and a finding for which no such commit is found stays held. The two commands are stated in [`phase-6-finalize/SKILL.md`](../../phase-6-finalize/SKILL.md) Step 3 item 7c, step (0).

   - **A stamp that does not reach the pull request head.** A finding the respond pass reports with `reason: fix_commit_not_on_pr_head` is stamped again with the one commit on the branch whose patch for the finding's file equals the replaced commit's, a task fix and an inline fix alike, and the respond pass runs once more. The comparison is `git log --cherry-mark` between the replaced commit and the pushed head, restricted to the finding's `file_path`; it stamps on exit status 0 with exactly one line marked `=`. No such line, more than one, any other exit status, a finding with no `file_path` and a finding with no readable `fix_commit_sha` stamp nothing; the hook logs each such finding at WARNING, naming its `hash_id` and the reason, and it stays held. A finding reported with `pr_head_unreadable` or `fix_commit_ancestry_unreadable` is not stamped again: a failed read does not show that the stamped commit was replaced. An equal patch for one file shows that this file's change is in a commit on the branch. It does not show that a later commit did not undo it, and it says nothing about other files the fix touched. A `review_body` finding has no file path, so after a rewrite it stays held until it is re-resolved or stamped by hand.
   - **An inline fix a stopped firing left unstamped.** The firing that would have stamped it ended before it wrote the stamp. The hook stamps it with the one commit it made for inline dispositions that touches the finding's file: a commit after the finding's `reviewed_commit_sha`, on the pushed head, whose subject is exactly `fix(review): apply inline review dispositions`. It stamps on exit status 0 of the `git log` search with exactly one such commit. None, more than one, any other exit status, a finding with no `file_path` and a finding with no `reviewed_commit_sha` stamp nothing; the hook logs each such finding at WARNING, naming its `hash_id` and the reason, and it stays held. The commit shows that the hook committed inline dispositions to that file after the review. It does not show which of several edits in that commit belongs to this finding, nor that a later commit kept the edit.

   ⚠ **The hold-back is the GitHub verb's only — a known gap.** `gitlab_pr post_responses` reads neither stamp field and transmits a `fixed` finding at once, in the pass that follows triage. On a GitLab project the reviewer is therefore still told "fixed", and the thread resolved, before the fix commit exists.

   **What the reviewer sees when no fix commit ever arrives (GitHub, `producer=finalize-feedback`).** A plan can end after a finding was resolved `fixed` without the fix reaching a commit. Each path, and what the pull request then shows when the reply was held:

   | Path | What the reviewer sees |
   |------|------------------------|
   | The fix task is dropped — marked infeasible and dropped, left blocked or failed, or passed over with a forced transition. | No reply. The thread stays open. The finding stays listed as `deferred_until_commit` on every respond pass until it is re-resolved. |
   | The inline edit is discarded — reverted, or the run stops between triage and the finalize hook's commit of it. | A reply is sent only when exactly one commit with the hook's inline message touches the finding's file after the reviewed commit; the hook of a later firing then stamps that commit once the branch is `synced`. A discarded edit has no such commit: No reply. The thread stays open. The finding stays listed as `deferred_until_commit` on every respond pass until it is re-resolved. An edit that is uncommitted in the worktree when the run stops is committed by the hook's next firing under that message and is answered by the firing after it. |
   | The plan is abandoned before another respond pass runs. | No reply. The thread stays open. |
   | The finding is re-resolved to another disposition. | The stamp and the fix-task number are cleared, and the new disposition is transmitted normally in the next respond pass: its reply, and for a thread-bearing finding the resolved thread. |

   The hold itself stops nothing: `post_responses` lists the finding and still returns `success`, so this step does not keep a plan from going on while a thread is open and unanswered. The remedy on the first two paths, wherever the reply stays held, is the fourth: re-resolve the finding to the disposition that is now true.

   Two further states leave a `fixed` finding held although a commit exists, and both end when the right commit is stamped: the fix was committed without the stamp being written (`reason: no_fix_commit`), and the stamped commit was rewritten by a rebase or force-push (`reason: fix_commit_not_on_pr_head`, or `fix_commit_ancestry_unreadable` when GitHub no longer knows the commit). Which of them the hook ends:

   | State | The hook |
   |-------|----------|
   | `no_fix_commit`, task fix | Ends it: it stamps the pushed head once the fix task is `done` and the branch is `synced`. |
   | `no_fix_commit`, inline fix | Ends it when exactly one commit with the hook's inline message touches the finding's file after the reviewed commit, on a `synced` branch: it stamps that commit. Does not end it when there is no such commit or more than one, the search cannot be made, or the finding carries no file path or no reviewed commit. |
   | `fix_commit_not_on_pr_head` | Ends it when exactly one commit on a `synced` branch carries the replaced commit's patch for the finding's file: it stamps the finding again with that commit. Does not end it when there is no such commit or more than one, the comparison cannot be made, or the finding carries no file path or no readable stamp. |
   | `fix_commit_ancestry_unreadable` | Does not end it. The finding stays held until a later read succeeds or the finding is stamped or re-resolved by hand. |

   Under a producer that passes `--send-unstamped-fixed` the first three paths of the table read differently: the reviewer already has the "fixed" reply and the thread is already resolved, and both stay that way although the fix is on no commit. Nothing on the pull request shows the gap. The remedy is the fourth path there too — re-resolve the finding to the disposition that is now true, which clears the `responded` marker so the next respond pass transmits the new disposition as a further reply. `reason: no_fix_commit` is not reported under these producers.

2. **Sonar server-side dismissals** — one `sonar post_responses` call transmits every terminal `sonar-issue` dismissal keyed by `hash_id`: it maps a `suppressed` resolution to a `wontfix` transition and a `rejected` resolution to a `falsepositive` transition, reading the Sonar issue key from each finding's own record (never a positional pairing). See `workflow-integration-sonar` Canonical invocations → `sonar — post_responses`:

   ```bash
   python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar \
     post_responses --plan-id {plan_id} --project {project_key}
   ```

   This RESPOND-side dismissal is gated by the `do_transition` param (owned by the `default:sonar-roundtrip` step; default `false`): the sonar branch of Step 8 runs `sonar post_responses` only when `do_transition == true`. Under the default `do_transition == false`, dispositions are recorded git-visibly as in-code suppressions during triage and NO server-side transition is transmitted.

The respond verbs FAIL LOUD when the provider is not configured (typed `unconfigured`, never a silent no-op).

**Idempotency is an explicit per-finding marker, not a property of terminality.** Terminality (`_RESPONDABLE_RESOLUTIONS`) is the RESPOND loop's *selection* criterion, not an exclusion criterion: a finding is respondable precisely *because* its resolution is terminal, so a terminal finding stays eligible on every pass and would re-transmit forever without a guard. The guard is therefore a `responded` marker stamped on each finding in the same unit of work that transmits its reply; a later pass skips any finding already carrying it. Every respond verb — **GitHub** (`github_pr`), **GitLab** (`gitlab_pr`), and **Sonar** (`sonar`) — implements this marker, so a loop-back re-entry re-transmits **nothing** for a disposition already sent and each verb's `count_responded` reports only the dispositions transmitted **that round**, never a standing re-count of every terminal finding. A disposition that genuinely CHANGED between rounds is transmitted again: `manage-findings resolve` clears the marker whenever it changes a finding's resolution or reply body, so the guard is keyed on `(finding, disposition)`, never a blanket suppression. A held `fixed` finding carries no marker, which is what lets the second respond pass transmit it.

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
loop_back_target: 5-execute | 6-finalize   # present on every loop_back return, omitted otherwise
```

`status: loop_back` when `fix_tasks_created > 0` OR `overflow_deferred > 0` OR an inline-fixable disposition (SUPPRESS, narrow-rationale ACCEPT, or single-annotation FIX) requires the calling step to be replayed. The single-annotation FIX is the inline fix of [`triage.md`](triage.md) § 3c: it allocates no task, so it is not counted in `fix_tasks_created`, and under `producer=finalize-feedback` its `fixed` reply is held until its commit is stamped, exactly like a task fix's; under every other producer both are transmitted in Step 8 (Step 8, "Ordering"). Every `loop_back` return carries `loop_back_target`, and every other status omits it; the value is computed by the rule in [`phase-5-execute/standards/operations.md`](../../phase-5-execute/standards/operations.md) § "Verification-feedback loop-back returns (`loop_back_target`)" — `5-execute` when `fix_tasks_created > 0` OR `overflow_deferred > 0`, otherwise `6-finalize`. Manifest-step callers forward it verbatim to `mark-step-done --outcome loop_back --loop-back-target {value}`. The phase-6-finalize unified-triage hook consumes the returned target directly and routes the continuation without creating a phase-step record. `status: ci_failure` is reserved for `producer=pr-state` when the CI wait completed with failed checks AND zero further findings were emitted (the failure itself is the surfaced state). Otherwise `status: success` (every pending finding resolved without requiring a replay).

## Related

- [`triage.md`](triage.md) — canonical Steps 1-6 (decision + action + overflow + scope-deviation).
- [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) — store schema and producer/consumer contract.
- [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 5.1 — phase-scoped resolution + producer-mode bundling rationale.
- `pm-plugin-development:plugin-doctor` — rule catalog and references loaded by `producer=plugin-doctor`.
- `plan-marshall:workflow-integration-github` / `…-gitlab` / `…-sonar` — producer-side fetchers used by `producer=pr-state`.
