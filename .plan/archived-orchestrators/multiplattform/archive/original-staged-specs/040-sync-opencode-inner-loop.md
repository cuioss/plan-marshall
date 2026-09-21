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

# A developer can deploy the generated OpenCode tree in one command

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper and relative links would dangle)
**Branch prefix:** feature — a new developer-workflow capability

## Problem

The Claude inner loop is one command: edit `marketplace/bundles/`, run `/sync-plugin-cache`
(project-local, `.claude/skills/sync-plugin-cache/`), and the cache reflects the change. The
OpenCode inner loop has no equivalent: **no `sync-opencode` skill and no `sync_opencode.py` exist
anywhere in the tree**, so deploying the generated `target/opencode/` output means hand-copying
with a structural rename — the generator emits singular `skill/`/`agent/`/`command/` directories
while OpenCode discovers plural `skills/`/`agents/`/`commands/`. OpenCode cannot read the Claude
source format, so the loop is necessarily two-phase (generate, then deploy), and the deploy phase
is currently manual.

Separately, `doc/developer/distribution.adoc` misstates the distribution surface it documents: it
describes the publish matrix as a single Claude entry and OpenCode publication as hypothetical,
while `.github/workflows/claude-distribute.yml` carries a live `opencode` matrix entry publishing
the `dist-opencode` branch and `opencode`-prefixed dist tags.

## Goal

`/sync-opencode` deploys a generated `target/opencode/` tree into an OpenCode config directory
with the singular→plural rename in one command, removing stale entries it manages while never
touching user-managed ones, testable without a live OpenCode install; and the distribution
documentation states the publish matrix as it is.

## Deliverables

1. **D1 — The `sync-opencode` project-local skill** — `.claude/skills/sync-opencode/` with
   `scripts/sync_opencode.py`: sync of `target/opencode/skill/` → `{dest}/skills/`,
   `agent/` → `{dest}/agents/`, `command/` → `{dest}/commands/`. **Deletion is bounded to managed
   entries**: the destination is the shared `~/.config/opencode/` where user-managed skills also
   live, so the sync removes only stale entries the generated tree owns — those matching the
   generated `{bundle}-{skill}` namespace of the bundles being synced — and never touches entries
   outside that managed set; with `--bundles`, unselected bundles' entries are likewise preserved
   (the boundary model is the OpenCode emitter's own prune behaviour, which removes only generated
   component subtrees). Default destination `~/.config/opencode/`; flags `--source`,
   `--target-dir`, `--bundles`, `--dry-run`. Project-local for the same reason `sync-plugin-cache`
   is: only this repository generates OpenCode output, and a consumer project would be confused by
   the command.
   *Done when:* running it against a generated tree produces the plural layout at the
   destination with stale **managed** entries removed and unmanaged entries untouched; the skill
   is invocable as `/sync-opencode`; the SKILL.md mirrors the `sync-plugin-cache` shape
   (source-of-truth statement, parameters table) and states the deletion boundary.
2. **D2 — Unit tests** — under `test/sync-opencode/`, mirroring the `test/sync-plugin-cache/`
   precedent: the singular→plural path mapping, `--dry-run` (no filesystem effect, actions
   listed), `--bundles` subsetting, stale-managed-entry deletion, **preservation of unmanaged
   destination entries**, and **preservation of unselected bundles' entries under `--bundles`**,
   all against temp directories — no live OpenCode install involved.
   *Done when:* the tests pass in `./pw verify` and each behaviour above has at least one case.
3. **D3 — Inner-loop documentation** — `doc/developer/marketplace-build.adoc` gains the OpenCode
   inner loop: generate → `/sync-opencode` → test, and the deploy options with the precedence
   caveat spelled out — (a) sync into the global config dir for daily work; (b) point
   `OPENCODE_CONFIG_DIR` at a plural-renamed staging copy, noting that a committed project-local
   `.opencode/` shadows the env-var directory and that the env var cannot point at the singular
   `target/opencode/` directly; (c) a marketplace-install path exercises distribution, not rapid
   iteration, and is unverified until the validation protocol
   (`doc/plans/multiplattform/reference/opencode-validation-protocol.md`) runs.
   *Done when:* the section exists, cross-references rather than duplicates the generator
   documentation, and every claim in it is exercisable without a live OpenCode session or is
   explicitly marked validation-gated.
4. **D4 — `distribution.adoc` states the live matrix** — the document describes the actual
   two-entry publish matrix (`dist-claude`/`dist-opencode` branches, `claude`/`opencode` tag
   prefixes, unified source-tag versioning) and states plainly that the OpenCode consumption path
   against those refs is unverified on a live client.
   *Done when:* the document contains no claim that the matrix is Claude-only or that OpenCode
   publication is hypothetical, and its statements match `.github/workflows/claude-distribute.yml`
   read at run time.

