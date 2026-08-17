# Run report — 010-runtime-seam-neutrality (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/runtime-seam-neutrality-osuaxx` (harness-assigned; kept as-is per the lane contract)    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by reading the bundle source path — the `plan-marshall` plugin is not installed in this cloud
session, so `Skill: {bundle}:{skill}` notation was not attempted.

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill: cloud-plan-lane` (project-local, `.claude/skills/`) — first action of the run |
| `plan-marshall:ref-code-quality` | bundle path |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `plan-marshall:persona-implementer` | bundle path (production code) |
| `pm-dev-python:python-core` | bundle path (Python production code) |
| `pm-dev-python:pytest-testing` | bundle path (Python tests) |

No skill was unobtainable by either route.

Epic context read alongside: `doc/plans/multiplattform/reference/principles.md` (the governing
cross-cutting principles, §6 in particular).

## Deliverables

| # | Deliverable | Commit | Verification state |
|---|---|---|---|
| D4 | Parameterized OpenCode dispatch | `ecccbbe` | Red-first demonstrated, then green |
| D3 | Registration consolidated | `29c58d6` | Both lockstep invariants demonstrated red against deliberate mismatches, then green |
| D1 | Target-opaque install op | `e43e2e7` | New guard mutation-tested; existing Claude install behaviour unchanged in effect |
| D2 | Target-neutral ABC docstrings | `12fa439` | Zero-hit search re-run at verification time |

**D1 — Target-opaque install op.** `runtime_base.project_install_hook` now states intent only. Its
docstring carries no Claude hook-event name, no `CLAUDE_CODE_*` string, and no settings-file path;
the only `.json` in it is `marshal.json`, plan-marshall's own file. The signature's `target` is the
target identifier, and the Claude settings-path resolution — including the absolute-path
test/recovery override — moved into `_claude_runtime_impl`, documented there and advertised by
neither the ABC nor the router help.

The two Claude-named booleans `overwrite_statusline` / `overwrite_env_disable` were named in the
plan's Problem §1 as part of the coupling, and D1's goal statement requires the `statusLine` command
to appear only in the Claude implementation — so a rename was mandatory. They became one
`overwrite: Sequence[str]` of **target-defined conflict keys**. That shape was chosen over two
renamed booleans because two booleans would still hardcode *two* conflict points in the shared ABC,
which is principle 6's "core-owned target table" in miniature; the sequence lets a third target with
different conflict points need no ABC change at all. Claude defines `statusline` and `env-disable`
and rejects anything else with `unknown_overwrite_key` **before any write**, because silently
ignoring a typo would answer "conflict preserved" to a caller who explicitly asked to overwrite.

Existing Claude install behaviour is pinned by the pre-existing test bodies, which pass unchanged in
effect: the ~60 call sites that pass an absolute `tmp_path` still work, because the recovery override
survives inside the Claude implementation. Only the two `overwrite_*=True` call sites changed shape.

**A refuted plan claim.** The plan labelled as HYPOTHESIS: *"No caller outside `platform-runtime`
constructs the Claude settings path for the install op."* This is **refuted**.
`marshall-steward/references/menu-healthcheck.md` invoked
`project install-hook --target .claude/settings.local.json` — a **relative** path, which the
implementation has been rejecting with `unknown_target` since the `candidate.is_absolute()` guard
was introduced. That documented invocation could not have worked. It now passes `--target claude`
and reads the resolved file from the response's `settings_path`; two neighbouring prose statements
in the same file that asserted the write would land in `./.claude/settings.local.json` were
corrected with it, since `--target claude` may resolve to `.claude/settings.json` instead.

**D2 — Target-neutral ABC docstrings.** The hit list was re-derived by search rather than taken from
the plan: eleven `On Claude` hits and eleven `On OpenCode` hits, spanning `layout_skill_roots`,
`layout_bundle_cache_root`, `session_capture`, `session_push_title_token`, `session_bind`,
`session_resolve_plan`, `session_doctor`, `session_teardown`, `session_reload_directive`,
`metrics_capture`, and `metrics_normalized_tokens` — plus `subagent_dispatch`'s inline
"``Task:`` on Claude, ``task`` on OpenCode". A case-sensitive search for both phrases over
`runtime_base.py` now returns **0**.

Three further target leaks in the same file, outside the `On Claude` hit list but the same
anti-pattern, were cleared under D2's goal (a third implementer reading `runtime_base.py` alone):
the module docstring naming both concrete classes, `project_initial_setup`'s `target` argument
documented as `"claude"` or `"opencode"`, and `metrics_normalized_tokens`' doc-residency example
naming `CLAUDE.md`. A search for `Claude|OpenCode|claude|opencode|CLAUDE` over `runtime_base.py`
now returns zero hits of any kind.

Displaced notes landed in the concrete classes: Claude gained the `hook_not_configured` rationale on
`session_capture`, the transcript-sum note on `metrics_capture`, the transcript paths / record shapes
/ `CLAUDE.md` doc-residency member on `metrics_normalized_tokens`, and the tool-name plus passthrough
note on `subagent_dispatch`; OpenCode gained the reason its `session_capture` declines as `no-op`
rather than `hook_not_configured`, and the "explicit count is always honoured" note on
`metrics_capture`.

**D3 — Registration consolidated.** `platform_runtime.py` declares `_DEFAULT_TARGET`, `_REGISTRY`
and `_TARGET_BOOTSTRAP_LIBS` adjacently as one block; all three argparse defaults and the bare
fallback read the constant. `_TARGET_BOOTSTRAP_LIBS` could only move below the pre-import bootstrap
call once `_bootstrap_glob_discover` guarded on `target is not None` — the pre-import call passes
`None`, so the name is never evaluated at that point. The literal `"claude"` now appears in
`platform_runtime.py` only inside the registration block and the constant definition.

`marketplace_paths.py`'s three fallback returns collapse onto `_DEFAULT_RUNTIME_TARGET`.

**One addition beyond D3's stated "Done when".** `marketplace_paths._invoke_layout_op` carried its
own `if target == 'opencode': … else: ClaudeRuntime` branch — a second target→class registration
site in a shared script, and precisely principle 6's forbidden `if target == …`. It now resolves the
class through the router's `_make_runtime`, so the module names no runtime class and enumerates no
target. This is not in D3's literal done-when, but the plan's **Goal** ("adding a runtime target is
one registration edit plus one default constant") is unreachable while adding target X still
requires editing `marketplace_paths.py`. Recorded here as a deliberate, Goal-driven addition rather
than silent scope creep.

**D4 — Parameterized OpenCode dispatch.** The literal `execution-context-level-3` no longer appears
in `opencode_runtime.py`; `subagent_type` echoes the requested `agent`, mirroring the Claude
passthrough. `standards/contract.md` states the passthrough as a cross-target rule.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` returns **10 files** — Python changes are
present, so the gate applies.

