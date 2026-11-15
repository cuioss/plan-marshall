# Landing Analysis: PLAN-LB-150 — apply-changes-skill

epic: live-blockers
workstream: WS-04
pr: #1986

> Landing record for one shipped plan. Merged as `aaa06bf4479ae82ead97229cad24f22c06841b84` (parent `ec155e334`) through the merge queue; ten files, +1045 −2. Lane: runbook, OpenCode harness, `rb-lb-150-apply-changes-skill`. Source: the lane's inbox message `rb-lb-150-apply-changes-skill-001.md`, corroborated against the merge commit's diff, the PR's review state and the merged code. `complete: false` for `total_tokens` alone (`unknown`, no measurement), which is no defect under the operator's ruling of 2026-10-23.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Claude entry point and settings | shipped-as-specified | `.claude/skills/apply-changes/SKILL.md` carries seven `bash` fences in the specified order (`:40,44,48,64,82,99,112`), a bare engine call, no direct `./pw`, `cache_status: success` on steps 3-5, the main-checkout and meta-project-only statements (`:23-26`) and the post-run block (`:157-166`); `.claude/settings.json` gains exactly the two `Skill(apply-changes…)` entries (diff re-read). |
| D2 — OpenCode command and Antigravity skill | shipped-as-specified | `.opencode/commands/apply-changes.md` (no `name`) and `.agents/skills/apply-changes/SKILL.md` (`name: apply-changes`) carry the same seven commands and the same post-run block (the leaf read all three; the Claude and Antigravity heads and post-run block re-read here). |
| D3 — parity pin | shipped-modified | `test/apply-changes/test_apply_changes_command_parity.py` (18 tests) plus a shared reader `test/_shared/_harness_entry_point_scan.py`. Every pin that fires has a control, but not every pin has one (see layer 2), and the reader is a near-copy of the sibling module's private helpers, which the spec forbade. The red-with-the-violation-removed runs the Done-when asks for are not in the record. |
| D4 — operator documents | shipped, Done-when not evidenceable | `CLAUDE.md:139`, `AGENTS.md:77`, `doc/developer/marketplace-build.adoc:218` each name `/apply-changes` in one sentence and point at the skill; none repeats the step list. The Done-when is spec-owned (L1-1): it demands "fails at `270fb4e07`" of three documents with no test, and one half of it (none repeats the list) cannot fail at base. The lane graded it `not met as written` (`deliverables_done=3`), which is the accurate grade; the PR body's `met` overstates it. |
| Unplanned | added-unplanned | `marketplace/targets/README.md` (new-harness checklist, explained by the parity pin) and `test/_shared/_harness_entry_point_scan.py` (explained by D3). The lane named one of the two outside the declared surface. |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved through `orchestrator.analyze`), and the orchestrator re-read the points recorded below as re-read. By reading, no build, no test run, no write. The leaf had no Grep or Glob and used `git log -S`, `git ls-tree` and `git show`.

- **Dispatch:** one read-only leaf for this landing — reason: the rule dispatches every full ship; the leaf was briefed with a condensed spec (not the verbatim one) and graded the whole diff, not only the lane's claims.
- **Verdict:** layer 1 findings (3, all minor or info); layer 2 findings (5 minor); layer 3 findings (1 major not shown by reading, 5 minor). No blocker.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | D4's Done-when says every condition fails at `270fb4e07`; "none repeats the five-step list" already holds at base and the deliverable names no test | checked | refutes | spec D4; base has no `apply-changes` in any of the three documents |
| L1-2 | D3 says reuse the existing helpers, D1 says `test_harness_command_parity.py` passes unchanged; the only helpers were private to that module | checked | refutes | `test/sync-harnesses/test_harness_command_parity.py:95-115,254-261` |
| L1-3 | "`/reload-plugins` named nowhere else" is true only per entry point | checked | refutes | `.claude/skills/sync-harnesses/SKILL.md:228` names it |
| L1-4 | the gate premise: a `behind` registry gives `partial` while `cache_status` keeps the cache result | checked | confirms | `marketplace/targets/sync.py:1032-1038` |
| L1-5 | `--repin` is accepted by the engine, a bare call repins nothing | checked | confirms | `sync.py:867-868, 1190-1197` |
| L1-6 | `reconcile_daemon.py` never aborts the run | checked | confirms | `reconcile_daemon.py:493-521` |
| L1-7 | `registry_pin.py --apply` as its own step pins each bundle to its newest cache directory, not to the version this run synced | checked | confirms | `registry_pin.py:562-566`; the skill covers it by telling the operator to compare the `entries` rows (`SKILL.md:125-129`, re-read) |

