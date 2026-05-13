# 04 — Validate and Document

## Objective

Define how we know the refactor is complete, implement validation mechanisms, and document the new architecture.

## Why This Cluster Exists

A refactor without clear acceptance criteria is never finished. We need:
- Automated drift detection
- Health checks that work on both targets
- A single comprehensive architecture document
- Test coverage for the new components

## Output

- Drift detection CI gate
- `platform-runtime` health-check script
- `doc/multi-target-marketplace.adoc`
- Test plan with pass/fail criteria per cluster

## Drift Detection

Claude target drift detection is specified in [02 — Build System](02-build-system). This cluster defines the CI enforcement:

```bash
./pw generate -- --target claude --output target/claude
# Exit 0 = no drift
# Exit 2 = drift detected, print diff
```

## OpenCode Target Validation

The OpenCode target generates output under `target/opencode/` (see [02 — Build System](02-build-system)). Validation means:
- `target/opencode/opencode.json` is valid JSON with correct `$schema`
- All referenced skill directories exist in `target/opencode/skill/`
- Agent files are valid markdown with required frontmatter
- All agent tools are mapped (build fails with exit 2 on unmapped tools)
- Agents using `Task` or `Skill` have `task`/`skill` permissions correctly mapped

**CI behavior:**
```bash
./pw generate -- --target opencode --output target/opencode
# Exit 0 = valid output generated
# Exit 2 = generation failed (e.g., unmapped tool in agent, invalid frontmatter)
```

### Execution-context post-refactor validation

Carried over from the `refactor-execution-context` PR (the 11 named-agent → 1 `execution-context` consolidation; see `.plan/local/refactor-agents-reviewed/`). The Claude target was validated end-to-end during that PR; the OpenCode runtime was not. Cluster 04 owns the OpenCode side now.

- [ ] **Implementation**: deploy the post-refactor surface to an OpenCode test environment via `python3 marketplace/targets/generate.py --target opencode --output target/opencode`. Confirm exactly one `execution-context` agent emerges under `.opencode/agents/`, plus per-level variants if the OpenCode adapter emits them (or just the canonical if the OpenCode adapter uses the `model:` invocation argument instead of variant filenames). Smoke-test a fresh-init plan flow + a finalize sweep on OpenCode.
- [ ] **Testing**:
      - `AskUserQuestion` from an OpenCode subagent — the accepted risk from [`01-design-platform-api/plan.md`](../01-design-platform-api/plan.md) (and `07-rollout.md` § 4.3 in the predecessor planning set). First real OpenCode test of `execution-context`; the entire dispatcher contract assumes subagents can `AskUserQuestion` back to the user.
      - By-reference triage path — OpenCode subagent dispatched as `verification-feedback` (under `--phase phase-6 --role verification-feedback`, with `producer` runtime input) loads `manage-findings`, queries the per-plan findings store, processes findings with smart grouping, returns TOON.
      - Per-iteration parallel dispatch — `enrich-module` (dispatched under `--phase phase-6`) fans N dispatches in parallel under OpenCode's `task` tool model.
- [ ] **Documentation**: record any OpenCode-specific divergence in [`01-design-platform-api/plan.md`](../01-design-platform-api/plan.md) § `subagent dispatch`. If `AskUserQuestion` does not work as expected, escalate via the cluster-01 accepted-risk follow-up and document in [`doc/build-system.adoc`](../../build-system.adoc). If the by-reference triage shape or parallel dispatch surface issues, document the workaround in [`doc/build-system.adoc`](../../build-system.adoc) § Dispatch-Cost Considerations.

## Health Checks

`platform-runtime health-check --checks all` verifies:

**Claude:**
- `.claude/settings.local.json` exists (project or global)
- `claude_pre_prompt.js` exists (if display configured)
- MCP diagnostics available (if IDE integration enabled)

**OpenCode:**
- OpenCode config file exists (resolved from `./opencode.json`, `~/.config/opencode/opencode.json`, or `$OPENCODE_CONFIG_DIR/opencode.json`)
- Permissions configured in the resolved config

## Test Plan

### Unit Tests

