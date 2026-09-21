# Epic: Plan-Optimization — Token-Usage Analysis & Roadmap

slug: plan-optimization

> Ledger document for one epic under `.plan/local/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

A long-running token-usage optimization campaign over the plan-marshall archived + dormated
plan corpus. Wave 1 — the core token-optimization cost-driver roadmap plus the entire
aggregated findings/lessons queue (P1–P9 + design-first SS) — has SHIPPED (#899, #906→#922),
along with the `marshall-orchestrator` epic skill (#915). What remains is **Wave 2**: four
startable, surface-disjoint plans distilled from the open defects Wave 1 surfaced, plus parked
follow-ups. "Done" at the epic level is Wave 2 landed and the plans queue drained.

> **Migrated 2026-07-17** from the ad-hoc ledger at `.plan/plan-optimization/` into the
> orchestrator store, mirroring the plan-server migration precedent. The pre-migration ledger
> is preserved verbatim in this tree: `HANDOVER.md` (the pre-migration ledger — enduring context
> in §1/§2, defect detail in §5/§6), `00-README.md` (index), `HISTORY.md` /
> `HISTORY-snapshot-4-queue-wave.md` (frozen shipped record), the `01/02/03` analysis docs,
> `lessons-findings-queue.md`, and `landed/` (pre-roadmap design specs). **As of the 2026-07-17
> `decompose`, `status.json` is now the queue authority** (2 workstreams, 5 staged/parked plans);
> HANDOVER §4's queue is superseded by the Ordered Queue below.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug plan-optimization
     Paste the returned block verbatim between the markers. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: MODE: DRAINING COMPLETE - nothing is running. Awaiting operator direction before any emit. SHIPPED (WS-10 = 10): PLAN-20 #961 + PLAN-21 #957 + PLAN-22 #959 + PLAN-24 #963 + PLAN-25 #965 + PLAN-26 #964 + PLAN-28 #962 + PLAN-29 #969 + PLAN-30 #967 + PLAN-31 #968. ⚠⚠⚠ NEW BINDING PRACTICE, lesson 2026-07-21-22-001 FILED AGAINST marshall-orchestrator ITSELF: verify-before-implement is n=3 (PLAN-24/26/29 all correct symptom + falsified orchestrator-inferred mechanism). EVERY future spec whose mechanism is orchestrator-INFERRED must LABEL IT A HYPOTHESIS and NAME THE CONFIRM/REFUTE ARTIFACT - ad-hoc verify-first prose is insufficient, make it structural. APPLY RETROACTIVELY before emitting PLAN-23/33/34/35. KEY LESSON from #969: AN ADR IS NOT SELF-VALIDATING (ADR-011's own claim was falsified at execute; executor escalated rather than shipping a stub; ADR amended in-plan). ⚠⚠ ZERO RUNNING. ⚠ PLAN-32 IS LAUNCHED-BUT-ITS-SESSION-IS-DEAD: no worktree despite use_worktree true, stuck at 4-plan/in_progress, last write ~18:09, stale title_token build-busy. Status left 'launched' deliberately (literally true; downgrading would lose that it consumed real work). PROGRESS PRESERVED at .plan/local/plans/build-timeout-truthful-status/: 1-init/2-refine/3-outline DONE, solution_outline.md 18657 bytes, deep lane, confidence 95.5. OPERATOR FORK OWED: (a) RESUME [RECOMMENDED - the outline is the expensive artifact and it survived]; (b) PARK and re-stage; (c) ABANDON and re-emit fresh. STAGED = PLAN-23/27/33/34/35. ⚠⚠ LIVENESS RULE (I mis-stated in-flight counts THREE times this session): 'cross-check launched rows vs merged PRs' is INSUFFICIENT - it catches SHIPPED plans, not DEAD ones. Liveness = merged-PR check AND worktree presence AND plan-dir mtime recency. A launched plan with no worktree and stale mtimes is DEAD, not in-flight. AT PLAN-29 CHECK: (a) did D4's split guard fire (targets:-filter route => STAGE the follow-up generator plan); (b) did re-grounding find its inventory moved => verify-before-implement n=3; (c) ADR-011 allocation held (ADR-010 consumed by #965 - CONFIRMED). AT PLAN-32 CHECK: (a) did lessons-housekeeping strand? 32 is the CONTROL, composed post-#962 - if it strands, ESCALATE not file-as-expected; (b) does its inner<outer BOUND GUARD GENERALIZE to the ci_complete_precondition instance (lesson 2026-07-21-21-001: inner 600s EQUALS the harness Bash ceiling so it always loses the race and is backgrounded with zero output) - if not, stage a follow-up; do NOT inject scope while live; (c) PLAN-32's ACTUAL touched surface decides whether PLAN-35 is emittable. STAGED QUEUE STATE: PLAN-23 = ADJACENT to live PLAN-32 (both under script-shared/scripts/build/; PLAN-23 must edit _build_cli.py which carries PLAN-32's --timeout flag + adaptive-timeout subcommand = DIRECT FILE COLLISION) AND owes re-grounding after #963 AND must get a verify-first clause before emit. PLAN-27 DEPENDS ON PLAN-23. PLAN-33 = caller for the already-working 'session doctor --fix' + UNRESOLVED multiply-bound-plan conflict semantics + empty-dir prune; may become ADJACENT to PLAN-34 if D1 picks steward as the call site. PLAN-34 = consumer freshness gap + retention/prune + orphan-oracle gate; retention = UNION of keep-rules (N newest OR younger than D days OR is live/provisioned), N=5/D=3 operator-SUGGESTED NOT decided; ⚠ live-version pin LOAD-BEARING; DISJOINT from both in-flight = FIRST to emit when draining ends. PLAN-35 = OPERATOR-DIRECTED CONSOLIDATION: build_map is THE oracle, no other variants; seed scan found FOUR oracles (build-decision glob; six-bucket classifier; aspect-classify pure-doc not_necessary; freshness-gate steps-shape) and the VOCABULARY COLLIDES (documentation_only and not_necessary each mean 2 things) which is why divergence was invisible in review; 5 deliv at the split-guard edge w/ a STOP-AND-SPLIT trigger; retire documentation_only/lint_only w/ ADR-007 survivor sweep; preserve phase-3-outline's file-role question as legitimately separate; ⚠ ADJACENT to live PLAN-32. OPEN ITEMS NOT STAGED (draining): PLAN-25's D2/D3 implementation successor; module-level-caches-vs-daemon-longevity sweep (instance fixed in #965, CLASS unswept, routed to plan-server); contract-drift sweep (lesson 2026-07-21-17-002). CLEANUP DONE 07-21: token-optimization epic CLOSED+ARCHIVED (all 15 plans verified shipped/migrated); ~280 stale git refs pruned; session store swept 566/571, re-run clean, all live bindings verified survived. NOT DONE deliberately: plugin cache untouched (973MB, 550 markers) - its delete-time oracle is PLAN-34 D1. FLAGGED ELSEWHERE: test-suite-quality PLAN-02 = #966 MERGED but its ledger says launched - needs 'analyze slug=test-suite-quality' THERE. plan-server NOT closeable: routing observed BROKEN (preflight ready + daemon up but ran in-process with ZERO audit records; PREFLIGHT READINESS IS NOT EVIDENCE OF ROUTING; lesson 2026-07-21-14-001). ADVISORY: bundles 0.1.1179; marshal.json provisioned_version 0.1.1163 is a provisioning STAMP not an installed-code pointer - cache and target/claude ARE current; /marshall-steward reconciles the stamp + regens the executor, it does NOT fetch (that gap is PLAN-34). Executor regenerated ~5x today - restart advisable. WATCHES: docs-only-freshness-deadlock (now owned by PLAN-35); bound-ordering class n=2; fix-the-instance-not-the-neighbours (2026-07-18-14-001 sharpened); worktree-containment; disjointness-not-rechecked-on-scope-growth n=2; unrun-GC pattern n=2; verify-before-implement n=2 (PLAN-31 positive datapoint: both blockers held, still worth it); composed-manifest-snapshot (PLAN-32 = control); guards-are-highest-risk-artifact n=4 w/ PLAN-26 counter-example; gemini n=7 - SUNSET DECISION DESERVES REVISITING; landing-record-completeness-depends-on-handoff n=2. AT EPIC CLOSE: decide WS-10 successor-epic migration then close+self-archive via #937.
**Phase**: orchestrating
**Queue** (staged, in order):
1. PLAN-23 (WS-10)
2. PLAN-27 (WS-10)
3. PLAN-35 (WS-10)
4. PLAN-37 (WS-10)
5. PLAN-38 (WS-10)
- PLAN-01 (WS-01) — PR 926 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-01) — PR 927 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-01) — landing=landings/PLAN-03.md — status: resolved
- PLAN-04 (WS-01) — PR 930 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-02) — PR 931 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-02) — PR 929 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-03) — plan=steward-wizard-config-integrity — PR 932 — landing=landings/PLAN-07.md — status: shipped
- PLAN-08 (WS-03) — plan=executor-manifest-resolution — PR 934 — landing=landings/PLAN-08.md — status: shipped
- PLAN-09 (WS-03) — plan=merge-queue-merge-group-guard — PR 935 — landing=landings/PLAN-09.md — status: shipped
- PLAN-10 (WS-04) — plan=review-barrier-noise-filter — PR 936 — landing=landings/PLAN-10.md — status: shipped
- PLAN-11 (WS-05) — plan=footprint-driven-build-gating — PR 938 — landing=landings/PLAN-11.md — status: shipped
- PLAN-12 (WS-06) — plan=orchestrator-archive-verb — PR 937 — landing=landings/PLAN-12.md — status: shipped
- PLAN-13 (WS-03) — plan=steward-provisioning-fail-closed — PR 950 — landing=landings/PLAN-13.md — status: shipped
- PLAN-14 (WS-04) — plan=scoped-whole-tree-module-tests — PR 942 — landing=landings/PLAN-14.md — status: shipped
- PLAN-15 (WS-07) — plan=stale-merge-lock-reclaim — PR 940 — landing=landings/PLAN-15.md — status: shipped
- PLAN-16 (WS-08) — plan=planning-phase-checkout-guard — PR 945 — landing=landings/PLAN-16.md — status: shipped
- PLAN-17 (WS-05) — plan=fast-ci-footprint-gating — PR 948 — landing=landings/PLAN-17.md — status: shipped
- PLAN-18 (WS-09) — plan=merge-queue-coexistence — PR 952 — landing=landings/PLAN-18.md — status: shipped
- PLAN-19 (WS-09) — plan=finalize-queue-enforced-enqueue — PR 944 — landing=landings/PLAN-19.md — status: shipped
- PLAN-20 (WS-10) — PR 961 — landing=landings/PLAN-20.md — status: shipped
- PLAN-21 (WS-10) — PR 957 — landing=landings/PLAN-21.md — status: shipped
- PLAN-22 (WS-10) — PR 959 — landing=landings/PLAN-22.md — status: shipped
- PLAN-24 (WS-10) — PR 963 — landing=landings/PLAN-24.md — status: shipped
- PLAN-25 (WS-10) — PR 965 — landing=landings/PLAN-25.md — status: shipped
- PLAN-26 (WS-10) — PR 964 — landing=landings/PLAN-26.md — status: shipped
- PLAN-28 (WS-10) — PR 962 — landing=landings/PLAN-28.md — status: shipped
- PLAN-29 (WS-10) — PR 969 — landing=landings/PLAN-29.md — status: shipped
- PLAN-30 (WS-10) — PR 967 — landing=landings/PLAN-30.md — status: shipped
- PLAN-31 (WS-10) — PR 968 — landing=landings/PLAN-31.md — status: shipped
- PLAN-32 (WS-10) — plan=build-timeout-truthful-status — PR 972 — landing=landings/PLAN-32.md — status: shipped
- PLAN-33 (WS-10) — plan=session-binding-gc-and-conflict-semantics — PR 974 — landing=landings/PLAN-33.md — status: shipped
- PLAN-34 (WS-10) — plan=consumer-upgrade-cache-freshness — PR 976 — landing=landings/PLAN-34.md — status: shipped
- PLAN-36 (WS-10) — plan=finalize-machinery-integrity — PR 973 — landing=landings/PLAN-36.md — status: shipped
- PLAN-37 (WS-10) — plan=credentials-key-normalization — PR 978 — landing=landings/PLAN-37.md — status: shipped
- PLAN-38 (WS-10) — plan=domain-ambiguity-candidate-set — PR 975 — landing=landings/PLAN-38.md — status: shipped
<!-- END GENERATED: resume-summary -->

## Ordered Queue

Mirrors `status.json` `plans[]` (reconcile status.json → here). Surface-disjointness governs
pairing; up to 3 concurrent cleanly (PLAN-02 and PLAN-04 share the phase-6 surface → same group).

| # | Plan | Workstream | Status | Surface (expected) | Notes |
|---|------|------------|--------|--------------------|-------|
| 1 | PLAN-01-manifest-compose-gaps | WS-01 | ✅ shipped | `manage-execution-manifest.py` + `_manifest_rules.py` + phase-4 compose | PR #926 (`09915b14c`). D1 shipped; D2 found already-closed + locked. Landing: `landings/PLAN-01.md` |
| 2 | PLAN-02-finalize-step-integrity | WS-01 | ✅ shipped | phase-6-finalize step scripts + bodies | PR #927 (`107ea1b8c`). 4/4 deliverables; D4 added CWE-59 hardening; dogfooded own fixes. Landing: `landings/PLAN-02.md` |
| 3 | PLAN-03-leaf-validator-yield | WS-01 | ✅ resolved (no-op audit) | `execution-context` topology + step body/topology docs | No PR — premise already shipped (#920/#493/q-gate). Audit → lesson `2026-07-18-10-001`; saved ~1M tokens. Landing: `landings/PLAN-03.md` |
| 4 | PLAN-04-docs-contract-consistency (P7) | WS-01 | ✅ shipped | phase-6 SKILL.md prose + config-knob docs + persona standards | PR #930 (`8e218474b`). Last WS-01 plan. Landed LAST → rebased over #929 (`configuration.adoc`) + #931 (`agent-behavior-rules.md`) — both predicted adjacencies HELD. Landing: `landings/PLAN-04.md` |
| 5 | PLAN-05-terminal-title-stale-build-busy (TT) | WS-02 | ✅ shipped | `manage-terminal-title` + `_status_core.py` + `agent-behavior-rules.md` | PR #931 (`ba04f4b6b`). REAL fix (not the no-op I flagged): `drop_stale_build_busy` on phase transition, scoped to build-busy. Landing: `landings/PLAN-05.md` |
| 6 | PLAN-06-ci-pr-safe-merge | WS-02 | ✅ shipped | `tools-integration-ci` verb + `default:branch-cleanup` config + finalize merge-step | PR #929 (`629cc44a3`). Premise already-shipped → re-scoped to 3 `configuration.adoc` doc rows. Landing: `landings/PLAN-06.md` |
| 7 | PLAN-07-steward-wizard-config-integrity | WS-03 | ✅ shipped | `_cmd_system_plan.py` + `_cmd_sync_defaults.py` + `wizard-flow.md` + steward SKILL.md | PR #932 (`cbae070db`). D1 `unknown_field` guard + D2 wizard sync-defaults lanes + bonus error-doc self-review catch. Landing: `landings/PLAN-07.md` |
| 8 | PLAN-08-executor-manifest-resolution | WS-03 | ✅ shipped | `generate_executor.py` (`find_installed_manifest_path`) + `_config_defaults.py` (`stamp_provisioning_fields`) | PR #934 (`cc9a6515f`). D1 clone-root resolver +traversal guard, D2 non-destructive stamp, D3 fail-closed `marshal_status: unknown`. ADR-009. PLAN-07↔PLAN-08 adjacency HELD (rebased clean). Landing: `landings/PLAN-08.md` |
| 9 | PLAN-09-merge-queue-merge-group-guard | WS-03 | ✅ shipped | `merge-queue-setup.md` (MQ-2) + `ci repo merge-queue enable` | PR #935 (`ff568b962`). D1 refuse-at-API (`_repo_has_merge_group_trigger`, direct-child-indent anchored) + D2 doc reconcile; resolved (a) refuse. Landing: `landings/PLAN-09.md` |
| 10 | PLAN-10-review-barrier-noise-filter | WS-04 | ✅ shipped | `github_pr.py` + `github_re_review.py` | PR #936 (`38cbf227a`). Dropped pipeline-authored triggers + CodeRabbit rate-limit notices; DOGFOODED (0 loopback on its own re-review). Lesson 14-002 removed. ⚠ residual 13-21-001 (bot-agnostic) still open. Landing: `landings/PLAN-10.md` |
| 11 | PLAN-11-footprint-driven-build-gating | WS-05 | ✅ shipped (⭐) | phase-5-execute Step 11b + `manage-config build-decision` (existing authority) | PR #938 (`cdcc630b9`). D1 gated whole-tree phase-5 build on `should_execute_build` (same authority phase-6 uses — NO new mechanism; q-gate rejected a proposed dup verb). D2 kept aspect-classify pure. Behavioral-verify: wiring confirmed, full E2E deferred to next docs-only run. Landing: `landings/PLAN-11.md` |
| 12 | PLAN-12-orchestrator-archive-verb | WS-06 | ✅ shipped | `orchestrator.py` + `marshall-orchestrator/SKILL.md` + `workflow/archive.md` + orchestration-model standard | PR #937 (`25a46b407`). `archive` verb → `.plan/local/archived-orchestrators/{slug}/` (close still freezes; read-verbs resolve archived, write strict). CodeRabbit caught 4 real defects (lesson 12-001: read-fallback needs sibling write-guards). **This epic can self-archive at close** (after cache refresh). Landing: `landings/PLAN-12.md` |
| 13 | PLAN-13-steward-provisioning-fail-closed | WS-03 | ✅ shipped (⭐ 5/5) | `generate_executor.py` + `_config_core.py`/`_cmd_system_plan.py` + `provisioning-fail-closed-audit.md` + `platform-runtime` seam + steward upgrade | PR #950 (`e45c7ac8f`, 23 files/+824). **All 5 deliverables shipped-as-specified; NEITHER split seam needed** (operator's unsplit call held). D1 resolver highest-version-wins + 2-manifest regression test; **D2 verified LIVE on the real machine** (session opened with `executor_action: regenerated` at identical versions → post-merge two consecutive preflights `fresh`); D3 audit doc (+111) enumerating the surface; D4 validated-write helper + invariant test (+116), ADR-009 already Accepted so `adr-propose` correctly emitted NO new ADR; D5 harness-agnostic reload directive resolving per `runtime.target` (Claude/opencode/no-op) + steward interface adapted. Local gates outperformed bots (whole-tree caught a D5 test under-scope; self-review caught 3 real doc defects; CodeRabbit clean, 2 gemini comments refuted as false positives). **WS-03 COMPLETE.** Landing: `landings/PLAN-13.md` |
| 14 | PLAN-14-scoped-whole-tree-module-tests | WS-04 | ✅ shipped | `_test_scope_divergence.py` + `pyproject_build resolve-test-scope` + `pre-push-quality-gate.md` + fixture | PR #942 (`e2d0f45f8`). Re-grounded at outline (light→deep): pre-push gate is mypy+ruff only (no pytest), so PLAN-08's regression was never in-scope. Shipped a callable divergence seam + whole-tree module-tests finalize gate (match-or-warn). Local whole-tree degraded to loud warning (marshalld inert + harness ceiling) → CI verified green ×2. Bots caught 2 real leaf-missed defects. **WS-04 COMPLETE** (PLAN-10 + PLAN-14). Landing: `landings/PLAN-14.md` |
| 15 | PLAN-15-stale-merge-lock-reclaim | WS-07 | ✅ shipped | `manage-locks` `_locks_core.holder_has_live_worktree` | PR #940 (`ff0c109e7`). Root cause was `holder_has_live_worktree`'s bare `.exists()` (not `holder_is_dead` — outline re-grounded); orphaned shell now auto-reclaims. Fixes the ~5-incident class. Landing: `landings/PLAN-15.md` |
| 16 | PLAN-16-planning-phase-checkout-guard | WS-08 | ✅ shipped | `planning-outline.md` Step 2c/4b clean-main assertions + `_analyze_phase2_refine_contract.py` 3-phase generalization | PR #945 (`a4ba622ec`). Seam confirmed at outline = (b) phase-boundary clean-main assertion + static plugin-doctor complement (rejected Q-Gate + execution-context write-guard). D1 delivered both halves: runtime `git -C . status --porcelain` refuse-on-dirty-main at 3-outline→4-plan (`outline_contract_violation`) and 4-plan→5-execute (`plan_contract_violation`), NO phase-5/worktree assertion; static analyzer emits `outline/plan-contract-violation`. No PLAN-11 rebase conflict. Self-review caught 2 real contract-drift defects. Absorbs planning-phase class of 17-001/13-002; phase-5 occ 17-001(07-17) retained OoS. **WS-08 COMPLETE.** Landing: `landings/PLAN-16.md` |
| 17 | PLAN-17-fast-ci-footprint-gating | WS-05 | ✅ shipped | `.github/workflows/python-verify.yml` (+7 opt-in) + CLAUDE.md (+4/-1) | PR #948 (`250f9a4ea`). Re-grounding SHRANK it: D1 org gate already landed (v0.11.0), D2 pin bump already landed (#946) — but **the feature was INERT** (`skip-on-docs-only` defaults false, nobody opted in); D3's ruleset move already done since 2026-06-23, only CLAUDE.md prose stale. Real residual = the opt-in + a doc fix. **Gate proved itself mid-run**: docs-only push SKIPPED `verify / verify` while `verify / conclusion` reported green (required check satisfied, queue not stalled); workflow-touching commits still built. Concurrent org bump #947 (v0.11.1) conflicted mid-finalize → rebased to v0.11.1 pin + opt-in (both on main, verified in diff). **WS-05 COMPLETE.** Landing: `landings/PLAN-17.md` |
| 18 | PLAN-18-merge-queue-coexistence | WS-09 | ✅ shipped | `github_ops.py` (+53) + `merge-queue-setup.md` (+77) + manage-config defer signal + 2 new test files | PR #952 (`464f53ec1`, 10 files/+381). **A's central premise was FALSE** — bypass-actor support was already shipped (refine verified A against the stale `github-impl.md` doc and passed it through; outline caught it against `github_ops.py`), so A collapsed to D1 (warn on bypass-less create + stale-doc reconcile). B `externally_managed` discriminator w/ zero-mutation argv assert; C `merge_queue_managed_externally` defer signal + probe short-circuit; steward MQ-0 gate + `warnings[]`. Never-mutate-foreign verified in security-audit. **Fitting proof: at merge the probe reported `externally_managed: true`** — D2 classifying the org queue it coexists with. Pruned gemini caught a REAL `setdefault` None-key bug. **WS-09 COMPLETE — original Wave-2 queue fully DRAINED.** Landing: `landings/PLAN-18.md` |
| 19 | PLAN-19-finalize-queue-enforced-enqueue | WS-09 | ✅ shipped | `phase-6-finalize/standards/branch-cleanup.md` merge routing | PR #944 (`f63649b49`). Re-grounded at outline: desired-outcome D (enqueue on `use_merge_queue=true`, no `--delete-branch`, no admin fallback) was ALREADY implemented+tested at all 3 layers; stale `:543`/`:707` citations predated the landed routing. Residual = 1 doc fix (Pre-Merge Confirmation Gate + auto-merge bypass authorization conditional on `use_merge_queue`, `(if <condition>)` convention). Review caught the auto-merge-bypass mirror site the plan missed (coderabbit TASK-003 + gemini TASK-002). Validated E2E: finalize enqueued #944 via `pr merge-queue` on a genuinely queue-enforced main. Landing: `landings/PLAN-19.md` |

| 20 | PLAN-20-execution-accounting-integrity | WS-10 | staged (emittable) | phase-5 leaf verification composition + `resolve-test-scope` reuse + `mark-step-done`/manifest `step_id` + structural guard | **Survivor plan (2026-07-20).** D1 leaf runs the tests it can break (lesson 22-001, **n=3** — PLAN-14/16/13); D2 prefixed-step record key matches manifest `step_id` (12-003, **n=5**, highest in epic; the plan-16 #885 residual, NOT a redo); D3 structural guard. D1+D2 deliberately kept together — split apart they'd both land on execution-manifest and serialize |
| 21 | PLAN-21-review-barrier-residuals | WS-10 | staged (emittable) | `github_pr.py`/`github_re_review.py` noise pre-filter + `_ci_barrier.py`/automatic-review completeness guard + `enabled_bots` defaults | **Survivor plan (2026-07-20).** Direct PLAN-10 #936 residual. D1 bot-agnostic rate-limit classifier (13-21-001, recurred at #948 → plan-worthy trigger SATISFIED); D2 completeness guard must not loop_back pre-triage (05-001, recurred at #948); D3 retire sunset gemini from `enabled_bots` defaults (caveat: a pruned bot can STILL post valid findings — remove from default set only). Self-validating: its own finalize run is the acceptance evidence |
| 22 | PLAN-22-lock-staleness-scope-guard | WS-10 | staged (emittable) | `manage-locks`/`_locks_core.py` release-path staleness + CWD-keyed store-scope resolution | **Survivor plan (2026-07-20).** From the LIVE #948 incident (released #950's lock on a worktree-scoped query; no damage, unsound check). D1 staleness resolves against main-checkout store, empty/unresolvable ⇒ `unknown` not `stale`, release REFUSES on unknown; D2 sweep CWD-keyed store-resolution sites where an empty result drives an authority-bearing decision (incl. known `manage-lessons` hazard); D3 encode invariant + retire lesson. **Inverse of PLAN-15 #940** (auto-reclaim hardened; manual-release path unguarded) |

| 23 | PLAN-23-marker-detector-ownership-and-fixture | WS-10 | staged (emittable) | `pm-dev-java-cui` (new home) + retire `_markers_search.py`/script-shared + build-maven + build-gradle + extension-api build-API contract + test rewrite | **Operator-surfaced 2026-07-20, ALL CLAIMS ORCHESTRATOR-VERIFIED.** `search-markers` is a VACUOUS GATE: `MARKER_PATTERN` (`_markers_search.py:23`) closes `)>*/` but real markers close `)~~>*/` — `~~` present in the opening delimiter, absent from the closing one; empirically matches NOTHING. `:154` exits 1 only on `ask_user_count > 0`, so it always exits 0. **⚠ Orchestrator-found and WORSE than reported: the ~40-test suite PINS THE BUG** — every test hand-writes the broken `)>*/` form (`:35`, `:130`, `:147`), so it cements rather than catches the defect. D1 relocate to format-owner `pm-dev-java-cui` (+ retire from both build bundles, amend the extension-api contract — a surface the report did not name); D2 fix regex + **provenance-bearing real-marker fixture** (hand-written fixtures caused this) + rewrite ~30 assertions; D3 make the gate able to fail (`total_markers > 0`, not `ask_user_count`) |
| 24 | PLAN-24-maven-run-truthful-status | WS-10 | ✅ shipped | `script-shared/scripts/build/_build_shared.py` + `_build_result.py` + testfailureignore fixture log + mock `mvnw` + 3 test files | PR #963 (`c865a2938`, 7 files/+361). **2/2 shipped** (not 3 — see landing's correction note). ⚠ **PREMISE FALSIFIED**: the spec's mechanism (`success_result()` hardcoding) was WRONG; the real defect was two distinct call paths in `_build_shared.py` that never cross-checked the parsed test summary — seam (a) `cmd_run_common` trusted `returncode==0`, seam (b) `cmd_parse_common` used the `build_status` string alone. PLAN-24 therefore joins PLAN-17/18/19 as a collapsed-premise plan. **The plan succeeded because D1 was scoped reproduce-first — direct vindication of the do-NOT-fix-on-hypothesis discipline**; implemented against the stated mechanism it would have fixed the wrong thing. Both seams fail-closed per ADR-009 + per-seam failing-then-passing regression tests; D2 `assert_truthful_status`/`TruthfulStatusError` at the emit choke point. **gemini caught 2 real defects in the plan's OWN guard** (tautologically-zero `exit_code`, misfire on explicit `None`) → loop-back TASK-005/006, 2/2 actionable 100% resolved-as-fixed, lesson `2026-07-21-14-002`. 3M tokens / 2h20m. Bumped v0.1.1174. ⚠ lessons-housekeeping promotion STRANDED by pre-merge-composed manifest ordering → follow-up lesson `2026-07-21-15-002`, owed a re-run. Landing: `landings/PLAN-24.md` |
| ~~24 (spec)~~ | *(original staging note retained below for provenance)* | | | **Operator-surfaced 2026-07-20 as its own entry.** `maven run` returned `status: success, exit_code: 0` over a real Maven **BUILD FAILURE** ×3 in one session. **Symptom NOT yet orchestrator-reproduced; plausible MECHANISM verified in source:** `_build_result.py:228-256` `success_result()` **hardcodes** `status: success` + `exit_code: 0`, so truthfulness depends entirely on the caller's branch — nothing derives status from the real return code. **Strictly worse than the known `pyproject_build` exit-0 class**: there the TOON `status` was still truthful; here `status` ITSELF lied, so "read the status field" does not save the caller. D1 reproduce+root-cause (do NOT fix on the hypothesis); D2 derive from process outcome, fail closed, sweep shared callers; D3 structural guard |

| 25 | PLAN-25-domain-conditional-loading-concept | WS-10 | ✅ shipped — PR #965 (`18b7140db`, 9 files/+1193) — 5/5; ADR-010 taken; **D3 scope discipline HELD** (`generate_executor.py` NOT touched — specify-then-decline honoured); D4 = 17 sites (3 FIX/14 JUSTIFY); D5 took the skip-not-block arm; 3.5M tok/3h20m; **2 gemini loop-backs BOTH in D5's own code** (redundant resolve subprocess; `lru_cache` never cleared per-compose = stale in the marshalld daemon), 4 speculative declined per Principle 7; landing `landings/PLAN-25.md` | new ADR + `extension-api/standards/` ext-point spec + specification doc + inventory doc (docs-dominant; `generate_executor.py` READ-ONLY) | **Operator-surfaced 2026-07-20, scoped against an orchestrator survey.** Establishes the missing concept: domain content in play ONLY when its domain is active. Survey: activation already exists and gates KNOWLEDGE/SKILLS (`resolve-workflow-skill-extension` null-on-absent; `find_implementors`; `discover_applicable_extensions`; `domain-detect`→`references.domains`) but NOT scripts/verbs — two genuinely NEW pieces: domain-owned build verbs (`ext-point-build` mandates core-bundle) and domain-aware notation exposure (`generate_executor.py` is domain-blind). D1 ADR decides gating layer + visibility semantics (invisible vs present-but-refusing — ADR-009 argues against silent absence); D2 contract for domain-contributed executable surfaces; **D3 SPECIFICATION ONLY of executor domain-awareness — explicitly NOT implemented** (⚠ that file already produced PLAN-08 #934 and PLAN-13 #950 D1/D2; "specify then decline" is a legitimate outcome); D4 inventory of core-resident domain specifics (the marker case is an instance, not the population); **D5 (folded 07-20) CONCRETE ANCHOR + FIX — arch-gate seed/resolve mismatch** (`configure` seeds `default:verify:arch-gate` on domain-presence but a Maven module without an `arch-gate` command can't resolve it → blocks compose; fix = seed-on-resolvability or skip-not-block; non-durable manual remove). Now **5 deliv**, design-first D1-D4 + concrete D5; D5 cleanly separable if it balloons. Implementation of D2/D3 deferred — expect >1 plan total |

| 26 | PLAN-26-terminal-title-refresh-cadence | WS-10 | ✅ shipped | `_claude_runtime_impl.py` (title vs footer emit + `/dev/tty` write) + `claude_runtime.py` (statusLine reg + hook list) + `_status_core.py` repaint seam | **Operator-surfaced 2026-07-20, root cause VERIFIED.** Tab TITLE freezes at an early phase (`2-refine`/`4-plan`) while the FOOTER is correct — a **delivery-cadence divergence**, NOT composition/dedup/#931. Both share `compose()`+`status.json` via `session_render_title`; footer rides the continuously-polled `statusLine` (always fresh), title only repaints on turn-boundary hooks + a `/dev/tty` write that **silently no-ops** off the controlling terminal (sub-agent/worktree/bg = phase-5/6). Within one long turn spanning phases 2→6 the title has no reliable refresh → freezes. D1 give the title a footer-equivalent continuous cadence (⚠ claude-code-guide consult at outline: can `statusLine` carry a `terminalSequence`?); D2 stop the in-turn path silently no-opping without a tty (route via host envelope, not raw `/dev/tty`); D3 the missing footer/title-consistency regression test. Disjoint from all other WS-10 plans. **LANDED: PR #964 (`920f98879`, 20 files/+1466). 4/4 shipped.** ⚠ **Symptom analysis HELD, proposed MECHANISM FALSIFIED** — `statusLine` **cannot** carry OSC-0 (that candidate is dead); the real gap was that the render hook was already on Pre/PostToolUse but **matcher-scoped to Bash/AskUserQuestion**, so Read/Edit/Write/Grep/Task fired no render at all — now matcher-less on PostToolUse. The spec's *"needs a claude-code-guide consult at outline"* instruction is what caught it. D1+D2 **collapsed into one mechanism** exactly as the size-guard predicted; `/dev/tty` demoted to a labelled fallback (`no_controlling_tty`/`dev_tty_fallback`) surfacing non-delivery at WARNING. `/clear` proved hookable via `SessionStart`+`source: "clear"`, so D4a stayed in scope and the split-trigger never fired. **Self-validated 4× during its own finalize.** 3.1M tokens / 2h57m; CI 11/11; self-review 104 candidates (largest in epic); 3 findings → 2 fixed 1 declined; 3 lessons. Bumped v0.1.1175. Landing: `landings/PLAN-26.md` |

| 27 | PLAN-27-openrewrite-log-finding-retrieval | WS-10 | staged | `build-maven` OpenRewrite log/finding retrieval | Unblocked by cui-open-rewrite#116 → #118. **DEPENDS ON PLAN-23** (shares the build-maven marker/finding surface). Do not emit before PLAN-23 lands |
| 28 | PLAN-28-lessons-housekeeping-plugin-doctor-contract | WS-10 | ✅ shipped | `finalize-step-lessons-housekeeping` SKILL.md + `extension-api/standards/ext-point-finalize-step.md` + new `_analyze_mutates_source_order.py` + registry/runner/catalog/provenance + 4 test files | PR #962 (`cd931fb63`, 12 files/+873). 3/3 deliverables shipped-as-specified, D3 **exceeded spec** (merge-gate order resolved DYNAMICALLY from discovered `branch-cleanup`, not hardcoded). D1 resolved the contradiction in favour of the lint (provenance → tombstone + decision log), NOT by carving an exception. D2 `order: 4` + `mutates_source: true` rides EXISTING pre-merge commit instrumentation — no new mechanism. **Self-validating: the step ran in its own finalize and left a clean tree** — eliminated its own wedge in the same run. 3 review iterations all productive; CodeRabbit caught a self-contradictory sentence in the contract THIS PLAN authored; **gemini caught a real `#`-comment filter inconsistency (4th consecutive landing where sunset-flagged gemini produced a real finding)**; 1 gemini finding correctly refuted on grounded evidence. 3.9M tokens / 1h56m. Bumped v0.1.1173. Landing: `landings/PLAN-28.md` |
| 29 | PLAN-29-platform-agnostic-waiting-standard | WS-10 | ✅ shipped — PR #969 (`ca8a044b0`, 23 files/+1816) — 4/4; **ADR-011 = HYBRID** (policy = target-neutral standard everywhere; primitive = Runtime op declining via no-op+alternative). **D4 split guard did NOT fire** (Runtime-op route chosen) → no follow-up generator plan owed, question CLOSED. ADR-011 allocation held (re-checked at outline AND again when #965 landed 010 mid-run). ⚠⚠ **verify-before-implement → n=3**, lesson `2026-07-21-22-001` filed **against marshall-orchestrator itself**. Falsified TWICE: at refine (Runtime ABC has **23 ops not ~22**; admission test lives in `01-finish-portability.md`; **`_UNMAPPED_TOOLS` is Claude-scoped so my D2 route would have been ACTIVELY WRONG**) and at execute (**ADR-011's own claim was false** — Claude's background-watch affordance is agent-level with no Python API a runtime subprocess can register against; executor STOPPED AND ESCALATED rather than ship an always-`unknown` stub; operator narrowed to build-job; **ADR-011 amended in-plan**). **KEY LESSON: an ADR is not self-validating.** 0 bot comments — every finding from local gates; self-review 142 candidates. 3.1M tok/2h31m. Landing `landings/PLAN-29.md` | platform-runtime waiting seam (route TBD at D1) | From the `Monitor` observation. **ADJACENT to live PLAN-26** on `platform-runtime` IF D1 picks the Runtime route; disjoint if D1 picks the `targets:`-filter route. Wait for PLAN-26 to land, or let D1 settle the route first. **LAUNCHED 07-21** — PLAN-26 landed so the adjacency is MOOT. Two orchestrator instructions carried in the emit but NOT in the spec file: **(1) D1 must allocate ADR-011, not 010** — live PLAN-25 (#965) already claimed `doc/adr/010-Domain_content_is_active_only_when_its_domain_is_active.adoc` on its branch (verified via `git diff` vs `origin/feature/domain-conditional-loading-concept`; main's highest is 009); **(2) re-ground the Design-inputs inventory before designing** — it was researched BEFORE #964 landed and #964 changed exactly that surface (`runtime_base.py` +51, `claude_runtime.py` +147, `_claude_runtime_impl.py` +100, `contract.md` +77), so the "~22 goal-based ops" count, `_UNMAPPED_TOOLS` membership and the no-op contract are all UNVERIFIED. **At landing check**: (a) did D4's split guard fire (`targets:`-filter route ⇒ generator build splits to a follow-up plan as an epic decision, 29 ships D1–D3 + spec) — if so STAGE the follow-up; (b) did re-grounding find the inventory moved — if so **verify-before-implement becomes n=3** |
| 30 | PLAN-30-orchestrator-title-push-coverage | WS-10 | 🚀 launched (07-21) | `marshall-orchestrator/workflow/{orchestrate,analyze,decompose,lessons-handling,init,resume}.md` (+ possibly the persona standard) | **Operator-surfaced 2026-07-21, ORCHESTRATOR-VERIFIED.** The `Orchestrator-{SlugName}` title is built end-to-end (`manage_terminal_title.py:121` composes it; `platform-runtime` carries `session push-title-token --store orchestrator` in BOTH runtimes) but only **4 of 8 verbs invoke the seam** — `init`/`resume`/`close`/`archive` do, while **`status`, `next`, `analyze`, `decompose`, `lessons` never push**. Root cause = the "session-opening verbs" categorization (`init.md:16`, `resume.md:15`), which presumes sessions begin with `init`/`resume`; the uncovered set is the daily-driver set. Observed live: a session opened with `status` pushed nothing. Docs-only. ⚠ **Verification depends on PLAN-26** — until its `/dev/tty` no-op defect lands, added pushes fire but render nothing; verify by asserting the invocation per verb doc, NOT by eyeballing the tab. Surface-disjoint from PLAN-26; **ADJACENT to PLAN-31** on `analyze.md`/`decompose.md` |
| 31 | PLAN-31-orchestrator-dispatch-ruleset | WS-10 | ✅ shipped — PR #968 (`dc919162f`, 6 files/+41-5) — 4/4; **all three orchestrator carries honoured** (re-grounded by direct read; both blockers re-verified TRUE; #967's state-once template mirrored). ⚠ **My guessed 3-stage-pipeline mechanism was WRONG — the plan found BETTER**: split on PROVENANCE not tool surface (ci/git fetch inline so Bash never leaves the orchestrator; first-party ground truth dispatches; the operator's own paste stays inline = dispatching trusted input is containment theatre). It also corrected TWO of my spec errors (stale `analyze.md` step numbers; a PLAN-30 blocker already moot). 2.3M tok/1h35m. Surfaced the docs-only freshness deadlock → **PLAN-35**; landing `landings/PLAN-31.md` | `persona-marshall-orchestrator/standards/orchestration-model.md` (primary) + `marshall-orchestrator/workflow/{analyze,decompose}.md` + SKILL.md Enforcement | **Operator-surfaced 2026-07-21, ORCHESTRATOR-VERIFIED.** The orchestrator has **no dispatch rule at all** — exhaustive grep for `execution-context`/`Task:`/`dispatch`/`subagent`/`Agent` across both skill trees returns **ZERO hits**; every verb runs inline by silence, not decision. D1 three-test rule (depth / fork-freedom / write-freedom) under "dispatch gathers, the orchestrator decides"; D2 the two safety constraints (read-only BY INSTRUCTION — the Bash-capable `execution-context` has Write/Edit; ALL ledger writes stay in the orchestrator context or they bypass the carve-out + log-everything) plus a fall-back-to-inline clause for the known stream-idle timeouts; D3 `analyze` depth-threshold + resolve the vehicle mismatch (**`execution-context-reader` has NO Bash** → cannot verify ground truth; likely two-stage reader→`validate_struct`→Bash-capable); D4 `decompose` split along the fork line — **`AskUserQuestion` is absent from BOTH agent surfaces**, colliding with persona attribute #9, so it may NOT be dispatched wholesale; D5 structured-return obligation. 5 deliv, under the split guard. ~~ADJACENT to PLAN-30~~ — hold RELEASED by #967. **LAUNCHED 07-21** with three orchestrator instructions not in the spec: **(1) RE-GROUND MANDATORY** — #967 rewrote ALL THREE primary targets (`analyze.md` +27, `decompose.md` +23, `orchestration-model.md` +18/-1), so every file:line in the spec is stale; **(2) MIRROR #967's TEMPLATE** — it added a "Terminal-Title Repaint Contract" section stating a cross-cutting orchestrator rule ONCE in the standard (canonical invocation + placement + gating + exception verbs) and referenced from the per-verb docs; PLAN-31's dispatch rule is the same shape, do NOT invent a new structure; **(3) re-verify the two hard blockers** (`execution-context-reader` has NO Bash; `AskUserQuestion` absent from BOTH agent surfaces) — read off the agent-type listing, which can drift with the harness |

