# Gaps — 110-landed-residue-promotion-sweep

**Source:** verification.md (same directory)   **Open items:** 4

## G1 — State the ledger stamp predicate as the three-way conjunction source implements

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md:74-82` — § Entry Shapes, the `kind=build` bullet
- **What is wrong:** The bullet says "Build-class-ness is a **conjunction**: the notation must sit under a `build-*` skill AND the dispatched subcommand must be the build-executing verb (`run`)", and names only "a bare `--help` dispatch that carries no subcommand at all" as suppressed. Source has had a **third** conjunct since `415dcf13` (#1127, 2026-08-09): `execute-script.py.template:1609` reads `if _is_build_class_notation(notation, subcommand) and not _mentions_help(script_args):`, so `run --help` — which satisfies both stated conditions — stamps **no** row. Removing that conjunct turns 6 tests in `test_build_class_stamp_discriminator.py` red, so the behaviour is pinned; only the doc is behind. The promoted section this plan landed states the conjunction correctly as three-way (`extension-api/standards/build-systems-common.md:110-124`) and cross-links this exact section for the ledger contract, so the two documents now disagree.
- **Why it matters:** A reader following the promotion's cross-link lands on a weaker rule and can conclude that a `run --help` probe stamps a freshness-satisfying row — the precise false-fresh hole the third conjunct closed. It also falsifies the run's recorded "beyond-diff staleness sweep found no false statement in any untouched build/ledger doc".
- **Fix:** In the `kind=build` bullet, state the conjunction as three conditions — a `build-*` notation, the build-executing `run` verb, and no help spelling anywhere in argv (`--help`, `--help=…`, `-h`, `-h` inside a short-flag cluster) — and extend the suppression list from "a bare `--help` dispatch" to include `run --help`. Cite `_mentions_help` beside `_is_build_class_notation` as the boundary that applies it.
- **Done when:** `manage-change-ledger/SKILL.md` § Entry Shapes names all three conjuncts and lists `run --help` among the dispatches that write no row, and no wording there contradicts `build-systems-common.md:110-124`.
- **Module/topic:** `plan-marshall:manage-change-ledger` (ledger contract docs) / build-ledger stamp discriminator.

## G2 — Give residues (a) and (c) a path from the surface that actually runs builds

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:69-90` and `:186-196` — the (a) and (c) subsections; the missing pointer belongs in `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md:73-78` — § Bash timeout for build/verify commands
- **What is wrong:** Residues (a) ("don't poll a backgrounded build's output") and (c) ("don't self-background a long build; run it in the foreground at 600000 ms") are addressed to the agent invoking a build, but they were filed in `extension-api`, whose SKILL.md declares it a `mode: knowledge` reference to "load on-demand when creating or modifying extensions". `grep -rn build-systems-common` over `marketplace/` and `.claude/` returns readers only in `extension-api/**` and the four `build-*/standards/*-impl.md` files; no agent-facing surface (`persona-plan-marshall-agent`, `phase-5-execute`, `execute-task`, `.claude/skills/cloud-plan-lane`, `CLAUDE.md`) references it.
- **Why it matters:** The audience that would background a long build and then poll an empty file never loads the document containing the rule that forbids it — the rule was filed, not promoted, by the plan's own Verification criterion.
- **Fix:** Add one cross-reference from `persona-plan-marshall-agent/SKILL.md` § Bash timeout (immediately after the 600000 ms floor sentence at :78) to `extension-api/standards/build-systems-common.md` § "Background build execution — reading a long build's completion signal", naming what the reader gets there (the output file carries no liveness information; use the `kind=build` ledger row). Keep the rule text in one place — a pointer, not a copy.
- **Done when:** `grep -rn "build-systems-common" marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` returns a hit reaching the background-execution section, and an agent following the build-invocation guidance can arrive at residues (a) and (c) without loading the extension-author skill.
- **Module/topic:** `plan-marshall:persona-plan-marshall-agent` + `plan-marshall:extension-api` (build guidance reachability).

## G3 — Reconcile the two opposed framings of harness auto-backgrounding

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:186-196` vs `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md:75`
- **What is wrong:** The promoted (c) presents harness auto-backgrounding as the thing that "preserved the job every time" and instructs the reader to "let the harness auto-background the job at its own ceiling". `persona-plan-marshall-agent/SKILL.md:75` presents the same event as a loss: "the host platform will silently auto-move the call to background and the dispatch will lose the synchronous-return path". Both are true of different aspects (the job survives; the caller's synchronous return does not), but neither document says so.
- **Why it matters:** A reader who meets both takes away contradictory postures on whether auto-backgrounding is an acceptable outcome, which is exactly the ambiguity the (a) subsection was already amended once (F2) to remove.
- **Fix:** In `build-systems-common.md:186-196`, add one clause stating that auto-backgrounding preserves the *job* but forfeits the caller's synchronous return, so the explicit 600000 ms bound is set to make auto-backgrounding the rare case rather than the plan — and cross-link `persona-plan-marshall-agent` § Bash timeout for the caller-side consequence.
- **Done when:** The two documents state the same thing about auto-backgrounding, with the job-survival and synchronous-return halves named apart in at least one of them.
- **Module/topic:** `plan-marshall:extension-api` build standards / agent build-invocation guidance.

## G4 — Reconcile the run report's stale figures with what actually landed

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/110-landed-residue-promotion-sweep/report-01.md` — § Build gate, § Contract check rows 2 and 7, and § Run continuation ("all six commits")
- **What is wrong:** Three statements were true when written and were not re-derived after the run continued: (i) Build gate says "no local build was run", while the continuation section below records "Verified locally with `./pw quality-gate`"; (ii) the contract-check table names the branch as the harness-assigned `claude/landed-residue-promotion-sweep-11npl8` "kept as-is" and the PR as #1161, while the work landed from `chore/landed-residue-promotion-sweep` as PR #1169 (GitHub API on #1169; the report's own header says so); (iii) "all six commits" — PR #1169 carries 10.
- **Why it matters:** The report is the durable record a retrospective reads for build-invocation counts, branch-form conformance and commit accounting; each of these three would be read off wrong.
- **Fix:** Amend those three places in `report-01.md`: note in § Build gate that a local `./pw quality-gate` was run later for the merge_group fix; update contract-check rows 2 and 7 to the branch and PR that landed, keeping the re-issue reason; replace "six commits" with the count on #1169 (10) or drop the number. The dated-record exemption in `CLAUDE.md` § Standalone Plan Lane permits the correction to stay inside the report.
- **Done when:** No statement in `report-01.md` contradicts another statement in the same file or the landed PR's branch, number, or commit count.
- **Module/topic:** `doc/plans/truthful-signals/110-landed-residue-promotion-sweep` run record.
