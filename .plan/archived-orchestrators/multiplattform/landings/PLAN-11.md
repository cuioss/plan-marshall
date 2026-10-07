# Landing Analysis: PLAN-11 — target-scoping adoption

epic: multiplattform
workstream: WS-02
pr: #1438 (https://github.com/cuioss/plan-marshall/pull/1438)

> Landing record for one shipped plan. Lives at `landings/PLAN-11.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/target-scoping-adoption-001.md`, corroborated against the merged diff
(`8f6066cab`), the CI abstraction, and the change ledger. **This landing closes the last live
row in WS-02.**

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — file-level `targets:` scoping as an extension of `component_targets.py` | **shipped-as-specified** | `marketplace/targets/component_targets.py` +111/−, both emitters consuming it (`claude/emitter.py` +8, `opencode/emitter.py` +80), doctor rule `_analyze_target_scope.py` +141. Tests: `test_component_targets.py` +157, `test_target_scoped_emission.py` +43, `test_analyze_target_scope.py` +120. The spec's ⛔ "do not invent a second mechanism" held — the change is inside `component_targets.py`, not beside it. |
| **D2** — the `marshall-steward` split | **shipped-as-specified** | New sibling component `marshall-steward-claude-wizards/` (SKILL.md, 50 lines) taking `references/menu-enforcement-hook.md` and `references/menu-terminal-title.md` as pure renames (0 content lines changed). The neutral steward keeps SKILL.md, `menu-configuration.md`, `menu-healthcheck.md`. |
| **D3** — apply scoping to the five §D candidates | **shipped-as-specified** | Three file-level declarations landed at +4 lines each: `plan-marshall/references/hook-authoring-guide.md`, `plan-retrospective/references/permission-prompt-analysis.md`, `plugin-architecture/references/askuserquestion-patterns.md`. The two wizard surfaces were scoped via D2's component split rather than file-level declarations — a legitimate route, and the one the spec anticipated. |
| **D4** — report the §D rows, ledger untouched | **shipped-as-specified** | `../reference/coupling-inventory.md` is absent from the merge diffstat, so the ⛔ off-limits constraint held. Reporting rode the PR body and the inbox message. |

### The ADR-020 question the anchor asked, answered

The standing anchor asked specifically whether PLAN-11 applied ADR-020 to the
`wrapper-tangle-scan.py` §D row rather than scoping it. **It did.** The inbox message states
"`wrapper-tangle-scan.py` answered by ADR-020", and the merged diff confirms it: the file
(`marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/wrapper-tangle-scan.py`)
is untouched. A repo-scoping row was decided by the repo-scoping ADR instead of being absorbed
into the target-scoping mechanism. This is the ADR being used as designed.

## ⛔ Under-declaration is now measured at 15 paths — the worst in the epic, and it is structural

The anchor named under-declaration as a MEASURED repeating pattern (PLAN-04: 1 undeclared file;
PLAN-15: 6) and asked for the check. Realized footprint: **22 paths**. Machine-comparable declared
surface covers **7** of them. The 15 undeclared paths do not fall into one bucket, and the
distinction matters because only some of them are a spec-authoring fault:

| Class | Count | Paths | Fault? |
|---|---|---|---|
| **D2's split output — sibling of the declared glob** | 3 | `marshall-steward-claude-wizards/{SKILL.md, references/menu-enforcement-hook.md, references/menu-terminal-title.md}` | **Structural, not careless.** The spec declared `marshall-steward/**`. A *split* creates a new component by definition, so its output can never be inside the glob it splits out of. No declaration written before the split boundary was chosen could have named this path. |
| **Declared in prose, not as a path** | 2 | `marketplace/targets/{claude,opencode}/emitter.py` | Spec said "both component-tree emitters' consumption sites" — a real declaration the parser cannot compare. |
| **HYPOTHESIS resolved correctly at outline** | 3 | `plan-marshall/references/hook-authoring-guide.md`; `plugin-architecture/references/askuserquestion-patterns.md`; `plan-retrospective/references/permission-prompt-analysis.md` | **No fault — this is the spec working.** All three were labelled HYPOTHESIS with an explicit "verify-at-outline: re-derive the actual paths from the §D rows". The plan re-derived and corrected. |
| **Genuinely undeclared, unanticipated** | 6 | `doc/user/enforcement-hook.adoc`; `manage-terminal-title/standards/terminal-title-architecture.md`; `plan-retrospective/SKILL.md`; `platform-runtime/SKILL.md`; `platform-runtime/standards/pretooluse-enforcement.md`; `marketplace/targets/README.md` | **Yes.** Reference-integrity follow-on from D2's move — nothing named these. |
| **Undeclared test home** | 1 | `test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py` | **Yes.** The spec declared `test/plan-marshall/marshall-steward/**`, which realized nothing, and never declared the test home for its own `_analyze_target_scope.py` change. |

**Over-declaration, the other direction, is 2 paths:** `tools-permission-doctor/references/permission-prompt-analysis.md`
(a phantom — the file lives under `plan-retrospective/references/`; correctly HYPOTHESIS-labelled,
and the plan found it) and `test/plan-marshall/marshall-steward/**` (declared OBSERVED, realized
nothing).

### ⛔ The gate consequence, stated concretely