| 32 | PLAN-32-truthful-build-timeout-accounting | WS-10 | 🚀 launched (07-21) | `script-shared/scripts/build/_build_execute.py` + `manage-run-config/scripts/run_config.py` + `pyproject.toml` + possibly `_build_result.py` + `test/plan-marshall/build-operations/` | **Promoted from watch 2026-07-21 after PLAN-28 #962 supplied hard numbers.** **Direct sibling of PLAN-24 #963** — that fixed status lying GREEN over a real failure; this fixes status lying RED over a real success (same class, same emit layer). Two ORCHESTRATOR-VERIFIED root causes: (1) **BOUND INVERSION** — `pyproject.toml:90-94` sets pytest-timeout `timeout = 300` (added by plan-server PLAN-03 #949, intent *"failure with a stack rather than an opaque job timeout"*) but the OUTER adaptive wrapper budget ~120s is SMALLER, so the wrapper preempts the backstop and it can never fire = **partial regression of PLAN-03's own remediation**; (2) **misleading observation surface** — `62.47s` is pytest-INTERNAL time while the budget is wall-clock incl. collection/coverage/teardown (later run ~103s), so the true margin was ~103 vs ~120 but the log invited "62s timed out against 120s". ⚠ **Adaptive learning already self-heals** (timeout doubles the learned value) — do NOT rework it wholesale; the defects are the discarded run + the misdirecting log. ⚠⚠ **CROSS-EPIC: plan-server OWNS the governing invariant** (`plan-server-core.md:148` property (b) *"a wait that returns on its time bound is NOT a timeout and must never look like one"*, #909) — this plan CITES and CONFORMS, never re-derives; confirm at outline whether that contract is hoisted shared-layer-wide. Routing defects found → handed to plan-server, never absorbed. **CONTRACT RESOLVED 07-21 (operator-confirmed): #909 hoisted as a SCOPED SPLIT** — half (a) terminal-status correctness HOISTED to the shared build layer (the violated half, `_build_execute.py:264`), half (b) bound-expiry running-liveness stays daemon-local (no in-process analogue). D3 conforms to the SHARED contract; **D3 unblocked, plan fully emittable**. ⚠ **Orchestrator refinement**: line 264 is `except subprocess.TimeoutExpired`, which only fires on a genuine kill — so the PROCESS did not complete; the TEST PHASE did, before the kill landed in the post-test tail. The naive "don't say timeout when it completed" therefore does NOT resolve it. Real defect = the branch DISCARDS the passing test summary it already holds. **Exact mirror of PLAN-24**: that made the SUCCESS path consult `test_summary` instead of trusting `returncode==0`; D3 makes the TIMEOUT path consult it instead of trusting `TimeoutExpired` alone |

