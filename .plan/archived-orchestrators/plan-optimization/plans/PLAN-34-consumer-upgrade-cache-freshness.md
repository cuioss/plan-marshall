# PLAN-34: Steward Owns the Plugin-Cache Lifecycle (Fetch + Prune)

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Surfaced 2026-07-21 by the operator in two steps: first catching the
> orchestrator's false claim that finalize-driven cache sync covers everyone (it is
> meta-project-only), then directing that **the same `upgrade` verb that updates should also
> prune**. That second point collapsed a design fork and merged what had been two plans.

## Objective

`marshall-steward upgrade` is the natural — and currently missing — owner of the **whole**
plugin-cache lifecycle: bring the cache **forward** (fetch/verify freshness) and keep it
**bounded** (prune superseded versions). Today it does neither.

### Half 1 — nothing brings a consumer's cache forward

Verified against source:

- The consumer stage matrix (`upgrade.py:101,120`) is exactly Stage 1 `['regenerate-executor']`,
  Stage 3 `['executor-preflight']` — **no cache step in any of the four stages**.
- `references/upgrade-flow.md:133-134` states the consumer "uses the **freshly-synced**
  cache-version generator under the plugin cache" — an **assumed precondition with no
  establishing step and no guard**.
- No `/plugin marketplace update` (or equivalent) guidance exists anywhere in the
  `marshall-steward` skill — grepped, zero hits.
