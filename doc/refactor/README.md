# OpenCode Support — Remaining Work

## What this directory is

The plan-marshall marketplace was redesigned for multi-target distribution (Claude Code
native + OpenCode + future targets) without changing the source-of-truth format. The
foundational work has landed. This directory is the focused record of the genuine next
steps to take OpenCode from "fully built but never run" to "validated and installable."

These are **planning documents, not implementation.** Each document below describes
remaining open work; completed work is captured once in "Landed baseline" and not
re-listed as tasks. Read [`principles.md`](principles.md) first — it governs every
workstream (goal-based API, no-op policy, single source of truth, no universal templating,
**openness to further targets**, terminology, document hygiene).

**The design is built for *N* targets, not a Claude-vs-OpenCode binary.** Adding a target
must cost only: implement two contracts + a data file, register once, edit zero general skill
bodies or shared scripts. That bar — and the seam work to reach it — is
[principles §6](principles.md) + [07](07-target-extensibility.md), and it shapes how every
other workstream resolves "where does this Claude-specific thing go."

## Landed baseline (do not re-plan)

These are in the tree today. Treat them as the foundation, not as open work.

| Capability | Where it lives |
|------------|----------------|
| `platform-runtime` abstraction (15 ops, both runtimes; OpenCode no-ops where the mechanism is absent) | `marketplace/bundles/plan-marshall/skills/platform-runtime/` |
| Target generator framework (`TargetBase`, `TARGET_REGISTRY`, `generate.py`); Claude target (verbatim mirror + `plugin.json` + variant emission) and OpenCode target (emitter, frontmatter transform, body transforms, dual-emit, mapping) | `marketplace/targets/` |
| Target-aware executor (Claude-cache resolver or OpenCode 7-root resolver, switched on `runtime.target`) | `tools-script-executor/scripts/generate_executor.py` |
| Distribution pipeline — target-parametrized `strategy.matrix`, `dist-{name}` orphan branch + `{name}/v*` tags | `.github/workflows/claude-distribute.yml` |
| Token capture, multi-platform bootstrap, `marshal.json runtime.target`, OpenCode body-transformer wiring | see [01](01-finish-portability.md) "Already landed" |
| Canonical build/distribution docs (present-tense AsciiDoc) | `doc/developer/marketplace-build.adoc`, `doc/developer/distribution.adoc`, `doc/concepts/execution-context.adoc` |

**Design facts that supersede the retired seven-cluster plan** (do not re-introduce the
old assumptions):

- Distribution uses the dist-branch + tag matrix, **not** a repo-root `marketplace.json`,
  GitHub Pages, or release tarballs. Adding a target is a matrix-entry change.
- Canonical docs live under `doc/developer/` and `doc/concepts/` as present-tense AsciiDoc,
  **not** flat `doc/{topic}.md` plan ports.
- The agent effort-variant scheme is `level-1 … level-7` (source of truth:
  `variant_emitter.py` `LEVEL_TABLE` + `effort-levels.md`), **not** the
  `low/medium/high/xhigh/xxhigh` names from the old plan.

## Remaining workstreams

| # | Workstream | Open work | Document |
|---|------------|-----------|----------|
| 01 | Finish portability gaps | 8 code-level gaps from a full sweep: permission tooling (both sides), metrics/transcript engine, `session_id` validation, project-local skill resolution, bundle/cache discovery, body-text tool-name transforms, terminal-title verification, target-aware authoring tools. All route to one of three homes (platform-runtime / OpenCode build target / stays-agnostic) per the placement model | [01-finish-portability.md](01-finish-portability.md) |
| 02 | Validate the OpenCode runtime live | Never run on a real OpenCode install. Accepted risks unconfirmed; smoke flows not executed. Setup checks (sections 0–1) are automatable and pass; sections 2–3 need an interactive session. Runbook: [02-verification-protocol.md](02-verification-protocol.md) | [02-validate-opencode-runtime.md](02-validate-opencode-runtime.md) |
| 02-protocol | Verification runbook for 02 | Companion checklist — exact commands, expected observations, pass/fail per check | [02-verification-protocol.md](02-verification-protocol.md) |
| 03 | Add the OpenCode distribution target | Matrix entry + generation-gate CI exist; the OpenCode install/consumption path is unverified on a live client | [03-distribution-opencode-target.md](03-distribution-opencode-target.md) |
| 04 | OpenCode developer inner loop | `sync-opencode` deploy skill + script do not exist yet | [04-developer-workflow-sync-opencode.md](04-developer-workflow-sync-opencode.md) |
| 05 | OpenCode user + developer documentation | Write once the runtime is validated | [05-opencode-documentation.md](05-opencode-documentation.md) |
| 06 | Execution-context cross-target mapping | Reference + one open task: OpenCode variant emitter (concrete model-per-level is already mappable via the existing `model_map`) | [06-execution-context-cross-target.md](06-execution-context-cross-target.md) |
| 07 | Target extensibility (optimise for further targets) | Generalise the seams so target #3 is cheap: target-opaque `install-hook`, target-neutral ABC contracts, data-driven body transforms, consolidated registration | [07-target-extensibility.md](07-target-extensibility.md) |
| 08 | Claude-coupling candidate inventory | Reference — the exhaustive `file:line` registry from a read-everything audit of ~880 files; the evidence base behind 01's gap classes and 07's seam fixes | [08-claude-coupling-inventory.md](08-claude-coupling-inventory.md) |

## Sequencing

```
01 finish-portability ──┬──► 07 target-extensibility (generalise the seams 01 lands on)
                        ▼
            02 validate-opencode-runtime ──┬──► 03 distribution-opencode-target
            (+ 02-verification-protocol)   ├──► 04 developer-workflow-sync-opencode
                                           └──► 05 opencode-documentation
```

- **01 first.** The remaining bypass call sites (permission tooling, transcript
  resolution, `session_id` validation) must route through `platform-runtime` before anyone
  runs the runtime on OpenCode, so the live validation in 02 exercises the real path.
- **02 is the gate.** OpenCode has never been run. 02 confirms or escalates the accepted
  risks (subagent `AskUserQuestion`, `task`-tool dispatch, parallel dispatch, instruction
  following) and runs the smoke flows. 03/04/05 are only worth finishing once 02 proves the
  runtime works.
- **06's variant-emitter task** feeds 02's `level-N` variant-resolution check (2.2d); it
  can be built independently but must land before that check can pass.
- **03, 04, 05 are independent** of each other and can proceed in parallel after 02.
- **07 runs alongside 01** — it generalises the seam shapes (target-opaque interfaces,
  data-driven transforms) that 01's call-site migrations land on; settling them with 01 keeps
  the migrations from baking in a two-target assumption.

## What we are NOT doing

- No change to the Claude Code source-of-truth format.
- No universal templating syntax (`{{ }}`) for cross-platform body text.
- No revival of the retired distribution design (repo-root `marketplace.json`, GitHub
  Pages, release tarballs).
- No re-porting of already-published canonical docs into flat `doc/*.md` files.
- No version numbers, changelogs, or dated update sections in any document.
