# 02 — Validate the OpenCode runtime live

## Objective

Run plan-marshall on a real OpenCode installation for the first time. Every OpenCode
operation is coded (`opencode_runtime.py` implements all 15 operations and the OpenCode
emitter produces a full `target/opencode/` tree), but **none of it has executed in a
live OpenCode session.** This document is the gate: 03/04/05 are only worth finishing
once the runtime is proven.

The original design recorded a set of **accepted risks** — behaviours assumed to work on
OpenCode but never tested. This workstream confirms or escalates each one.

The executable companion to this document is
[02-verification-protocol.md](02-verification-protocol.md): it carries the exact commands,
expected observations, and pass/fail criteria for every check named here. This document is
the *why and what*; the protocol is the *how*.

## Why this is the highest-value remaining work

The marketplace already *emits* OpenCode artifacts and the runtime already *answers*
every operation. What is unknown is whether OpenCode's `task` tool, `skill` tool, and
permission model behave the way the runtime assumes. Until someone runs it, the OpenCode
support is theoretical.

## Setup

1. Generate the OpenCode tree: `python3 marketplace/targets/generate.py --target opencode
   --output target/opencode`.
2. Deploy it to a live OpenCode install (the deploy mechanism is workstream
   [04](04-developer-workflow-sync-opencode.md); until that ships, stage manually —
   singular→plural rename into `~/.config/opencode/` or an `OPENCODE_CONFIG_DIR`).
3. Initialize a plan with `--target opencode` and confirm `marshal.json` carries
   `runtime.target: opencode`. The OpenCode-resolver `.plan/execute-script.py` is a
   separate artefact: `project initial-setup` only creates `.plan/` and seeds
   `marshal.json`. To generate the executor, run `/marshall-steward` or invoke
   `tools-script-executor:generate_executor` directly.

## Accepted risks to confirm (from the original design)

| Risk | What to verify | If it fails |
|------|----------------|-------------|
| **Subagent `AskUserQuestion`** | A dispatched OpenCode subagent (e.g. a finalize step that prompts for branch-deletion confirmation) can prompt the user back through OpenCode's native `ask`/`question` tool and the answer propagates to the host. The entire `subagent dispatch` contract assumes this. | Add an `inline_only: true` flag to the affected step kinds so the orchestrator runs them in-context instead of dispatching. Document in the runtime contract. |
| **`task`-tool dispatch** | `execution-context` (and its `-level-N` variants) dispatch correctly via OpenCode's `task` tool; the workflow doc passed in the prompt body is honoured; the return TOON comes back intact. | Document the divergence; consider a script-based fallback for the affected workflow. |
| **`skill`-tool loading** | The `Skill:`-directive body rewrite (`Call the \`skill\` tool with { name: "{bundle}-{skill}" }`) actually loads the named skill in OpenCode. | Adjust the body transform spec in `marketplace/targets/opencode/transforms.md`. |
| **Parallel dispatch** | The one parallel-dispatch site in the marketplace (`enrich-module` under `--phase phase-6-finalize`) fans out correctly under OpenCode's `task` model. | Serialize the fan-out on OpenCode, or document the limitation. |
| **Instruction following** | OpenCode's `AGENTS.md` loads once and may be lost on compaction; Anthropic models in OpenCode may ignore the `instructions` array (upstream #8892). Complex multi-step workflows degrade. | Keep the `opus`→latest-Opus mapping (no downgrades); document that Opus is required for complex skills. |

## Smoke flows to run

1. **Fresh-init → refine → outline** on a trivial request; confirm phase transitions and
   `session capture` no-op handling.
2. **Execute → finalize** sweep; confirm a finalize step that prompts the user works
   (the `AskUserQuestion` risk above).
3. **By-reference triage path** — dispatch `verification-feedback` (under `--phase
   phase-6-finalize --role verification-feedback`) and confirm it loads `manage-findings`,
   queries the findings store, and returns TOON.
4. **Token capture no-op** — confirm `metrics capture` returns `no-op` with the manual
   `--total-tokens` alternative and the phase still completes.

## CI: OpenCode generation gate

The gate already exists (`.github/workflows/opencode-generate-check.yml`): it runs
`generate.py --target opencode` on every PR touching `marketplace/bundles/**` or
`marketplace/targets/**` and fails on any generator error — unmapped agent tool, invalid
frontmatter, or a `user-invocable: true` skill missing a `description`. The remaining work
is to confirm it actually fails on each of those error classes (the false-positive /
false-negative checks in [02-verification-protocol.md](02-verification-protocol.md) §4.1),
not just on the happy path.

## Acceptance

- Each accepted risk above is marked **confirmed working** or **escalated** with a
  documented remediation.
- The four smoke flows complete on a live OpenCode session (or their failures are
  documented with remediation).
- The OpenCode generation CI gate runs on every PR and fails on emitter errors.
- Any OpenCode-specific divergence is recorded in the runtime contract and in the
  OpenCode documentation ([05](05-opencode-documentation.md)).

## Dependencies

- [01 — Finish portability gaps](01-finish-portability.md) should land first so the live
  session exercises the real `platform-runtime` path.