| Component | What to Test |
|-----------|-------------|
| `platform-runtime` router | Correct target dispatch based on `runtime.target` |
| `ClaudeRuntime` | Settings patch, hook write, session ID capture |
| `OpenCodeRuntime` | Config patch, no-op behavior |
| `SessionStart` hook (Claude only) | Installed by `project initial-setup` on Claude, sets `$CLAUDE_CODE_SESSION_ID`. On OpenCode `project initial-setup` skips hook installation; verify nothing is written. |
| `session capture` | Reads env var, stores in `status.json` via `manage-status` |
| `metrics capture` | Reads stored session ID, locates transcript, sums usage |
| TOON output | All operations return valid TOON |
| No-op handling | Callers receive `status: no-op` and continue |
| Error handling | `hook_not_configured` when env var absent |
| User-invocable dual-emit | For each `user-invocable: true` source skill, the OpenCode emitter writes both a skill dir and a matching command wrapper from `templates/user-invocable-command.md`, with `description`, optional `model`, and `skill_id` substituted from frontmatter |
| Body transform — `Skill:` directive | Standalone-line `Skill: {bundle}:{skill}` rewrites to `Call the \`skill\` tool with \`{ name: "{bundle}-{skill}" }\` before continuing.` Inline `` `Skill: foo:bar` `` references in prose are untouched. |
| Body transform — slash command | `/{user-invocable-skill-name}` rewrites to `/{bundle}-{user-invocable-skill-name}` for every known user-invocable skill. Path-like substrings (`path/to/foo`) are not matched. |
| Executor resolver — Claude | `python3 .plan/execute-script.py plan-marshall:manage-status:manage_status get …` resolves under `~/.claude/plugins/cache/plan-marshall/*/skills/manage-status/scripts/manage_status.py` |
| Executor resolver — OpenCode | Same notation resolves under the first match across OpenCode's documented skill discovery roots plus the env-var override — `$OPENCODE_CONFIG_DIR/skills/` (when set), `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`, `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` — at directory `plan-marshall-manage-status/scripts/manage_status.py`. Returned path is absolute. |

### Integration Tests

| Scenario | How to Test |
|----------|-------------|
| Fresh project init (Claude) | Run `project initial-setup --target claude` (via `marshall-steward`), verify `.plan/`, `marshal.json` with `runtime.target: claude`, the SessionStart hook is installed in `.claude/settings.json`, and `.plan/execute-script.py` is generated with the Claude-cache resolver |
| Fresh project init (OpenCode) | Run `project initial-setup --target opencode`, verify `.plan/`, `marshal.json` with `runtime.target: opencode`, **no** SessionStart-equivalent hook is written, and `.plan/execute-script.py` is generated with the OpenCode-skill-roots resolver |
| Session capture | Run `session capture`, verify `session_id` stored in `status.json` via `manage-status` |
| Permission config | Run `permission configure`, verify settings file updated |
| Permission analyze | Run `permission analyze --checks all --scope both`, verify TOON output with findings array |
| Permission fix normalize | Run `permission fix --operation normalize --scope project --dry-run`, verify defaults added, duplicates removed |
| Permission ensure wildcards | Run `permission ensure-wildcards --scope project`, verify all bundle skill wildcards present |
| Permission ensure steps | Run `permission ensure-steps --marshal .plan/marshal.json --scope project`, verify missing `project:{skill}` steps have matching skill permissions |
| Permission web analyze | Run `permission web-analyze --scope both`, verify domain categorization and duplicate detection |
| OpenCode `ensure-executor` | Run `permission fix --operation ensure-executor` on OpenCode target, verify `permission.bash: { "python3 .plan/execute-script.py *": "allow" }` is added to the resolved opencode.json |
| OpenCode `cleanup-scripts` | Run `permission fix --operation cleanup-scripts` on OpenCode target with stale executor entries pre-seeded; verify the stale entries are removed from `permission.bash` and `permission.skill` in the resolved opencode.json |
| OpenCode `migrate-executor` | Run `permission fix --operation migrate-executor` on OpenCode target with a legacy-shape executor entry pre-seeded; verify it is rewritten to the current OpenCode permission shape |
| Bundle sync (Claude) | Run target generator, verify skills mirrored to `~/.claude/plugins/cache/` via `sync-plugin-cache` |
| Bundle sync (OpenCode) | Run target generator, verify output under `target/opencode/`; deploy via `sync-opencode` or `OPENCODE_CONFIG_DIR` |
| Drift detection | Introduce intentional orphan in `plugin.json`, verify CI fails |
| OpenCode generation | Generate OpenCode output, verify structure |

