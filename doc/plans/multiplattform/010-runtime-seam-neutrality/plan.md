> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The Runtime contract is target-opaque and registered in one place per side

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper and relative links would dangle)
**Branch prefix:** chore — refactoring of the runtime abstraction, no new capability

## Problem

The `Runtime` ABC (`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py`)
is the contract a new target implements, and four seams in it encode the Claude target instead of
stating target-neutral intent:

1. **`project_install_hook` is a target-shaped contract.** Its ABC docstring specifies the Claude
   hook-event vocabulary (`SessionStart`, `UserPromptSubmit`, `Notification`, `Stop`,
   `PreToolUse:AskUserQuestion`, `PreToolUse:Bash`, `PostToolUse:*`), the `statusLine` command, and
   `env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE`, and it types `target` as a settings-file path
   (`.claude/settings.local.json`), with `overwrite_statusline` / `overwrite_env_disable` named for
   Claude mechanisms. The canonical *invocation* is already semantic (`project install-hook
   --target claude`, with the Claude implementation resolving its own settings path; an absolute
   path is a test/recovery escape hatch) — the coupling is the contract text and the path-typed
   parameter shape, which describe Claude's wiring rather than an intent a third target could
   realise its own way.
2. **The ABC docstrings enumerate targets.** The layout, session, and metrics operation docstrings
   read "On Claude: … On OpenCode: …", and `subagent_dispatch` names both targets inline
   ("`Task:` on Claude, `task` on OpenCode"). The hit list, not any count, is the work list —
   re-derive it by searching `runtime_base.py` for `On Claude`. A third implementer has no slot,
   and every new target grows the enumeration — the exact anti-pattern
   `doc/plans/multiplattform/reference/principles.md` §6 forbids in a contract.
3. **Registration is scattered.** `platform_runtime.py` holds two separate per-target dicts
   (`_REGISTRY` and `_TARGET_BOOTSTRAP_LIBS`), three `default="claude"` argparse defaults, and a
   bare `target = "claude"` fallback, with no `_DEFAULT_TARGET` constant;
   `script-shared/scripts/marketplace_paths.py` repeats its own `'claude'` fallback returns.
   "Register once" is currently five-plus edit sites.
4. **`opencode_runtime.subagent_dispatch` hardcodes the dispatch level.** It returns
   `subagent_type: "execution-context-level-3"` regardless of the requested agent, while the Claude
   implementation passes the requested `agent` through — a behavioural inconsistency (level
   selection is silently discarded on OpenCode) and a target-shaped assumption in one.

## Goal

A third-target implementer can read `runtime_base.py` alone and implement or decline every
operation without ever opening `claude_runtime.py`; adding a runtime target is one registration
edit plus one default constant; and no runtime returns a dispatch payload that discards the
caller's level selection.

## Deliverables

