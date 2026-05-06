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
| `SessionStart` hook | Installed by `project initial-setup`, sets `$CLAUDE_CODE_SESSION_ID` |
| `session capture` | Reads env var, stores in `status.json` via `manage-status` |
| `metrics capture` | Reads stored session ID, locates transcript, sums usage |
| TOON output | All operations return valid TOON |
| No-op handling | Callers receive `status: no-op` and continue |
| Error handling | `hook_not_configured` when env var absent |

### Integration Tests

| Scenario | How to Test |
|----------|-------------|
| Fresh project init | Run `project initial-setup` (via `marshall-steward`), verify `.plan/`, `marshal.json`, and SessionStart hook installed |
| Session capture | Run `session capture`, verify `session_id` stored in `status.json` via `manage-status` |
| Permission config | Run `permission configure`, verify settings file updated |
| Permission analyze | Run `permission analyze --checks all --scope both`, verify TOON output with findings array |
| Permission fix normalize | Run `permission fix --operation normalize --scope project --dry-run`, verify defaults added, duplicates removed |
| Permission ensure wildcards | Run `permission ensure-wildcards --scope project`, verify all bundle skill wildcards present |
| Permission ensure steps | Run `permission ensure-steps --marshal .plan/marshal.json --scope project`, verify missing `project:{skill}` steps have matching skill permissions |
| Permission web analyze | Run `permission web-analyze --scope both`, verify domain categorization and duplicate detection |
| OpenCode no-op executor | Run `permission fix --operation ensure-executor` on OpenCode target, verify `status: no-op` with reason |
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
- No terminal title hooks
- No automatic token usage extraction (requires `--total-tokens` manual input)
- Direct script execution (no `execute-script.py`)

## Acceptance Criteria

The entire refactor is complete when:

### For Cluster 01 (Design Platform API)
- [ ] API contract document exists covering all 13 operations
- [ ] TOON schemas defined for success, error, no-op
- [ ] Router specification documented
- [ ] Boundary rules prevent new leakage

### For Cluster 02 (Build System)
- [ ] `marketplace/targets/` exists with framework
- [ ] Claude target produces zero drift on committed source
- [ ] OpenCode target produces valid output under `target/opencode/` with `skill/`, `agent/`, `command/`, and `opencode.json`
- [ ] `./pw generate -- --target {claude,opencode} --output target/{claude,opencode}` works
- [ ] `marketplace/adapters/` retired

### For Cluster 05 (Distribution)
- [ ] GitHub Actions workflow builds and publishes artifacts on push to main
- [ ] GitHub Pages hosts browsable `target/opencode/` output at stable URL
- [ ] GitHub Releases attach versioned tarballs to tags
- [ ] Installation documentation exists for both Claude Code and OpenCode
- [ ] `opencode-marketplace install {pages-url}` succeeds

### For Cluster 03 (Refactor for Portability)
- [ ] No `.claude/` or `~/.claude` leakage in plan-marshall skill bodies
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