### End-to-End Test

1. Check out fresh clone
2. Run `./pw verify` — must pass
3. Run `./pw generate -- --target claude --output target/claude` — must report zero drift
4. Run `./pw generate -- --target opencode --output target/opencode` — must succeed
5. Run `./pw generate -- --target all --output target` — must do both

## Documentation

The six cluster plan documents in `doc/refactor/` (`README.md`, `principles.md`, and `01` through `06`) contain comprehensive design rationale, API contracts, architecture decisions, and migration guidance. They are the basis for the canonical project documentation produced by this cluster.

**Task:** After implementation stabilizes, port the refactor plans into their canonical homes:

| Source | Destination | What to Port |
|--------|-------------|--------------|
| `doc/refactor/README.md` | `doc/multi-target-marketplace.adoc` (umbrella overview) | Overview, dependency graph, terminology, source → engine → runtime → output architecture |
| `doc/refactor/principles.md` | `doc/principles.md` | Cross-cutting constraints, API design rules, no-op policy |
| `doc/refactor/01-design-platform-api/plan.md` | `doc/platform-runtime-api.md` | Full 13-operation API reference, TOON schemas, bootstrap invocation pattern, target framework + extension guide |
| `doc/refactor/02-build-system/plan.md` | `doc/build-system.md` | Target framework, generator CLI, drift detection, OpenCode emitter, source-format contract |
| `doc/refactor/03-refactor-for-portability/plan.md` | `doc/migration-guide.md` | Audit checklist, skill rewrites, permission migration, bootstrap migration, marshall-steward multi-platform behavior |
| `doc/refactor/05-distribution/plan.md` | `doc/distribution.md` | CI/CD, artifact hosting, end-user installation (Claude + OpenCode) |
| `doc/refactor/06-developer-workflow/plan.md` | `doc/developer-workflow.md` | Inner loop for Claude Code and OpenCode developers |

`doc/multi-target-marketplace.adoc` is the umbrella entry point — it carries the overview, architecture, and limitations summary, then cross-references the per-topic documents above. Per-topic documents own their domain content; the umbrella does not duplicate it.

**Rules for porting:**
- Remove "plan" language ("this cluster will...", "when complete...") — rewrite in present tense as authoritative documentation
- Keep all technical specifications (API contracts, schemas, exit codes, command examples)
- Update paths from hypothetical (`target/opencode/`) to actual once implemented
- Remove acceptance criteria and risk registers (those belong in planning artifacts, not user docs)
- Cross-reference between documents instead of duplicating

**Delete `doc/refactor/`** once all clusters are implemented and canonical documentation is published. The plans are temporary scaffolding, not permanent project documentation. Double-check that every specification, API contract, and migration guide has been ported to its canonical document (see table above) before deleting.

### Target-Specific Notes

**Claude Code:**
- Native target — source of truth format
- All agents and commands available
- Full feature set