- Per-commit gate: every commit touching `*.py` was preceded by `./pw quality-gate` reporting
  `mypy … Success: no issues found in 411 source files`, `ruff … All checks passed!`,
  `SPDX-header check passed`, and plugin-doctor `status: pass` / `total_issues: 0` / `issues[0]`
  empty. The plan-directory commit (`a21b353`) is a pure `git mv` and needed no gate.
- Branch gate: `./pw verify` (all three sub-steps — quality-gate, test-compile, module-tests) run
  over the branch diff: **`=== verify: SUCCESS ===`, 20565 passed, 14 skipped**.
- `UV_HTTP_TIMEOUT=600` was set on every `./pw` call. No `uv.lock` churn appeared at any point;
  deliverable paths were staged explicitly, never `git add -A`.

## Findings

_pending — verification rounds in progress._

## Reviewer participation

_pending._

## Cost

- **Tokens:** not available to the agent in this session — the harness exposes no token counter to
  the running agent, so no figure is stated rather than an estimated one.
- **Wall-clock:** run start 2026-08-17 ~18:54 UTC (container clone timestamp); end time recorded at
  the close of the run.
- **Population:** whatever figures appear here count **this single Claude Code cloud session**. That
  is **NOT comparable** to a plan-marshall `metrics.toon` total, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. This
  session shares neither that boundary nor that tree, so the two cannot be reconciled and no parity
  is implied.

## Contract check (Step 9)

_pending._

## What have we learned (Step 9)

_pending._

## Residue

_pending._
