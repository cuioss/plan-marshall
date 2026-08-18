# Gaps — 120-rename-marshall-orchestrator-to-plan-orchestrator

**Source:** verification.md (same directory)   **Open items:** 3

No behavioural defect was found. The landed change is provably a pure token rename: over the whole
landed diff excluding this plan's own documents, the removed and added line multisets are identical
under the four rename substitutions (242 removed, 242 added, 0 unmatched either way). Every one of
the plan's substantive acceptance conditions holds at HEAD — zero old-token occurrences outside
`doc/plans/`, all three directories moved with history, 72 orchestrator-bearing relative links
resolving, 613 tests green across the renamed and cross-referencing suites, and a mutation of the
bundle README turning the registration-drift guard RED. The three items below are cosmetic or
record-accuracy residue.

## G1 — Restore alphabetical position of the two renamed entries in `plugin.json`

- **Kind:** incomplete-sweep
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:45` — `"./skills/persona-plan-orchestrator"`; `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:73` — `"./skills/plan-orchestrator"`
- **What is wrong:** the rename kept both entries at their pre-rename array positions, so
  `persona-plan-orchestrator` now precedes `persona-module-tester` and `plan-orchestrator` precedes
  `marshall-steward`. Re-derived at HEAD: the `skills` array holds 76 entries with 6 out-of-order
  adjacent pairs, of which exactly these 2 were introduced by this plan (the other 4 —
  `ref-code-quality`/`persona-auditor`, `persona-security-expert`/`execute-task`,
  `manage-ci-artifacts`/`manage-change-ledger`, `platform-runtime`/`plan-doctor` — pre-date it).
- **Why it matters:** the array is grouped and broadly sorted, so a reader scanning for
  `plan-orchestrator` alphabetically looks past it. Nothing gates ordering, so it will not be caught
  automatically; it only gets fixed if someone does it deliberately.
- **Fix:** move `"./skills/persona-plan-orchestrator"` to sit between
  `"./skills/persona-plan-marshall-agent"` and `"./skills/persona-security-expert"`, and move
  `"./skills/plan-orchestrator"` to sit between `"./skills/plan-marshall-plugin"` and
  `"./skills/plan-retrospective"`, leaving `"./skills/marshall-steward"` directly after
  `"./skills/manage-terminal-title"`. Change no other entry — the 4 pre-existing inversions are out
  of scope for this fix.
- **Done when:** re-running the adjacent-pair check over `plugin.json`'s `skills` array yields 4
  out-of-order pairs, none of them involving `plan-orchestrator` or `persona-plan-orchestrator`, and
  `./pw quality-gate` stays clean.
- **Module/topic:** `plan-marshall` bundle registration (`.claude-plugin/plugin.json`)

## G2 — Correct the D0 surface count in `report-01.md`

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/report-01.md:20`
- **What is wrong:** the report states the D0 gate derived "**265 matching lines across 74 files**".
  Re-deriving with `git grep -n 'marshall-orchestrator' <sha> -- .` gives **264 lines across 73
  files**, identically at the merge parent `68a21cac` and at the two preceding mainline commits
  `4faacf1b` and `b59f3b93`. No hidden-path or untracked file explains the extra one (`.claude/**`
  is tracked and counted; `AGENTS.md` contains no "orchestrat" substring at all).
- **Why it matters:** D0 was the plan's gate, and its whole point was that the surface count is the
  thing not to take on trust. A gate figure that does not reproduce is exactly the class of claim this
  epic exists to eliminate — and this report is the record a future orchestrator would re-read. The
  derived scope figures elsewhere in the report (65 files / 270 occurrences, 47/16) all reproduce to
  the digit, so only this one line is wrong.
- **Fix:** in `report-01.md:20`, replace "**265 matching lines across 74 files**" with
  "**264 matching lines across 73 files**", and add the base commit the figure was derived at
  (`68a21cac`) so it is re-derivable.
- **Done when:** `git grep -n 'marshall-orchestrator' 68a21cac -- . | wc -l` and
  `git grep -l … | wc -l` return exactly the two numbers the sentence states.
- **Module/topic:** `doc/plans/truthful-signals/120-…` run report

## G3 — Correct the D6 rationale: `.plan/` is not wholly git-ignored

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/120-rename-marshall-orchestrator-to-plan-orchestrator/report-01.md:40` — D6 paragraph
- **What is wrong:** the report asserts "`.plan/` is git-ignored and absent". `.gitignore:45-47` is
  `.plan/*` followed by `!.plan/marshal.json` and `!.plan/project-architecture/`, and
  `git ls-files '.plan/*'` returns 13 tracked files, all present in a fresh clone. The conclusion the
  report draws from the premise still holds — `git grep -i 'marshall-orchestrator' -- .plan/` returns
  no match, and `.plan/marshal.json:182` carries only the `"orchestrator"` config-block key — but the
  premise is false.
- **Why it matters:** the same premise appears in `CLAUDE.md`'s Standalone Plan Lane section, and a
  future rename or sweep that trusts "`.plan/` is absent" will skip two tracked subtrees that a cloud
  clone does in fact carry — `marshal.json` (live project configuration) and
  `project-architecture/**` (12 enriched inventories). A rename touching a config key or a module
  name would be silently incomplete there.
- **Fix:** in `report-01.md:40`, replace the blanket "`.plan/` is git-ignored and absent" with the
  accurate form: the *ledger* subtree (`.plan/local/**`) is git-ignored and absent, while
  `.plan/marshal.json` and `.plan/project-architecture/` are tracked, were searched, and contain no
  occurrence of the renamed token.
- **Done when:** the D6 paragraph names which `.plan/` paths are tracked and states that they were
  searched, and `git ls-files '.plan/*'` agrees with the paths named.
- **Module/topic:** `doc/plans/truthful-signals/120-…` run report; adjacent wording in `CLAUDE.md`
  § Standalone Plan Lane