| 33 | PLAN-33-session-binding-caller-and-conflicts | WS-10 | staged | `platform-runtime/scripts/session_binding.py` (read-mostly) + `platform_runtime.py` `session doctor` + wherever D1 wires the caller + tests | **From the 07-21 cleanup sweep.** The session store held **571 slots, 566 stale (99%), 88 conflicts, `gc_removed: 0`** — the GC had never run. Swept during cleanup (`session doctor --fix` → 566 removed; re-run `scanned:5 stale:0 conflicts:0`; all 5 live bindings verified survived). **The logic is CORRECT — the missing piece is an automatic CALLER**; a GC reachable only by a human running a doctor verb is indistinguishable from no GC. D1 wire the caller (reuse `--fix`, do NOT write a second GC); **D2 the UNRESOLVED conflict semantics** — 88 slots had one `plan_id` bound to several sessions and `close`/`archive` use `resolve-plan` to pick the restore title, so a multiply-bound plan is ambiguous; the sweep cleared them only incidentally and nothing prevents recurrence among LIVE sessions; decide last-driven-wins vs fail-closed (ADR-009); D3 prune empty session dirs (26 remained, only 5 with slots). May become ADJACENT to PLAN-34 if D1 picks steward as the call site |
| 34 | PLAN-34-steward-plugin-cache-lifecycle | WS-10 | staged — **emittable first when draining ends** (disjoint from both in-flight) | `marshall-steward/scripts/upgrade.py` (`:101`/`:120`) + `references/upgrade-flow.md` (`:133`) + SKILL.md + the sync-plugin-cache GC path + executor-preflight + tests | **Operator-surfaced 2026-07-21 after catching an orchestrator error** — I claimed finalize-driven cache sync "covers everyone"; it is `project:finalize-step-sync-plugin-cache`, **meta-project-ONLY** per CLAUDE.md, and its existence MASKS the gap from anyone testing only on plan-marshall. **Half 1 — consumer freshness**: the consumer stage matrix is exactly Stage 1 `[regenerate-executor]` + Stage 3 `[executor-preflight]`, **no cache step anywhere**, while `upgrade-flow.md:133` assumes a "freshly-synced" cache with **no establishing step and no guard** and zero marketplace-update guidance exists. So `upgrade` is likely a **misnomer on a consumer** — re-provisions against a stale cache and reports success. **Half 2 — retention**: 973 MB, 550 markers, **55/55 versions marked incl. the live one**, oldest exactly 7 days and unswept. **Operator ruling**: the same verb that updates must also prune. Retention = **UNION** of keep-rules (N newest OR younger than D days OR is live/provisioned), N=5/D=3 **suggested not decided**; ⚠ **the live-version pin is LOAD-BEARING** — a naive age-prune written against marker state would delete the running version. D1 gates on reading executor-preflight AND the delete-time oracle. **Consumer-facing** (4 repos) |
| 35 | PLAN-35-one-build-decision-mechanic | WS-10 | staged — ⚠ ADJACENT to live PLAN-32 | `manage-tasks` freshness gate + `manage-config` `_cmd_build_map.py`/`_cmd_aspect_classify.py` + `manage-execution-manifest.py:222-332` + `extension_base.py:1072-1075` + `decision-rules.md` + `pre-push-quality-gate.md:34` + `phase-3-outline/SKILL.md:299-317` + the D1 inventory doc + tests | **Surfaced by PLAN-31 #968** (hit the deadlock TWICE, ~200s wasted pytest each, resolved honestly with real builds not `--force`). ⚠ **My first framing was WRONG and corrected pre-staging**: the narrative said "docs-only has no exemption" but TWO exist (`documentation_only`, `lint_only`). **OPERATOR RULING — build_map is THE oracle, "to build or not to build", no other variants; scan ALL decision points, introduce ONE mechanic.** Seed scan found **FOUR** oracles: build-decision glob; the six-bucket classifier; aspect-classify's pure-doc `not_necessary`; the freshness gate's steps-shape reasons. **The vocabulary COLLIDES** — `documentation_only` and `not_necessary` each mean two different things, which is why divergence was invisible in review. D1 exhaustive inventory (the four are a SEED) → D2 design the one mechanic → D3 migrate + retire w/ ADR-007 survivor sweep → D4 compose-time contradiction guard → D5 regression from PLAN-31's real shape. 5 deliv at the guard's edge w/ recorded rationale + a **STOP-AND-SPLIT trigger** if D1 finds materially more sites. Preserve the phase-3-outline **file-role** question (`profiles[]`) as legitimately separate |

