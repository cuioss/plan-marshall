# Dispatch Walkthrough — Worked Examples

Concrete end-to-end traces of `execution-context-{level}` dispatches at three representative call sites: a single-workflow phase entry, a finalize step that sub-dispatches `verification-feedback` (producer=pr-comment) by reference, and a per-iteration parallel fan-out. For the dispatch contract itself (prompt-body fields, role-key resolution, mandatory rules), see [`agents.md`](agents.md). For the heuristics that decide *whether* a step should dispatch, see [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md). For the holistic visual call graph covering every dispatch path (not just these three exemplars), see [`call-graph.md`](call-graph.md).

## Generic eight-step sequence

Every dispatched phase or step follows the same shape:

1. **Orchestrator: pick role key + workflow doc + skills.** From a slash-command action, a manifest step, or an inline call site.
2. **Orchestrator: resolve the level** via `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config effort resolve-target --role <role_key>`. Returns the variant target name (`execution-context-{level}` or canonical `execution-context` for `inherit`).
3. **Orchestrator: construct prompt body** — five required fields (`name`, `plan_id`, `skills[]`, exactly one of `workflow`/`instructions`, `WORKTREE`) plus any workflow-specific runtime inputs.
4. **Orchestrator: dispatch** — `Task: plan-marshall:execution-context-{level}` with the prompt body.
5. **Subagent: load skills + read workflow** — `dev-general-practices` first (implicit), then each `skills[]` entry in order, then `Read` the resolved workflow path.
6. **Subagent: execute the workflow** — runtime inputs substitute into the doc's `{placeholder}` tokens.
7. **Subagent: return TOON** — minimum shape `status` + `display_detail`; workflow-specific fields per its return contract.
8. **Orchestrator: record outcome** via `manage-status mark-step-done` and accumulate usage via `manage-metrics accumulate-agent-usage`.

The three examples below instantiate this sequence with realistic prompts and return shapes.

---

## Example A — phase-2-refine entry (single-workflow phase)

The simplest case: a phase whose role key is flat (`phase-2-refine`), one dispatched workflow, the confidence loop iterates *inside* the envelope.

### Setup
- `{plan_id}` = `lesson-2026-05-11-foo`
- `marshal.json`: `"models": {"default": "medium", "roles": {"phase-2-refine": "high", ...}}`

### Trace

**Steps 1–3 (orchestrator):**
- role_key = `phase-2-refine`
- workflow = `plan-marshall:phase-2-refine/SKILL.md`
- skills = `[plan-marshall:manage-architecture, plan-marshall:manage-references, plan-marshall:manage-plan-documents]`

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models resolve-target --role phase-2-refine
```

Returns:
```toon
status: success
role: phase-2-refine
level: high
target: execution-context-high
```

**Step 4 (orchestrator constructs prompt body):**

```
name: phase-2-refine
plan_id: lesson-2026-05-11-foo
skills[3]:
- plan-marshall:manage-architecture
- plan-marshall:manage-references
- plan-marshall:manage-plan-documents
workflow: plan-marshall:phase-2-refine/SKILL.md
WORKTREE: .plan/local/worktrees/lesson-2026-05-11-foo
```

**Step 5 (dispatch):**

```
Task: plan-marshall:execution-context-high
  prompt: <the block above, verbatim>
```

**Step 6 (subagent body):**

1. `Skill: plan-marshall:dev-general-practices` (implicit)
2. `Skill: plan-marshall:manage-architecture`
3. `Skill: plan-marshall:manage-references`
4. `Skill: plan-marshall:manage-plan-documents`
5. `Read plan-marshall:phase-2-refine/SKILL.md` (notation resolved to filesystem path by the dispatcher)
6. Execute SKILL.md — the confidence loop (Steps 3b → 3c → 8 → 9 → 10 → 11 → 12) iterates inside this envelope until confidence ≥ threshold. AskUserQuestion in Step 11 propagates to the host UI directly from the subagent.

**Step 7 (subagent returns):**

```toon
status: success
display_detail: confidence 95 reached at iteration 2
plan_id: lesson-2026-05-11-foo
confidence: 95
track: complex
scope_estimate: multi_module
qgate_pending_count: 0
```

Plus `<usage>` tag with `total_tokens=38420, tool_uses=14, duration_ms=210000`.

**Step 8 (orchestrator records):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  mark-step-done --plan-id lesson-2026-05-11-foo \
  --phase 2-refine --step refine-analyze \
  --outcome done --display-detail "confidence 95 reached at iteration 2"

python3 .plan/execute-script.py plan-marshall:manage-metrics:manage_metrics \
  accumulate-agent-usage --plan-id lesson-2026-05-11-foo --phase 2-refine \
  --total-tokens 38420 --tool-uses 14 --duration-ms 210000
```

