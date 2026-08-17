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

# plan-marshall states runtime facts through the runtime, and single sources stay single

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper)
**Branch prefix:** chore — coupling residue across the plan-marshall bundle's prose and scripts

## Problem

The plan-marshall bundle carries Claude runtime facts, layout literals, and duplicated
single-source tables far beyond the inventory's registered sites: `manage-terminal-title`
contradicts its own "knows no hook-event vocabulary" contract with a resident Claude channel
specification; hook events, Bash-tool ceilings, the `<usage>` envelope, and `.claude` layout
appear as universal facts in general standards and scripts; the effort level→model table is
restated on five bundle surfaces against its build-target single source; `/marshall-steward` is
emitted as a remediation string from over a dozen general scripts (and persisted into
`.gitignore`); `CLAUDE.md` is a whole steward sub-operation's only write target; and three live
code sites construct Claude layout outside the layout helpers. The registry is
`doc/plans/multiplattform/reference/marketplace-audit.md` §M5–§M9.

## Goal

Runtime facts in the bundle are sourced from `platform-runtime` or stated as per-target notes;
the effort table, command forms, and agent-instructions filename each have exactly one source;
and no live code path outside the sanctioned homes constructs a Claude layout.

## Deliverables

1. **D1 — Layout code routed** — `configurable_contract.py::resolve_step_doc_path` through
   `get_project_skill_roots()`; the executor template's `_newest_cache_scripts_dir` recovery root
   through the runtime-resolved cache roots; `marketplace_paths.get_base_path` `global`/`project`
   scopes runtime-routed.
   *Done when:* the segment-wise/literal constructions are gone from the three sites, pinned by
   tests including a non-default-root case.
2. **D2 — `manage-terminal-title` split** — the channel-delivery/hook-event content
   (architecture standard sections, SKILL mapping table, script comments) moves to
   `platform-runtime` documentation; the composer skill keeps only the target-neutral contract
   its frontmatter claims.
   *Done when:* the skill's body no longer contradicts its self-description (no hook-event or
   channel vocabulary outside platform-runtime), and the displaced content is reachable from the
   runtime's docs.
3. **D3 — Hook/session/ceiling facts sourced** — the M5/M6 prose sites (manage-status build-busy
   contract, orchestration-model channel claim, manage-architecture search justification,
   session-id mechanism mentions, `_invariants.py`, worktree-handling rationale, Bash-ceiling and
   call-shape statements, `<usage>` mentions, phase-3 harness-config routing rule, q-gate
   validators, extension-api/manifest/config contract prose, coverage/wizard `.claude` prose,
   docstring target enumerations) state intent, cite the runtime op or single constant, or carry
   an explicit per-target conditional.
   *Done when:* a bundle sweep for hook-event names, `.claude` literals, and hard-coded ceiling
   values outside platform-runtime and declared Claude-target material is clean.
4. **D4 — Effort table single-sourced** — the five M7 surfaces reference the build-target source
   instead of restating it; `CLAUDE_CODE_SUBAGENT_MODEL` prose becomes a Claude-target note; the
   `LEVEL_TABLE`/`model_map` cross-target import direction is recorded as a proposal (the fix is
   `marketplace/targets` work outside this plan's surface).
   *Done when:* no bundle file carries the level→model rows; each cites the single source.
5. **D5 — Command form and agent-instructions file** — the `/marshall-steward` (and
   `/sync-plugin-cache`) emission sites consume one command-form lookup; `gitignore_setup.py`
   persists a neutral comment; `architecture-setup.md`'s write target and `determine_mode.py`'s
   rule-file lists resolve the agent-instructions filename per target (fixing the
   `['CLAUDE.md']`-only asymmetry); "CLAUDE.md § …" authority citations name the rule's owner;
   the steward `--settings` literals route through the permission skills' own semantic ops.
   *Done when:* the emission sites share one lookup; the asymmetry has a red-first test; the
   steward surfaces contain no settings-path literal.

## Out of scope

- **The steward terminal-title and enforcement-hook wizard splits** — §D/M6 target-specific
  candidates blocked on plan `020`'s mechanism; this plan fixes their `--settings` literals only.
- **Renaming the persisted `harness_cancellation` enum** — a data-migration cost for a
  terminology gain; recorded as a deliberate non-migration.
- **`trusted-domains` seed policy** — whether `code.claude.com` stays a full-trust default is an
  operator policy question; this plan records the proposal, never decides it.
- **pm-plugin-development and cross-bundle prose** — plans `060` and `050` own those surfaces.

## Expected surface

- `marketplace/bundles/plan-marshall/**` — the M5–M9-named skills, standards, and scripts
- `test/plan-marshall/**` for every touched script
- `marketplace/bundles/plan-marshall/skills/platform-runtime/**` docs only (D2's displaced
  content; any op-schema need is recorded, made minimally)

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `manage-terminal-title`'s body carries the hook-event mapping its own contract disclaims | OBSERVED | the SKILL.md and `standards/terminal-title-architecture.md` — re-read before D2 |
| Three live code sites construct Claude layout outside the helpers | OBSERVED, set is a lead | re-derive by segment-wise + literal probe over the bundle before D1 |
| The effort table is restated on five bundle surfaces | OBSERVED, set is a lead | re-derive by searching for the level rows |
| The `/marshall-steward` emission set spans the M8-listed scripts | OBSERVED, set is a lead | re-derive by literal search; the hit list is the work list |
| The M5–M9 prose sites are complete | HYPOTHESIS | the audit registry names the sweep patterns; extra hits are folded in and reported |

## Verification

- `./pw verify`; red-first tests for D1's routing and D5's rule-file asymmetry.
- The D3 sweep re-run at verification time over the changed tree.
- The pre-PR sub-agent **cold-reads** the reworded manage-status build-busy contract and reports
  whether an implementer on a hook-less target can tell what to do — the wording failed if not.

## Notes

- Shares plan-marshall bundle surfaces with `030` (permission scripts) and `010`
  (platform-runtime): run after both; concurrent with `040` only. Evidence:
  `reference/marketplace-audit.md` §M5–§M9.