| 36 | PLAN-36-finalize-machinery-integrity | WS-10 | staged — ⚠ ADJACENT to PLAN-35 (same file) | `phase-6-finalize/standards/pre-push-quality-gate.md:56-63` + `SKILL.md:127` + `standards/dispatch-inline-split.md` + the completion-guard/`mark-step-done` path + tests | **Combines all three PLAN-29 (#969) defects.** Theme: **phase-6-finalize's own machinery disagrees with what actually runs**; all three live in the same skill, so separate plans would collide and be serialized anyway. **FIRST spec written under the new binding practice** (lesson `2026-07-21-22-001`) — every mechanism labelled OBSERVED or HYPOTHESIS with a named confirm/refute artifact. **D1 OBSERVED** (rule read directly): `pre-push-quality-gate.md:56-63` rule 3 takes path segment 1 for `test/` entries, so `test/marketplace/targets/*.py` → **`marketplace`**, not a bundle but the generator's own test tree → **hard-fails on a CLEAN tree** (lesson `2026-07-21-21-002`); #969 shipped changes to exactly those files, so the next plan touching them hits it immediately. **D2 PARTLY OBSERVED** — `SKILL.md:127` claims **17 steps** and names `dispatch-inline-split.md` as the SoT the dispatch branch consumes, while real runs executed **22/21/21/20/20**; HYPOTHESIS that ~5 steps carry no classification; artifact = enumerate the roster against #969's archived `execution.toon`; **prefer DERIVING the roster over correcting a constant** (stale-count class). **D3 HYPOTHESIS, cause unknown** — completion guard evadable by a success-shaped return without `mark-step-done` (**7th recurrence**); artifact = the guard + call path + **the prior six recurrences** — if they are six causes wearing one label, `7 recurrences` is a taxonomy artifact and the plan must re-scope. **Seven means an owner, not a seventh point-fix.** Considered and REJECTED folding D1 into PLAN-35: that plan's ruling is about build/no-build, D1 is *scope* (which bundle) — a concern PLAN-35 already carves out as legitimately separate — and folding would breach its split guard |

| 39 | PLAN-39-manifest-tier-truthful-stamp | WS-10 | 🚀 launched (07-22) | `manage-execution-manifest.py` (`:1085` resolve / `:1092` per_task-default / `:1106` stamp) + `architecture resolve` `exceeds_bash_ceiling` + the execute-task leaf read-site + tests | **Promoted from lesson `2026-07-22-00-002`, n=3 (PLAN-32 run / PLAN-33 1221s / PLAN-36 946s vs the 600s cap).** Sibling of PLAN-20. The compose stamp reads `per_task` for `verify:coverage` while a live execute-time `architecture resolve` returns `orchestrator`/`exceeds_bash_ceiling` — and `per_task` is the DANGEROUS value here (inline → killed), so the `per_task`-on-any-failure default (`:1092`, "the safe floor") is the prime suspect. Runs survived only because the leaf **defensively re-resolved** = structural enforcement silently degraded to convention. **SEAM OBSERVED, ROOT CAUSE HYPOTHESIS with 2 candidates needing different fixes**: (A) masked resolution failure → stop silently flooring to per_task, fail-loud per ADR-009; (B) volatile-value snapshot (`exceeds_bash_ceiling` derives from the learned coverage duration that grows suite-over-suite; same class Q-Gate caught in PLAN-32 232s→216s) → leaf re-resolves / advisory stamp / stable ceiling input. NOT mutually exclusive. D1 GATES. Disjoint from live PLAN-34/37/38 |

| 40 | PLAN-40-orchestrator-standard-hardening | WS-10 | staged — emittable (disjoint from live PLAN-39) | `persona-marshall-orchestrator/standards/orchestration-model.md` + `marshall-orchestrator/workflow/{orchestrate,analyze,decompose}.md` + `templates/plan-spec.md` + lesson `2026-07-21-22-001` (retired) + ⚠ possibly `phase-1-init` (D4 lifecycle half — SPLIT if confirmed) | **Operator-directed 2026-07-22, 3 aspects + a promotion.** D1 PROMOTE verify-before-implement from the transient lesson into the durable standard (verified: grep of the standard is EMPTY, it lives only as the active lesson = fragile); D2 EXTEND its scope beyond the failure MECHANISM to Expected-Surface + orchestrator sharpenings (both inferred, both falsified in PLAN-37); D3 PROACTIVE-EMIT — every landing analysis must end with the next ready-to-run command(s) as copy-paste or a blocked-reason; D4 SINGLE-SOURCE SPECS — one-line `task="implement {spec_path}"` with all carries IN the file (GATED HYPOTHESIS: phase-1-init records the task VERBATIM today so the lifecycle half SPLITS to PLAN-41 if the gate confirms it). **Written under its own practice; self-sufficient spec ⇒ one-line hand-off = a live demo of D4.** My recommended priority: FIRST of the 4 candidates |

**Not staged as local specs** (tracked in WS-02): consumer-repo `/marshall-steward upgrade`
migrations (operator-deferred, steward action, run one-at-a-time from inside each consumer repo).

## Decisions

- 2026-07-17 — Migrated the ad-hoc `.plan/plan-optimization/` ledger into the orchestrator store
  as epic slug `plan-optimization`, mirroring the plan-server migration precedent (all original
  files preserved verbatim at the tree root; plan specs merged into canonical `plans/`).
  `HANDOVER.md` remains the queue authority until a formal `decompose` populates status.json.
- 2026-07-17 — Decomposed into 2 workstreams: WS-01-wave2-cleanup (the 4 startable
  surface-disjoint plans PLAN-01..04) and WS-02-parked-deferred (PLAN-05 TT + ci-pr-safe-merge /
  consumer-migration pointers). status.json is now the queue authority; HANDOVER §4 superseded.
- 2026-07-17 — Renamed the 5 migrated spec docs from `plan-*.md` to canonical
  `PLAN-NN-{slug}.md` (pure non-destructive renames). Their internal legacy hand-off footers
  (referencing `.plan/plan-optimization/plans/...`) are now stale historical residue — the
  authoritative launch command is emitted fresh by `next`, so the footers were left unedited.
- 2026-07-17 — No split-guard trip: each of the 4 startable specs is already scoped below the
  ~6-deliverable presumption; no plan required splitting at decompose.
- 2026-07-18 — ci-pr-safe-merge parked plan VANISHED from the checkout (operator-verified: no
  active/orphaned/archived copy; refine state from session 2fbcd009 never persisted here). DECISION:
  re-init fresh (over locate-old-work / drop). The design is settled + do-not-re-litigate, so only
  the cheap-to-reconverge refine/outline state was lost. Persisted the settled design as
  `plans/PLAN-06-ci-pr-safe-merge.md` (durable seed in the epic tree, not just memory) and
  registered PLAN-06 in WS-02; hand-off is `action=init` seeded, NOT a resume.
- 2026-07-18 — Consumer (cui-open-rewrite) reported 2 upstream bugs from a first-run
  `/marshall-steward` wizard. Both were treated as untrusted-ingestion LEADS and INDEPENDENTLY
  VERIFIED against upstream source before recording: Bug 1 (`project set` no field-name whitelist,
  `_cmd_system_plan.py:152`) and Bug 2 (first-run wizard skips finalize-lane materialization,
  `_materialize_finalize_lanes` only in sync-defaults; wizard-flow Step 16 runs only steps-sort).
  DECISION: staged as new workstream WS-03 + PLAN-07 (2 deliverables, under split guard) — distinct
  theme (consumer-onboarding config integrity) from the wave-1-landings cleanup. Orchestrator does
  not fix; plan lifecycle owns it.
- 2026-07-18 — Same consumer surfaced 2 MORE upstream bugs (upgrade + merge-queue landing), both
  orchestrator-VERIFIED: (manifest) `find_installed_manifest_path` (`generate_executor.py:1085`) never
  searches the marketplace clone root → executor stamp blanked → `stamp_provisioning_fields:1159`
  overwrites a good `provisioned_version` with `''` → staleness FAILS OPEN (Re-Run Remediation Pass
  inert); (merge_group) `merge_group` absent everywhere in steward/ci → wizard enables the queue
  without verifying merge-group CI → bricks `main` (PR #106 stalled). DECISION: staged as PLAN-08
  (executor-manifest-resolution, 3 deliv) + PLAN-09 (merge-queue merge_group guard, 1 deliv) in WS-03,
  kept SEPARATE from PLAN-07 (distinct surfaces: executor/provisioning vs manage-config-validation vs
  ci-merge-queue) and each own high-severity landing. PLAN-09 shares the ci merge-queue surface with
  in-flight PLAN-06 → sequenced after it (or rebase).
- 2026-07-19 — analyze(full-ship): PLAN-14 #942 (`e2d0f45f8`) verified merged on main. Shipped-MODIFIED:
  premise re-grounded at outline (light→deep, operator's call) — the pre-push quality-gate is mypy+ruff
  only (no pytest), so PLAN-08's regression was never in its scope. Closed the REAL gap with a callable
  divergence seam (`_test_scope_divergence.py` + `resolve-test-scope`) + a finalize whole-tree
  module-tests gate (match-or-warn), not a doc warning. Local whole-tree could not run (marshalld inert +
  ~33-min build over harness ceiling) → degraded to loud warning, CI verified whole tree green ×2. Bots
  (Gemini/CodeRabbit) caught 2 real leaf-missed correctness defects → loop-back fixed. RESOLVED the
  scoped-vs-whole-tree watch; RETAINED lesson 22-001 (leaf-skips-pytest reinforced, re-homed as a watch);
  new lesson 16-002. **WS-04 COMPLETE.** status→shipped; 0 in flight, 5 staged (PLAN-19 now unblocked).
- 2026-07-19 — analyze(full-ship): PLAN-19 #944 (`f63649b49`) verified merged on main (CI abstraction +
  `git show --stat`: doc-only change to `branch-cleanup.md` +9/-5 + `enriched.json` deploy artifact).
  Shipped-MODIFIED: light-lane re-grounding found desired-outcome D (queue-enforced enqueue, no
  `--delete-branch`, no admin fallback) ALREADY implemented+tested at all 3 layers (doc/`cmd_pr_merge_queue`/
  argv-tests); the `:543`/`:707` spec citations were stale. Residual = 1 documentation deliverable making
  the Pre-Merge Confirmation Gate + auto-merge bypass authorization conditional on `use_merge_queue`.
  Review earned its keep: the plan fixed the interactive prompt but missed the sibling auto-merge-bypass
  authorization (`final_merge_without_asking=true` path) + the `(if <condition>)` convention →
  coderabbit TASK-003 + gemini TASK-002 → one loop-back → clean re-review. Validated END-TO-END: finalize
  enqueued #944 via `pr merge-queue` on this meta-project's genuinely queue-enforced main (queue re-tested,
  merged, platform auto-deleted head via `delete_branch_on_merge`) — strongest possible proof of D. One
  lesson folded into 05-002. status→shipped; 3 launched (PLAN-13/16/17), 1 staged (PLAN-18). **PLAN-18's
  release still gates on PLAN-13 + PLAN-17, NOT on PLAN-19 (D is independent) — but D is now proven live,
  so PLAN-18 inherits a working enqueue path when it lands.**
- 2026-07-19 — analyze(full-ship): PLAN-16 #945 (`a4ba622ec`) verified merged on main (CI abstraction +
  `git show --stat`: 6 files = D1 runtime `planning-outline.md` +106 & phase-4 SKILL.md +1, D2 static
  `_analyze_phase2_refine_contract.py` +159 + `_doctor_analysis.py`/`rule-provenance.md`/tests). Seam
  confirmed at outline = (b) phase-boundary clean-main assertion + static plugin-doctor complement
  (rejected Q-Gate + execution-context write-guard/PLAN-03 overlap). Both halves shipped; acceptance holds
  (planning-phase main edit blocked at boundary, worktree edit unaffected). No PLAN-11 phase-4 rebase
  conflict (predicted adjacency did not bite). RESOLVED the planning-phase-edits-MAIN watch (was graduated
  to PLAN-16). New lesson 22-001 (live marshalld contaminates build-queue unit tests) re-homed into the
  build-server watch; `step_record_mismatched_key` recurred again (now a very strong promote candidate).
  **WS-08 COMPLETE.** status→shipped; 2 launched (PLAN-13/17), 1 staged (PLAN-18).
