# PLAN-PRQ-15: One AsciiDoc report per project, the three identity facts the outcome report does not carry, and a skill layout with one front door

epic: post-run-quality
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for hand-off.
> This spec is SELF-SUFFICIENT: the hand-off is a one-line pointer and carries no brief.

> ⚠ **ALL OF THIS PLAN'S WORK IS IN `cuioss/plan-marshall-telemetry`**, checked out at
> `/home/oliver/git/plan-marshall-telemetry`. ⛔ **It runs as a standalone Claude Code session in that
> repository, NOT as a `/plan-marshall` task** — same lane as `PLAN-PRQ-13`, for the same reasons, and
> § What replaces the lifecycle below is the contract.

## Provenance

Operator-directed, 2026-10-04, immediately after `PLAN-PRQ-13` landed (`5546bde`). Two halves: a
**project-level AsciiDoc aggregate** generated automatically after every `analyze` and committed with the
reports, and **three identity facts** the per-plan outcome report does not carry.

## Objective

**`PLAN-PRQ-13` built per-subject JSON reports, which are the right substrate and the wrong artefact for a
human.** A reader who wants to know how a project has been going must currently open one JSON file per
archived plan and hold the aggregate in their head. And the reports answer *how long, how much, how many
lines* without answering three questions a reader asks first: **did it actually finish, which repository
was it, and where are the PRs.**

## What already exists — do not rebuild it

`OBSERVED 2026-10-04`, read from `doc/outcome-report.md` and the report scripts at `5546bde`:

| Present | Shape |
|---|---|
| `wall_seconds`, `worked_seconds` | never substituted for one another |
| `total_tokens`, `tokens_by_phase` | with `floor: true` when summed over an empty population |
| `prs` | a LIST, each entry carrying the PR number, its `sources` (four unioned archived sources), and `landed: yes\|unknown` |
| `lines_added`, `lines_modified`, `lines_removed` | from every PR's merge commit, `not_measured` without `--source-repo` |
| `project_kind` | a SET over a nine-value vocabulary |
| `deliverables_total`, `deliverables_done` | from `solution_outline.md` headings and `tasks/TASK-*.json` states |
| the field envelope | ⛔ **every field already carries `state` / `value` / `provenance` / `basis` / `reason`** |
| `plan_rollup` (orchestrator report) | per-figure sums with `population` and `complete`, where `complete: false` makes the sum a floor |

## Deliverables

Seven deliverables. D0 is a gate. ⚠ **Two independent tracks**: D1–D3 add fields, D4–D5 add the aggregate
and its controls, and **D6 is a self-contained skill-layout cleanup that touches neither**. D6 may land
first, last or between — but its three parts are internally ordered, and (c) goes last of them.

**D0 — GATE: confirm the three gaps and settle the naming collision.** Read `doc/outcome-report.md`, the
`report_*.py` extractors and `subject_reports.py`, and publish which of the three requested facts is
absent, partially present, or derivable from what is already there. The expected answer, to be confirmed
or refuted rather than assumed:

- **Completion state — ABSENT.** `deliverables_total` / `deliverables_done` exist, so *partial* is
  derivable, but ⛔ **`aborted` is NOT**: a plan with `deliverables_done: 0` may have been abandoned, never
  started, or simply unmeasurable, and those are three different facts.
- **Repository URL — ABSENT.** Nothing in the report identifies the source repository at all.
- **PR links — PARTIAL.** `prs` carries numbers, not URLs. ⚠ **A URL cannot be built without the repository
  identity, so the repo-URL deliverable is a hard prerequisite for the links** — D0 confirms that ordering.

⛔⛔ **The naming collision, and D0 must settle it before any field is written.** The operator's word for
the first fact is `state` — but **`state` is already the envelope key on every field**, meaning
`measured` / `not_measured` / `not_applicable`. A top-level `state` would be two different things one key
deep from each other, and every reader would have to know which. **Pick a non-colliding name**
(`completion` / `implementation_state`) and record the choice; do NOT shadow the envelope key.

