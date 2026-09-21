# Landing Analysis: PLAN-25 — Domain-Conditional Loading Concept

epic: plan-optimization
workstream: WS-10
pr: #965 (`18b7140db`)

> **AUTHORITATIVE.** Written first as a provisional diff-only record (the merge was discovered
> while re-checking a launched-count discrepancy the operator raised), then upgraded when the
> narrative arrived.
>
> ✅ **The provisional inference HELD — all five deliverables mapped correctly from file
> evidence alone**, including the specify-then-decline outcome on D3. This is the first
> diff-only landing in the epic to survive narrative arrival unchanged, and it contrasts with
> PLAN-24, where the same method produced two false claims. The difference: PLAN-25's spec
> enumerated its deliverables as separable artifacts (one document each), so the file set was
> nearly one-to-one with the deliverable list. **The lesson is narrower than "diff-only
> analysis works"** — it works when deliverables are artifact-shaped, and fails when they are
> behavioural (PLAN-24's were code-path fixes with no distinguishing file signature).

## Deliverable Evidence vs Spec

Verified against merge commit `18b7140db` (9 files, +1193/-28). The staged spec listed 5
deliverables (D1 ADR, D2 ext-point contract, D3 executor-awareness SPEC-ONLY, D4 inventory,
D5 arch-gate seed/resolve fix). File evidence maps to all five:

| Spec deliverable | File evidence | Note |
|---|---|---|
| D1 — ADR deciding the gating layer + visibility semantics | `doc/adr/010-Domain_content_is_active_only_when_its_domain_is_active.adoc` (+302) | Took **ADR-010** as predicted; the orchestrator's ADR-011 instruction to PLAN-29 therefore holds |
| D2 — contract for domain-contributed executable surfaces | `extension-api/standards/ext-point-domain-verb.md` (+120, NEW) + `extension-contract.md` (+28/-…) | The amended `extension-contract.md` is the surface the spec flagged as "not named in the report" — it was found and amended |
| D3 — SPECIFICATION ONLY of executor domain-awareness | `domain-aware-notation-spec.md` (+66) | ✅ **Scope discipline held**: `generate_executor.py` is **NOT in the diff**. The spec explicitly warned that file had already produced PLAN-08 #934 and PLAN-13 #950 and that "specify then decline" was a legitimate outcome. It declined |
| D4 — inventory of core-resident domain specifics | `domain-residency-audit.md` (+132) | — |
| D5 — arch-gate seed/resolve mismatch fix | `manage-execution-manifest.py` (+164), `_manifest_validation.py` (+78), `test_domain_seeded_step_resolvability.py` (+207), `test_compose_execution_tier.py` (+124) | The only executable change; test-heavy (331 lines of tests vs 242 of source) |

**The design-first posture appears to have held.** Four of five deliverables are documents; the
single code change (D5) is the concrete anchor the spec carved out as separable. No
implementation of D2/D3 leaked in, which the spec explicitly guarded against.

## Deliverable Detail (from the narrative)

- **D1 ADR-010** decides the model: capability-provision layers gate **invisibly**;
  status-bearing gates **refuse diagnosably** — reconciled with ADR-009's fail-closed rule.
  Plus a null-on-absent degrade path and an explicit *"deliberately NOT gated"* list.
- **D2** a sibling ext-point (`ext-point-domain-verb.md` + `provides_domain_verb` hook) letting a
  domain bundle own an executable verb.
- **D3** specifies then **declines** domain-gating `generate_executor.py` — the high-blast-radius
  file stays domain-blind. The spec's explicit permission to decline was exercised.
- **D4** 17 core-resident domain specifics enumerated: **3 FIX** (routed to D5/D2) / **14 JUSTIFY**.
- **D5** compose-time resolvability filter: an unresolvable domain-seeded verify-step is
  **skipped with a diagnosable `[STATUS]` warning instead of blocking**, plus regression test.
  This is the "skip-not-block" arm of the fork the spec posed at staging.

## Metrics and Anomalies

- Tokens: **3.5M** · Duration: **3h20m** across 6 phases
- Finalize: 21/21; plugin-doctor clean (4 skills gated); **self-review caught and fixed 1
  doc-consistency defect**; CI green across **3 HEADs**
- Deploy: bundles bumped to **0.1.1178**; executor regenerated
- ⚠ **Corroborates PLAN-28's dirty-main incident.** PLAN-28's run reported a transient dirty
  state on `main` — `extension-contract.md` modified plus an untracked `ext-point-domain-verb.md`
  — which tripped the cache-sync staleness guard and cleared on re-check. **Both files are
  PLAN-25's**, and they now land in #965. So the "concurrent editing session" PLAN-28 suspected
  was PLAN-25, and its in-progress edits were briefly visible in the main checkout despite the
  plan running in a worktree. Worth a watch: worktree isolation did not fully contain them.
  Cause not established — a sync step, a `deploy-target` emit, or an editor writing through the
  main path are all candidates.

## Routing and Merge Behavior

- **Review — two genuine loop-back fixes, BOTH in D5's own new code:**
  - **TASK-007** — `_invoke_architecture_resolve` called redundantly; now cached.
  - **TASK-008** — `_domain_appended_canonicals` `lru_cache` **never cleared per-compose**, so it
    would serve stale results **in the long-lived marshalld daemon**. The more serious of the
    two: a defect invisible in short-lived CLI runs and only manifesting under daemon longevity.
  - **4 speculative defensive-guard / optional-log suggestions correctly declined** per
    Principle 7 — the decline discipline held alongside the accept discipline.
  - Both real findings from **gemini — n=7 consecutive** as a productive reviewer.
- **⚠ `guards-are-highest-risk-artifact` → n=4.** PLAN-20 (`canonicalize_step_key`
  non-idempotence), PLAN-24 (the truthfulness guard that was itself untruthful), PLAN-28 (a
  self-contradictory sentence in its own contract), now PLAN-25 (two defects in D5's new filter).
  PLAN-26 remains the lone counter-example. The refined hypothesis holds: the risk attaches to
  **newly-authored correctness/gating logic**, not to new code generally.
- **⚠ NEW CLASS — module-level caches vs daemon longevity.** TASK-008 is not a one-off: any
  `lru_cache`/module-global memo written for a short-lived CLI process becomes a staleness bug
  once the same module is imported into `marshalld`. Fixed here; **the class is unswept**. Sits
  at the plan-optimization ↔ plan-server boundary — the cache lives in core, the longevity comes
  from the daemon. Candidate for a targeted sweep; not staged (draining).
- **CI/merge**: merged to `main` at `18b7140db`; worktree removed; **zero open PRs** repo-wide.
- **Surface collisions**: none observed. Ran concurrently with PLAN-29/31/32 throughout.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated (status `shipped`, pr `965`, landing `landings/PLAN-25.md`)
- [x] epic.md queue row reconciled
- [x] Launched count corrected **4 → 3** (operator-raised discrepancy; the orchestrator had been
      asserting 4 from the ledger without re-verifying)
- [x] ADR-010 confirmed consumed → PLAN-29's ADR-011 instruction stands
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **D2/D3 implementation remains deferred by design.** The spec anticipated >1 plan total; the
  `ext-point-domain-verb` contract and the domain-aware notation spec are now written but not
  implemented. A successor plan is owed — **not staged now** (operator is draining the queue).
- **Worktree-containment watch** (see Anomalies): PLAN-25's in-progress files appeared in the
  main checkout mid-run. Low severity — it self-cleared and harmed nothing — but worktree
  isolation is load-bearing for the concurrency model this epic relies on.
- **Landing-record completeness, n=2.** Second plan this session to merge without its narrative
  reaching the orchestrator (after PLAN-24). The standing mitigation — cross-check launched rows
  against merged PRs each session — worked, but only because the operator prompted it.