- 2026-07-20 — analyze(full-ship): PLAN-13 #950 (`e45c7ac8f`) verified merged on main (CI abstraction +
  `git show --stat`: 23 files/+824 independently corroborating all 5 deliverables). **5/5
  shipped-as-specified — the epic's largest plan, and NEITHER split seam (D3-tail, D5) was needed, so the
  operator's recorded unsplit rationale held up.** D1 resolver highest-version-wins; **D2 verified LIVE on
  the real machine** (opened `regenerated` at identical versions → post-merge two consecutive `fresh`);
  D3 audit enumeration doc; D4 validated-write helper + structural test (ADR-009 already Accepted →
  `adr-propose` correctly emitted NO new ADR); D5 reload directive resolved per `runtime.target`, NOT
  Claude-hard-coded, per the operator's runtime constraint. RESOLVED 2 Open Defects (API-Sheriff resolver,
  folded reload feature) + 2 Watches (regenerate-every-run; META-PATTERN provisioning-fails-silent).
  **WS-03 COMPLETE.** Notable: local gates outperformed bots entirely (whole-tree caught a D5 test
  under-scope; self-review caught 3 real doc defects across 2 rounds; CodeRabbit clean; both gemini
  comments refuted as false positives) — reinforcing that this epic's value came from gates, not reviewers.
  2 dispatch deaths (lessons-capture, adr-propose) handled correctly via disk-state verification, no silent
  re-run. Operator action owed: `/marshall-steward` (marshal.json stamps stale 0.1.1152 vs 0.1.1159 —
  correct-by-design, never auto-mutated). status→shipped; **1 launched (PLAN-17), 1 staged (PLAN-18) —
  PLAN-18's {13,18} collision CLEARED, now gates ONLY on PLAN-17.**