**OpenCode:**
- Generated output — best-effort support
- All agents mapped with `task`/`skill` permissions (subagent dispatch and skill loading supported)
- Model aliases preserved (`opus` → `anthropic/claude-opus-4-7`); no forced downgrades to cheaper models
- No platform-driven status-line / terminal-title hook (anomalyco/opencode#8619); built-in `/statusline` TUI command available as alternative
- No automatic token usage extraction (requires `--total-tokens` manual input — see `session capture` no-op on OpenCode)
- `.plan/execute-script.py` is generated with the OpenCode-skill-roots resolver — same `{bundle}:{skill}:{script}` notation as Claude, different resolution table

## Acceptance Criteria

The entire refactor is complete when:

### For Cluster 00 (Cleanup / Precondition)
- [ ] No skill body contains a Claude tool name (`EnterPlanMode`, `ExitPlanMode`, `AskUserQuestion`, `Agent(subagent_type=…)`, `TaskCreate`, `Task:`, etc.) inside an instructional rule
- [ ] No skill body contains a section describing a Claude-only hook mechanism (terminal title, status-line, `SessionStart`, `UserPromptSubmit`, `PostToolUse`, etc.) — such content lives in `marketplace/bundles/{bundle}/skills/{skill}/references/{topic}.md`
- [ ] No skill body contains a section describing a Claude-only cache or session-resolver pipeline — such content lives in `references/{topic}.md`
- [ ] Every `.claude/` and `~/.claude/...` mention in skill bodies is either inside a `platform-runtime` call site (deferred to cluster 03) or removed because the prose described platform plumbing now living in `references/`
- [ ] The `plan-marshall` entry skill has its "Terminal Title Integration" and "Session ID Resolver" sections moved to `references/terminal-title.md` and `references/session-id-resolver.md` respectively
- [ ] `./pw verify` passes (canary — cleanup must not regress Claude Code)

### For Cluster 01 (Design Platform API)
- [ ] API contract document exists covering all 13 operations
- [ ] TOON schemas defined for success, error, no-op
- [ ] Router specification documented
- [ ] Boundary rules prevent new leakage

### For Cluster 02 (Build System)
- [ ] `marketplace/targets/` exists with framework
- [ ] Claude target produces zero drift on committed source
- [ ] OpenCode target produces valid output under `target/opencode/` with `skill/`, `agent/`, `command/`, and `opencode.json`
- [ ] Every Claude source skill with `user-invocable: true` produces both a `skill/{bundle}-{skill}/SKILL.md` and a `command/{bundle}-{skill}.md` wrapper (template-driven, frontmatter-derived)
- [ ] OpenCode-emitted bodies have all standalone-line `Skill:` directives rewritten to `skill` tool-call instructions per `transforms.md`
- [ ] OpenCode-emitted bodies have all `/skill-name` references rewritten to `/{bundle}-{skill-name}` for every user-invocable skill
- [ ] `marketplace/targets/opencode/transforms.md` exists and is the authoritative spec; `body-transforms.py` implements exactly those transforms (no silent extras)
- [ ] `./pw generate -- --target {claude,opencode} --output target/{claude,opencode}` works
- [ ] `marketplace/adapters/` retired

### For Cluster 05 (Distribution)
- [ ] GitHub Actions workflow builds and publishes artifacts on push to main
- [ ] GitHub Pages hosts browsable `target/opencode/` output at stable URL
- [ ] GitHub Releases attach versioned tarballs to tags
- [ ] Installation documentation exists for both Claude Code and OpenCode
- [ ] `opencode-marketplace install {pages-url}` succeeds

### For Cluster 03 (Refactor for Portability)
- [ ] No remaining `.claude/` or `~/.claude` **behavioural** references (writes, reads, hook installation) in plan-marshall skill bodies — all routed through `platform-runtime` (prose cleanup is verified under cluster 00)
- [ ] `tools-script-executor` is target-aware: same notation resolves correctly via the Claude-cache resolver on Claude and the OpenCode-skill-roots resolver on OpenCode
- [ ] `marshall-steward` uses goal-based calls
- [ ] `marshal.json` template includes `runtime.target`
- [ ] `./pw verify` passes on all 10 bundles

### For Cluster 04 (Validate and Document)
- [ ] CI generates both targets on every push
- [ ] CI fails on Claude drift
- [ ] `platform-runtime health-check` works on both targets
- [ ] `doc/multi-target-marketplace.adoc` published and accurate
- [ ] Test coverage for new components

### Global
- [ ] All tests pass (`./pw verify`)
- [ ] No regressions in Claude Code functionality
- [ ] Documentation matches implemented code

## Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Bootstrap scripts still hardcode Claude paths | Medium | Extend `bootstrap_plugin.py` to search multiple locations |
| OpenCode subagent/task tool behavior differs from Claude | Medium | Map permissions correctly; document behavioral differences |
| OpenCode instruction following weaker than Claude Code (AGENTS.md loads once, may be lost on compaction; Anthropic models may ignore instructions array) | Medium | Preserve `opus` mapping; document limitation; recommend Opus for complex skills |
| OpenCode spec drift | Low | Generated output labeled "best effort" |
| Documentation out of sync | Low | Write docs after implementation; review against code |

## Dependencies

- Clusters 01, 02, 03 must be complete for final validation
- Documentation can be drafted in parallel but must be verified against final code