One dispatch, ~210 s wall-clock, the entire confidence loop runs inside one envelope. No per-iteration dispatch.

---

## Example B — phase-6-finalize automated-review with `verification-feedback` (sub-dispatch by reference)

The most complex case. The manifest step `automated-review` runs **mostly inline as scripts** (producer fetch, finding enumeration) and **dispatches `verification-feedback` once** with `producer=pr-comment` when there are findings to triage. Findings live in the per-plan findings store; the subagent queries them as its first workflow step — they are NEVER embedded in the prompt body.

### Setup
- `{plan_id}` = `feature-jwt-auth`
- `manifest.phase_6.steps` includes `automated-review` (after `ci-wait`, before `sonar-roundtrip`)
- CI just completed; the orchestrator just finished `ci-wait` inline

### Orchestrator: inline orchestration prologue

```bash
# 1. Read CI completion signal
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  read --plan-id feature-jwt-auth

# 2. Wait for review-bot comments
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id feature-jwt-auth pr wait-for-comments \
  --pr-number 142 --timeout 180

# 3. Producer: stage PR comments as findings into the store
python3 .plan/execute-script.py plan-marshall:workflow-integration-github:github_pr \
  --plan-id feature-jwt-auth comments-stage --pr-number 142

# 4. Gate-check: count pending findings (NOT content)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  query --plan-id feature-jwt-auth --type pr-comment --resolution pending
```

If pending count is 0 → skip the dispatch, mark step done. If non-zero → proceed to dispatch.

### Orchestrator: dispatch `verification-feedback` by reference

**Steps 2–3 (resolve level):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models resolve-target --phase phase-6-finalize --role verification-feedback
```

Returns `target: execution-context-high`.

**Step 4 (prompt body — no findings list inline):**

```
name: verification-feedback
plan_id: feature-jwt-auth
skills[1]:
- plan-marshall:manage-findings
workflow: plan-marshall:plan-marshall/workflow/verification-feedback.md
producer: pr-comment
pr_number: 142
caller_phase: phase-6-finalize
WORKTREE: .plan/local/worktrees/feature-jwt-auth
```

**Step 5 (dispatch):** `Task: plan-marshall:execution-context-high` with the block above.

**Step 6 (subagent body — smart-grouping algorithm):**

1. `Skill: plan-marshall:dev-general-practices` (implicit)
2. `Skill: plan-marshall:manage-findings`
3. `Read plan-marshall:plan-marshall/workflow/triage.md`
4. **Fetch findings from the store** (NOT from the prompt body):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
     query --plan-id feature-jwt-auth --type pr-comment --resolution pending
   ```

   Returns 6 pending findings of mixed `(domain, rule_id)` pairs. This is the single source of truth. On loop-back re-entry the second query sees only currently-pending findings — stale-data failure mode avoided.

5. **Pre-group by `(domain, rule_id)`**. The subagent calls `architecture which-module` for each finding once to populate the `domain` field, then groups. Findings with no `rule_id` form singleton groups.

6. **Sequential between groups, batched LLM decision within a group:**
   - Per group: load `ext-triage-{domain}` once (idempotent across same-domain groups in the same envelope).
   - One LLM call decides every finding in the group, returning `decisions[N]{hash_id, outcome, rationale}`.
   - Act on each decision sequentially: `manage-findings resolve`, PR thread reply, fix-task allocation. Sequential action preserves cross-group feedback — TASK-N allocated for group 1 can be referenced when triaging group 2.

7. AskUserQuestion (within a batched decision): the LLM can flag M of N findings as `ASK_USER_QUESTION`; the subagent raises the M prompts one by one. Batching the *decision* call does not batch the user UX.

**Step 7 (subagent returns):**

```toon
status: loop_back
display_detail: 6 comments triaged, 2 fix tasks created
producer: pr-comment
findings_processed: 6
findings_resolved: 6
fix_tasks_created: 2
fix_task_numbers[2]:
- 27
- 28
```

Plus one `<usage>` tag — one envelope cost, not six.

**Step 8 (orchestrator):** `mark-step-done --outcome loop_back`. The phase-6-finalize dispatcher's loop-back continuation transitions back to phase-5-execute, dispatches the fix tasks, transitions forward, re-enters the manifest. The next `automated-review` run sees 0 pending findings and short-circuits.

