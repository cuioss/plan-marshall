# PLAN-35: Freshness Gate and Build Decision Use Disagreeing Oracles

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Surfaced by PLAN-31 (#968), which hit the deadlock **twice in one finalize
> run** and resolved both honestly with real ~200s whole-tree pytest runs rather than `--force`.
> ⚠ **The orchestrator's first framing of this defect was WRONG and was corrected before
> staging** — see "Sharpened diagnosis" below. The narrative's framing ("docs-only plans have no
> exemption") does not survive source inspection: exemptions exist.
>
> **Re-grounded at `main` @ `39f24b3ad` (2026-07-22, after PLAN-39 #980 rewrote
> `manage-execution-manifest.py` +88/−).** All four seed oracles still present. ⚠ **Anchor drift
> from #980**: `_classify_paths_via_extensions` now **defs at `:169`** (not `:222`); its
> classification body and the `documentation_only` returns are at `:238/:328-332`. The other three
> anchors are stable: `cmd_build_decision` at `_cmd_build_map.py:124-134` (build/not_necessary glob
> verdict), `_cmd_aspect_classify.py:44` (`not_necessary` for pure-doc). **Treat ALL cited lines as
> approximate and re-confirm in D1's inventory** — #980 shifted this file and D1 is a full re-trace
> GATE regardless.

## Objective

Two gates decide related questions using **different, unreconciled oracles**, and a plan can
land in the gap between them with **no legal path through finalize**.

## ⚠ At least FOUR independent oracles answer "does this need a build?"

An orchestrator scan (2026-07-21, seed inventory — **D1 must complete it**) found *four*
separate mechanics deciding a variant of the same question, each with its own vocabulary:

| # | Site | Verdict vocabulary | Oracle |
|---|------|--------------------|--------|
| 1 | `manage-config build-decision` (`_cmd_build_map.py:124-132`) | `build` / `not_necessary` | **`build_map` glob match** against changed paths |
| 2 | `manage-execution-manifest._classify_paths_via_extensions` (`:222-332`) | six buckets: `production_only` / `test_only` / **`documentation_only`** / `mixed_code` / `mixed_with_docs` / `unknown` | **per-domain `ExtensionBase.classify_paths()`** overrides + a generic suffix rule |
| 3 | `manage-config aspect-classify` (`_cmd_aspect_classify.py:44`) | returns **`not_necessary`** for pure-doc, skipping the whole-tree build | **request-aspect classification** |
| 4 | `manage-tasks pre-commit-verify-freshness` (`manage-tasks/SKILL.md:80,191-256`) | `fresh` + **`documentation_only`** / **`lint_only`**, else `stale` / `undecidable` | **composed `phase_5.verification_steps` shape**, else a `kind=build` ledger entry |

**The naming collision is itself a hazard**: `documentation_only` means two different things
(#2's file-type bucket, #4's freshness reason) and `not_necessary` means two different things
(#1's build verdict, #3's aspect verdict). Identical vocabulary across distinct oracles makes
divergence *invisible in review* — which is plausibly why this survived so long.

The PLAN-31 deadlock is one observable consequence: #1 says `not_necessary` so **no build runs
and no `kind=build` entry can ever be written**, while #4's exemptions do not fire and it
demands exactly such an entry. Fail-closed on both sides, contradictory premises, no legal
transition. **With four oracles there are more such pairs than the one we have observed** —
the deadlock is a symptom of the multiplicity, not a bug in either site.

## Sharpened diagnosis (orchestrator-verified — do NOT re-derive the wrong version)

The freshness gate **already carries two docs-only exemptions** (`manage-tasks/SKILL.md:80`):

- `reason: documentation_only` — when `execution.toon` composes an **empty**
  `phase_5.verification_steps`, so no build runs at all;
- `reason: lint_only` — when **every** `verification_steps` entry is a structural-lint
  `quality-gate` step and **none** is a build/test step.

So the defect is **not** "docs-only plans have no exemption." It is that the exemption keys on
the **composed verification-steps shape** while the build decision keys on the **`build_map`
glob match** — and a docs-only plan whose manifest happens to compose *any* build/test
verification step satisfies **neither** exemption while still being ruled `not_necessary`.
PLAN-31 was exactly that shape: a markdown-only change that nonetheless composed a build/test
step, so `documentation_only` and `lint_only` both missed and the ledger could never be stamped.

**This changes the fix — and the operator has ruled on the target shape.**

> **The build_map decision is THE oracle. `to build or not to build` — no other variants.**

So this is **not** a reconciliation of two peers, and certainly not a third exemption. It is a
**collapse to one authority**. `build-decision` (build_map glob → `build` / `not_necessary`) is
the single question, and the freshness gate becomes a consumer of that verdict rather than a
second, independently-reasoning judge:

- `not_necessary` ⇒ no build evidence can exist ⇒ **`fresh`**, with the verdict as its reason.
- `build` ⇒ demand the matching `kind=build` ledger entry, exactly as today.

The shape-based heuristics `documentation_only` and `lint_only` are **the wrong variants** and
should be **retired**, not extended. They exist only because the gate was inferring "can build
evidence exist?" from the verification-steps shape — a proxy for a question `build-decision`
already answers directly. Every such proxy is a fresh opportunity for the two to disagree; this
deadlock is that disagreement made visible.

## ⚠ OBSERVED vs INFERRED

- **OBSERVED**: both oracles and their locations; the two existing exemptions and their exact
  trigger conditions; that PLAN-31 hit the deadlock twice and paid ~200s per occurrence.
- **INFERRED, NOT verified**: the precise reason PLAN-31's manifest composed a build/test step
  despite a markdown-only footprint. The plan's `execution.toon` was **not read** — that is D1.
  If it turns out the manifest composed an *empty* steps list and `documentation_only` still
  failed to fire, the defect is a different one (a broken exemption, not disagreeing oracles)
  and this spec's premise is falsified. **Read it first.**

## Deliverables

1. **Exhaustively inventory EVERY build/no-build decision point (GATE — the load-bearing
   deliverable).** The four above are a **seed, not the answer**. Trace the full flow —
   phase-3-outline classification → phase-4-plan compose → phase-5-execute verification →
   phase-6-finalize gates — and enumerate every site that decides, infers, or branches on
   "does this change need a build?", including consumers that merely *read* a verdict. For each:
   its input, its vocabulary, its authority, and whether it is a decider or a consumer.
   **Explicitly hunt for vocabulary collisions** (`documentation_only` and `not_necessary` each
   already mean two different things). Deliver the inventory as a document — it is the evidence
   base for D2 and the artifact that makes a future regression detectable.
   Also confirm the concrete PLAN-31 shape: read the composed `phase_5.verification_steps` in
   `.plan/local/archived-plans/2026-07-21-orchestrator-dispatch-ruleset/` and establish which
   exemption should have fired. **That detail determines the D5 regression, not whether to
   proceed** — the consolidation is right regardless, and a broken exemption would be one more
   argument for deleting the proxies rather than repairing them.
2. **Design the ONE mechanic (design-first, gated on D1's inventory).** Specify the single
   build/no-build authority — per the operator ruling, the `build_map` decision — with one
   vocabulary, one input contract, and one place it is computed. Define what every site in D1's
   inventory becomes: **consumer of the verdict**, or **deleted**. Nothing may retain an
   independent inference path. Where a site needs *more* than build/no-build (the six-bucket
   classifier also drives `profiles[]` assignment in phase-3-outline, which is a genuinely
   different question), state explicitly which part is the build decision — that part consumes
   the one oracle — and which part is a separate concern that legitimately survives.
   **Record the boundary**; conflating "needs a build" with "what kind of files are these" is
   how four oracles grew in the first place.
3. **Migrate every site onto the one mechanic and RETIRE the variants.** The freshness gate
   consumes the verdict directly: `not_necessary` ⇒ `fresh` (carrying the verdict as its
   reason); `build` ⇒ demand the matching `kind=build` entry as today. **Delete
   `documentation_only` and `lint_only` as freshness reasons.** Resolve the vocabulary
   collisions D1 surfaced — a term must mean one thing.
   ⚠ **Survivor sweep before deleting** (ADR-007): any consumer branching on a retired reason,
   and any doc prose promising it, must be found and updated. A stale reference to a deleted
   verdict is precisely the class ADR-007 governs.
   Preserve the fail-closed posture (ADR-009): remove the *impossible* demand, never weaken the
   gate where build evidence is genuinely obtainable.
4. **Add a contradiction guard.** Once one oracle governs, the deadlock becomes *structurally
   impossible* rather than merely fixed — the guard pins that. Any state where the build verdict
   says no build can run while a downstream gate demands build evidence must fail loudly at
   compose time, same shape as PLAN-20's `check_emitted_steps_canonical`. **It must be
   impossible to compose a manifest with no legal path through finalize.**
5. **Regression covering the exact PLAN-31 shape.** A markdown-only footprint whose manifest
   composes a build/test verification step must reach `push` without a whole-tree build. Use
   PLAN-31's **real composed shape from D1**, not a hand-built fixture — hand-written fixtures
   are exactly what pinned the bug in PLAN-23's marker suite.

**Five deliverables — at the split guard's edge, proceeding unsplit with rationale.** They are
one coupled consolidation: D1's inventory is the evidence base for D2's design, D3 cannot
migrate before D2 defines the target, and D4/D5 pin what D3 does. Splitting would ship a
half-migrated flow with *more* oracles in play mid-flight than before — the opposite of the
goal. **If D1's inventory returns materially more than the four seeded sites, STOP and split**
along the migration boundary rather than pushing a mega-plan through.

## Expected Surface

⚠ **Wider than a normal WS-10 plan — this is a cross-cutting consolidation.** D1's inventory
may extend it; treat this as the seed:

- `manage-tasks` `pre-commit-verify-freshness` implementation + `SKILL.md:80,146-157,191-256`
- `manage-config/scripts/_cmd_build_map.py` (`cmd_build_decision`) — the surviving oracle
- `manage-config/scripts/_cmd_aspect_classify.py:44` (the `not_necessary` collision)
- `manage-execution-manifest/scripts/manage-execution-manifest.py:222-332`
  (`_classify_paths_via_extensions`) + `standards/decision-rules.md:257-279`
- `script-shared/scripts/extension/extension_base.py:1072-1075` (the bucket vocabulary contract)
- `phase-6-finalize/standards/pre-push-quality-gate.md:34` (contract prose)
- `phase-3-outline/SKILL.md:299-317` (classifier consumer — the file-role concern that survives)
- the manifest compose path (D4's contradiction guard)
- tests under the manage-tasks / manage-config / manifest-compose suites
- the D1 inventory document itself

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **ADJACENT to PLAN-32 (live)** — PLAN-32 owns `script-shared/build` + `manage-run-config`
  and reasons about build-result truthfulness; PLAN-35 touches `manage-tasks` and
  `manage-config`'s build-decision. Different modules, but both live in the build-verdict
  neighbourhood. **Check PLAN-32's actual touched surface before emitting**; sequence behind it
  if it grew into `_cmd_build_map.py`.
- ⚠ **ADJACENT to PLAN-20's territory** (shipped) — D3's compose-time guard sits beside
  `check_emitted_steps_canonical`. Re-ground against it and reuse the pattern.
- **High value for this epic specifically**: WS-10 ships docs-only plans constantly (PLAN-30,
  PLAN-31, likely PLAN-29), and each pays ~200s of pointless whole-tree pytest per occurrence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-35-freshness-gate-oracle-disagreement.md"

OPERATOR RULING ON SCOPE, binding: carefully scan ALL decision points to avoid multiple ways of deciding the same thing — deeply analyze the current flow and introduce ONE mechanic. This is a CONSOLIDATION plan, not a two-site patch. An orchestrator seed scan already found FOUR independent oracles answering a variant of "does this need a build?": (1) manage-config build-decision via build_map glob match, verdicts build/not_necessary (_cmd_build_map.py:124-132); (2) manage-execution-manifest._classify_paths_via_extensions six-bucket file-type classifier including documentation_only, driven by per-domain ExtensionBase.classify_paths() overrides plus a generic suffix rule (manage-execution-manifest.py:222-332); (3) manage-config aspect-classify, which returns not_necessary for pure-doc and skips the whole-tree build (_cmd_aspect_classify.py:44); (4) manage-tasks pre-commit-verify-freshness, keying on the composed phase_5.verification_steps shape with reasons documentation_only/lint_only (manage-tasks/SKILL.md:80,191-256). THOSE FOUR ARE A SEED, NOT THE ANSWER — deliverable 1 must complete the inventory across the full flow (phase-3-outline classification, phase-4-plan compose, phase-5-execute verification, phase-6-finalize gates), covering consumers as well as deciders. Hunt explicitly for VOCABULARY COLLISIONS: documentation_only already means two different things (#2's file-type bucket vs #4's freshness reason) and not_necessary means two different things (#1's build verdict vs #3's aspect verdict) — identical vocabulary across distinct oracles makes divergence invisible in review, which is plausibly why this survived. One caution for the design: the six-bucket classifier also drives profiles[] assignment in phase-3-outline, which is a genuinely DIFFERENT question — separate the build decision (which consumes the one oracle) from the file-role question (which legitimately survives), and record that boundary, because conflating "needs a build" with "what kind of files are these" is how four oracles grew.

OPERATOR RULING ON THE TARGET SHAPE, binding: the build_map decision is THE oracle — "to build or not to build", no other variants. This is NOT a reconciliation of two peer oracles and NOT a third exemption; it is a COLLAPSE TO ONE AUTHORITY. build-decision (build_map glob -> build / not_necessary) answers the single question, and pre-commit-verify-freshness becomes a CONSUMER of that verdict rather than a second independently-reasoning judge: not_necessary => fresh (carrying the verdict as its reason); build => demand the matching kind=build ledger entry exactly as today. The existing shape-based reasons documentation_only and lint_only are THE WRONG VARIANTS and must be RETIRED, not extended — they are proxies for a question build-decision already answers authoritatively, and every proxy is a fresh opportunity for the two to disagree. Before deleting them, sweep for other consumers that may branch on reason == documentation_only or lint_only, and for doc prose promising them: that is the ADR-007 survivor-sweep obligation and a stale reference to a deleted reason is exactly the class it covers.

MANDATORY: deliverable 1 is a verify-first GATE, and the orchestrator's FIRST framing of this defect was already wrong once — do not inherit it. The WRONG framing (from the PLAN-31 narrative) is "docs-only plans have no freshness exemption". Source inspection falsifies that: manage-tasks/SKILL.md:80 documents TWO exemptions — reason: documentation_only when execution.toon composes an EMPTY phase_5.verification_steps, and reason: lint_only when every verification_steps entry is a structural-lint quality-gate step and none is a build/test step. The CORRECTED framing is that two gates use different unreconciled oracles: manage-config build-decision keys on a build_map GLOB MATCH against changed paths (_cmd_build_map.py:124-132) returning build/not_necessary, while pre-commit-verify-freshness keys on the COMPOSED verification-steps SHAPE and otherwise demands a kind=build ledger entry whose worktree_sha matches. A markdown-only plan whose manifest nonetheless composes any build/test verification step satisfies NEITHER exemption while still being ruled not_necessary — so no build runs, no ledger entry can exist, and the gate fails closed demanding one. Contradictory premises, no legal path through finalize. STILL INFERRED and NOT verified: why PLAN-31's manifest composed a build/test step despite a markdown-only footprint — its execution.toon was NOT read. Read .plan/local/archived-plans/2026-07-21-orchestrator-dispatch-ruleset/ FIRST and confirm the composed phase_5.verification_steps. If the shape genuinely missed both exemptions, proceed with oracle reconciliation. If an exemption SHOULD have fired and did not, this spec's premise is falsified — that is a broken-exemption defect instead, so re-scope and say so rather than implementing against the wrong mechanism. This epic has had plans whose symptom was real but whose inferred mechanism was falsified at outline (PLAN-24 #963, PLAN-26 #964), and this spec has ALREADY been corrected once before staging.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-35.md is recorded}
