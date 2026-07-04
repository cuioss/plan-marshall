# 02 — OpenCode Runtime Verification Protocol

## Objective

Execute and record every verification described in [02-validate-opencode-runtime.md](02-validate-opencode-runtime.md) against a live OpenCode installation. Each step defines exact commands, expected observations, and pass/fail criteria.

## Status tracking convention

Each check below records its result as one of:

| Status | Meaning |
|--------|---------|
| **PASS** | Behaviour matches documented expectation |
| **FAIL** | Behaviour diverges from expectation; remediation recorded |
| **BLOCKED** | Cannot run because a prerequisite is not met |
| **N/A** | Check is not applicable in current context |

Record all results in `.plan/logs/opencode-validation-{date}.md`.

---

## 0. Prerequisites

### 0.1 Workstream 01 landed

Verify that portability gaps from [01-finish-portability.md](01-finish-portability.md) are resolved before any live session.

| Check | Command | Pass | Fail |
|-------|---------|------|------|
| 0.1a | `git log --oneline -5` | Contains commits implementing 01 tasks | File as BLOCKED; do not proceed |
| 0.1b | `grep -r 'platform_runtime permission' marketplace/bundles/plan-marshall/skills/tools-permission-doctor/` | At least 1 match (SKILL.md delegates to runtime; the invocation token is `plan-marshall:platform-runtime:platform_runtime permission …`) | NOTE — settings I/O lives in `claude_runtime.py`; residual `.claude/` literals are listed in [01 § Closing audit](01-finish-portability.md#closing-audit) |
| 0.1c | `grep -r 'platform_runtime' marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` | At least 1 match (session/metrics capture delegated) | BLOCKED — phase-5 must use runtime |
| 0.1d | `grep -r 'runtime.target' marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py` | At least 1 match (bootstrap reads target) | BLOCKED — bootstrap must resolve both targets |

### 0.2 OpenCode installed and discoverable

| Check | Command | Pass | Fail |
|-------|---------|------|------|
| 0.2a | `which opencode` | Returns a path | BLOCKED — install OpenCode first |
| 0.2b | `opencode --version 2>&1 \|\| echo "no version flag"` | Captures version string | Document version for the log |
| 0.2c | `ls ~/.config/opencode/ 2>/dev/null \|\| echo "no global config dir"` | Directory exists or alternate config path works | BLOCKED — must have a config dir |
| 0.2d | `python3 marketplace/targets/generate.py --help` | Shows `--target {claude,opencode,all}` choices | BLOCKED — emitter must support opencode |

---

## 1. Setup verification

### 1.1 Generate the OpenCode target tree

```
python3 marketplace/targets/generate.py --target opencode --output target/opencode
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 1.1a | Exit code | `0` | FAIL — diagnose from stderr |
| 1.1b | `ls target/opencode/` | Contains `skill/`, `agent/`, `command/`, `opencode.json` | FAIL — emitter produced incomplete tree |
| 1.1c | `ls target/opencode/skill/ \| head -20` | Directories named `{bundle}-{skill}` (e.g. `plan-marshall-phase-1-init`) | FAIL — wrong naming convention |
| 1.1d | `ls target/opencode/agent/ \| head -20` | Agent files present | PASS if agents exist; NOTIFY if empty |
| 1.1e | `python3 -c "import json; d=json.load(open('target/opencode/opencode.json')); print(d.keys())"` | Contains `$schema` and `skills`; `agent` present when agents exist. `instructions` is absent — it's a distributed plugin, not a project root. | FAIL — missing required keys or leaking project-level config |
| 1.1f | `grep -r '^Skill:' target/opencode/skill/plan-marshall-phase-1-init/SKILL.md \| head -5` | Zero matches (Skill: directives rewritten) | FAIL — body transforms not applied. Ensure `OpenCodeTarget.generate()` passes `body_transformer` to `emit_bundles`. |
| 1.1g | Regenerate idempotence: run generate again, then `diff -r target/opencode/ target/opencode-2/ \|\| echo "identical"` | No diffs (excluding timestamps/metadata) | FAIL — non-idempotent emission |

### 1.2 Deploy to OpenCode with singular→plural rename

Before a deploy skill exists (04), stage manually:

```bash
# Create a staging directory with plural layout
STAGE=/tmp/opencode-stage-$$
mkdir -p "$STAGE"/skills "$STAGE"/agents "$STAGE"/commands

# Copy with singular→plural rename
cp -r target/opencode/skill/* "$STAGE"/skills/
cp -r target/opencode/agent/* "$STAGE"/agents/
cp -r target/opencode/command/* "$STAGE"/commands/

# Verify layout
ls "$STAGE"/skills/ | head -5
ls "$STAGE"/agents/ | head -5
ls "$STAGE"/commands/ | head -5

# Deploy to OpenCode config
cp -r "$STAGE"/skills/* ~/.config/opencode/skills/
cp -r "$STAGE"/agents/* ~/.config/opencode/agents/
cp -r "$STAGE"/commands/* ~/.config/opencode/commands/
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 1.2a | `ls ~/.config/opencode/skills/ \| head -10` | Contains namespaced skill dirs | FAIL — deploy failed |
| 1.2b | `ls ~/.config/opencode/agents/ \| head -10` | Agent files present | FAIL — agent deploy failed |
| 1.2c | `ls ~/.config/opencode/skills/plan-marshall-phase-1-init/SKILL.md 2>/dev/null \|\| echo "not found"` | Skill script is discoverable | FAIL — singular→plural rename may have missed |
| 1.2d | `opencode --list-skills 2>&1 \|\| opencode skill list 2>&1 \|\| ls ~/.config/opencode/skills/` | Deployed skills visible in OpenCode's discovery | FAIL — OpenCode does not discover the deployed skills |
| 1.2e | Namespace format: `ls ~/.config/opencode/skills/ \| grep -c -- '--'` | Zero consecutive `--` in names | FAIL — names contain `--` which OpenCode may not resolve |

### 1.3 Initialize a plan with `--target opencode`

```bash
mkdir -p /tmp/opencode-test-$$ && cd /tmp/opencode-test-$$

# Run platform-runtime initial-setup for opencode
python3 /path/to/plan-marshall/.plan/execute-script.py \
  plan-marshall:platform-runtime:platform_runtime \
  project initial-setup --target opencode
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 1.3a | Exit code | `0` | FAIL — initial-setup failed |
| 1.3b | `python3 -c "import json; print(json.load(open('.plan/marshal.json'))['runtime']['target'])"` | `opencode` | FAIL — target not recorded |
| 1.3c | `ls .plan/execute-script.py 2>/dev/null \|\| echo "not found"` | File exists | NOTE — executor is a separate artefact from `initial-setup`. Run `/marshall-steward` or `tools-script-executor:generate_executor` after `initial-setup`. |
| 1.3d | `head -5 .plan/execute-script.py` | Contains OpenCode 7-root resolver (comments referencing OPENCODE_CONFIG_DIR or 7-root walk) | FAIL — Claude resolver generated instead. Regenerate executor after bootstrap changes land. |

---

## 2. Accepted risks verification

### 2.1 Subagent `AskUserQuestion`

**What the runtime does** (`opencode_runtime.py`, `subagent_dispatch`): returns `{"tool": "task", "subagent_type": "execution-context-level-3"}` (the hardcoded level is the known [07 §5](07-target-extensibility.md) leak). It assumes a dispatched subagent can call `question` to prompt the user.

**Test procedure:**
1. Start a plan that reaches a finalize step requiring user confirmation (e.g. branch-deletion)
2. When the subagent dispatches, observe whether OpenCode's `task` agent can invoke `question`

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:phase-6-finalize \
  --plan-id test-001 --phase phase-6-finalize --role default
```

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 2.1a | Subagent dispatches via `task` tool | OpenCode creates a sub-agent | FAIL — investigate OpenCode task tool availability | HUMAN |
| 2.1b | Subagent calls `question` tool | User sees a prompt in the terminal | FAIL — record whether question tool is available to subagents | HUMAN |
| 2.1c | Answer propagates to parent | Parent agent receives the user's input | FAIL — investigate answer propagation mechanism | HUMAN |
| 2.1d | Logged result | `subagent_ask_user_question: PASS or FAIL with notes` | Document subagent_type used and result | HUMAN |

**Remediation if FAIL**: Add `inline_only: true` to the affected step kinds (e.g. `phase-6-finalize` confirmation steps) so the orchestrator runs them in-context instead of dispatching. Update the runtime contract document.

### 2.2 `task`-tool dispatch

**What the runtime does**: `execution-context` (and its `-level-N` variants) dispatch sub-workflows via the `Task` tool. The task body passes a workflow document in the prompt and expects a TOON return value.

**Test procedure:**
1. Initiate a plan dispatch that uses `execution-context-level-3`
2. Observe the dispatch and return flow

```bash
python3 .plan/execute-script.py plan-marshall:execution-context-level-3:execution_context \
  --plan-id test-001 --phase phase-4-plan
```

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 2.2a | Dispatch succeeds | OpenCode creates a sub-agent for the workflow task | FAIL — OpenCode may not support Task-style dispatch | HUMAN |
| 2.2b | Workflow doc in prompt body | The workflow instructions are passed to the subagent | FAIL — document how OpenCode passes task prompts | HUMAN |
| 2.2c | TOON return | Sub-agent returns structured output that the parent can parse | FAIL — OpenCode subagent returns different format | HUMAN |
| 2.2d | `level-N` variant resolution | The specific `-level-3` variant is used, not a default | FAIL — effort variants not resolved | HUMAN |

> **Precondition for 2.2d**: the OpenCode target does not yet emit `execution-context-level-N`
> variants (no OpenCode variant emitter exists). Until the variant-emitter task in
> [06-execution-context-cross-target.md](06-execution-context-cross-target.md) lands, 2.2d
> necessarily fails — the canonical agent is dispatched regardless of level. Build that
> emitter first, then run 2.2d.

**Remediation if FAIL**: Document the divergence in the runtime contract. Consider a script-based fallback where the orchestrator runs the workflow inline instead of dispatching.

### 2.3 `skill`-tool loading

**What the emitter does** (`transforms.md` Transform 1): rewrites `Skill: {bundle}:{skill}` to `` Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing. ``

**Test procedure:**
1. Pick a deployed skill that contains a `Skill:` directive in its source
2. Verify the rewrite happened in the deployed copy
3. Start an OpenCode session and trigger a step that should load the referenced skill
4. Observe whether OpenCode's `skill` tool recognises the namespaced name

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 2.3a | Rewrite in deployed SKILL.md | Line reads `Call the \`skill\` tool with \`{ name: "{bundle}-{skill}" }\`` | FAIL — emitter transform not firing | — |
| 2.3b | `skill` tool loads the target | OpenCode resolves `{bundle}-{skill}` to a known skill | FAIL — OpenCode may use different name resolution | HUMAN |
| 2.3c | The loaded skill's instructions are followed | LLM acts on the skill content | FAIL — OpenCode's skill tool is advisory only | HUMAN |
| 2.3d | Skill: lines that were references in prose (backtick) | These are unaffected by the rewrite | PASS if unchanged; FAIL if falsely rewritten | — |

**Remediation if FAIL**: Adjust the body transform spec in `marketplace/targets/opencode/transforms.md`. Possibly add a third transform for OpenCode's name resolution format, or document that OpenCode's `skill` tool is LLM-driven and does not guarantee skill loading.

### 2.4 Parallel dispatch

**What the runtime does**: The one parallel-dispatch site is `enrich-module` under `--phase phase-6-finalize`.

**Test procedure:**
1. Trigger a `phase-6-finalize` run that includes `enrich-module`
2. Observe whether multiple `task` agents are created in parallel
3. Observe whether all results are collected

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:phase-6-finalize \
  --plan-id test-001 --phase phase-6-finalize --role verification-feedback
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 2.4a | Multiple tasks dispatched | OpenCode creates concurrent sub-agents | FAIL — OpenCode may serialize task dispatch |
| 2.4b | All results return | All sub-agent outputs are collected by the parent | FAIL — parallel results may be lost |
| 2.4c | No resource conflicts | No "already locked" or file contention errors | FAIL — parallel agents conflict on shared state |

**Remediation if FAIL**: Serialize the fan-out on OpenCode. In the `execution-context` workflow, detect `runtime.target == "opencode"` and iterate task dispatch sequentially instead of in parallel. Document the limitation.

### 2.5 Instruction following

**Test procedure:**
1. OpenCode's `AGENTS.md` was loaded during setup
2. Start a complex multi-step workflow (e.g., full init→refine→outline→execute→finalize)
3. Observe whether the LLM maintains context through compaction

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 2.5a | `AGENTS.md` instructions honoured | Agent behaviour follows the rules from AGENTS.md | FAIL — AGENTS.md not loaded or lost |
| 2.5b | Compaction does not drop instructions | After a compaction event, behaviour is unchanged | FAIL — document compaction behaviour |
| 2.5c | Multi-step workflow completes | End-to-end flow without manual re-direction | FAIL — complex workflows degrade |
| 2.5d | Model is Opus-level or better | `opencode --model` or similar shows the model ID | NOTIFY — record which model was used |

**Remediation if FAIL**: Keep the `opus`→latest-Opus mapping (no downgrades). Document that Opus is required for complex skills. If `instructions` array is ignored, move critical rules into the system prompt or first user message.

---

## 3. Smoke flows

### 3.1 Fresh-init → refine → outline

Start with a trivial request (e.g. "Add a README.md to this project").

```bash
# Set up a test directory
mkdir -p /tmp/smoke-1-$$ && cd /tmp/smoke-1-$$
git init
echo "# test" > README.md && git add . && git commit -m "init"

# Create a request
echo "Add a .gitignore file for a Python project" > request.md

# Bootstrap plan
python3 /path/to/plan-marshall/.plan/execute-script.py \
  plan-marshall:phase-1-init:phase-1-init \
  --plan-id smoke-1 --request-dir . --project-dir .
```

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 3.1a | Phase transitions | Steps execute in order: init → refine → outline | FAIL — orchestrator ordering broken | HUMAN |
| 3.1b | `session capture` no-op | Log shows no-op with alternative suggestion, does not abort | FAIL — no-op not handled gracefully | — |
| 3.1c | Outline produced | `solution_outline.md` written with deliverables | FAIL — outline phase not working | HUMAN |
| 3.1d | Plan metadata | `manage-status` shows expected plan state | FAIL — plan state machine not working | — |

### 3.2 Execute → finalize sweep

Continue from smoke 3.1: execute the plan and finalize.

```bash
python3 .plan/execute-script.py \
  plan-marshall:phase-5-execute:phase-5-execute \
  --plan-id smoke-1 --phase phase-5-execute

python3 .plan/execute-script.py \
  plan-marshall:phase-6-finalize:phase-6-finalize \
  --plan-id smoke-1 --phase phase-6-finalize
```

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 3.2a | Execute phase completes | All tasks run without abort | FAIL — execute phase broken | HUMAN |
| 3.2b | Finalize prompt works | If finalize prompts for confirmation, user sees and can answer | FAIL — prompt not working (see 2.1) | HUMAN |
| 3.2c | Archived plan | Plan is archived after finalize | FAIL — archiving not working | HUMAN |
| 3.2d | No hard errors logged | `manage-status` shows no error state | FAIL — unexpected errors | — |

### 3.3 By-reference triage path

Dispatch `verification-feedback` under `--phase phase-6-finalize --role verification-feedback`.

```bash
python3 .plan/execute-script.py \
  plan-marshall:verification-feedback:verification_feedback \
  --plan-id smoke-1 --phase phase-6-finalize --role verification-feedback
```

| Check | What to observe | Pass | Fail | Human? |
|-------|----------------|------|------|--------|
| 3.3a | `manage-findings` loads | No "skill not found" error | FAIL — skill loading broken | HUMAN |
| 3.3b | Findings store queried | Returns existing findings or empty set | FAIL — data access broken | HUMAN |
| 3.3c | TOON returned | Structured response back to caller | FAIL — TOON contract broken | HUMAN |

### 3.4 Token capture no-op

```bash
# Attempt metrics capture without total-tokens
python3 .plan/execute-script.py \
  plan-marshall:platform-runtime:platform_runtime \
  metrics capture --plan-id smoke-1 --phase smoke

# Then with total-tokens
python3 .plan/execute-script.py \
  plan-marshall:platform-runtime:platform_runtime \
  metrics capture --plan-id smoke-1 --phase smoke --total-tokens 42
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 3.4a | No-token call returns no-op | Status is `no-op` with `alternative` field | FAIL — wrong status returned |
| 3.4b | No-token call does not abort | Exit code 0, phase continues | FAIL — no-op bubbles as error |
| 3.4c | With-token call returns success | Status is `success`, tokens_captured = 42 | FAIL — manual token path broken |
| 3.4d | Alternative suggestion is actionable | `alternative` string tells user to pass `--total-tokens` | FAIL — unhelpful alternative |

---

## 4. CI: OpenCode generation gate

### 4.1 Generation check in CI

A workflow file `.github/workflows/opencode-generate-check.yml` exists. It runs on every PR
touching `marketplace/bundles/**` or `marketplace/targets/**` and fails on any generator
exit code != 0.

```yaml
name: OpenCode Generation Gate

on:
  pull_request:
    paths:
      - 'marketplace/bundles/**'
      - 'marketplace/targets/**'

jobs:
  generate-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - name: Generate OpenCode target
        run: |
          python3 marketplace/targets/generate.py \
            --target opencode \
            --output target/opencode
```

| Check | What to observe | Pass | Fail |
|-------|----------------|------|------|
| 4.1a | PR with valid bundles | CI passes (green) | FAIL — false positive |
| 4.1b | PR with broken frontmatter | CI fails (red), exit code 2 | FAIL — error not caught |
| 4.1c | PR with unmapped agent tool | CI fails with clear error message | FAIL — UnmappedToolError not surfaced |
| 4.1d | PR with `user-invocable: true` skill missing `description` | CI fails | FAIL — validation gap |
| 4.1e | Workflow only triggers on relevant paths | Changing an unrelated file does not trigger | FAIL — too broad trigger |

---

## 5. Recording template

Create `.plan/logs/opencode-validation-{date}.md` with this structure:

```markdown
# OpenCode Validation Log — {date}

**OpenCode version**: {output of `opencode --version` or equivalent}
**Plan-Marshall commit**: {output of `git rev-parse HEAD`}
**Tester**: {name}

## Prerequisites

| Check | Status | Notes |
|-------|--------|-------|
| 0.1a — 01 portability landed | | |
| 0.2a — opencode installed | | |
| 0.2d — generate.py works | | |

## 1. Setup

| Check | Status | Notes |
|-------|--------|-------|
| 1.1a — generate exits 0 | | |
| 1.1b — tree structure | | |
| 1.2a — deploy succeeds | | |
| 1.3a — init-plan succeeds | | |

## 2. Accepted Risks

| Risk | Status | Notes | Remediation needed? |
|------|--------|-------|---------------------|
| 2.1 AskUserQuestion | | | |
| 2.2 task-tool dispatch | | | |
| 2.3 skill-tool loading | | | |
| 2.4 Parallel dispatch | | | |
| 2.5 Instruction following | | | |

## 3. Smoke Flows

| Flow | Status | Notes |
|------|--------|-------|
| 3.1 Init→Refine→Outline | | |
| 3.2 Execute→Finalize | | |
| 3.3 Triage path | | |
| 3.4 Token capture no-op | | |

## 4. CI Gate

| Check | Status | Notes |
|-------|--------|-------|
| 4.1a — valid PR passes | | |
| 4.1b — broken PR fails | | |

## Summary

**Overall verdict**: {PASS / FAIL / CONDITIONAL}
**Blocking issues**: {list}
**Documentation updates needed**: {list of 05 items}
```

---

## Acceptance criteria (from 02 doc)

- [ ] Each accepted risk (2.1–2.5) marked **confirmed working** or **escalated** with documented remediation
- [ ] All four smoke flows (3.1–3.4) complete on a live OpenCode session (or failures documented with remediation)
- [ ] OpenCode generation CI gate (4.1) runs on every PR and fails on emitter errors
- [ ] Any OpenCode-specific divergence recorded in the runtime contract and in the OpenCode documentation ([05](05-opencode-documentation.md))

## Dependencies

- [01 — Finish portability gaps](01-finish-portability.md) — section 0.1 verifies this
- [04 — Developer workflow](04-developer-workflow-sync-opencode.md) — section 1.2 uses manual deploy until 04 lands