**D1 — The repository identity, with its URL.** Add the source repository to the plan outcome report —
enough to build a PR URL and to tell a reader which codebase a plan touched. ⚠ **Derive it, do not
configure it**: `--source-repo`'s git remote is the obvious source, and the archived plan's own records may
carry it. ⛔ **Without `--source-repo` and with no archived evidence, this is `not_measured`** — never a
guess from the project slug, which is a directory name and not a repository identity.

**D2 — PR links on every `prs` entry.** Each entry gains its URL, built from D1's repository identity. ⛔
**An entry whose repository is `not_measured` carries no URL and says so** — a link assembled from a
guessed host is worse than no link, because it looks authoritative and 404s. Keep the existing `number`,
`sources` and `landed` fields unchanged; this is additive.

**D3 — The completion state, over a closed vocabulary, derived with its inputs published.** The vocabulary
is the operator's three plus the honest fourth that the other three cannot express:

| Value | Meaning |
|---|---|
| `fully_implemented` | every deliverable done |
| `partially_implemented` | at least one done, at least one not |
| `aborted` | the plan stopped without delivering, and **evidence says so** |
| `indeterminate` | the records cannot distinguish the above — reported as the envelope's `not_measured` |

⛔ **`aborted` needs POSITIVE evidence and may never be inferred from a zero.** D0/outline establishes what
that evidence is in the archive — a terminal status, an abandonment record, an unfinished phase with no
later activity — and if no such evidence exists in the records, then **`aborted` is not derivable and the
vocabulary ships with three reachable values and one documented as unreachable**, stated plainly rather
than quietly never emitted. ⭐ Publish the inputs the state was derived from, as `severity` already does,
so a reader can re-derive it.

**D4 — The project-level AsciiDoc aggregate, generated automatically.** One human-readable report per
project at `reports/{project-slug}/` — *one level up* from the per-subject JSON — aggregating every plan and
every orchestrator epic of that project.

- ⛔ **It is generated by the ENGINE, not by `analyze`.** `analyze/SKILL.md` declares it has no computation
  and no report format of its own, and names `audit.py` the only analysis path and only report schema in
  the repository. An aggregator living in `analyze` would be the second formatter that skill forbids —
  the same trap `PLAN-PRQ-13` D1 had to be corrected for.
- **Automatic, and committed with the reports.** It regenerates on every `analyze` run, before the commit,
  so the committed aggregate always matches the committed JSON. A stale aggregate beside fresh reports is
  the failure this deliverable exists to prevent.
- **It is a VIEW, never a second source of truth.** Every figure comes from the JSON reports; the
  aggregator computes no fact of its own. A figure that disagrees with its report file is a defect in the
  aggregator by definition.
- ⛔⛔ **It MUST carry the measurement states through, and this is the whole risk of the deliverable.**
  Summing a `not_measured` as zero would reintroduce, at the aggregate level, precisely the defect this
  epic exists to eliminate — and an aggregate is where it would do the most damage, because it is the
  artefact a human actually reads. ⭐ **Reuse `plan_rollup`'s established pattern rather than inventing
  one**: every aggregate figure carries its `population` and a `complete` flag, and an incomplete sum is
  rendered **as a floor, visibly** (e.g. "≥ 41.2M tokens over 12 of 19 plans"). A bare total is only
  emitted when the population was complete.
- **AsciiDoc**, per the operator. ⚠ The repo's existing docs are Markdown and the plan-marshall AsciiDoc
  standards skill is not available in that repository, so the plan carries what it needs: blank line before
  every list, and no reliance on plan-marshall tooling to render it.
- Content: per-project totals and the per-plan table, the quality axes rolled up (mechanism × resolution,
  severity bands, scope stability), the orchestrator epics, and — ⛔ **a named section for what could not be
  measured and why**, because an aggregate that silently omits its gaps is the least honest artefact in the
  repository.

**D6 — The skill layout: one front door, no peer reaching into a peer, and a name that matches the job.**
Three structural corrections to the four project skills, operator-directed. ⚠ **They are independent of
D1–D5 and of each other — land them in the order below, each with its own green `pytest`**, so a
regression is attributable.

