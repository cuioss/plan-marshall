# HISTORY — Snapshot 4: the post-roadmap TAIL + aggregated-queue wave (2026-07-15 → 2026-07-17)

> **ARCHIVE ONLY — nothing here is actionable.** This snapshot freezes the full shipped record of
> the work that landed AFTER the core token-optimization roadmap closed (plan-8 #899, 2026-07-15):
> the bounded-fix TAIL, the `marshall-orchestrator` epic skill, and the entire aggregated
> findings/lessons queue (P1–P9 + the design-first SS). Open follow-ups spawned by these plans do
> NOT live here — they are tracked in HANDOVER §4 (queue) and §5 (open defects). This file is the
> "what shipped" record only.
>
> Companion archives: `HISTORY.md` Snapshots 1–3 (the roadmap proper, #811→#899). Live status:
> `HANDOVER.md`.

## Finale marker

- **plan-8 context-trim (finale)** | #899 | per-dispatch dispatch-context trim + finalize-wait consolidation onto the Monitor primitive + build-test-failure-detail Cluster C. SOLO-last cost-driver plan → the token-optimization roadmap COMPLETE. (Full detail: `HISTORY.md` Snapshot 3.)

## TAIL — bounded/deferred fixes (not new cost-driver plans)

| Plan | PR | One-liner (full detail was in HANDOVER §3 before this archive) |
|------|----|----|
| upgrade-regen-safety (⭐ was HIGHEST PRIO) | #908 | Un-gates consumer migrations. Leg A `detect_project_kind()` + kind-aware stage plan (consumer skips meta-only sub-steps instead of HALTING); Leg B self-checking atomic executor regen (`TEMPLATE_FORMAT_VERSION` handshake + `py_compile` + `os.replace` ⇒ skewed generator fails loud, executor byte-identical). +2 mid-flight: template-comment corruption (`{{SCRIPT_MAPPINGS}}` in a doc comment substituted → IndentationError, 64 failures) + version-decoupled template resolution root cause. Lesson `2026-07-15-22-001`. ⚠ NO METRICS/ARCHIVE — finalize ran `worktree-remove` BEFORE `integrate_into_main` (`.plan/local/` gitignored ⇒ unrecoverable); contributes NO token-corpus datapoint. (Guard shipped later as P1 #914 arm 5.) |
| build-maven-classify-globs-resources (side) | #909 | Extend `_CLASSIFY_PATTERNS` glob tables in BOTH build-maven and build-gradle (Maven-standard resource paths + shell scripts were `unknown` ⇒ blocked Q-Gate deliverable validation) + cross-extension parity regression guard. Refine contradicted the filed issue on 3 points, each verified against real code (named `classify_globs()` wasn't the bug; gradle had the byte-identical gap; suggested `**/*.sh` misses repo-root `foo.sh`). 2.51M / 1h26m worked / 10h25m wall (6-finalize alone = 8h25m wall + 1.08M / 43%). |
| hardening-sweep (HS) | #910 | D1 centralize path-traversal containment guard at the shared `create_log_file` sink (all three `_scope_fn` callables fed unsanitized `scope`) + D2 remediate meta-repo's own always-on agentfiles (`CLAUDE.md`/`AGENTS.md`) + D3 promote 2 agentfile-hygiene rules to build-failing `quality-gate` (sequenced `depends:2`). Refine dropped already-shipped items (incl. `architecture discover --force` `_project.json` corruption, lesson `2026-06-29-23-002` retired). D3 flip caught a real fixture bug (lesson `2026-07-16-08-001`). 3.2M / 2h31m worked. ⚠ Recovered a `finalize-step-simplify` LEAF whose backgrounded build died silently ~12h (harness-kill class). |
| whole-tree-gate git-native rebuild (WT) | #911 | PREMISE FALSIFIED at design-first outline — the requested git-native whole-tree oracle ALREADY EXISTS (`source_fingerprint.compute_source_tree_fingerprint` → `.emit-marker.json` → `sync.py::_staleness_guard`/`_file_level_drift`; `content_drift.py` covers `.md`). PR #723 was a different invariant; #793's rules are doc-mirror. Shipped **ADR-006** ("Generated-tree drift is gated at the consume boundary not in CI" — `target/` gitignored ⇒ CI gate inert). NO production code. Lesson `2026-07-16-12-001`. 1.9M / 1h14m worked. |
| background-build-kill (BK, plan-server keystone) | #912 | Harness-kill mitigation. D1 truthful `status` (`success|error|timeout|killed`) on every `kind=build` ledger row + freshness gate re-predicated `exit_code==0`→`status=='success'` fail-closed (closes false-fresh correctness bug); D2 `manage-change-ledger classify-outcome` verb (`killed`+0-byte ⇒ `externally_killed` "not flaky, do not blind-retry"); D3 kill-aware `await-long-running` seam. SELF-VALIDATED LIVE (own detached module-tests harness-killed → classify-outcome's first live call returned `externally_killed`, Monitor recovery). Lesson `2026-07-16-14-001`. 2.5M / 2h56m worked. |
| ext-point-verify-consumers (EV) | #906 | code-review + simplify-codebase + `pm-documents:doc-verify` wired onto `ext-point-verify` via a new `quality` verify profile (mirrors `security`). Refine invalidated 2 source premises before any code (bogus anchor; "WS-05" already shipped #795). Retires `2026-06-28-20-001`; new `2026-07-15-18-001`. Zero Q-Gate/real review findings. 2.8M / 1h41m worked. |

## marshall-orchestrator epic skill

| Plan | PR | One-liner |
|------|----|----|
| marshall-orchestrator | #915 | Resumable epic-orchestration skill above plan-marshall — orchestrate, never implement. 14 deliverables: D0 store-root abstraction (`get_store_dir`, **ADR-002 main-anchored** — the path-layer seam that gated Rung 1) + persona + orchestration-model standard (Epic→Workstream→Plan) + 8-verb router + workflow docs + `kind=orchestrator` schema + logging store wiring + `orchestrator.py` + templates + plugin/executor regen + dogfood (roadmap migrated into `.plan/local/orchestrator/{slug}/`) + `doc/concepts/orchestration.adoc` + lessons-handling + `Orchestrator-{SlugName}` terminal title + TASK-024 store write-locking. Finalize lessons: scoped-vs-whole-tree plugin-doctor CI-red gap (`09-002`); stale-FIFO-merge-queue recovery; machine-load≠plan-builds. 6.4M / 6h46m worked. **D0 UNBLOCKED Rung 1.** |

## Aggregated findings/lessons queue — P1–P9 + SS (all shipped 2026-07-17)

Built 2026-07-16 from HANDOVER §5 findings + the 96-lesson corpus, aggregated into 9 large
parallelizable plans + the design-first SS, grouped by same component/phase/error-class.

| P | PR | One-liner |
|---|----|----|
| P1 finalize-commit-integrity | #914 | Closes "code local but pipeline acts as shipped." 5 code guards: remote-parity push re-fire (`branch-sync-state`); structural clean-tree post-condition at 5→6 (`worktree_dirty_at_boundary`); loop-back handshake-drift auto-resolve; `lessons-capture` `mutates_source:true` (closes `16-002`/`18-001`); worktree-remove move-back guard (closes #908 bookkeeping-loss). **Arm 6 freshness-gate SPLIT OUT** → follow-up. Retired 5 folded lessons; +2 net-new. 4.4M / 4h34m worked. |
| P2 unified-finalize-triage (UT) | #920 | Fixes TokenSheriff-572 finalize deadlock — replaced the global `requires:[ci-complete]` gate with a per-signal gate on each producer's own `_ci_barrier.py` arm (failed arm still FINDs) + ONE dispatcher-owned unified triage over pr-comment∪sonar-issue. 13 tests reproducing #572. Cross-producer dedup deferred; `_ci_barrier.py` read-only. Retired `17-010`; new `17-001` (leaf edited MAIN checkout). ⚠ Did NOT absorb its parked follow-ups (→ HANDOVER §4/§5). 3.6M / 5h49m wall. |
| P3 architecture-resolution | #917 | 6 classifier-correctness fixes on manage-architecture verification-derivation: Failsafe-IT routing; unified `route_matches` (nested-pom classify); domain-affinity module ties; `build.maven.profiles.mutating` signal; `pm-documents` impl-profile skill set; stale-notation retire. New `2026-07-17-09-001`. Retired 6 folded lessons. 4.3M / 3h56m worked. |
| P4 execution-manifest-gaps | #916 | Gaps A (`enhancement` change_type) / B1 (unmapped orchestrator-verb → `verify:{verb}` prune) / B2 (marshal-authoritative phase-steps) / C1 (negation-phrase classifier → `drops_build_steps:true`). Retired `17-001/02/06`+`13-12-001`. ⚠ **C1 fixed the CLASSIFIER only — the phase-1→phase-4 aspect wiring survives → docs-only plans STILL build** (→ HANDOVER §4 manifest-compose-gaps plan). 3.7M / 3h32m worked. |
| P5 consumer-domain-standards | #918 | 5 marketplace standard docs updated as authoring rules (cui-http resolver-adoption + secure-default-flip; cui-http-testing MockWebServer IT self-checks; cui-logging CWE-117; cui-testing `@TypeGeneratorMethodSource`; asciidoc self-check pair). Authoring-only. Removed 4 folded lessons `17-017/018/019/020`. ⚠ Meta-irony: the catch-at-authoring plan itself needed 11 review-bot corrections. 2.4M / 1h46m worked. |
| P6 small-tooling-batch | #921 | 4 disjoint tooling fixes: D1 ADR width-agnostic numbering; D2 build-npm `--warning-baseline` exit-authority; D3 manage-lessons cross-repo wrong-store REFUSAL guard (structural fix for the lesson-store trap); D4 test-compile wired into `cmd_verify` = CI gates mypy over `test/` (closes `2026-07-15-12-001`). Dropped merge_lock/owasp (done). Retired 3 lessons; folded `12-001`. Follow-up PR #924 (doc residue). 4.8M / 3h44m worked. |
| P8 merge-queue-squash-reconcile | #919 | Merge-queue ruleset method parameterized from `pr_merge_strategy` (squash→SQUASH) + enable-time reconcile + probe seam + merge-routing mismatch warn. Self-validated live (reproduced #445 legibly). ⚠ **Queue must be RE-PROVISIONED via steward to activate** — every plan since rode the old MERGE queue. 1.9M / 1h42m worked. |
| P9 metrics-corpus-integrity | #922 | Makes `manage-metrics` per-step attribution sound: D1 phase-total↔dispatch-boundary reconcile (fixes under-count); D2 inline 6-finalize attribution (fixes inline=0); D3 loop-back monotonicity guard (fixes timestamp corruption); D5 era-stamp. D4 corpus-confidence caveat DROPPED from PR (gitignored targets) → applied out-of-PR to `gen.py`+01/02. Dogfooded clean. ~2.9M / 9h6m wall. |
| SS survivor-sweep (design-first) | #913 | Shipped **ADR-007** — the cross-file referential-completeness invariant, decided NO new gate (orphaned files already covered by `_file_level_drift`; residual in-body survivors → dev-time/self-review; `target/` gitignored ⇒ CI gate inert). Rejects PR #723's diff-text parser by name. Lessons folded into `2026-07-16-17-020`. 1.8M / 2h2m worked. |

**Cross-cutting note preserved from the wave:** most of these plans hit harness-killed background
builds and operator-skipped coverage gates (documented infra limit; root-cause fix = the marshalld
build server, plan-server epic). Every one landed via MERGE not squash because P8's reconcile fix
was never re-provisioned — a standing steward action, per-repo. See HANDOVER §4/§5 for the open tails.