The three lane-settled hypotheses that the spec carried as `HYPOTHESIS` were all settled by the lane against code and agree with the leaf's read. The spec of a shipped plan is not a staged spec, so no `corpus set-verdict` call is made.

**Layer 1 verdict:** findings — 3 (L1-1, L1-2, L1-3); L1-1 is this orchestrator's authoring defect (a Done-when with no test and a clause that cannot fail).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `.claude/skills/apply-changes/SKILL.md`, `.claude/settings.json` | module `:305-360` | none | checked |
| D2 | `.opencode/commands/apply-changes.md`, `.agents/skills/apply-changes/SKILL.md` | the mirror checks | none | checked |
| D3 | `test/apply-changes/…`, `test/_shared/_harness_entry_point_scan.py` | itself | two files outside the declared surface, both explained; "reuses shared code instead of a second copy" is refuted (the reader copies the sibling's helpers, the sibling stays) | checked |
| D4 | the three documents | none | the PR's `met` | checked |

Unborne claims of the lane's report: (a) "every pin has a matched control" is partly true: no control plants a bare `status: success` gate, the command-list divergence branch, the registry-last branch or the missing-description branch, and the restrictive-condition control plants step 3 only (`test_apply_changes_command_parity.py:436-452`, re-read: it strips the gate of steps 3, 4, 5 and plants `only when` on step 3 only); (b) the Done-when's red run per control is not in the narrative; (c) "one file outside the declared surface" undercounts by one; (d) the PR body grades D4 `met` while the landing grades it not met. The lane's `never ran the command` claim cannot be shown by reading either way.

**Layer 2 verdict:** findings — 5 minor (control gaps, undelivered red runs, the copied reader, the surface undercount, the D4 overstatement).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `.claude/skills/apply-changes/SKILL.md:1-7`; `.claude/settings.json` | the skill carries `user-invocable: true` and `allowed-tools: Bash` and no field that stops model invocation; `Skill(apply-changes)` is pre-allowed; the Antigravity description adds "Use when carrying a bundle change…" | if a harness invokes the skill on its own, `registry_pin.py --apply` runs without the operator's own invocation, which the skill and ADR-025 state as the consent; the sibling `sync-harnesses` has the same frontmatter but writes no registry | major, not shown by reading (the harness's invocation behaviour needs a run) |
| L3-2 | `SKILL.md:82/85, 99/102, 112/115` | the Claude skill states each gate after the fence it gates; the mirrors and `sync-harnesses` state it first | an agent reading top-down can run a gated command before the condition; `step_blocks` cannot detect position | minor |
| L3-3 | `SKILL.md:79-94, 131-135` | step 3's own failure; a refused repin write ending `unreadable` or `ahead` | no rule for a failed executor regeneration before step 4 uses the executor; step 5 reads only `registry_parity`, so a refused write is reported as "not errors" | minor |
| L3-4 | `marketplace/targets/README.md:200` | a new harness added to `SYNC_TARGETS` | "the same seven commands" is wrong for exactly the case the sentence describes (the test derives the generate calls, so it becomes eight) | minor (re-read) |
| L3-5 | `doc/developer/marketplace-build.adoc:218` | `xref:` to a `.md` target beside `link:` at `:216` | the rendered link is likely broken | minor, not shown by reading |
| L3-6 | `test/_shared/_harness_entry_point_scan.py:40-43`; test `_settings_allow` | malformed frontmatter or settings | a bare `ValueError`/`JSONDecodeError`; the test errors, never passes silently | info |