- 2026-07-20 — analyze(full-ship): PLAN-17 #948 (`250f9a4ea`) verified merged on main (CI abstraction +
  `git show`: 2 files — `skip-on-docs-only: true` opt-in against the **v0.11.1** pin, corroborating the
  mid-finalize rebase over the concurrent #947 org bump, + CLAUDE.md). Re-grounding SHRANK the plan: D1
  and D2's pin had pre-landed and D3's ruleset move was done since 2026-06-23 — **but the feature was
  INERT** (`skip-on-docs-only` defaults false, nobody had opted in), so the residual was the opt-in + a
  doc fix. **Gate self-demonstrated mid-run** (docs-only push: `verify / verify` SKIPPED, `verify /
  conclusion` green). **WS-05 COMPLETE** (PLAN-11 local + PLAN-17 CI — the footprint-gating pair now
  closed at both layers). **Opened a NEW high-value defect**: this run released another plan's merge lock
  on an UNSOUND staleness inference (queried a worktree-scoped store, not the main checkout); no damage
  (#950 and #948 both merged cleanly) but the check was wrong and the tooling made it easy — inverse of
  PLAN-15 #940 (auto-reclaim hardened; manual-release path unguarded), same CWD-keyed store-resolution
  class as the manage-lessons hazard. Reinforced 13-21-001 (recurrence now SATISFIES its plan-worthy
  trigger) + 05-001. status→shipped. **ALL in-flight work is now DONE; PLAN-18 (the last plan) has NO
  remaining gate and is RELEASABLE.**
- 2026-07-20 — **decompose(survivors): modeled the 3 plan-worthy survivors into WS-10
  "Pipeline Integrity Hardening" as PLAN-20/21/22** (operator-directed: "model the 3 survivors to one or
  more plans as it fits best"). **Grouping rationale — the count was driven by surface disjointness, not
  by theme count:** ONE plan would be ~8 deliverables, well past the ~6 split presumption; FOUR plans
  (splitting PLAN-20's leaf-verification and step-key halves) would put both halves on the
  execution-manifest surface, creating an adjacency that forces sequencing; **THREE is the only shape
  where all are mutually surface-disjoint and can run in parallel** — PLAN-20 (phase-5 leaf verification +
  step-record/manifest), PLAN-21 (`github_pr.py`/`_ci_barrier.py`/`enabled_bots`), PLAN-22
  (`manage-locks`/store-scope). Each is 3 deliverables, all under the split guard. Retired 1 Open Defect
  (merge-lock staleness → PLAN-22) and 2 Watches (`step_record_mismatched_key` n=5 → PLAN-20 D2;
  leaf-skips-pytest n=3 → PLAN-20 D1) plus the 13-21-001 defect + 05-001 lesson + gemini-prune note →
  PLAN-21. Also reconciled WS-03/05/08 `active`→`complete` (their plans had all shipped).
  **⚠ Thematic drift RECORDED for the close decision:** WS-10 is pipeline-correctness work, NOT the
  epic's original token-usage-optimization Vision — staged here for ledger continuity (the recurrence
  history lives in this epic's Watches), but WS-10 is a clean seed for a successor epic and can be
  migrated intact if the operator prefers a hard boundary. Epic close is consequently deferred beyond
  PLAN-18.
- 2026-07-20 — analyze(observation → 2 plans): operator surfaced the `search-markers` vacuous-gate defect
  with a full structural analysis, plus a second independent defect in the same bundle. **Every technical
  claim VERIFIED against source before staging** (regex tested empirically: shipped pattern matches
  NOTHING, fixed pattern extracts correctly; exit path confirmed at `:154`; both build-maven AND
  build-gradle consumers confirmed). **Orchestrator found the defect is WORSE than reported: the ~40-test
  suite pins the bug** — every test hand-writes the broken `)>*/` form, so it cements the defect rather
  than catching it; fixing the regex breaks ~30 tests and a naive fixer could revert the fix. This makes
  the operator's "pin with a fixture" the load-bearing item AND sharpens it: the fixture must be
  **provenance-bearing** (captured from real cui-rewrite output), because hand-written fixtures are
  precisely what produced the defect. Also found an unnamed surface: `extension-api`'s
  `build-api-reference.md` declares `search-markers` as build-API contract, so relocation is a CONTRACT
  change, not a file move. **Modeled as TWO plans** (PLAN-23 marker ownership+fixture, PLAN-24 maven
  truthful status) per the operator's "needs its own entry" — they are ADJACENT on `maven.py` but in
  different regions (subparser registration vs `run` status derivation), so a trivial rebase is expected
  and both stay parallel-startable. Item 3 (narrow build-maven to log-only) recorded as a **deferred
  decision Watch** blocked on cui-open-rewrite#116, with the "do NOT delete tree scanning" rationale
  preserved. PLAN-24's symptom is operator-reported and NOT orchestrator-reproduced — its D1 is
  reproduce-and-root-cause, explicitly forbidding a fix on the verified-but-unconfirmed mechanism.
- 2026-07-20 — analyze(full-ship): PLAN-18 #952 (`464f53ec1`) verified merged on main (CI abstraction +
  `git show --stat`: 10 files/+381 corroborating all 4 deliverables incl. 2 new test files). **A's central
  premise was FALSE** — bypass-actor support already shipped; refine verified A against the stale
  `github-impl.md` doc and passed it through, outline caught it against `github_ops.py` source and rescoped
  A to D1. B/C shipped as specified; steward flow decomposed; never-mutate-foreign verified. **Fitting E2E:
  the merge-time probe reported `externally_managed: true`** — D2 classifying the org queue it was built to
  coexist with. Pruned gemini (sunset 07-17) caught a real `setdefault` None-key bug (vindicates
  never-ignore-pruned-bot → sharpens PLAN-21 D3). **WS-09 COMPLETE — the epic's original Wave-2 queue is
  fully DRAINED (PLAN-01..19 all shipped/resolved).** Opened 2 new Watches (adr-propose lane-vs-manifest
  precedence; CI-wait-budget-too-small) + reinforced the docs-drift meta-pattern (5th confirmation → new
  lesson "verify behavioural claims against source not standards docs" → folds toward PLAN-25 D4). **Owed
  operator action COMPOUNDED: `/marshall-steward` + session restart** (PLAN-13 marshal.json debt STILL
  unpaid + executor regenerated + commits bumped to 0.1.1162). **Epic now holds ONLY WS-10** (6 staged
  follow-ups PLAN-20..25); close deferred until WS-10 drains, when the WS-10-migration decision is due
  (WS-10 outgrew "survivors" — pipeline correctness + plugin architecture, a strong successor-epic seed
  distinct from the token-optimization Vision).
- 2026-07-20 — analyze(observation → 1 plan): operator surfaced (screenshots) the terminal TAB TITLE
  freezing at an early phase (`2-refine`/`4-plan`) while the FOOTER is correct. **Root cause VERIFIED via
  source survey:** title and footer share `compose()`+`status.json` but DIVERGE at delivery — footer rides
  the continuously-polled `statusLine` (fresh), title only repaints on turn-boundary hooks + a `/dev/tty`
  write that silently no-ops off the controlling terminal (sub-agent/worktree/bg, i.e. phase-5/6). Within
  one long multi-phase turn the title has no reliable refresh → freezes. NOT composition/dedup/#931's
  build-busy logic. No test covers footer/title consistency (the shipping gap). Staged **PLAN-26** in WS-10
  (3 deliv: footer-equivalent cadence + kill the silent no-tty no-op + consistency regression test);
  D1 needs a claude-code-guide consult at outline (can `statusLine` carry a `terminalSequence`). Disjoint
  from all other WS-10 plans. WS-10 now 7 plans (PLAN-20..26) — further evidence it is a successor epic,
  not a survivor tail; the migration call at close grows more clearly "yes".

## Open Defects

Tracked in the migrated `HANDOVER.md` §4/§5 (Wave-2 defects fold into the four staged plans) and
`lessons-findings-queue.md`. Not yet transcribed into this section.

**Open — PLAN-04 dropped-to-follow-up (anti-orphan re-home, source: PLAN-04 #930):** the scope-bloat
guard correctly dropped two candidates out of PLAN-04; re-homed here so they are NOT orphaned:
- **4a — `*_without_asking` config key rename** (deferred from PLAN-04). Small doc/config-contract
  follow-up. Candidate fold into a future docs-contract micro-plan or PLAN-10's WS-04 barrier work if
  a knob-rename touches the same surface. Plan-worthy on its own if it grows.
- **4b — `blocked_user_review` halt→ASK conversion** (deferred from PLAN-04). A behavior question
  (should the halt become a real ASK gate?), not just docs — needs its own outline if pursued. Held
  until the operator decides it's wanted; do NOT let it vanish silently.
- ~~**bot-agnostic rate-limit filtering**~~ — **GRADUATED to PLAN-21 (WS-10)** 2026-07-20, together with
  lesson `2026-07-18-05-001` and the gemini-prune note. No longer an open defect — owned by a plan.
  (source: PLAN-10 #936 residual, lesson `2026-07-13-21-001`) — PLAN-10 dropped the CodeRabbit-specific rate-limit notice only; a Sourcery
  weekly-rate-limit notice was still filed. A bot-agnostic rate-limit classifier is the genuine
  follow-up. **RECURRED at PLAN-17 #948** (a Sourcery rate-limit notice again stored as an actionable
  finding, suppressed BY HAND) — "plan-worthy on recurrence" is now SATISFIED. Fold into the successor
  plan. Also recurring alongside it: **lesson `2026-07-18-05-001`** — automatic-review's D3 completeness
  guard fires `loop_back` on findings pending for the not-yet-run unified triage, and sunset **gemini had
  to be pruned from `enabled_bots` per-plan** again to break the loop (the standing project-wide prune
  note still applies — see [[feedback_infra_steps_must_be_opt_in]]).

**✅ RESOLVED by PLAN-13 #950 (`e45c7ac8f`) — consumer-surfaced (API-Sheriff, 2026-07-19):** stale cache-root
`dist-manifest.json` permanently shadows the marketplace-root manifest → the staleness signal fails
**silent-fresh** (not fail-closed). Corroborated at `generate_executor.py:1156-1159`: the candidate loop
is first-hit-wins, and candidate 3 (cache root, `base_path/dist-manifest.json`, line 1127) is appended
BEFORE candidate 4 (marketplace clone root, line 1152) with NO version/recency comparison. A leftover
cache-root manifest (0.1.1144) beats the authoritative clone-root manifest (0.1.1152) forever. **This is
a PLAN-08 (#934) residual** — #934 ADDED candidate 4 but placed it after candidate 3, so it only helps
when the cache copy is absent. Poisons the whole staleness chain (resolver→executor stamp→provisioned_version
→preflight all read the same stale source → self-consistent, can never detect its own lag). Currently
harmless by luck (only `version`/`source_sha` differ 1144→1152; `executor_changed_at_version`/
`config_changed_at_version`/`config_seed_fingerprint` byte-identical) — but the next release that bumps
either `*_changed_at_version` silently misses the executor-regen / config-reconcile. **Fix (resolver-level,
preferred):** collect ALL existing candidates and pick the highest `version` (parse-and-compare, not
first-hit-wins) + regression test with two manifests at differing versions. Same **fail-silent-fresh class
PLAN-13 is chartered to sweep + fail-close** — this is PLAN-13's concrete highest-value boundary.
**→ FOLDED into PLAN-13 as D1** (operator-directed 2026-07-19), avoiding a `generate_executor.py` collision
and keeping PLAN-13 in the emitted parallel triple. **SHIPPED in #950**: resolver now collects all
candidates and picks the highest `version`; two-manifest-at-differing-versions regression test locks it.
Fail-closed (`unknown`) still holds when none is resolvable. Defect CLOSED.

**✅ RESOLVED by PLAN-13 #950 — folded feature: single-command upgrade + plugin reload (operator 2026-07-19):**
`/marshall-steward upgrade` regenerates executor/agents that are session-pinned at session start, so today
it demands a full restart. Claude Code supports in-session reload via **`/reload-plugins`** (reloads
plugins/skills/agents/hooks; only *monitors* need restart, plan-marshall uses none). Hard constraint:
`/reload-plugins` is a harness-level user-typed command — a script CANNOT invoke it — so the achievable
shape is "upgrade does the work, then emits the harness-resolved reload directive." Per operator, MUST land
in the runtime (harness-agnostic), interface adapted. **→ FOLDED into PLAN-13 as D5** (operator chose fold
over its own plan). New `platform-runtime` op resolving Claude=`/reload-plugins` vs opencode/other=
equivalent/no-op, + adapt steward upgrade interface + the "Session Restart Required" SKILL section.
**SHIPPED in #950**: the `platform-runtime` seam (`contract.md`, `runtime_base.py`,
`_claude_runtime_impl.py`, `opencode_runtime.py` + per-target tests) resolves the directive from
`runtime.target` — NOT hard-coded to Claude, exactly as the operator constrained — and the steward
`upgrade` interface + SKILL section emit it instead of a blanket restart. The separability escape hatch
went unused. Feature CLOSED.

**→ GRADUATED to PLAN-22 (WS-10), 2026-07-20 — no longer an open defect, owned by a plan.** (source:
PLAN-17 #948 in-run): **merge-lock staleness judged from a WORKTREE-SCOPED store.** The PLAN-17 run released `steward-provisioning-fail-closed`'s merge lock after
`manage-status list` and `worktree-list` returned nothing — but both ran with **cwd pinned to the
releasing plan's own worktree**, so they saw only a worktree-local store view. That plan was LIVE in
another session and landed as #950. **No damage** — disjoint files, `no_overlap`, both merged cleanly
(orchestrator-confirmed: #950 `e45c7ac8f` and #948 `250f9a4ea` are both on main) — **but the check was
unsound, and the tooling made the wrong answer the easy one to reach.** A staleness test MUST query the
MAIN-CHECKOUT store, never a worktree-scoped view. Same **CWD-keyed store-resolution class** as the known
`manage-lessons` cross-repo hazard (a store resolved by CWD/git-common-dir silently answers about the
wrong scope). **Inverse of PLAN-15 #940**: that hardened the *auto-reclaim* live-worktree gate; this is
the *manual release* path, which has no equivalent guard — `release-under-holder-id` exists, but the gap
is the staleness **inference** that precedes it. **Plan-worthy**: wants both a lesson and a `merge_lock`
guard (e.g. refuse/warn when the staleness query's store scope is not the main checkout). Strong
candidate for the successor plan alongside the two co-strongest watches.

**⚠ OPEN — ARCHITECTURAL (operator, 2026-07-20): no plugin concept for DOMAIN-CONDITIONAL loading;
domain specifics leak into the CORE.** Surfaced while scoping PLAN-23's relocation. **CONCRETE INSTANCE
folded 2026-07-20 (cui-open-rewrite datapoint) → PLAN-25 D5:** `manage-config configure` seeds
`default:verify:arch-gate` gated ONLY on domain-extension presence (`_cmd_skill_domains.py:908-909`;
pm-dev-java declares `provides_arch_gate()` → seeded) but the step resolves at compose via `architecture
resolve --command arch-gate` against the MODULE's commands — a Maven module with no `arch-gate` command →
unresolvable → BLOCKS compose. The seed (domain-level) and resolve (module-command level) disagree. The
agent's "no implementor anywhere" was WRONG (pm-dev-java:arch-gate-java exists, java active); the real
defect is seed-vs-resolve mismatch. Manual `remove-step` is NON-DURABLE (next `configure` re-seeds). This
is the concept's flagship worked example — grounds D1's visibility ADR (skip-with-warning vs silent drop)
and D4's inventory. The concrete instance:
cui-openRewrite marker handling belongs to `marketplace/bundles/pm-dev-java-cui` and should be in play
ONLY when that skill/domain is active — yet today the cui specifics (`AUTO_SUPPRESS_RECIPES` naming
`CuiLogRecordPatternRecipe`/`InvalidExceptionUsageRecipe`, the marker parser, and a `search-markers` verb
declared in the core build-API contract) sit in the CORE `plan-marshall` bundle, unconditionally present
for every consumer regardless of domain. **This is the general shape, not one file:** a "loading filter" /
domain-gated activation concept is missing, so domain content has nowhere to live except the core.
**Relationship to PLAN-23 (settled 2026-07-20): PLAN-23 does NOT block on this and this does NOT block on
PLAN-23.** Relocating the marker detector to its format-owner is a *precondition* for domain-gated
activation, not a competing approach — and the gate is broken NOW (a consuming repo had three markers
committed on main while the tool reported clean), so the fix cannot wait on a new architectural concept.
PLAN-23's D1 carries an explicit constraint to use the simplest existing seam and **name it in the
landing**, so this concept generalizes from a REAL instance rather than a hypothetical.
**→ GRADUATED to PLAN-25 (design-first) 2026-07-20 after an orchestrator survey.**

**Survey result — mostly GENERALIZATION, two genuinely NEW pieces.** Domain-conditional activation
already exists and is pervasive, but it gates **knowledge/skills, not scripts/verbs**:
- *Already domain-conditional* (generalizable): `resolve-workflow-skill-extension --domain {d} --type {}`
  with a **null-on-absent** contract; `extension_discovery.find_implementors()` with
  `default_on`/`presets`/`source`; `discover_applicable_extensions()` as the bundle-relevance predicate;
  and the activation SIGNAL itself — `_cmd_domain_detect.py`'s `detector ∪ always_on ∪ glob_matched`
  persisted to `references.domains`.
- *Genuinely NEW*: (1) **build verbs from domain bundles** — `ext-point-build.md` mandates
  `skills/build-{tool}/` under the CORE bundle and all 4 build skills are core-owned, so a domain bundle
  structurally CANNOT own an executable verb (this is why the marker detector had nowhere to go);
  (2) **domain-aware notation exposure** — `generate_executor.py` has **zero** `domain`/`skill_domains`
  references and registers every script of every installed bundle unconditionally. Nothing to generalize.
- **Core→domain reverse dispatch is ESTABLISHED** (`ext-triage-{domain}` ×7, `arch-gate-{domain}`,
  `ext-self-review-plan-marshall`, `provides_outline_skill`) — but **every one contributes a SKILL/markdown
  surface, never a SCRIPT**. The lone script-level workaround is `ext-point-self-review-surfacing`'s
  "first implementor whose notation resolves in the current executor, else zero-generator fallback" — a
  resolvability probe, not real gating.

**⚠ Consequence for PLAN-23, recorded:** because the executor is domain-blind, **relocation ALONE does
NOT achieve domain-gating** — post-move the detector is still exposed to every consumer, merely under a
`pm-dev-java-cui:*` notation. PLAN-23's honest achievement is **ownership inversion** (the format and its
recipe map live with the recipes that define them, so the next format change has an owner and a test),
NOT activation gating. PLAN-23's spec was corrected to say so and to prefer the existing
resolve-or-degrade seam.

**Retired by landings:**
- ~~docs-only/design-first plans STILL run the full phase-5 build (P4-C1 wiring survivor)~~ —
  RESOLVED by PLAN-01 D1 (#926), `request_aspect` consumer self-read wired into the aspect-step-drop.
- ~~`execution_tier=orchestrator` guard misses the INITIAL phase-5 envelope (#897 gap)~~ — RESOLVED
  by PLAN-01 D2 (#926): found already-closed by total `step_execution_tier` stamping, locked with a
  regression test + stale-marker retire.

## Watches

- ~~**`adaptive-build-timeout-false-timeout`**~~ — **GRADUATED to PLAN-32 (WS-10)**, 2026-07-21. No
  longer a watch: owned by a plan. Escalated from soft watch on PLAN-28 #962's hard numbers
  (`1868 passed in 62.47s` reported as `status: timeout`; later run 103s vs a ~120s budget), then
  promoted the same session once orchestrator investigation found **two** verified root causes —
  the pytest-timeout/wrapper **bound inversion** (a partial regression of plan-server PLAN-03
  #949) and the **pytest-internal-vs-wall-clock** observation-surface defect. Note the initial
  framing "the budget is simply too short" was WRONG and was corrected before staging: adaptive
  learning already self-heals by doubling. See `plans/PLAN-32-truthful-build-timeout-accounting.md`.
- **⚠⚠ VERIFY-BEFORE-IMPLEMENT is the epic's highest-value spec instruction — n=2 consecutive**
  (NEW 2026-07-21). PLAN-24 #963: *"D1 reproduce+root-cause, do NOT fix on the hypothesis"* — the
  spec's `success_result()` mechanism was **falsified**; the real defect was two `_build_shared.py`
  call paths. PLAN-26 #964: *"D1 needs a claude-code-guide consult at outline"* — the spec's
  `statusLine`-carries-`terminalSequence` mechanism was **falsified**; `statusLine` cannot carry
  OSC-0 and the real gap was a matcher-scoped render hook. **In BOTH cases the symptom analysis
  was RIGHT and the proposed mechanism was WRONG, and in both the explicit verify-first
  instruction is what prevented fixing the wrong thing.** Candidate promotion to standing
  guidance: *any spec whose mechanism is orchestrator-INFERRED rather than observed MUST carry an
  explicit verify-first instruction.* Applies live to **PLAN-32 D1** and **PLAN-23**.
- **⚠ Composed-manifest snapshot: a step-ordering fix on main does NOT reach in-flight plans**
  (NEW 2026-07-21, PLAN-24 #963 + PLAN-26 #964, **n=2 confirmed**). PLAN-26's manifest scheduled
  `lessons-housekeeping` at **position 18 (post-merge)** despite its `order: 4` declaration,
  because the manifest was composed before #962 — the very PR that moved it into the settle band.
  Handled BETTER than PLAN-24's case: run **classify-only** as a deliberate workaround, and it
  happened to have nothing to promote, so no harm. **PLAN-30 (composed pre-#962) may hit it;
  PLAN-32 (composed post-#962) is the CONTROL — if PLAN-32 strands, escalate, do not file as
  expected.** Original PLAN-24 detail: PLAN-28 (#962) moved `lessons-housekeeping` into
  the pre-merge settle band, landing at `cd931fb63`. PLAN-24 merged 23 minutes later at
  `c865a2938` — but its manifest had been **composed before** that, so it still carried the OLD
  post-merge ordering and its promotion edit could not ride the already-merged PR. Correct
  disposition taken (stranded edit reverted, follow-up lesson `2026-07-21-15-002` filed per
  `source-edit-pushability.md`, nothing pushed unreviewed). **This validates PLAN-28's fix and
  simultaneously exposes its migration boundary.** Every plan whose manifest predates `cd931fb63`
  is affected — **PLAN-25 / PLAN-26 / PLAN-30 were all in flight at that moment.** Expect the
  same stranding on their finalize runs; it is EXPECTED behaviour, not a new defect, and the
  correct response is the same revert-and-file-follow-up path. Owed: re-run the deferred
  promotion of `2026-07-21-14-002` via a normal plan.
- **⚠ Review bots' best findings keep landing in the plan's OWN new guard code — n=3, with a
  COUNTER-EXAMPLE** (updated 2026-07-21). PLAN-26 #964 broke the streak: 3 findings, 2 fixed 1
  declined, **none in its own new code**. Discriminating factor worth testing: PLAN-26's new code
  is delivery/observability *plumbing*, whereas PLAN-20/24/28's was *correctness guards* — new,
  unexercised, and trusted. The watch may be specifically about **guards**, not about new code in
  general. Original n=3 detail: PLAN-20: `canonicalize_step_key` non-idempotence in D2's own new code.
  PLAN-28: a self-contradictory sentence in the contract that plan authored. PLAN-24: the D2
  truthfulness guard was itself untruthful — checking a tautologically-zero `exit_code` never
  forwarded, and misfiring on explicit `None`. **A structural guard is the highest-risk artifact
  a plan produces**: it is new, unexercised, and trusted. Candidate standing instruction — a plan
  that authors a guard must exercise it against a *known-bad* input before finalize, not only
  against the case it was written for.
- **Recurring bot-infrastructure red has no cheap-recurrence triage path** (NEW 2026-07-21,
  PLAN-28 #962, n=1). CodeRabbit's check was red on all three HEADs with **no `run_id`, no log, no
  timestamps** while every required check was green — a bot-infrastructure signal, not a code
  finding. The contract's default is a full triage envelope per occurrence (~150k tokens); the plan
  triaged the first fully then resolved the two identical recurrences inline, an **operator-flagged
  deviation the orchestrator endorses** (identical, already-diagnosed signal). The gap is
  structural: nothing lets an already-triaged bot-infra signal be cheaply re-dispositioned at a new
  HEAD. Fold into PLAN-31 or a future review-barrier plan; do NOT stand alone.
- **Landing-record completeness depends entirely on the hand-off** (NEW 2026-07-21, PLAN-24 #963,
  n=1). PLAN-24 merged without its narrative ever reaching the orchestrator; the merge was
  discovered incidentally while verifying PLAN-28's landing. The resulting `landings/PLAN-24.md` is
  diff-grounded only — no metrics, no review detail, no finalize-step outcomes, because none were
  ever observed. **Nothing currently detects a merged PR whose plan never reported in.** Cheap
  mitigation: have `status`/`analyze` cross-check `launched` queue rows against merged PRs on main
  (the orchestrator did this by hand this session). Consider folding into PLAN-30/PLAN-31's
  orchestrator-surface work.
- **Sunset-flagged gemini keeps producing real findings — n=5 consecutive** (updated 2026-07-21).
  PLAN-24 #963: **2/2 actionable, 100% resolved-as-fixed**, both in the plan's own guard. PLAN-28
  #962: a genuine internal inconsistency (ext-point membership test not filtering `#` comments
  while the key-parse loop two lines below did). Prior: PLAN-20 #961 (canonicalize
  non-idempotence), PLAN-22 #959 (2 fixes applied inline). The standing rule — *a pruned bot can
  still post a valid finding, don't ignore it* — is now empirically load-bearing, not cautionary.
  **At n=5 with a 100%-actionable landing, the sunset decision itself deserves revisiting.**
- ~~Roadmap token-efficiency +36% trend (08-001)~~ — **RETIRED** 2026-07-18: the token-optimization
  roadmap it belonged to is CLOSED (#899); no longer an actionable watch.
- ~~Aspect-classifier false positive on narrative-about-a-bug~~ — **RETIRED** (mooted by PLAN-11 #938):
  the run-time footprint gate (`build-decision`) is now the authority for whether phase-5 actually
  builds, so a wrong NARRATIVE aspect no longer drives the real build decision either way. aspect-classify
  kept pure; the two signals reconciled as complementary. No longer a live risk.
- ~~**`step_record_mismatched_key` — n=5**~~ — **GRADUATED to PLAN-20 (WS-10) as D2**, 2026-07-20. No
  longer a watch — owned by a plan. (sources: PLAN-11 #938 automatic-review; PLAN-16 #945 merged a
  mark-step-done key-form-mismatch into `2026-07-13-12-003` — project:/default:-prefixed finalize steps
  record under a key mismatching the manifest `step_id`) — a recurring step-key mismatch. n=5 is now VERY
  high — **strongest promote candidate on the board** (finalize step-key hygiene plan). Promote at the
  next watch review or fold into a finalize-hardening plan (WS-04). Do NOT let it keep recurring silently.
- **No-op-close hand-driven `worktree-remove` deletes plan bookkeeping** — **HANDED to the plan-server
  epic** (`../plan-server/`) worktree-context-resolution cluster (same class as its inherited defects
  + P1 #914's move-back guard). Not a plan in THIS epic. (source: PLAN-03 teardown,
  n=1) — hand-driving `git-workflow worktree-remove` from inside a zero-diff worktree errored
  (`[Errno 2]`) but removed the git worktree BEFORE the move-back, deleting the plan's status.json /
  solution_outline.md / metrics.md. Substantive output (the lesson) survived only via the main
  corpus. SAME worktree move-back-ordering class as P1 #914's guard and the plan-server epic's
  inherited worktree-context-resolution defects. Mitigation (recorded): for a zero-diff close, run
  the real phase-6-finalize (owns correct move-back→remove ordering) or move the plan dir back to
  main FIRST. Plan-worthy on recurrence, or fold into a future finalize/worktree plan.
- **Premise-lossy tail — evidence #7** (source: PLAN-03) — refine falsified both PLAN-03 headline
  datapoints against shipped code (work already done), joining the six §5 tail plans. Reinforces
  "do NOT make refine conditional." The no-op audit is the system working: refine caught a stale
  spec before ~1M tokens of wasted implementation.
- ~~Stale merge-lock recurring (~n=5 across the epic)~~ — **RESOLVED by PLAN-15 #940** (`ff0c109e7`).
  Root cause was ONE predicate: `holder_has_live_worktree`'s bare `worktree_dir.exists()` let an
  orphaned/empty worktree shell masquerade as mid-recovery. Now requires a concrete marker (`.git`
  gitdir link or live plan dir) → orphaned shells auto-reclaim, genuine mid-recovery protected. Expect
  the class to stop recurring once #940 is in the running cache. (`holder_is_dead` was already correct —
  the spec's citation was re-grounded at outline.)
- ~~**`preflight` reports `executor_action: regenerated` on EVERY run**~~ — **RESOLVED by PLAN-13 #950 D2,
  VERIFIED LIVE** (not just fixture-tested): the #950 session OPENED with preflight reporting
  `executor_action: regenerated` at identical versions — the exact defect — and after the merge two
  consecutive preflights both report `fresh`. Regen now prunes superseded version dirs, so the
  multi-version-pollution trigger no longer survives its own remedy. Original detail retained below.
  (source: API-Sheriff 2026-07-19,
  likely SEPARATE from the resolver defect above) — not version staleness (executor_version ≥
  executor_changed_at_version) but the multi-version-cache-pollution trigger: 4 version dirs present
  (`cache/plan-marshall/plan-marshall/{0.1.1131,1137,1144,1152}`) and regen does NOT prune superseded
  dirs, so the trigger survives its own remedy and the signal never clears. Related to the plugin-cache
  orphan-GC / multi-version-PYTHONPATH surface (7-day orphan GC exists but does not prune version dirs on
  regen). OPEN QUESTION: should regen prune superseded version dirs, or should the pollution check be
  advisory-once rather than regenerate-every-time? **→ FOLDED into PLAN-13 as D2** (operator-directed
  2026-07-19). NOT the same fix as the resolver ordering (D1) — a distinct deliverable within PLAN-13.
- ~~**Phase-5 leaf verification runs mypy+ruff+compile but NOT pytest**~~ — **GRADUATED to PLAN-20
  (WS-10) as D1**, 2026-07-20 at n=3. No longer a watch — owned by a plan. (source: PLAN-14 #942 in-run —
  lesson `2026-07-18-22-001` RETAINED, reinforced not closed) — PLAN-14 fixed the *finalize gate*
  (whole-tree module-tests divergence seam), but its OWN leaf shipped 2 real correctness defects (bot-caught,
  loop-back-fixed) precisely because per-task verification never ran pytest. The deeper facet — a leaf's
  per-task verification must run the tests it can break, not just type/lint/compile — is a standing gap the
  finalize gate does not close. Watch; plan-worthy on recurrence (candidate WS reopen or fold into a
  future verification-hardening plan). Related: new lesson `2026-07-19-16-002` (footprint classifier must
  fail-safe at boundaries). **n=3 as of PLAN-13 #950** — whole-tree module-tests caught a D5 base-class
  test under-scope that per-task testing missed. Third independent confirmation (PLAN-14, PLAN-16,
  PLAN-13). The good news: PLAN-14's whole-tree finalize gate is what CAUGHT it each time — the gate
  works, the leaf is still the hole. **Now co-strongest promote candidate with `step_record_mismatched_key`.**
- ~~Scoped quality-gate blind to a whole-tree regression~~ — **RESOLVED by PLAN-14 #942** (`e2d0f45f8`).
  The finalize whole-tree module-tests divergence gate (callable seam, match-or-warn) now catches a
  scoped-green / whole-tree-red change at finalize. Premise re-grounded at outline (pre-push gate was
  mypy+ruff only). Same scoped-vs-whole-tree class PLAN-02 #927 D1 fixed for plugin-doctor.
- **Harness instability across the epic (NOT a plan-marshall defect — infra)** — recurring through the
  wave: `run_in_background` build kills (0-byte, externally-killed; PLAN-01/04/08) AND dispatched
  execution-context agents dying on stream-idle timeouts (PLAN-09 → phases 5/6 driven INLINE). Every
  dispatch completed its on-disk work before the stream died (nothing lost), but it inflates wall time
  and forces inline fallback. Same class as [[project_background_jobs_killed_by_harness]] (#912
  mitigation). No epic action — recorded so the wall-time inflation and inline-drive fallbacks across
  these landings are attributed to infra, not to the plans.
- ~~Planning-phase edit of the MAIN checkout (n=2)~~ — **RESOLVED by PLAN-16 #945** (`a4ba622ec`). The
  invariant is now ENFORCED, not reactive: `planning-outline.md` refuses the 3-outline→4-plan and
  4-plan→5-execute transitions on a dirty main checkout (`outline/plan_contract_violation`), with a
  static plugin-doctor complement. Absorbs the planning-phase class of 17-001 (#920) + `2026-07-18-13-002`
  (PLAN-05). The phase-5-execution occurrence `2026-07-17-17-001` is OUT of scope and retained.
- ~~`pre_merge_comment_barrier` vs trigger-A re-review-comment churn~~ — GRADUATED to **PLAN-10**
  (WS-04 finalize-barrier-hardening), lesson `2026-07-18-14-002`, relates to open `2026-07-13-21-001`.
  Verified surface: the github noise pre-filter doesn't drop self-authored trigger comments / rate-limit
  notices. No longer a watch — owned by a plan.
- ~~META-PATTERN: steward provisioning FAILS OPEN / FAILS SILENT (4 bugs)~~ — **RESOLVED by PLAN-13 #950**
  (`e45c7ac8f`). Graduated to PLAN-13 and now shipped 5/5: the surface was swept and ENUMERATED
  (`provisioning-fail-closed-audit.md`), the invariant encoded ONCE as a validated-write helper +
  structural test (D4, tied to ADR-009 which was already Accepted), and the two concrete fail-silent-fresh
  sites fixed (D1 resolver, D2 regen-prune). A new silent-success / vacuous-default provisioning write is
  now caught structurally, not only by a reviewer. **The systemic answer this epic's WS-03 was chartered
  for is complete — WS-03 COMPLETE (PLAN-07/08/09/13).**

- **⚠ BUILD SERVER not in the build path (operator-requested verify, 2026-07-19)** — marshalld daemon
  IS running (PID 6973, `manage-build-server/scripts/marshalld.py run`) and registered plan-marshall,
  BUT `~/.plan-marshall/marshalld/registry.json` shows EMPTY `worktree_containers` + `notation_allowlist`
  and `job-logs/` is EMPTY → **zero build jobs routed through marshalld**; the plans build INLINE. The
  audit logs show only the daemon `start` + an empty `register` — no per-build "all infos" because no
  jobs were dispatched. (Distinct from `build-queue.json` = manage-locks merge-lock FIFO, which IS
  working — `run_log` populated.) **NOT working as designed.** This is a **plan-server epic** defect
  (build server is their component) — HAND there, not fixed in this epic. Bears on PLAN-11's
  landing-verify: "account for active marshalld" resolves to marshalld NOT being in the build path.
  **(Separately, 07-19: a `python3.14` crash report the operator pasted is NOT marshalld — it's an
  x86_64/Rosetta HOMEBREW python (`/usr/local/Cellar/python@3.14/3.14.0_1`, missing dylib) under the
  IntelliJ coalition; marshalld runs the python.org `/Library/Frameworks` build and is alive. Do not
  conflate the two.)** **(Also 07-19, PLAN-16 #945 in-run: a live+registered marshalld makes the
  script-shared build-queue UNIT tests spuriously fail in a whole-tree run — the tests route real builds
  to the daemon. NOT a regression, reproduces on main; the runner stopped the daemon for clean runs and
  restarted it. Lesson `2026-07-19-22-001`. Test-isolation facet owned by the plan-server epic, not this
  one — recorded so future whole-tree runs stop the daemon first.)**

- **DEFERRED DECISION — narrow build-maven to log-only? Blocked on cuioss/cui-open-rewrite#116**
  (operator-directed 2026-07-20; deliberately NOT folded into PLAN-23). #116 requests that recipes log
  each finding with path and position and emit a warning for **every pre-existing marker**. **If #116
  lands:** log parsing can answer "are markers present in the tree?" (presence would be re-reported on
  every build, not only the build that introduced a marker), tree scanning demotes to a fallback, and the
  java-cui component gains a log-parsing mode. **If it does not land, or lands partially:** tree scanning
  remains primary. **Scope caveat carried from #116:** its "existing Changes have been made to …"
  reporting arguably belongs to `rewrite-maven-plugin` rather than the cui recipe set, so part of the
  request may be redirected upstream. **Neither outcome changes PLAN-23's D1/D2/D3** — which is why the
  decision is deferred: it is cheaper to make once the outcome is known.
  **⚠ Do NOT delete tree scanning even if #116 lands fully** — two cases stay uncovered: (a) checking a
  tree WITHOUT running a build (a cheap pre-commit hook, or a checkout never built — log parsing needs a
  full build, ~3 min observed), and (b) a build that fails BEFORE `rewrite:run` executes (e.g. a compile
  error): no findings logged, but markers may be present. Tree scanning is the cheap, build-independent
  check, not a redundant one. **Governing convention it serves: never commit code with markers present —
  a property of the TREE**, which is why a tree-state detector matters at all. Revisit when #116 resolves.

- **NEW (PLAN-18 #952) — `adr-propose` lane-vs-manifest precedence gap:** `adr-propose` carries
  `lane: off` yet the composer still emits it into the manifest; the run honoured the opt-out manually. A
  lane opt-out the composer ignores is a real precedence defect (lane knob should win over manifest
  emission). Plan-worthy on recurrence — candidate fold into PLAN-20 (execution-accounting) or a
  config-precedence item. Logged in the run.
- **NEW (PLAN-18 #952) — CI-wait budget (600s) too small for this repo:** consistently exceeded by the
  ~13-min verify job, so every CI wait costs two polls. Cheap tune (raise budget or make adaptive, cf.
  plan-14 adaptive `ci:wait` #877). Act on convenience; not blocking.
- **Docs-drift meta-pattern — CONFIRMED a 5th time (PLAN-18 #952):** the spec's central premise (A) was
  true of the standards doc, false of the code; refine trusted the doc, outline caught it against source.
  Same shape as PLAN-06/14/17/19's stale-citation re-grounds. New lesson: **verify behavioural claims
  against SOURCE, not standards docs.** The refine→outline re-ground gate catches it every time — the
  standing gap is that refine trusts standards docs. Candidate fold into PLAN-25 D4's inventory (docs that
  assert behaviour the code contradicts are the same core-vs-reality drift) or a refine-hardening item.
  Directly motivates PLAN-24's "reproduce, don't fix on the hypothesis" discipline.

> **Kept (not promotable):** the *premise-lossy tail* (evidence #7) and *harness instability* watches
> above remain — the first is anti-change evidence, the second is infra (mitigation = plan-server +
> #912). Neither is a plan.
