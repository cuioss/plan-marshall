# Gaps — 060-invented-plan-scoping-flags-are-an-overgeneralized-convention

**Source:** verification.md (same directory)   **Open items:** 4

The plan halted at its own ⛔ STOP CONDITION and correctly did not execute D2/D3. Those two
deliverables being unimplemented is **not** a gap — it is the designed outcome. The gaps below are
defects in what the run *did* deliver (D1(b), D1(c)), plus one item a future run would otherwise
mis-read as already fixed.

## G1 — Extend the D1(b) carve-out population to the `create_workflow_cli` declarative CLI shape

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/060-invented-plan-scoping-flags-are-an-overgeneralized-convention/report-01.md` § D1(b) — the published denominator; the un-scanned surface is `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py:274-410`, `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/build_queue.py:654-680`, `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py:1597-1675`
- **What is wrong:** The denominator is derived entirely from `.add_parser(` nodes and from three `--plan-id` grep patterns (`add_plan_id_arg(`, `add_argument('--plan-id'`, `add_body_consumer_args(`). Three `manage-*` scripts build their CLI declaratively via `create_workflow_cli(subcommands=[{'name': …, 'args': [{'flags': ['--plan-id'], …}]}])` and so match **none** of those patterns: they contribute 0 to the published population while actually carrying **10 verbs and 7 `--plan-id` declarations** (re-derived at the landed commit `c586d2cb`). `manage-locks` is absent from the report entirely — not in the 22-script list, not in the carve-out table. `manage-change-ledger` is mentioned but described as having "no `--plan-id` addition", which reads as "does not accept `--plan-id`"; it declares one on `append` (`manage-change-ledger.py:313`).
- **Why it matters:** `plan.md` § Verification makes the published population load-bearing — "A list of exceptions with no denominator is not a carve-out, it is a sample." A denominator with an unstated blind spot is the same defect one level up. The report hedges the counts as an "upper-bound proxy", which points the wrong way: the greps are a *partial* bound, not an upper one, so a future run sizing D2 from this carve-out under-counts the plan-scoped side of the convention and may mis-classify `manage-locks`/`manage-change-ledger` as non-plan-scoped.
- **Fix:** Re-derive the D1(b) population with a pattern set that covers both CLI construction shapes — `.add_parser(` **and** `create_workflow_cli(` `'name':` subcommand literals; `--plan-id` via the three existing patterns **and** `'flags': ['--plan-id']`. State the covered construction shapes explicitly beside the numbers, replace the "upper-bound proxy" hedge with "partial: covers the `add_parser` shape only" (or drop it once coverage is complete), add `manage-locks` to the enumeration, and correct the `manage-change-ledger` sentence to say it declares `--plan-id` on `append` through a different construction shape. While there, make the `manage-maven-profiles` cell use the `(parsers, plan-id)` form the other cells use — it is `(4, 1)`, not `(4)`.
- **Done when:** The carve-out enumeration names every `manage-*` script that declares `--plan-id`, by either construction shape, and the published population states which construction shapes its counts cover.
- **Module/topic:** `doc/plans/truthful-signals/060-…` report; surface under `plan-marshall/skills/manage-locks` + `manage-change-ledger`

## G2 — Add a recurrence signature for a router-scoped flag placed AFTER the verb

- **Kind:** stale-statement (report) + omission (the rule itself)
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md:342` — § "Never invent script subcommands", recurrence signature #2; the claim under test is in `report-01.md` § D1(c), second bullet
- **What is wrong:** `report-01.md` states the prose rule "already names this exact signature", citing signature #2. Signature #2 names the **mirror** defect and prescribes the **opposite** move: "placing `--plan-id` … immediately after the notation … where those flags are declared **on the subcommand**", worked example `manage-architecture --plan-id X resolve …` → `manage-architecture resolve … --audit-plan-id X`. Plan 060's failure is `ci checks status --plan-id X`, where `--plan-id` is a **router** flag consumed by `extract_routing_args` (`ci_base.py:570-599`) before argparse runs and declared nowhere on the parser tree — verified by execution, `_root_router_option_strings(parser)` returns `[]`. So `ci --plan-id X checks status` works and the verb-level placement fails, which is exactly the placement signature #2 teaches. No signature in the section covers the router-flag-after-verb shape.
- **Why it matters:** The report uses this claim to conclude the prose lane is saturated and that only a runtime error remains genuinely uncovered. A future corpus-enabled run reading that conclusion skips a signature that is in fact absent — and signature #2's worked example, read by a `ci` caller, points *toward* the failing invocation rather than away from it.
- **Fix:** Add a fifth recurrence signature to `agent-behavior-rules.md` § "Never invent script subcommands": **router-scoped flag placed after the verb** — `--plan-id`/`--project-dir` on the `tools-integration-ci:ci` surface are consumed by the router *before* the subcommand token and are not declared on any subparser, so they belong ahead of the verb. Worked example: `tools-integration-ci:ci checks status --plan-id X` → canonical `tools-integration-ci:ci --plan-id X checks status`. Add it as a positive control in `test/pm-plugin-development/plugin-doctor/test_analyze.py` beside the existing four (`:1721`, `:1745`, `:1769`, `:1798`). Correct the `report-01.md` D1(c) bullet to say the rule names the *mirror* signature, not this one.
- **Done when:** `agent-behavior-rules.md` § "Never invent script subcommands" contains a signature whose worked example is a router flag moved from after the verb to before it, and a plugin-doctor positive-control test pins it.
- **Module/topic:** `plan-marshall/skills/persona-plan-marshall-agent` (agent-behavior-rules) + `pm-plugin-development/skills/plugin-doctor` tests

## G3 — Record that the later router-flag note does not cover the `ci` surface

- **Kind:** doc-drift (a residue item that reads as closed but is not)
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-input-validation/scripts/input_validation.py:982-1016` — `_augment_misplaced_router_flag`; residue recorded in `report-01.md` § Residue, first bullet
- **What is wrong:** `report-01.md` recommends, as the one non-duplicate remedy, "a **runtime** actionable argparse error in `parse_args_with_toon_errors`'s fall-through". A later commit — `4ac41326` (#1213) — added exactly that: `_augment_misplaced_router_flag`, wired into the fall-through at `input_validation.py:1079`. It cannot fire on the surface plan 060 is about. It gates on `name in router_flags` where `router_flags = _root_router_option_strings(parser)`, i.e. options **declared on the root parser**; the `ci` providers strip `--plan-id`/`--project-dir` with `extract_routing_args` before building the parser (`github_ops.py:1822-1829`) and never declare them, so that set is empty. Executed against the live parser at HEAD: `_root_router_option_strings` → `[]`, and `ci checks status --plan-id X` → `unrecognized arguments: --plan-id X`, exit 2, with no note.
- **Why it matters:** Anyone picking up this plan's residue will see a symbol named after the recommended remedy sitting in the recommended seam and conclude the item landed. It did not — for the exact invocation the plan is named after, the message is still a bare exit-2. That is a false "already fixed" signal, which is this epic's own theme.
- **Fix:** Either (a) make the ci front-ends declare their router flags on the root parser (a no-op for parsing, since `extract_routing_args` has already consumed any pre-verb occurrence, but it populates `_root_router_option_strings` so the note fires), or (b) give `parse_args_with_toon_errors` an explicit extra-router-flags parameter that `github_ops.main` / `gitlab_ops.main` pass (`{'--plan-id', '--project-dir'}`). Add a test asserting that `ci checks status --plan-id X` emits a message naming `--plan-id` as a top-level flag and showing `ci --plan-id VALUE checks status`. Until then, amend `report-01.md` § Residue to state that #1213's note does not reach the `ci` surface.
- **Done when:** Running the CI parser with `['checks','status','--plan-id','X']` produces an error message that names the working invocation `ci --plan-id X checks status`, and a test pins it.
- **Module/topic:** `plan-marshall/skills/tools-input-validation` + `tools-integration-ci` / `workflow-integration-{github,gitlab}`

## G4 — Fill the report's PR field

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/060-invented-plan-scoping-flags-are-an-overgeneralized-convention/report-01.md:3` — the header line
- **What is wrong:** The header still reads `**PR:** _pending_`. The plan landed as PR #1150, commit `c586d2cb` (`git log --oneline -- <plandir>`).
- **Why it matters:** The run report is the lane's durable record of one execution; a permanently-`pending` PR field makes the record unlinkable to the change that carried it, and every downstream audit has to re-derive the number from git.
- **Fix:** Replace `_pending_` with `#1150` in the header line of `report-01.md`.
- **Done when:** `report-01.md:3` names PR #1150.
- **Module/topic:** `doc/plans/truthful-signals/060-…` run report