1. **D1 — Target-opaque install op** — `project_install_hook`'s ABC contract states intent only
   ("wire this target's session/display integration into its own configuration, or decline via
   no-op") plus the no-op fallback; the Claude hook-event vocabulary, the `statusLine` command, and
   the `CLAUDE_CODE_DISABLE_TERMINAL_TITLE` env var appear only in `claude_runtime` /
   `_claude_runtime_impl`. The contract is pinned, not left open: callers pass the **target id
   only** (the existing semantic `--target claude` invocation is unchanged), each implementation
   resolves its own configuration location, and the absolute-settings-path escape hatch becomes
   Claude-implementation-internal (a test/recovery override handled inside the Claude
   implementation, absent from the ABC signature and the router help). The router, both
   implementations, `standards/contract.md`'s op entry, callers, and tests change together. The
   operation's wire name stays `project install-hook` — the coupling is the vocabulary and the
   path typing, not the word "hook", and keeping the name avoids a caller sweep.
   *Done when:* `runtime_base.py` contains no Claude hook-event name, no `CLAUDE_CODE_*` string,
   and no settings-file path in `project_install_hook`'s signature or docstring; existing Claude
   install behaviour is pinned by tests that pass unchanged in effect (updated only for the new
   parameter shape); the OpenCode implementation declines honestly per the no-op policy.
2. **D2 — Target-neutral ABC docstrings** — every enumerating docstring (the re-derived hit list
   from the Problem) and the `subagent_dispatch` inline mention are rewritten as intent + no-op
   fallback; the per-target behaviour notes move to the concrete `*_runtime` classes.
   *Done when:* a case-sensitive search for `On Claude` and `On OpenCode` over `runtime_base.py`
   returns zero hits, the concrete runtimes carry the displaced notes, and `./pw verify` passes.
3. **D3 — Registration consolidated** — `platform_runtime.py` declares one `_DEFAULT_TARGET`
   constant consumed by every argparse default and fallback, and declares `_REGISTRY` and
   `_TARGET_BOOTSTRAP_LIBS` adjacently as the single registration block; `marketplace_paths.py`'s
   fallback returns collapse onto one module-level constant. A lockstep test asserts the two
   modules' default-target values agree and that `_TARGET_BOOTSTRAP_LIBS`'s key set equals
   `_REGISTRY`'s, so the two-module split cannot drift silently.
   *Done when:* the literal `"claude"` appears in `platform_runtime.py` only inside the
   registration block and the constant definition; the lockstep test exists and fails when either
   invariant is broken (demonstrated red-first against a deliberate mismatch, then green).
4. **D4 — Parameterized OpenCode dispatch** — `opencode_runtime.subagent_dispatch` returns the
   requested agent name as `subagent_type`, mirroring the Claude implementation's passthrough.
   *Done when:* the literal `execution-context-level-3` no longer appears in
   `opencode_runtime.py`; a test dispatching two different level variants observes each name
   echoed back.

## Out of scope

- **Renaming the `project install-hook` operation** — a rename buys no abstraction (the coupling is
  the vocabulary and the path parameter) and costs a sweep of every caller; excluded so the run
  does not drift into a marketplace-wide rename mid-run.
- **New `Runtime` operations or removals** — the 24-operation surface is unchanged; this plan
  reshapes contracts, and growing the surface would entangle it with contract-schema work
  (`standards/contract.md`) it does not need.
- **The `targets:` frontmatter mechanism and the Claude-literal script residuals** — owned by plans
  `020` and `030`; pulling them in here would break the epic's surface partition.
- **Migrating existing waiting call sites onto `wait_for`** — deliberate follow-up work recorded
  in `doc/plans/multiplattform/reference/coupling-inventory.md` § "Deliberate non-migrations"; not
  a seam-shape defect.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — D1, D2
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — D3
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`,
  `_claude_runtime_impl.py` — D1 (vocabulary and path resolution move here), D2 (displaced notes)
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — D2
  (displaced notes), D4
- `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — only if the
  install op's documented parameter shape changes there; no schema addition
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` — D3
- `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/script-shared/**` — tests for all
  four deliverables
- Callers of `project install-hook` (locate by searching for the operation string) — only if D1's
  parameter-shape change reaches their invocations

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `project_install_hook`'s docstring names Claude hook events, `statusLine`, `CLAUDE_CODE_DISABLE_TERMINAL_TITLE`, and types `target` as a settings-file path; the canonical steward invocation is already semantic (`--target claude`, path resolved inside the implementation) | OBSERVED | `runtime_base.py` — `project_install_hook`; `_claude_runtime_impl.py` — its implementation; re-read before acting |
| The set of "On Claude/On OpenCode"-enumerating ABC docstrings spans the layout, session, and metrics operations, plus `subagent_dispatch` inline | OBSERVED, membership is a lead | re-derive by searching `runtime_base.py` for `On Claude` — fix every hit, whatever the set |
| `platform_runtime.py` has no `_DEFAULT_TARGET`; `"claude"` defaults sit at three argparse sites plus one bare fallback | OBSERVED, count is a lead | re-derive by searching `platform_runtime.py` for `"claude"` |
| `marketplace_paths.py` carries its own repeated `'claude'` fallback returns | OBSERVED | `marketplace_paths.py` — the layout-op fallback helpers; re-derive by search |
| `opencode_runtime.subagent_dispatch` hardcodes `execution-context-level-3`; the Claude side passes `agent` through | OBSERVED | `opencode_runtime.py` — `subagent_dispatch`; `_claude_runtime_impl.py` — `subagent_dispatch` |
| The `Runtime` ABC has 24 abstract operations | OBSERVED, count is a lead | re-derive: count `@abstractmethod` in `runtime_base.py` |
| No caller outside `platform-runtime` constructs the Claude settings path for the install op | HYPOTHESIS | search the marketplace for the op invocation string and for `settings.local.json` near it; a caller found → its invocation is part of D1's surface |

## Verification

- `./pw verify` over the branch diff (Python changes — the build gate applies).
- The D2 zero-hit search and the D1 vocabulary sweep over `runtime_base.py`, run at verification
  time, not carried from authoring.
- The D3 lockstep test demonstrated red-first, then green.
- **Cold read (contract-shape check):** the pre-PR verification sub-agent reads the new
  `project_install_hook` and layout/metrics docstrings **cold** — without `claude_runtime` in
  context — and reports whether it could implement or decline each for a hypothetical third target
  from the ABC text alone. A reading that needs Claude specifics to make sense means the wording
  failed, however complete it looks.

## Notes

- The concrete Claude wiring this plan relocates is behaviour, not new design: the Claude
  event→state mapping for the terminal title already lives in `claude_runtime`
  (`_claude_event_to_process_state`), so D1 follows an established relocation pattern.
- `_TARGET_BOOTSTRAP_LIBS` stays a dict (its content is genuinely per-target data); D3 changes
  *where* it is declared and how its consistency is enforced, not its shape.
- Plan `030` also edits `claude_runtime` / `_claude_runtime_impl`; the two plans share that surface
  and must not run concurrently — see the epic README's concurrency table.
