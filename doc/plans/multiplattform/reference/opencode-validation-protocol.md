# OpenCode Live-Runtime Validation Protocol

The runbook for the first execution of plan-marshall on a real OpenCode installation. Every
OpenCode operation is coded — `opencode_runtime.py` implements the full `Runtime` contract
(count it by `@abstractmethod` in `runtime_base.py`; most operations are honest no-ops on
OpenCode) and the OpenCode emitter produces a complete
`target/opencode/` tree — but none of it has executed in a live OpenCode session. Until it has,
OpenCode support is theoretical: the marketplace *emits* OpenCode artifacts and the runtime
*answers* every operation, and what is unknown is whether OpenCode's `task` tool, `skill` tool,
and permission model behave the way the runtime assumes.

**This protocol is not a cloud plan.** Its core sections need an interactive session on a live
OpenCode install — a human at a terminal answering prompts — which the cloud plan lane cannot
provide (no operator, no OpenCode install). It lives here so the epic's plans can reference it
and so the operator who runs it has exact commands, expected observations, and pass/fail
criteria. The [post-validation work](#post-validation-work) section names what becomes plannable
once it has run.

## Status vocabulary

| Status | Meaning |
|--------|---------|
| **PASS** | Behaviour matches documented expectation |
| **FAIL** | Behaviour diverges; remediation recorded |
| **BLOCKED** | Cannot run because a prerequisite is not met |
| **N/A** | Not applicable in current context |

Record results outside the repository while running (any scratch log); the durable outcome is
the set of follow-up plans and documentation updates authored from them, not the log itself.

---

## 0. Prerequisites

| Check | Command | Pass |
|-------|---------|------|
| 0.1 | `which opencode` | Returns a path; otherwise BLOCKED — install OpenCode first |
| 0.2 | `opencode --version` | Version string captured for the log |
| 0.3 | `ls ~/.config/opencode/` | Config dir exists (or an alternate config path works) |
| 0.4 | `python3 marketplace/targets/generate.py --help` | `--target` choices include `opencode` (registry-derived) |

Plans `010` (runtime seam neutrality) and `040` (`sync-opencode` inner loop) should land first:
`010` removes the fixed dispatch level the runtime currently returns (check 2.2d exercises the
parameterized path), and `040` replaces the manual staging in § 1.2 with the deploy skill.
Neither is a hard prerequisite — § 1.2 documents the manual fallback.

---

## 1. Setup verification

### 1.1 Generate the OpenCode target tree

```bash
python3 marketplace/targets/generate.py --target opencode --output target/opencode
```

| Check | What to observe | Pass |
|-------|----------------|------|
| 1.1a | Exit code | `0` |
| 1.1b | `ls target/opencode/` | Contains `skill/`, `agent/`, `command/`, `opencode.json` |
| 1.1c | `ls target/opencode/skill/` | Directories named `{bundle}-{skill}` (e.g. `plan-marshall-phase-1-init`) |
| 1.1d | `ls target/opencode/agent/` | Agent files present, including `execution-context-level-1 … level-7` variants with a concrete `model: anthropic/<id>` per level |
| 1.1e | `opencode.json` keys | Exactly what `_generate_opencode_json` (`marketplace/targets/opencode/emitter.py`) writes — re-derive the expected key set from that function. `instructions` is absent: this is a distributed plugin, not a project root |
| 1.1f | Read a generated `SKILL.md` and scan for lines beginning `Skill:` | Zero `Skill:` directives — all rewritten to the `skill`-tool call form (`target/` is generated output outside the crawled inventory, so `Read`, not `architecture search`) |
| 1.1g | Regenerate and `diff -r` the two outputs | Identical — idempotent emission |

### 1.2 Deploy with the singular→plural rename

The generated tree uses singular `skill/`/`agent/`/`command/`; OpenCode discovers plural
`skills/`/`agents/`/`commands/`. The `sync-opencode` skill (plan `040`) performs the rename;
until it lands, stage manually:

```bash
STAGE=$(mktemp -d)
mkdir -p "$STAGE"/skills "$STAGE"/agents "$STAGE"/commands
cp -r target/opencode/skill/* "$STAGE"/skills/
cp -r target/opencode/agent/* "$STAGE"/agents/
cp -r target/opencode/command/* "$STAGE"/commands/
cp -r "$STAGE"/skills/* ~/.config/opencode/skills/
cp -r "$STAGE"/agents/* ~/.config/opencode/agents/
cp -r "$STAGE"/commands/* ~/.config/opencode/commands/
```

| Check | What to observe | Pass |
|-------|----------------|------|
| 1.2a | `ls ~/.config/opencode/skills/` | Namespaced `{bundle}-{skill}` dirs present |
| 1.2b | `ls ~/.config/opencode/agents/` | Agent files present |
| 1.2c | A deployed `SKILL.md` is discoverable at its namespaced path | Present |
| 1.2d | OpenCode's own skill discovery lists the deployed skills | Deployed skills visible |
| 1.2e | `ls ~/.config/opencode/skills/ \| grep -c -- '--'` | Zero consecutive `--` in names |

### 1.3 Initialize a plan with `--target opencode`

```bash
python3 {plan-marshall-checkout}/.plan/execute-script.py \
  plan-marshall:platform-runtime:platform_runtime \
  project initial-setup --target opencode
```

| Check | What to observe | Pass |
|-------|----------------|------|
| 1.3a | Exit code | `0` |
| 1.3b | `.plan/marshal.json` → `runtime.target` | `opencode` |
| 1.3c | Executor generation | `initial-setup` only creates `.plan/` and seeds `marshal.json`; generate the executor separately via `/marshall-steward` or `tools-script-executor:generate_executor` |
| 1.3d | Generated `.plan/execute-script.py` resolver | Contains the OpenCode multi-root resolver (references `OPENCODE_CONFIG_DIR` / the multi-root walk), not the Claude-cache resolver |

---

## 2. Accepted risks to confirm

Behaviours the runtime assumes but that have never been observed on OpenCode. Each is confirmed
working or escalated with a documented remediation.

### 2.1 Subagent user-prompting

The `subagent dispatch` contract assumes a dispatched OpenCode subagent can prompt the user
through OpenCode's native `question`/`ask` tool and the answer propagates to the host.

Procedure: start a plan that reaches a finalize step requiring user confirmation (e.g.
branch-deletion) and observe the dispatched subagent.

| Check | Pass criterion |
|-------|----------------|
| 2.1a | OpenCode creates a sub-agent via its `task` tool |
| 2.1b | The subagent's `question` call renders a prompt the user can answer |
| 2.1c | The answer propagates back to the parent agent |

Remediation if FAIL: add an `inline_only: true` flag to the affected step kinds so the
orchestrator runs them in-context instead of dispatching; record the divergence in the runtime
contract (`platform-runtime/standards/contract.md`).

### 2.2 `task`-tool dispatch and variant resolution

`execution-context` and its `-level-N` variants dispatch sub-workflows; the workflow document
passes in the prompt body and a TOON return is expected back.

| Check | Pass criterion |
|-------|----------------|
| 2.2a | Dispatch creates a sub-agent for the workflow task |
| 2.2b | The workflow instructions in the prompt body are honoured |
| 2.2c | The sub-agent returns TOON the parent can parse |
| 2.2d | The specific `execution-context-level-N` variant named by the dispatch is used, not a default — and the level's `reasoningEffort:` provider-passthrough key is honoured (or its being ignored is recorded: same-model tiers then degrade to equivalent behaviour while staying independently resolvable) |

Remediation if FAIL: document the divergence in the runtime contract; consider a script-based
fallback where the orchestrator runs the workflow inline.

### 2.3 `skill`-tool loading

The body transform rewrites `Skill: {bundle}:{skill}` to
``Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing.``

| Check | Pass criterion |
|-------|----------------|
| 2.3a | The rewrite is present in the deployed copy |
| 2.3b | OpenCode's `skill` tool resolves the namespaced `{bundle}-{skill}` name |
| 2.3c | The loaded skill's instructions are acted on |
| 2.3d | `Skill:` mentions inside backtick prose remain unrewritten |

Remediation if FAIL: adjust `marketplace/targets/opencode/mapping.json::directive_rewrites`
(the template is data; the engine is shared) or record that OpenCode's `skill` tool is
LLM-driven without a loading guarantee.

### 2.4 Parallel dispatch

The one parallel-dispatch site in the marketplace is `enrich-module` under
`--phase phase-6-finalize`.

| Check | Pass criterion |
|-------|----------------|
| 2.4a | Multiple `task` sub-agents run concurrently |
| 2.4b | All results are collected by the parent |
| 2.4c | No lock/contention errors on shared state |

Remediation if FAIL: serialize the fan-out on OpenCode and document the limitation.

### 2.5 Instruction following

OpenCode loads `AGENTS.md` once and may lose it on compaction; Anthropic models in OpenCode may
ignore the `instructions` array (upstream OpenCode issue #8892). Complex multi-step workflows
degrade if instructions are lost.

| Check | Pass criterion |
|-------|----------------|
| 2.5a | `AGENTS.md` rules are honoured |
| 2.5b | Behaviour survives a compaction event |
| 2.5c | A full multi-step workflow completes without manual re-direction |
| 2.5d | The model in use is recorded (Opus-level recommended for complex skills) |

Remediation if FAIL: keep the `opus`→latest-Opus mapping (no downgrades); document that Opus is
required for complex skills; if the `instructions` array is ignored, move critical rules into
the system prompt or first user message.

---

## 3. Smoke flows

1. **Fresh-init → refine → outline** on a trivial request — phase transitions occur in order,
   `session capture` returns `no-op` without aborting, `solution_outline.md` is written, plan
   state reads correctly.
2. **Execute → finalize sweep** — tasks run without abort, a finalize step that prompts works
   (risk 2.1), the plan archives, no error state remains.
3. **By-reference triage path** — dispatch `verification-feedback` under
   `--phase phase-6-finalize --role verification-feedback`; it loads `manage-findings`, queries
   the findings store, and returns TOON.
4. **Token capture no-op** — `platform_runtime metrics capture` without `--total-tokens`
   returns `no-op` with an actionable `alternative` and exit code 0; with `--total-tokens N` it
   returns success with the tokens captured.

---

## 4. CI generation gate — error-class coverage

`.github/workflows/opencode-generate-check.yml` runs `generate.py --target opencode` on every
PR touching `marketplace/bundles/**` or `marketplace/targets/**` and fails on any generator
error. The open question is negative coverage: confirm the gate actually fails on each error
class, not just passes on the happy path.

| Check | Scenario | Pass criterion |
|-------|----------|----------------|
| 4.1a | Valid bundles | Green |
| 4.1b | Broken frontmatter | Red, non-zero exit |
| 4.1c | Unmapped agent tool | Red with `UnmappedToolError` surfaced |
| 4.1d | `user-invocable: true` skill missing `description` | Red |
| 4.1e | Unrelated-file change | Workflow does not trigger |

These are exercisable as generator unit tests without a live OpenCode install; plan `020`
carries the fail-closed emission tests that overlap this table.

---

## Post-validation work

Plannable only after this protocol has run; authored as new plans in this epic at that point.

1. **Pin the OpenCode install path.** The `claude-distribute.yml` matrix publishes
   `dist-opencode` (branch) and `opencode/v*` (tags) on every `main` push / source tag. Which
   consumption path works against those refs — a git-ref add, an OpenCode marketplace install,
   or a deploy into `~/.config/opencode/` — is unverified on a live client. Test, then pin and
   document the working path as the primary one, and confirm the generated tree's root holds
   whatever manifest the chosen path expects.
2. **OpenCode user + developer documentation.** Add the verified install/update path to
   `doc/user/installation.adoc`; extend `doc/developer/` with the OpenCode inner loop
   (generate → `sync-opencode` → test, the deploy options, the singular→plural rename);
   document the per-operation OpenCode behaviour (real vs `no-op` with `reason`/`alternative`)
   as an orientation layer over `platform-runtime/standards/contract.md`; record the confirmed
   limitations (no platform-driven title/status hook, manual `--total-tokens`, any
   `inline_only` step kinds discovered). Every documented behaviour traces to something this
   protocol confirmed.
3. **Upgrade the validation framing** in `doc/developer/marketplace-build.adoc` and the
   repo-root multi-assistant sections once OpenCode is a validated runtime rather than
   best-effort output.