## Out of scope

- **Running against a live OpenCode install** — this run has no OpenCode installation and no
  operator; D2's temp-directory tests are the verifiable substitute, and the live confirmation
  belongs to the validation protocol
  (`doc/plans/multiplattform/reference/opencode-validation-protocol.md`). Excluded so the plan
  cannot stall on an environment it cannot have.
- **Shipping `sync-opencode` in a marketplace bundle** — consumer projects never generate OpenCode
  output; shipping it would put a meta-project tool in every install. Revisit only if live
  validation surfaces a consumer-side need.
- **Pinning the OpenCode install path** — which consumption path works against `dist-opencode` is
  a live-client question; D4 states it as unverified rather than guessing.
- **CI changes** — the generation gate and distribution workflows already cover OpenCode; this
  plan adds a developer tool, not pipeline steps.

## Expected surface

- `.claude/skills/sync-opencode/SKILL.md`, `.claude/skills/sync-opencode/scripts/sync_opencode.py` — D1
- `test/sync-opencode/**` — D2
- `doc/developer/marketplace-build.adoc` — D3
- `doc/developer/distribution.adoc` — D4

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| No `sync-opencode` skill or `sync_opencode.py` exists anywhere in the tree | OBSERVED (asserted absence — the high-risk kind) | re-derive before building: search the whole tree; a hit refutes the premise and HALTS the plan for re-scoping |
| The generator emits singular `skill/`/`agent/`/`command/` directories | OBSERVED | `marketplace/targets/opencode/emitter.py` — the output-directory names |
| OpenCode discovers plural `skills/`/`agents/`/`commands/` directories | HYPOTHESIS (external-product fact — no clone artifact can settle it) | the validation protocol's live discovery check (`doc/plans/multiplattform/reference/opencode-validation-protocol.md` § 1.2); D1's `--target-dir` flag keeps the rename correctable if the layout assumption is refuted, and the run states the assumption in its report rather than as fact |
| `sync-plugin-cache` is the shape to mirror (project-local skill, sync engine, bundle filtering) | OBSERVED | `.claude/skills/sync-plugin-cache/SKILL.md` and `scripts/sync.py` |
| Project-local skill tests live under `test/{skill-name}/` | OBSERVED | `test/sync-plugin-cache/` exists |
| `claude-distribute.yml` carries an `opencode` matrix entry (`dist-opencode`, tag prefix `opencode`) | OBSERVED | `.github/workflows/claude-distribute.yml` — the `strategy.matrix` block; re-read at run time for D4 |
| `distribution.adoc` claims a single-entry Claude-only matrix and hypothetical OpenCode publication | OBSERVED | `doc/developer/distribution.adoc` — locate the matrix and install-command statements by content, not line |
| The generated `target/opencode/` tree is committed and present in the clone for manual testing | HYPOTHESIS | `ls target/opencode/` in the run's clone; absent ⇒ generate it locally as D2's fixture source instead |

## Verification

- `./pw verify` over the branch diff (Python changes — the build gate applies).
- D2's behaviour tests demonstrated red-first against the not-yet-implemented flags.
- A manual end-to-end run into a temp directory recorded in the run report: generate, sync,
  re-sync after deleting a source file, and confirm the stale managed entry is removed while a
  planted unmanaged entry survives.
- The pre-PR verification sub-agent re-reads D3/D4's documentation claims against the workflow
  and generator files they describe — documentation that restates another file's facts is the
  consumer-kind most likely to drift here.
- **Cold read (caveat check):** the sub-agent reads D3's deploy-options text cold and answers,
  without the plan in context: where does OpenCode look for skills when `OPENCODE_CONFIG_DIR` is
  set and a committed project-local `.opencode/` also exists, and can the env var point at
  `target/opencode/` directly? Any answer other than "the project-local directory shadows the env
  var" / "no — the layout is singular there" means the wording failed.

## Notes

- The deploy engine should mirror `sync-plugin-cache`'s source-of-truth stance: it consumes
  generated output (`target/opencode/`), never `marketplace/bundles/` directly.
- Namespacing is `{bundle}-{skill}` with no consecutive `--`; the rename maps directory *kind*
  (singular→plural), never component names.
- The validation protocol (`doc/plans/multiplattform/reference/opencode-validation-protocol.md`
  § 1.2) consumes this skill as its deploy step once it lands; until then it documents the manual
  fallback.
