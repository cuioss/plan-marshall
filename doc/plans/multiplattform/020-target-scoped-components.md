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

# Components can declare the targets they ship to

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
[`README.md`](README.md), evidence in [`reference/`](reference/))
**Branch prefix:** feature — a new build-pipeline capability

## Problem

The placement model ([principles §6](reference/principles.md)) names a fourth home for
capabilities that exist only on some targets: a `targets:` frontmatter filter that makes the
component simply *absent* on non-matching targets, instead of shipping everywhere or forcing a
runtime no-op onto targets where the capability has no analog. **No such mechanism exists.**
Neither emitter consults any per-component target allowlist: the OpenCode emitter's
`_emit_agent`/`_emit_command` paths and the Claude verbatim path emit every component
unconditionally, so Claude-only capabilities — the IDE-MCP command
`plan-marshall/commands/tools-fix-intellij-diagnostics.md` is the confirmed first consumer — ship
into every target's output tree.

The mechanism is not a data-only change on the canonical side: the Claude target is a
byte-for-byte verbatim mirror gated by `run_equality_check`
(`marketplace/targets/claude/equality_check.py`), so a filter that *excludes* a source file from
a target's output must be reconciled with the equality invariant on the Claude side, and with the
bundle-verbatim emission path both non-Claude bundle-tree targets share.

## Goal

A component author writes `targets: [claude]` (or any registry-valid subset) in frontmatter and
the build ships the component only to those targets, fails closed on an unknown target name, and
keeps the Claude equality gate meaningful; an absent `targets:` field continues to mean "all
targets", so the normal case is untouched.

## Deliverables

1. **D1 — The filter mechanism** — frontmatter parsing plus an emission filter honoured by every
   registered target's pipeline: absent `targets:` ⇒ emit everywhere (the default, no behaviour
   change); present ⇒ emit only when the generating target's registry name is listed. The Claude
   equality check treats a component excluded by its own `targets:` declaration as deliberately
   absent, not as drift.
   *Done when:* a fixture component with `targets: [claude]` appears in the Claude output and in
   no other registered target's output; one with no `targets:` appears in all; `run_equality_check`
   passes on a tree containing a `targets:`-excluded component; all existing generation tests pass.
2. **D2 — Fail-closed validation** — a `targets:` value naming a target absent from
   `TARGET_REGISTRY` fails the build with an error naming the component and the unknown value; an
   empty list fails the same way (a component shipped nowhere is authoring error, not intent).
   *Done when:* tests prove generation fails on `targets: [typo]` and on `targets: []`, and the
   error message names the offending file.
3. **D3 — First consumer** — `tools-fix-intellij-diagnostics` declares `targets: [claude]`.
   *Done when:* the command is present in the Claude output tree and absent from every other
   registered target's output, asserted by test or by generation-output listing in the run report.
4. **D4 — Authoring surface** — `plugin-doctor`'s frontmatter validation accepts `targets:` with
   registry-valid values and flags unknown ones, and the field is documented in the
   `pm-plugin-development` frontmatter standards where component authors look.
   *Done when:* the doctor passes on D3's declaration, a doctor test covers an invalid value, and
   the standards document states the field's semantics (absent ⇒ all targets) and its admission
   test per [principles §6](reference/principles.md).

## Out of scope

- **The `marshall-steward` terminal-title wizard split** — the other confirmed Claude-only
  capability is spread across several steward surfaces and needs a skill split before it can be
  scoped; bundling a multi-surface split into the mechanism plan would double its size and risk.
  It stays in the [coupling inventory](reference/coupling-inventory.md) §D until the mechanism has
  proven itself on the simple consumer.
- **Scoping reference files** (`hook-authoring-guide.md`, `permission-prompt-analysis.md`) —
  references are files inside a skill, not components with their own frontmatter, so they need a
  file-level mechanism this plan does not build; excluded so D1 stays a frontmatter-level
  mechanism with one clear semantics.
- **Non-Claude-scoped consumers** (`targets: [opencode]` components) — no candidate exists; the
  mechanism supports it by construction, and inventing a consumer to prove it would be
  speculative work.
- **Doctor rule-pack restructuring** — D4 extends frontmatter validation; the engine/rule-pack
  split documented in `plugin-doctor/references/rule-provenance.md` is a separate concern.

## Expected surface

- `marketplace/targets/` — the shared emission path that all bundle-tree targets use for
  component emission, the Claude target + `equality_check.py`, and whichever per-target emitters
  consult the filter (locate by following `generate()` from each registered target)
- `marketplace/bundles/plan-marshall/commands/tools-fix-intellij-diagnostics.md` — D3
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — D4 validation
- `marketplace/bundles/pm-plugin-development/**` frontmatter standards document — D4 docs (locate
  the standards file that owns frontmatter fields before editing)
- `test/marketplace/targets/**`, `test/pm-plugin-development/plugin-doctor/**` — tests

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| No `targets:` frontmatter filter exists anywhere under `marketplace/targets/` | OBSERVED (asserted absence — the high-risk kind) | re-derive before building: search `marketplace/targets/` for `targets` frontmatter handling; a hit refutes the premise and HALTS the plan for re-scoping |
| The Claude target is a verbatim mirror gated by `run_equality_check`, with no `mapping.json` | OBSERVED | `marketplace/targets/claude/equality_check.py` — `run_equality_check`; `claude/target.py` |
| `TARGET_REGISTRY` holds `claude`, `opencode`, `pr-agent` | OBSERVED, membership is a lead | re-derive from `marketplace/targets/__init__.py`; D1/D2 iterate the registry, never an enumeration |
| `tools-fix-intellij-diagnostics.md` has YAML frontmatter (`name`, `description`, `tools` incl. `mcp__ide__getDiagnostics`) | OBSERVED | the file itself |
| `pr-agent`'s emission path also needs the filter | HYPOTHESIS | `marketplace/targets/pr_agent/` — read its `generate()`; if it does not emit per-component bundle trees, the filter may be inert there, which D1 records rather than forces |
| `plugin-doctor` frontmatter validation would flag an unknown `targets:` key today | HYPOTHESIS | the doctor's frontmatter analyzers — run the doctor against D3's declaration before D4 and record the result |

## Verification

- `./pw verify` over the branch diff (Python changes — the build gate applies).
- D1's fixture matrix and D2's failure tests demonstrated red-first where they pin new behaviour.
- Full generation for every registered target (`generate.py --target all`) exits 0 on the tree
  containing D3's declaration.
- **Cold read (semantics check):** the pre-PR verification sub-agent reads the D4 standards text
  cold and answers, without seeing the implementation: what does an absent `targets:` field mean,
  and what happens on an unknown value? Any answer other than "all targets" / "the build fails"
  means the wording failed.

## Notes

- The Claude-side reconciliation is the plan's real design work: `run_equality_check` compares
  source and output byte-for-byte, so exclusion must be visible to it as intent (e.g. the check
  derives the expected file set from the same filter) rather than special-cased per file.
- The `pr-agent` target proves the registry already has a third member; D1 must iterate the
  registry rather than hardcoding the two bundle-tree targets, or the next registration silently
  bypasses the filter.
- Plans `010`, `030`, `040` touch none of `marketplace/targets/**`; this plan touches no
  `platform-runtime` script — see the epic README's concurrency table.
