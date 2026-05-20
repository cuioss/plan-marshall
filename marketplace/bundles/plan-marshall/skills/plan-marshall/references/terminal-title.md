# Terminal Title Integration

Each Claude Code session tab can display the active plan, current phase, and a live status icon (`▶` running, `?` waiting, `◯` idle, `✓` done). Rendering is split between a **writer** (plan-marshall) and a **reader** (per-target platform runtime):

- **Writer** — `manage-status` mutation paths publish a plaintext title body to `{plan_dir}/title-body.txt` whenever phase, short_description, or archive lifecycle changes. The publication contract (location, encoding, lifecycle, atomicity) is owned by `manage-status` and specified in [`../../manage-status/standards/status-lifecycle.md` § Title-Body Artifact](../../manage-status/standards/status-lifecycle.md).
- **Reader** — Per-target `session render-title` operation composes `{icon} {body}` from the active-command-state cache plus the contents of `title-body.txt` and forwards the resulting OSC sequence to the controlling terminal. The reader is specified in the cluster-01 platform-api design doc (`doc/refactor/01-design-platform-api/plan.md`) under the `session render-title` operation.

## Resolution Contract

The reader's resolution chain is intentionally flat:

1. **`title-body.txt` exists** — read the file's contents verbatim and render `{icon} {body}`. The writer guarantees the body is well-formed (`pm:{phase}` or `pm:{phase}:{short_description}`) or absent; the reader does not parse, re-derive, or fall back to `status.json`.
2. **`title-body.txt` absent** — no plan to render. Fall through to the active-command segment (if any), otherwise the `{icon} claude` fallback.
3. **Active slash command** — captured per session by the platform-runtime hook from the `UserPromptSubmit` prompt when it starts with `/`, stored at a per-target session-cache location, and cleared on `Stop`/`SessionStart`. Shown as `{icon} {command}` when no `title-body.txt` resolves.
4. **Fallback** — `{icon} claude` when neither a title body nor an active command is known.

The absence of a resolver chain is the design point: the writer publishes structured state, the reader composes the displayed string. Plan-id resolution, status.json parsing, terminal-phase guards, session-cache fallbacks, and worktree-cwd walk-up logic all live in the writer side, not the renderer.

## Done emission

When `phase-6-finalize` archives a plan, the `archive` mutation deletes `title-body.txt`. The reader therefore naturally falls through to active-command / `claude` on the next render — no separate stateless "done" emission is required. If a target platform chooses to display a sticky `✓ pm:done:{short_description}` label after archive, the platform-runtime implementation owns that policy; the writer's contract ends at file deletion.

## Cross-References

- [`../../manage-status/standards/status-lifecycle.md` § Title-Body Artifact](../../manage-status/standards/status-lifecycle.md) — writer contract: file location, content shape, encoding, lifecycle table, atomic-write semantics.
- `doc/refactor/01-design-platform-api/plan.md` § `session render-title` — reader contract (per-target platform runtime): how the icon, active-command segment, and `title-body.txt` are composed and forwarded to the terminal.
- [`hook-authoring-guide.md`](hook-authoring-guide.md) — general JSON envelope contract for any hook-driven plan-marshall script.
