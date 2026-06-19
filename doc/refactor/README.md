# OpenCode Support — Remaining Work

## What this directory is

The plan-marshall marketplace was redesigned for multi-target distribution (Claude
Code native + OpenCode + future targets) without changing the source-of-truth format.
The **foundational work has landed.** This directory no longer contains the original
seven-cluster plan — that plan is superseded by the code now in the tree. What remains
here is a focused record of the genuine next steps to take OpenCode from "fully built
but never run" to "validated and installable."

This is a **documentation plan, not an implementation.** Nothing here has been
implemented by the rewrite that produced these files; the documents describe work to be
done.

## Landed baseline (do not re-plan)

These are in the tree today. Treat them as the foundation, not as open work.

| Capability | Where it lives | Notes |
|------------|----------------|-------|
| `platform-runtime` abstraction (15 operations, goal-based API) | `marketplace/bundles/plan-marshall/skills/platform-runtime/` | Router + `runtime_base.py` + `claude_runtime.py` + `opencode_runtime.py` + `claude_hook.py`. **`opencode_runtime.py` implements every one of the 15 operations** (with `no-op` where OpenCode lacks the mechanism). |
| Target generator framework | `marketplace/targets/` | `TargetBase`, `TARGET_REGISTRY`, `generate.py` CLI; `claude/` (verbatim mirror + always-generate `plugin.json` + variant emission) and `opencode/` (emitter, frontmatter transform, body transforms, dual-emit, mapping). |
| Source-side prose cleanup | skill bodies + `references/*.md` | Claude-only plumbing prose moved out of skill bodies; tool-name rules rephrased role-first. |
| Target-aware executor | `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` | Reads `runtime.target`; emits the Claude-cache resolver or the OpenCode 7-root resolver. Same `{bundle}:{skill}:{script}` notation on both. |
| `marketplace/adapters/` retired | (deleted) | Logic migrated into `marketplace/targets/opencode/`. |
| Distribution pipeline | `.github/workflows/claude-distribute.yml` | Target-**parametrized** `strategy.matrix`; publishes `target/claude/` to the `dist-claude` orphan branch and immutable `claude/v*` dist tags. |
| Tests | `test/plan-marshall/platform-runtime/`, `test/marketplace/targets/`, `test/plan-marshall/targets-claude/` | Router, both runtimes, hook, bootstrap, generator, variant emitter. |
| Canonical docs (partial) | `doc/developer/marketplace-build.adoc`, `doc/developer/distribution.adoc`, `doc/concepts/execution-context.adoc` | The build + distribution architecture is already documented here — in present-tense AsciiDoc, not as flat `doc/*.md` plan ports. |

## How reality diverged from the original plan

Three places where the codebase chose a different (better) path than the retired plan
assumed. The next-step documents below reflect the *current* reality, not the old plan.

1. **Distribution did not move `marketplace.json` to the repo root and did not use
   GitHub Pages / tarballs.** Instead, `claude-distribute.yml` publishes the generated
   `target/{name}/` tree to a `dist-{name}` orphan branch plus `{name}/v*` tags, and
   `/plugin marketplace add` points at the dist ref. Adding OpenCode is therefore a
   **matrix-entry change**, not a new hosting design. See
   [03 — Distribution: OpenCode target](03-distribution-opencode-target.md).

2. **Canonical documentation landed under `doc/developer/` and `doc/concepts/`**, in
   present-tense AsciiDoc, rather than the old "port each cluster plan into a flat
   `doc/{topic}.md`" table. New OpenCode docs extend that structure rather than create a
   parallel one. See [05 — OpenCode documentation](05-opencode-documentation.md).

3. **The agent effort-variant scheme is `-level-1` … `-level-7`**, not the
   `low/medium/high/xhigh/xxhigh` names the original cluster-02 plan used. The build
   emitter and `effort-levels.md` are the source of truth; any OpenCode validation must
   assert against the level-N names.

## Remaining workstreams

| # | Workstream | Status going in | Document |
|---|------------|-----------------|----------|
| 01 | Finish portability gaps | tasks 1-3 done (bootstrap, phase-5, plan-retrospective). Task 4 partial (permission tools SKILL.md updated, scripts not migrated). Tasks 5-7 open. | [01-finish-portability.md](01-finish-portability.md) |
| 02 | Validate the OpenCode runtime live | section 0 (prereqs) and 1 (setup) automated: 21 PASS / 1 NOTE. Sections 2-3 require interactive OpenCode session. Section 4 CI gate exists. | [02-validate-opencode-runtime.md](02-validate-opencode-runtime.md) |
| 03 | Add the OpenCode distribution target | matrix entry added to `claude-distribute.yml`. CI gate `opencode-generate-check.yml` created. | [03-distribution-opencode-target.md](03-distribution-opencode-target.md) |
| 04 | OpenCode developer inner loop | `sync-opencode` deploy skill does not exist yet | [04-developer-workflow-sync-opencode.md](04-developer-workflow-sync-opencode.md) |
| 05 | OpenCode user + developer documentation | write once the runtime is validated | [05-opencode-documentation.md](05-opencode-documentation.md) |

## Sequencing

```
01 finish-portability ──┐
                        ▼
            02 validate-opencode-runtime ──┬──► 03 distribution-opencode-target
                                           ├──► 04 developer-workflow-sync-opencode
                                           └──► 05 opencode-documentation
```

- **01 first.** The remaining bypass call sites (bootstrap, phase-5/retrospective
  capture, permission-tool delegation) should route through `platform-runtime` before
  anyone runs the runtime on OpenCode, so the live validation in 02 exercises the real
  path.
- **02 is the gate.** OpenCode has never been run. 02 is where the accepted risks from
  the original design (subagent `AskUserQuestion`, `task`-tool dispatch, parallel
  dispatch) are confirmed or escalated. 03/04/05 are only worth finishing once 02
  proves the runtime works.
- **03, 04, 05 are independent** of each other and can proceed in parallel after 02.

## Governing principles

[`principles.md`](principles.md) still governs every workstream here — goal-based API,
no-op policy, single source of truth, no universal templating syntax, terminology, and
document hygiene. Read it before starting any document below.

## What we are NOT doing

- No change to the Claude Code source-of-truth format.
- No universal templating syntax (`{{ }}`) for cross-platform body text.
- No revival of the retired distribution design (repo-root `marketplace.json`, GitHub
  Pages, release tarballs) — the dist-branch + matrix design supersedes it.
- No re-porting of already-published canonical docs into flat `doc/*.md` files.
- No version numbers, changelogs, or dated update sections in any document.