### Key by-reference property

The findings list never lives in the prompt body. Passing `finding_type` plus the loaded `manage-findings` skill is all the subagent needs. Embedding inline would duplicate the store's data into the prompt for zero information gain — and would freeze the list at orchestrator-query time, defeating loop-back re-query semantics.

---

## Example C — phase-6-finalize architecture-refresh Tier-1 fan-out (per-iteration parallel)

The only per-iteration parallel dispatch in the contract. Phase-6 `architecture-refresh` Tier-0 runs inline scripts to discover the affected module set; Tier-1 dispatches one subagent per affected module, all in parallel. Per-iteration is the right shape because (a) modules are independent and (b) parallelism saves wall-time.

### Setup
- `{plan_id}` = `feature-jwt-auth`
- Tier-0 inline discovery completed; affected_modules = `[auth-core, auth-jwt, auth-tests]` (3 modules)

### Orchestrator: Tier-0 inline (scripts only)

```bash
# Discover affected modules from the worktree diff
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  diff-modules --plan-id feature-jwt-auth

# Persist the affected-set for the dispatch fan-out
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  mark-stale-modules --plan-id feature-jwt-auth \
  --modules auth-core,auth-jwt,auth-tests
```

If `affected_modules` is empty → Tier-1 is skipped; the step marks done with `display_detail: "no modules affected"`.

### Orchestrator: Tier-1 dispatches — N parallel envelopes

**Steps 2–3 (resolve once; same level for every module):**

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  models resolve-target --phase phase-6-finalize
```

Returns `target: execution-context-medium`.

**Step 4 (prompt body, parameterised per module):**

For module `auth-core`:

```
name: enrich-module-auth-core
plan_id: feature-jwt-auth
skills[1]:
- plan-marshall:manage-architecture
workflow: plan-marshall:plan-marshall/workflow/enrich-module.md
module: auth-core
WORKTREE: .plan/local/worktrees/feature-jwt-auth
```

Two more identical prompts for `auth-jwt` and `auth-tests`, only the `module` field changes.

**Step 5 (dispatch — three concurrent `Task:` calls):**

The orchestrator issues all three `Task: plan-marshall:execution-context-medium` calls in a single batch (parallel fan-out). Each subagent runs in its own envelope, isolated from the others. The host platform may rate-limit parallel `Task:` calls; the dispatcher falls back to sequential if rate-limited.

**Step 6 (per subagent — same workflow, different `module` input):**

1. `Skill: plan-marshall:dev-general-practices` (implicit)
2. `Skill: plan-marshall:manage-architecture`
3. `Read plan-marshall:plan-marshall/workflow/enrich-module.md`
4. Execute the enrichment workflow for the named module — the original `manage-architecture` Steps 5–8 (responsibility / key_packages / summary) run *inside* this subagent, in order, against the single module the prompt named. Intra-module ordering is preserved because the workflow doc declares it.

**Step 7 (each subagent returns):**

```toon
status: success
display_detail: enriched auth-core (responsibility + 4 key_packages)
module: auth-core
responsibility: <...>
key_packages[4]:
- ...
summary: <...>
```

Plus a `<usage>` tag per envelope — three envelopes total for three modules.

**Step 8 (orchestrator gathers + persists):**

The orchestrator collects all three returns, persists the enriched metadata via `manage-architecture enrich-merge`, and marks the step done.

### Why this shape — and why it is the ONLY one

Per-iteration parallel earns its envelope cost only because:
- Modules are independent (no cross-module data flow during enrichment).
- Wall-time savings (3 parallel × ~60 s ≈ 60 s total, vs. sequential 3 × 60 s = 180 s).

Every other per-X loop in the system runs *inside* a single envelope (one envelope iterates internally). Sequential per-iteration dispatch is the worst shape — linear envelope cost × N with no parallelism payoff. See [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 4 (Heuristic 3).

---

## Cross-references

- The dispatch contract (prompt-body fields, mandatory rules) — [`agents.md`](agents.md)
- Granularity heuristics (why dispatch vs script vs inline) — [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md)
- The triage smart-grouping algorithm — [`../../plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md)
- Workflow-doc implementor contract — [`../../extension-api/standards/ext-point-execution-context-workflow.md`](../../extension-api/standards/ext-point-execution-context-workflow.md)
- Level → primitive table — [`../../plan-marshall/standards/effort-levels.md`](../../plan-marshall/standards/effort-levels.md)
- Role-key registry — [`../../plan-marshall/standards/effort-roles.md`](../../plan-marshall/standards/effort-roles.md)