`marketplace/bundles/plan-marshall/skills/platform-runtime/**` is in **PLAN-06's** declared
surface AND **PLAN-07's**. PLAN-11 edited two files there and declared none of it. Had either
staged plan been launched concurrently — which the disjointness gate would have permitted,
because PLAN-11's declaration never named `platform-runtime` — that is a real, unpredicted
collision. This is the first instance in this epic where under-declaration is shown to have
produced a *false disjointness verdict* rather than merely an inaccurate record.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` → `complete: false`,
  `missing_keys: [total_tokens]`. **This is 6-for-6 on the OpenCode lane** — a standing lane
  property, already recorded, not a new defect. The producer wrote `unknown` rather than `n/a`,
  which is the correct choice under the anti-`n/a` rule: no session total was observed, and
  `unknown` says "not read" where `n/a` would falsely assert "there is no such thing".
- **Build gate: green, and the sha resolves — but it is a PRE-merge verify, not a post-merge one.**
  The operator's note called `ee4da4bb` a post-merge verify. It is not a git object; it is the
  build-job log id `ee4da4bbc2d34725a3dc59d21b65b26a.log`, recorded in the change ledger at
  `2026-09-07T07:18:58Z` with `exit_code: 0`, `tests_run: 24773`, `tests_population: measured`,
  `--project-dir …/worktrees/target-scoping-adoption`. The merge commit is timestamped
  `07:41:33Z`. So the green run happened **23 minutes before the merge, in the worktree**. The
  change ledger's most recent build entry is that same `07:18:58Z` row — **there is no
  post-merge verify on main recorded anywhere in the ledger.** The result is not disputed; its
  label is. See the Watch below.
- Duration: not reported by the payload (rides an optional key).
- Anomalies: none beyond the above.

## Routing and Merge Behavior

- **Review:** `cuioss-review-bot` reviewed, no suggestions. **CodeRabbit — required — did not
  review: arm `unobtainable`, and the disclosure is correct.** Account-level 7-day per-developer
  quota; the only re-trigger is a push; the base was fully merged so no legitimate new head
  existed; cosmetic pushes are forbidden. This is the disclosed-unobtainable path working as
  designed, not a bypass. `sourcery-ai` also rate-limited (optional). Note that PR **#1433**
  ("arm the CodeRabbit rate-window recovery") is open right now and is the standing fix for
  exactly this arm.
- **CI/merge:** merged via the merge queue; squash `8f6066cab5a6d39395ff0934bc314e5416d0c14e`,
  confirmed an ancestor of `origin/main`. Branch `feature/target-scoping-adoption` deleted local
  and remote; worktree removed. All corroborated.

## ⭐ The predicted PLAN-130 collision: warned, real in mechanism, disjoint in fact

The standing anchor carried a ⛔⛔ prohibition — do not run test-quality PLAN-130 while PLAN-11
runs, because both claim the test tree and the exact-path matcher cannot see containment. Both
ran anyway, and they landed **two minutes apart**:

- `5c1c8b212` — `test(docstrings): re-sweep historical-prose citations (1/2) (#1436)`, PLAN-130's
  part 1, merged `07:39:22Z`. It is **PLAN-11's merge parent**.
- `8f6066cab` — PLAN-11, merged `07:41:33Z`.

**Measured overlap: zero files.** PLAN-130 part 1 touched 76 paths, PLAN-11 touched 22, and the
intersection is empty. PLAN-130's still-open PR **#1435** (112 paths) likewise has an empty
intersection with PLAN-11's landed set.

Two things follow, and they point in opposite directions — record both:

1. **The risk assessment was sound and should not be softened.** The matcher's containment
   blindness is real; PLAN-11's own under-declaration (above) shows the gate producing a false
   clean verdict in this very landing. Disjointness here was luck of authorship, not a checked
   property.
2. **The prohibition cost nothing to violate, this time.** Recording only the warning would leave
   the next session unable to tell a near-miss from an over-cautious rule. It was a near-miss:
   PLAN-11's verify predates PLAN-130's landing by 20 minutes, so the green gate never saw the
   tree it merged into — and no post-merge verify replaced it.

## Reconciliation Actions

- [x] row `status` → `landed` — `orchestrator queue --transition PLAN-11 --status landed`
      (this ledger's terminal token: all 13 prior rows use `landed`, not the template's `shipped`)
- [x] row `pr` stamped `#1438`
- [x] row `landing` stamped `landings/PLAN-11.md`
- [x] row `plan_marshall_plan_id` stamped `n/a` (OpenCode lane — no plan-marshall plan id exists)
- [x] epic.md narrative reconciled from status.json
- [x] Open Defect opened — landing incomplete (`total_tokens`), folded into the standing lane entry
- [x] Open Defect opened — no post-merge verify on main
- [x] Watch opened — under-declaration produced a false disjointness verdict
- [x] Watch retired — the PLAN-130 containment collision, with the measurement
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- **F1** `frontmatter-standards.md:445` → carried to **PLAN-06** (spec already declares that file).
- **F2** R2-2 reference-integrity sites → **PLAN-06** (plugin-doctor / plugin-architecture) and the
  native bundle (`plan-retrospective`). ⛔ The `plan-retrospective` half is in **no** staged spec's
  declared surface — it is unowned.
- **F3** The worktree-executor regeneration trap the operator surfaced: a worktree lacking
  `.plan/local` makes root resolution walk up, so the runbook's "regenerate executor" remedy
  silently rewrites the **main-checkout** executor. Remedy in hand
  (`PLAN_TRACKED_CONFIG_DIR={worktree}/.plan` + plugin-cache bump + help-cache clear). **Proposed
  as a separate `chore/` PR against the runbook's stale-gate remedy — awaiting operator approval,
  not staged here.** This is a seventh member of the recorded six-defect orchestrator/executor
  tooling cluster.
- **F4** PLAN-11's own spec is terminal, so its `## Expected Surface` is not corrected. The
  correction that matters is to the **rule**, not this spec — see the Watch on prose-and-glob
  declarations.
