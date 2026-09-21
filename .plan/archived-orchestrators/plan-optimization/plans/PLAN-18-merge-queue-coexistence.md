# PLAN-18: merge-queue-coexistence

epic: plan-optimization
workstream: WS-09

> Staged plan spec. Consumer/org-surfaced (cuioss) — a bypass-less mandatory queue STRANDED a real
> release. Claims orchestrator-VERIFIED against source 2026-07-19. Re-ground citations at outline.

## Objective

Make marshall-steward's merge-queue provisioning a good citizen alongside an externally / org-managed
merge queue, and never itself create a mandatory queue that strands a repo's release/CI automation.
Covers desired outcomes A/B/C from the operator's spec (D is the sibling PLAN-19).

## Deliverables

### A — queue-create path supports bypass actors (release-safe)

**Verified:** `github-impl.md:140-144` — steward creates ruleset `plan-marshall-merge-queue` with
`enforcement: active` + a `merge_queue` rule and **no `bypass_actors`**, so a mandatory queue blocks
any direct push (release/tag automation → GH013). **Fix:** the create path must accept/declare bypass
actors (GitHub App / team / role) so release/CI automation is exempted; prompt for / accept a
bypass-actor config; **default to warning loudly if a mandatory queue is created with none.**
**Acceptance:** a steward-created queue can attach bypass actors; a queue created with a release-bot
bypass does not block that bot's direct pushes.

### B — detect an existing merge_queue rule regardless of ruleset name; treat as authoritative

**Verified:** the probe returns `eligible_configured` for ANY `merge_queue` rule
(`github-impl.md:111`), but reconcile/create only touches the literal `plan-marshall-merge-queue`
name (`:149`), and the wizard does not auto-set `use_merge_queue` on an external queue (set-time
validation `ci_base.py:66-68` PERMITS it, but nothing sets it). **Fix:** when a `merge_queue` rule
exists under a DIFFERENT ruleset name — do NOT create/reconcile/rename/delete it; DO set
`use_merge_queue=true` so finalize enqueues; log "merge queue externally managed". **Acceptance:**
steward on a repo with an org-managed queue under a different name creates nothing, errors nothing,
sets `use_merge_queue=true`, logs externally-managed.

### C — project-config signal to defer queue ownership

Add a project-config signal (e.g. `merge_queue_managed_externally=true` / `merge_queue_owner=org`).
When set: steward never prompts to create/enable a queue, never reconciles a foreign ruleset, only
aligns `use_merge_queue` to the detected platform state. **Acceptance:** a project with the signal set
→ steward fully defers (no create/reconcile prompts).

**Invariant (all deliverables):** plan-marshall must NEVER mutate a ruleset it did not create.

## Out of scope / do NOT expand
- Finalize branch-cleanup merge mechanics — that is PLAN-19 (D).
- The standalone single-project case MUST still work: steward may create + own `plan-marshall-merge-queue`
  when no external owner exists (non-goal to break it).

## Expected Surface
- `marshall-steward/references/merge-queue-setup.md` (Step 13.5 flow)
- `tools-integration-ci/standards/github-impl.md` + `scripts/ci_base.py` (repo merge-queue enable/probe + bypass_actors)
- `manage-config` (`merge_queue_managed_externally` param + set-time validation, `use_merge_queue`)
- tests: external-queue-different-name, create-with-bypass, managed-externally-defer

## Dependencies and Sequencing
- Depends on: none. **ALL GATES CLEARED as of 2026-07-20 — this is the LAST plan of the epic and there is
  nothing else in flight.**
- **PLAN-13 has SHIPPED (#950, `e45c7ac8f`)** — no longer "coordinate with a staged plan": its D4
  **fail-closed validated-write invariant is LIVE** (`_config_core.py` helper + `_cmd_system_plan.py`
  wiring + `test_provisioning_fail_closed_invariant.py`), and the surface is enumerated in
  `marshall-steward/standards/provisioning-fail-closed-audit.md`. **A bypass-less mandatory queue is an
  INSTANCE of exactly that invariant** (a provisioning write that "succeeds" while stranding the repo).
  **Read the audit doc + D4 helper at outline and BUILD ON them** — deliverable A's "warn loudly if a
  mandatory queue is created with no bypass actors" should use the shipped fail-closed seam rather than
  inventing a parallel one. Also re-ground `ci_base.py` against #950 and **PLAN-17 #948** (`250f9a4ea`),
  both of which landed after this spec was written.
- Disjoint from PLAN-19 (finalize, shipped #944 — its enqueue path is proven live, so D's behavior is a
  working precondition, not a dependency).

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-18-merge-queue-coexistence.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-18.md is recorded}