**(a) The engine stops being a second front door.** `OBSERVED`: both `analyze` and
`audit-archived-plan-retrospectives` declare `user-invocable: true`, so there are two user-facing entry
points to one computation — and `analyze`'s whole value is behavioural discipline it holds and the engine
does not (run exactly once, add no unrequested flags, surface verbatim, read `corpus-selection` /
`run-summary` / `subject-reports` first). ⛔ **That discipline is currently bypassable by design.** Drop
`user-invocable` from the engine so `analyze` is the single front door. ⚠ **This must not break the
invocation that matters**: `analyze` invokes the engine by *script path*, not as a skill, so it is
unaffected — confirm that before and after rather than assuming it.

**(b) `era-stamp-fill` folds into the engine as a maintenance verb.** `OBSERVED`: it is a sibling skill
that rewrites **another skill's source** — `audit.py` and `test/audit-archived-plan-retrospectives/test_audit_check_era_model.py`
— in lock-step. That is a layering inversion: a peer editing a peer's internals. ⭐ **The coupling is
already mutual**, which is the argument for folding rather than a matter of taste: the engine's own
SKILL.md and `audit.py` both reference the era-stamp mechanism. Move it inside the engine (a verb on
`audit.py`, or a script under the engine's own `scripts/`), where rewriting `audit.py` is a skill touching
its own code. ⛔ **Keep the behaviour and the test**: `test/era-stamp-fill/test_era_stamp_fill.py` must
still pass, relocated with it. Retire the standalone skill only once the verb works.

**(c) Rename the engine to match its role — SKILL DIRECTORY AND TEST DIRECTORY TOGETHER.** `OBSERVED`: the
name was inherited from plan-marshall, where it audited archived plan retrospectives. Here it writes
outcome and quality reports, which are not retrospective audits — and its own description already opens
*"The telemetry repository's single analysis engine"*, so **the description has outgrown the name**.

⛔⛔ **The test tree MIRRORS the skill tree one-to-one, and that mirror is the invariant — not a
coincidence to be broken by a half-done rename.** `OBSERVED`: `.claude/skills/` holds `analyze`,
`audit-archived-plan-retrospectives`, `era-stamp-fill`, `transfer`, and `test/` holds a directory of the
same name for each of the three that have tests. So the rename is **two** directories, and both parts of
D6 move a test directory:

| Change | Skill directory | Test directory |
|---|---|---|
| D6(b) fold | `.claude/skills/era-stamp-fill/` → retired | `test/era-stamp-fill/` → folds into the engine's test directory |
| D6(c) rename | `.claude/skills/audit-archived-plan-retrospectives/` → the new name | `test/audit-archived-plan-retrospectives/` → **the same new name** |

⛔ **A rename that moves the skill and leaves `test/audit-archived-plan-retrospectives/` behind is worse
than not renaming at all**: the tree then asserts a mirror it does not have, and the next reader cannot
tell which name is current. Use `git mv` for both so the moves are reviewable as moves rather than as
delete-plus-add.

⚠ **Measured blast radius, not estimated: 46 occurrences across 15 files** (excluding `__pycache__`), plus
the two directories. `pyproject.toml` does **not** reference the name (checked), so the test
configuration needs no change — but ⚠ it does set `pythonpath = [".", "test"]` and `testpaths = ["test"]`,
so confirm collection still finds the renamed directory before committing. D0 settles the new name;
`analysis-engine` is the obvious candidate given `analyze` is the wrapper.

⛔ **Do this LAST of the three and in ONE commit** — skill directory, test directory and all 46 references
together — so the rename is a single reviewable move rather than interleaved with behaviour changes, and so
reverting it costs nothing if the name turns out wrong.

⚠ **Report files already written under `reports/` may embed the old name in `basis` or `provenance`
strings** — check, and if so, state plainly that existing report files keep the old name rather than
rewriting committed output.

**D5 — Controls.** The aggregate is a view, so the controls are mostly agreement controls: every figure in
the aggregate equals its source JSON field; an incomplete population renders as a floor and never as a bare
total; a `not_measured` field appears in the could-not-measure section and is **not** summed; a
`not_measured` repository yields no PR URL; `aborted` is never emitted from a zero without positive
evidence; and the completion vocabulary's documented value set equals the constant the code validates
against, in both directions — the doc-vs-code control `PLAN-PRQ-13` D7 established.

**D6 owes two controls of its own**: one asserting the engine is reachable by `analyze` after (a) — the
single-front-door change must not become a no-front-door change — and the relocated
`test_era_stamp_fill.py` passing after (b). ⚠ The rename in (c) needs no new control: the existing 873
tests are the control, and any that still name the old path are the ones that prove the move was complete.

## Claim Labels

- OBSERVED (2026-10-04, `doc/outcome-report.md` at `5546bde`): the plan outcome report carries `wall_seconds`, `worked_seconds`, `total_tokens`, `tokens_by_phase`, `prs`, `lines_added/modified/removed`, `project_kind`, `deliverables_total`, `deliverables_done` — and no completion state, no repository identity and no PR URLs.
- OBSERVED: `prs` entries carry the PR number, a `sources` list over four unioned archived sources, and `landed: yes|unknown`; `no` is never derived because the archive never records a closed-unmerged PR.
- ⛔ OBSERVED: `state` is already the envelope key on EVERY field, with values `measured` / `not_measured` / `not_applicable` — so the operator's `state` must be renamed to avoid shadowing it.
- OBSERVED: `analyze/SKILL.md` declares no computation and no report format of its own, naming `audit.py` the only analysis path and only report schema — which is why D4 lands in the engine.
- OBSERVED: `plan_rollup` already establishes the population-plus-`complete` floor pattern D4 reuses.
- ⚠ HYPOTHESIS: the archive carries positive evidence distinguishing an ABORTED plan from one that never started or cannot be measured — confirm/refute against the archived corpus at outline (D0/D3 own it). If refuted, `aborted` ships documented-but-unreachable rather than silently never emitted.
- ⚠ HYPOTHESIS: the source repository's identity is derivable from `--source-repo`'s git remote or from the archived plan's own records — confirm/refute at outline (D1). If both fail, D1 is `not_measured` by construction and D2 emits no URLs.
- OBSERVED (2026-10-04): `analyze` and `audit-archived-plan-retrospectives` BOTH declare `user-invocable: true`, so the engine is a second front door and `analyze`'s surfacing discipline is bypassable — read from both skills' frontmatter.
- OBSERVED: `era-stamp-fill` rewrites `audit.py` and `test/audit-archived-plan-retrospectives/test_audit_check_era_model.py` — another skill's source and test — and the engine's own SKILL.md and `audit.py` reference the era-stamp mechanism in return, so the coupling is mutual.
- OBSERVED: `audit-archived-plan-retrospectives` appears **46 times across 15 files** (excluding `__pycache__`), plus its skill directory and `test/audit-archived-plan-retrospectives/`. `pyproject.toml` does NOT reference it, so the test configuration needs no change — measured by grep, not estimated.
- ⚠ HYPOTHESIS: committed report files under `reports/` may embed the engine's old name in `basis` or `provenance` strings, which D6(c) would otherwise silently orphan — confirm at outline. Since no project has been transferred, the likely answer is that no report files exist yet and the question is moot; check rather than assume.
- ⚠ HYPOTHESIS: no project has been transferred yet, so the aggregate has no real corpus to run against — the same gap `PLAN-PRQ-13` landed with. Confirm at D0; if still true, D5's controls and a fixture corpus are the only evidence available, and the plan says so rather than claiming a verified aggregate.

## Expected Surface

⛔ **Entirely outside the `plan-marshall` repository. Keep the `plan-marshall-telemetry/` prefix on every
entry** — a bare `test/` or `README.md` resolves against the wrong repository, and the parser reads this
section mechanically.

- OBSERVED: `plan-marshall-telemetry/.claude/skills/audit-archived-plan-retrospectives/` — the engine; its frontmatter at D6(a), the folded era-stamp verb at D6(b), and the whole directory RENAMED at D6(c): D0, D1, D2, D3, D4, D6
- OBSERVED: `plan-marshall-telemetry/.claude/skills/analyze/` — the engine invocation path, which D6(c)'s rename moves: D6
- OBSERVED: `plan-marshall-telemetry/.claude/skills/era-stamp-fill/` — RETIRED by D6(b) once the folded verb works: D6
- OBSERVED: `plan-marshall-telemetry/reports/` — where the aggregate lands, beside the per-subject JSON: D4
- OBSERVED: `plan-marshall-telemetry/doc/outcome-report.md` — the three new fields and the completion vocabulary: D1, D2, D3
- OBSERVED: `plan-marshall-telemetry/doc/` — the aggregate's own document, if D4 warrants one: D4
- OBSERVED: `plan-marshall-telemetry/test/audit-archived-plan-retrospectives/` — D5's controls, and RENAMED in lock-step with the skill directory at D6(c): D5, D6
- OBSERVED: `plan-marshall-telemetry/test/era-stamp-fill/` — folded into the engine's test directory at D6(b): D6
- OBSERVED: `plan-marshall-telemetry/test/` — the test root, whose per-skill directories mirror `.claude/skills/` one-to-one; that mirror is preserved, not broken: D5, D6
- OBSERVED: `plan-marshall-telemetry/README.md` — the Layout section (the aggregate, D4) and the Skills table (D6's three changes all alter it): D4, D6

## Dependencies and Sequencing

- **Depends on: `PLAN-PRQ-13` — SATISFIED** (`5546bde`). This plan extends its reports and its engine.
- **Internal ordering is binding: D1 → D2.** A PR URL cannot be built without the repository identity.
- **Does NOT depend on `PLAN-PRQ-14`.** That plan fixes the plan-marshall producers so future findings
  carry a mechanism marker and an upstream severity. This plan reads whatever the reports already hold; its
  aggregate will show more once PRQ-14 lands, and nothing here waits for it.
- **Collides with nothing in `plan-marshall`** — no in-repo surface, by construction.

## Hand-Off: a standalone session in the telemetry repo

```text
cd /home/oliver/git/plan-marshall-telemetry
```

```text
Implement the plan at
/home/oliver/git/plan-marshall/.plan/local/worktrees/_orchestrator/.plan/orchestrator/post-run-quality/plans/PLAN-PRQ-15-project-level-adoc-aggregate-and-outcome-identity-fields.md
Work only in this repository. Read § "What replaces the lifecycle" first.
```

⚠ That path is the **ledger worktree** on the unmerged `chore/orchestrator-ledger` branch; the
main-checkout path resolves once that branch lands. If neither resolves, re-resolve rather than guess:
`python3 /home/oliver/git/plan-marshall/.plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resolve-path --slug post-run-quality`
and read `epic_dir`. ⛔ The session does not edit the ledger copy.

## What replaces the lifecycle

Same lane as `PLAN-PRQ-13`, same substitutes:

| What the lifecycle would give | What replaces it |
|---|---|
| Phased execution, verification sweep | the deliverable order here, D0 first as a hard gate |
| `pre-push-quality-gate` | `python3 -m pytest` from the repo root, **green before every commit** (873 passed / 20 skipped at `5546bde` — do not regress it) |
| `pre-submission-self-review` | one deliberate self-review pass before the final commit, against D5's controls; record what it found |
| `create-pr`, `ci-verify`, `automatic-review` | nothing, by that repo's design — `main` only, no PRs, no CI, no review bots. Commit directly and push |
| `plan-retrospective`, `record-metrics`, `emit-landing` | nothing automated |
| `archive-plan` | not applicable |

⚠ **Same irony, same obligation**: this plan builds the human-readable quality report and will produce no
measured outcome of its own. **Write a run report under `doc/runs/`** — what shipped, every D0 verdict, the
self-review findings, the pytest result — and paste it to the orchestrator, which is the only way this
epic gets a landing record.

## Write-Boundary

⛔ The session writes ONLY inside `/home/oliver/git/plan-marshall-telemetry`. It does not edit the
`plan-marshall` repository, and not this ledger. ⚠ `{project-slug}/` is **archive data, read-only to
analysis** per the README invariant — the aggregate is written under `reports/{project-slug}/`, never into
the archive. The orchestrator owns every ledger write; see
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
