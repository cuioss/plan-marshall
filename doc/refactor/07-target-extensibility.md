# 07 — Target Extensibility (optimise for further targets)

## Objective

Make the multi-target structure optimal for *N* targets, not a Claude-vs-OpenCode binary.
The seams were built while standing up the second target; this workstream generalises them
so a third (Cursor, Windsurf, a future adapter) costs near-zero core change.

This document audits the extensibility seams and lists the structural work. The runtime
*call-site* migration (making the existing two targets clean) is [01](01-finish-portability.md);
this document is about the *shape of the seams themselves*.

## The cost-to-add-a-target contract

The bar from [principles §6](principles.md):

> Adding a target costs: implement two contracts + a data file, register once, and edit
> zero general skill bodies, shared runtime scripts, or other targets.

Concretely, adding target `X` should be exactly:

1. `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/x_runtime.py` —
   subclass `Runtime`, implement each op or decline via `no-op`. Declares X's layout roots.
2. `marketplace/targets/x/` — subclass `TargetBase`, plus `mapping.json` (+ transform config)
   declaring X's tool permissions, model map, body-transform rules, and frontmatter shape.
3. Register X once on each side (the runtime `_REGISTRY`, the build `TARGET_REGISTRY`).

Nothing else. No general skill body, no shared script, and no other target may need editing.

## Contracts are semantic — the data-format rule

A registry + ABC only delivers cheap targets if the **contract carries normalized data**, never
the target's wire/API format ([principles §1](principles.md)). This is the difference between a
real abstraction and a relocated coupling:

- A `Runtime` op takes and returns *semantic* values — normalized token categories, web domains,
  resolved roots, a phase/status state — not Claude's `message.usage` shape, permission-DSL
  strings (`Bash(...)`), transcript JSONL, or hook-event names.
- The format lives **inside** the concrete `*_runtime`. The headline example is metrics:
  `claude_runtime` parses the transcript and applies Anthropic cache weights, but the op returns
  `{input, output, cache_read, cache_creation, total}` — so a third target implements the same
  contract by returning the same normalized shape from its own source, and `manage-metrics` is
  untouched. Returning "the transcript path" instead would be a relocated coupling, not an
  abstraction.

When auditing a proposed op, apply the switch-targets test: if the data crossing the boundary
would change shape on a different target, the format is leaking — normalize the contract.

## Seam audit

### Already N-target-shaped (keep)

| Seam | Evidence | Why it scales |
|------|----------|---------------|
| Build target contract | `marketplace/targets/base.py` (`TargetBase` ABC), `__init__.py` `TARGET_REGISTRY` | Capability flags (`supports_agents`/`supports_commands`); add = subclass + register |
| Build CLI | `generate.py:34,79-82` | `--target` choices and `--target all` derive from the registry — no per-target CLI edit |
| Runtime contract | `runtime_base.py` (`Runtime` ABC, 15 ops), `platform_runtime.py:155` `_REGISTRY`, `_make_runtime` | Registry dispatch; add = subclass + register |
| Decline mechanism | `toon_noop` + [No-Op Policy](principles.md) | A target implements what it can, declines the rest, never fakes success |
| Per-target data | `marketplace/targets/opencode/mapping.json` (`tool_permissions`, `model_map`) under each `config_dir` | Mappings are data, not code |
| Layout resolution home | decided in [01](01-finish-portability.md) (Gaps 4/5) → `platform-runtime` op | Each target declares its own roots; the core owns no per-target root table |

### Not N-target-optimal (structural work)