- The meta project *does* stay fresh, via `project:finalize-step-sync-plugin-cache` — which
  CLAUDE.md scopes as **meta-project-only** (*"consumer projects of plan-marshall do not get
  it"*). **That mechanism masks this gap from anyone testing only on plan-marshall itself.**

Likely consequence: **`upgrade` is a misnomer on a consumer** — it re-provisions the executor
against a stale cache and reports success, so a consumer can sit many versions behind with a
green steward run.

### Half 2 — nothing bounds the cache, on any project kind

Measured on this machine 2026-07-21: `~/.claude/plugins/cache/plan-marshall/` =
**973 MB**, **550** `.orphaned_at` markers, **55/55** `plan-marshall` versions marked —
**including the live `0.1.1177`**, whose marker was written minutes after #967's sync. The
oldest marker (`0.1.1105`) is **exactly 7 days old and still present**, so the documented
7-day sweep has never actually removed anything.

⚠ **The live-version marker is the load-bearing hazard.** Any age-based prune written naively
against the existing markers would delete the version the project is running on. The retention
rule MUST pin the live version independently of marker state.

## Retention policy (operator-suggested — confirm the exact shape at outline)

Operator's steer: *"older than 3 days and/or the 5 newest."* Encode as a **union of keep-rules**,
never an intersection — a version survives if ANY rule keeps it:

- **keep** the N newest versions (suggested N=5), **and**
- **keep** anything younger than D days (suggested D=3), **and**
- **always keep** the live/provisioned version and the one `marshal.json` points at,
  *regardless of age, count, or marker* — this is the pin that makes the sweep safe.
- prune the remainder.

The union is deliberate: it degrades safely in both directions — a burst of releases in one day
cannot evict a still-referenced version, and a quiet week cannot strand you on a single copy.
**Confirm N and D with the operator at outline**; they were given as an example, not a decision.

## Deliverables

1. **Read `executor-preflight` and the cache GC's delete-time oracle (GATE).** Two questions,
   both currently unanswered: (a) does preflight already detect cache-version skew, so a
   consumer several versions behind gets a red upgrade rather than a green one? (b) what does
   the existing orphan sweep check *at unlink time* — does it re-verify liveness, or would it
   trust a marker and delete a live version? Record both verdicts. If (a) is already covered,
   Half 1 shrinks to documentation; if (b) is already safe, the live-version pin is belt-and-
   braces rather than a fix. **Say so and shrink rather than manufacturing work.**
2. **Give the consumer flow a freshness step or a fail-closed guard.** Either add a
   fetch/update sub-step to the consumer Stage 1, or — if fetching is the harness's job, not
   plan-marshall's — a **freshness check that refuses to report a successful upgrade** against a
   cache the operator has not refreshed, naming the exact command. Prefer the guard when the
   fetch is not ours to own: a truthful refusal beats a silent no-op (ADR-009 fail-closed
   precedent; the PLAN-24 truthful-status theme).
3. **Add prune to the upgrade flow, for both project kinds.** Wire the retention policy above
   into a stage/sub-step so pruning happens on the same operator action that updates. The sweep
   must **report what it kept and what it removed** — a silent no-op must be distinguishable
   from a clean run (this is precisely how 550 markers accumulated unnoticed). Regression must
   cover the live-version pin: a cache where every version carries a marker must still retain
   the live one.
4. **Close the documentation gap and state the asymmetry.** `upgrade-flow.md:133`'s
   "freshly-synced" precondition becomes either a real step or an explicit operator
   prerequisite with the command spelled out. Document the meta/consumer split — that the meta
   project's finalize-driven sync is invisible to consumers — so the next reader is not misled
   the way the orchestrator was.

Four deliverables, under the split guard. D1 gates D2 and D3; D4 is correct either way.

## Expected Surface

- `marshall-steward/scripts/upgrade.py` (stage matrix `:101`/`:120`; new sub-steps)
- `marshall-steward/references/upgrade-flow.md` (the `:133` precondition; Stage 1/3 bodies)
- `marshall-steward/SKILL.md` (canonical invocations, if the argparse surface grows)
- the sync-plugin-cache engine + its orphan/GC path (locate at D1 — do NOT assume a file)
- the executor-preflight implementation (locate at D1)
- tests: stale-cache consumer path; retention bound; **live-version-never-pruned invariant**

## Dependencies and Sequencing

- Depends on: none.
- **ABSORBS the plugin-cache half of PLAN-33.** PLAN-33 is reduced to the session-binding store.
  The two were adjacent — both would have edited `upgrade.py`/`upgrade-flow.md` once PLAN-33's
  "give the GC a caller" deliverable resolved to the steward verb. Merging at the seam removes
  the collision instead of sequencing around it.
- Overlaps with: **none in flight** (PLAN-25 `_cmd_skill_domains`, PLAN-29
  `marketplace/targets/` + `platform-runtime`, PLAN-31 orchestrator docs, PLAN-32
  `script-shared/build`). Emittable immediately.
- **Consumer-facing.** Four consumer repos tracked (nifi-extensions, cui-jsf-test-basic,
  TokenSheriff, API-Sheriff) — ranks above the meta-only items in the queue.
- Re-ground against **PLAN-13 (#950)** steward-provisioning-fail-closed and **PLAN-08 (#934)**
  executor-manifest-resolution at outline; both touched this surface and #950 shipped the
  highest-version-wins resolver that the retention policy must not fight.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-34-consumer-upgrade-cache-freshness.md"

MANDATORY: deliverable 1 is a verify-first GATE with TWO questions, neither answered yet. OBSERVED facts: the consumer stage matrix in upgrade.py:101/:120 is exactly Stage 1 [regenerate-executor] and Stage 3 [executor-preflight] with no cache step in any of the four stages; upgrade-flow.md:133-134 states the consumer uses the "freshly-synced" cache-version generator, an assumed precondition with no establishing step and no guard; there is no /plugin marketplace update guidance anywhere in the marshall-steward skill; project:finalize-step-sync-plugin-cache is explicitly meta-project-only per CLAUDE.md so the route keeping plan-marshall itself fresh is structurally unavailable to consumers; and the cache measured 973 MB with 550 .orphaned_at markers, 55 of 55 plan-marshall versions marked INCLUDING the live 0.1.1177, with the oldest marker exactly 7 days old and still present. INFERRED and NOT verified: (a) that a stale consumer cache actually yields a silently-stale executor — executor-preflight was NOT read, and PLAN-13/#950 shipped a highest-version-wins resolver plus a fail-closed marshal_status: unknown, so partial coverage may exist; (b) that the existing orphan sweep would delete a live version — its delete-time oracle was NOT read and it may re-verify liveness before unlinking. Read both first and record both verdicts; if (a) is covered, shrink Half 1 to documentation, and if (b) is safe, the live-version pin is belt-and-braces rather than a fix. Say so and shrink rather than manufacturing work — this epic has had two consecutive plans (PLAN-24 #963, PLAN-26 #964) whose symptom was real but whose inferred mechanism was falsified at outline. RETENTION POLICY: the operator suggested "older than 3 days and/or the 5 newest" as an example, not a decision — encode it as a UNION of keep-rules (keep the N newest, AND keep anything younger than D days, AND always keep the live/provisioned version regardless of age, count or marker), never an intersection, and confirm N and D with the operator at outline. The live-version pin is load-bearing: every cached version currently carries an orphan marker, so a naive age-based prune written against marker state would delete the version the project is running on.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-34.md is recorded}