**Layer 3 not shown by reading:** L3-1 (harness auto-invocation), L3-5 (render), the daemon-before-registry ordering effect (step 4's "verified pin" may read the registry that only step 5 writes), whether `pytest` collects `test/apply-changes/` without an `__init__.py`, and the bare-interpreter `--help` sweep for the two scripts.

**Layer 3 verdict:** findings — 6 (1 major not shown by reading, 4 minor, 1 info). No defect fails closed in the wrong direction by reading.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| `CLAUDE.md` Documentation Standards | no duplication; current state only; no timestamps | conforms | the five hunks add one sentence and a pointer each |
| `CLAUDE.md` Commit Trailer | `Co-Authored-By: plan-marshall`, no footer on the PR | conforms | merge commit message |
| `CLAUDE.md` AsciiDoc | `xref:` for cross-references | not_shown_by_reading | `marketplace-build.adoc:218` |
| spec D1 | `settings.json` gains exactly two entries | conforms | diff |
| spec ADR-025 | registry write its own step, no `--repin` anywhere | conforms | `SKILL.md:64, 112` |
| spec D3 | reuse the helpers, do not copy | deviates | reader copies `test_harness_command_parity.py:45-115,254-261` |
| spec D3 | every pin has a matched control | deviates | see layer 2 |
| spec constraint | the lane never runs the command it creates | not_shown_by_reading | no artifact either way |

## Metrics and Anomalies

- Tokens: `unknown` (the harness measured none; recorded as an unobserved fact, not a zero).
- Duration: not supplied.
- Anomalies: one forced push of the lane's own branch (`--force-with-lease`, `2f07185f6 → 2969890c2`) to drop an out-of-surface `uv.lock` commit; the lane disclosed it as outside the Git rule. Also `git checkout-index -f` and `git clean -f` inside two throwaway base trees, and three guard refusals (R1 pipe-with-`head`, two R2 `rm`), each redone a sanctioned way. The lane asked the operator once about the dirty `uv.lock` of the main checkout and went on.

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed three times, 11 body findings; the lane reports 11 handled (6 fixed, 5 declined, one of the declines with the bot's withdrawal). Sourcery (optional) refused for its own review budget. Four trigger refusals before an escalated `full review` was accepted.
- Re-read against the provider on the merged head: `runbook_lane review-gate --pr-number 1986` returns `unresolved_review_threads: 0` and `review_body_findings_total: 11`, both equal to the landing's. `review_body_findings_handled` is **not re-verified**: the gate called without the run's dispositions reports 0 handled, which is the absence of its input and not a difference; the progress file was not read.
- CI/merge: green on every pushed head, merge queue, `aaa06bf44`.
- Sonar: `n/a` (the project has no Sonar).

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1986`
- [x] row `landing` stamped `landings/PLAN-LB-150.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-150-apply-changes-skill`
- [x] epic.md narrative reconciled (a Watch for the minors of PRs 1986 and 1987, a Decisions entry)
- [x] inbox message archived
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- The operator-run checklist for this change is the command it created: after `/sync-harnesses`-class changes, `/apply-changes` (this session lists it as a skill) carries them; it has never been run by the operator on this machine. L3-1 means its first real run should be the operator's own invocation, not the model's.
- L3-1 is below the confidence to decide (the harness behaviour is unobserved) and goes to the operator as a one-item question; it is not staged.
- Layer-3 minors are one Watch, "The minors of PRs 1986 and 1987", not a plan; no plan is staged without the operator's word.
- L1-1 is recorded as an authoring lesson: a Done-when of the form "fails at {sha}" needs a test that can fail, or it is evidenced by a base read and says so.