**1. `project_install_hook` encodes Claude's hook model in the interface.**
`runtime_base.py:125-159` names `SessionStart`, `UserPromptSubmit`, `Notification`, `Stop`,
`PostToolUse:AskUserQuestion`, `statusLine`, and `CLAUDE_CODE_DISABLE_TERMINAL_TITLE`, and its
`target` parameter is a *settings-file path*. A third target can only no-op the whole thing.
**Required:** generalise to a target-opaque op (e.g. `session install-integration` — "wire up
whatever session/display integration this target needs into its own config"). The Claude
event vocabulary, the `statusLine` command, and the env-var move entirely into
`claude_runtime.py`. The router stops passing a Claude settings-file path as `target`.

**2. The ABC contract enumerates two targets.** Nearly every docstring in `runtime_base.py`
reads "On Claude: … On OpenCode: …" (e.g. `session_capture`, `metrics_capture`,
`subagent_dispatch` "`Task:` on Claude, `task` on OpenCode"). A third implementer has no slot.
**Required:** rewrite each ABC docstring as target-neutral *intent* + the no-op fallback;
move per-target behaviour notes into the concrete `*_runtime` classes.

**3. Body transforms are per-target code, not data.** `marketplace/targets/opencode/body_transforms.py`
hardcodes the rewrite strings (`Skill:` → skill-tool call, `/slash`). A new target must write a
whole new module. **Required:** a shared transform engine that reads per-target rewrite rules
(extend `mapping.json`, or a sibling `transforms.json`) — `directive_rewrites`,
`tool_name_rewrites`, `slash_rewrites`. Each target supplies data; the engine is shared.
Fold the existing `transforms.md` spec into the shared engine's contract. (This is the
mechanism behind [01](01-finish-portability.md) Gap 6 — `AskUserQuestion`/`Task:`/`Skill:`.)

**4. Registration is scattered.** Adding a runtime target touches `_REGISTRY`, two imports,
`_TARGET_BOOTSTRAP_LIBS:67`, and several `default="claude"` fallbacks
(`platform_runtime.py:239,490,507,513`). **Required:** consolidate to one registration block
plus a single `_DEFAULT_TARGET` constant, so "add a target" is one obvious edit per side.

**5. Two concrete leaks the full audit ([08](08-claude-coupling-inventory.md) §D) confirmed:**
- `opencode_runtime.py:411` hardcodes `subagent_type: "execution-context-level-3"` (a fixed
  level) while `claude_runtime` parameterizes `subagent_type`. Parameterize it — a hardcoded
  level is both a bug and a target-shaped assumption.
- `manage-terminal-title/scripts/manage_terminal_title.py:71-101` is labelled "platform-agnostic"
  but `resolve_icon` is keyed on Claude hook-event names + tool names (`AskUserQuestion`, `Bash`).
  The composer must take a target-neutral state, not Claude event strings — the event→icon
  mapping is a `platform-runtime` concern (audit class A3).

## Settled decision — source vocabulary

Source stays **Claude-native**; cross-target rewriting is **data + a shared engine**, not a
source rewrite:

- The source keeps Claude idioms (`AskUserQuestion`, `Task:`, `Skill:` directives, `/slash`).
- Each target declares its rewrites as data (structural item 3); the shared engine applies
  them. The Claude target declares none → its output stays verbatim and independently
  validatable.
- A **registered "Claude source vocabulary"** lets the engine **fail the build** on any source
  idiom in that vocabulary a non-verbatim target leaves unmapped — the same fail-closed
  discipline as the existing `UnmappedToolError`.

Rationale: keeps the canonical/tested target verbatim (lowest risk), avoids a 313-site source
rewrite, and still makes "add a target" a data-only change. Rejected alternative: neutralising
the source vocabulary — symmetric but loses Claude-verbatim validation and changes
[principles §4](principles.md) for a benefit the fail-closed registry already secures.

## Acceptance

- A documented "add target X" checklist exists and is exactly the three steps above.
- No `Runtime` / `TargetBase` ABC docstring or signature names a specific non-canonical target.
- `project_install_hook` is target-opaque; Claude hook specifics live only in `claude_runtime.py`.
- Body transforms run through one shared engine over per-target rule data; a new target adds
  no transform code.
- The build fails closed on an unmapped registered Claude idiom.
- Runtime + build target registration is each a single obvious edit site.
- Claude output remains verbatim and equality-validated.

## Dependencies

- [01 — Finish portability gaps](01-finish-portability.md) — the call-site migration; this
  workstream generalises the seams those migrations land on (esp. layout resolution + Gap 6).
- [principles §6](principles.md) — the governing rule this workstream realises.
- [06 — Execution-context cross-target mapping](06-execution-context-cross-target.md) — the
  variant emitter is a worked example of per-target build data (model-per-level).
