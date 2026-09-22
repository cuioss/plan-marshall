# Epic: Lessons Routing — a finding has an audience, and the store has no concept of one

slug: lessons-routing

> Ledger document for one epic under `.plan/local/orchestrator/lessons-routing/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

**Every finding plan-marshall produces lands in exactly one place — a git-ignored directory on the
machine that produced it — regardless of who can act on it.** In this repository that is tolerable: the
producer, the store, and the fixer are the same party. In a **consumer** repository it is not. A client
running plan-marshall accumulates findings about their own code (which they can fix) and findings about
plan-marshall itself (which they cannot) in one undifferentiated pile, invisible to their teammates and
invisible to plan-marshall's maintainers.

This epic gives a finding a **destination determined by who can act on it**: local findings stay
actionable for the client's team, upstream findings reach plan-marshall as issues, and neither depends
on one developer's untracked working directory to survive. **Done** looks like: no finding is stranded
by its own classification, no finding is lost by refusal, and no finding is visible to only one person.

⛔ It is more than one plan because it spans four independent surfaces — the classification predicate,
a new cross-repo transport, the durability substrate, and the already-stranded corpus — and because
the first of those must be re-derived before any of the others can be designed against it.

## Grounding — every claim below verified first-party at HEAD `77c9dc70a`, 2026-08-24

**1. The store is machine-local and cannot be shared.** `.gitignore:45` is `.plan/*` with exceptions
only for `marshal.json` and `project-architecture/`. `git ls-files .plan` returns **15 tracked files**,
none under `local/`. ⇒ `.plan/local/lessons-learned/` is untracked by construction, so a lesson exists
only on the machine that wrote it. **This is aspect 4's root cause and it is not a policy choice to be
argued with — it is the current design.**

**2. Consumer repos are already carrying stranded upstream findings.** Sampled two live consumer
checkouts:

| Repo | Lessons | Components |
|---|:--:|---|
| `cui-jsf-test-basic` | 4 | `cui-jsf-test-basic` · **`plan-marshall:recipe-refactor-to-profile-standards`** · **`plan-marshall:build-maven`** · **`plan-marshall:workflow-integration-sonar`** |
| `API-Sheriff` | 2 | `api-sheriff:maven-build` · `api-sheriff:ci-workflows` |

⛔⛔ **Three of the four lessons in `cui-jsf-test-basic` are about plan-marshall and that client can do
nothing with any of them.** They are not a hypothetical — they are on disk, in a git-ignored directory,
on one developer's machine, and plan-marshall's maintainers have never seen them. **This epic's first
deliverable is arguably to go and read them.**

**3. ⭐⭐ A discriminator EXISTS — and it discriminates the WRONG AXIS.** `manage-lessons add` carries a
cross-repo guard: a `--component` bearing a bundle prefix refuses with `error: wrong_store` when the
resolved main-anchored store repo *"does not own that bundle"*, and the ownership predicate is
**whether `marketplace/bundles/{prefix}` exists in that repo**. `--allow-foreign-store` bypasses it; a
prefix-less component (e.g. `integration-tests`) is treated as project-local and files freely.

⛔ **That predicate is plan-marshall-shaped.** Verified: `API-Sheriff` has **no `marketplace/bundles/`
directory at all**, so `api-sheriff:maven-build` — *the client's lesson about the client's own build* —
fails the ownership test exactly as `plan-marshall:build-maven` does. **In a consumer repo every
prefixed component is "foreign", including the client's own.** The guard answers *"is this bundle
mine?"* — a question only a marketplace repo can answer — where the question that matters is **"can the
reader of this store act on this?"**

**4. ⇒ The real defect is not that findings are mixed. It is that the upstream class has NO
DESTINATION.** The guard correctly notices that a `plan-marshall:*` lesson does not belong in a client
store, and then offers exactly two outcomes: **refuse** (the finding is lost) or **`--allow-foreign-store`**
(the finding is stranded in a store whose readers cannot act on it — the mixing the operator reports).
**Both are failures, and the second is how the three stranded lessons above got there.** A guard that
refuses without routing converts a finding into a dead end.

**5. The transport already exists.** `plan-marshall:tools-integration-ci:ci` exposes an `issue`
subcommand alongside `pr` / `checks` / `branch` / `repo`. ⇒ The issue-based approach the operator asks
for does not need a new integration — it needs a **route** that uses the one already there.

## Scope decisions taken at decomposition

Recorded so the run inherits them rather than re-deriving:

- **Issues are DECIDED as the upstream transport** (operator: *"We need an issue based approach here"*).
  Not re-opened.
- **Client-local sharing moves to issues LATER, not first.** The operator's *"eventually we should
  streamline here to issues anyway"* is read as a sequencing statement: WS-02 routes the upstream class
  to issues now; WS-03 addresses client-local durability, with the file store as the interim. ⚠ If that
  reading is wrong, WS-03's gate is where it surfaces cheaply — it is a gate precisely because this
  assumption is the one most worth testing early.
- **Per-component filing is a MEANS, not the goal.** The operator named it first among possible
  aspects, but grounding fact 3 shows component is already recorded and already load-bearing; what is
  missing is an *audience*, which component only proxies for. ⇒ WS-01 owns the axis question, and
  per-component directory layout is one candidate answer inside it, not a premise.

## Inbound routing — this epic is the FOURTH owner

Registered 2026-08-24 as a sibling of `truthful-signals`, `code-intelligence-substrate` and
`review-apparatus`. The canonical discriminator table lives in
[`truthful-signals/epic.md`](../truthful-signals/epic.md) § "Inbound routing rule" and was amended in
the same pass; `lessons` was removed from that epic's column and this one added.

**What routes HERE:** anything about **where a finding goes and whether it survives** — the lessons
corpus and its store resolution, audience/ownership classification, the upstream issue route out of a
consumer repo, lesson provenance (component, version), multi-developer durability, and the
consumer-repo corpus.

⭐ **The test is DESTINATION, not subject.** A defect *in* `manage-lessons`' behaviour that reads
confident while hiding a caveat is `truthful-signals`'. A question about *who should receive a finding
and whether it reaches them* is ours. ⚠ The two are easy to confuse on a keyword match — `PLAN-TRUTH-091`
carries a `lessons-housekeeping` deliverable that correctly stayed there, because its subject is verdict
currency over a mutable global store and lessons is merely the instance.

⛔ **What this epic does NOT own:** the plan-scoped findings store (`manage-findings` — Q-Gate and PR
findings, a different lifecycle), and the orchestrator inbox channel (`truthful-signals` owns it).
Cross-epic overlap is checked with `corpus cross-check` before any plan is emitted.

⚠ **Nothing was transferred at creation.** The `truthful-signals` corpus was searched first: of 17
staged rows, none carried a lessons subject, and the five historical lessons-subject plans are all
shipped. This epic starts from an empty inheritance, not from a migration.

## Standing Rule: Content Sweeps vs Router Infra

**(2026-09-21, operator directive — governs every future run over `.plan/local/lessons-learned/`, not
work already done.)** Operator's own words, recorded verbatim so a future run inherits the rule
rather than re-deriving it:

> Go through each lesson from `.plan/local/lessons-learned`. For each lesson, identify whether it is
> still valid (check ground truth). On first pass, do a consolidation/deduplication. You are
> authorized to use file-based access. Incorporate/ingest each lesson into this orchestrator (and move
> the lesson into the orchestrator's archive). Each handled lesson must be removed from the original
> location. You are explicitly allowed to use file-operations for this cleanup. If incorporated, group
> the extracted aspect into sensible deliverables/plans that suit together. The max number of
> deliverables is 12 per plan. Group them sensibly. **The orchestrator itself must not provide plans
> but act as a distribution point of the sibling orchestrators.**

⛔⛔ **The load-bearing sentence is the last one.** `lessons-routing` (this epic) is **permanent** and
owns only the routing/versioning **mechanism itself** — PLAN-LR-01..06 and any future infra plan about
*how* a finding gets classified, transported, or stamped. It never accumulates content-derived plans.

A future pass over the lesson corpus is a **separate, dated epic** — `lessons-handling-YY-MM-DD-NN`,
one per pass, mirroring the two already run and closed (`lessons-handling-26-08-08-01`,
`lessons-handling-26-08-26-01`). That dated epic does the actual work: read each lesson, check it
against ground truth (still valid vs stale), deduplicate/consolidate, cluster into ≤12-deliverable
groups per plan, and route each group via `orchestrator inbox write` to whichever sibling epic
actually owns the subject (or, when a cluster is a tooling defect in the routing/versioning mechanism
itself rather than lesson content, port it directly into `lessons-routing` as a new plan — the
precedent is `PLAN-LH2-18` → `PLAN-LR-06`, WS-05, done at this epic's 2026-09-21 consolidation). Each
handled lesson is removed from `.plan/local/lessons-learned/` via a sanctioned `manage-lessons remove`
call (never a raw `rm`) after it is ingested, and the dated epic closes and archives under its own
name once every lesson it touched has a disposition — it does not stay open as a permanent home.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug lessons-routing
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: === ▶ EPIC CREATED 2026-08-24 (operator). 5 plans staged, N=1, R=0. NOTHING RUNNING. Next action: emit PLAN-LR-01, the gate. READ R1-R13. ===
R1. ⭐⭐ **THE PROBLEM IS NOT THAT FINDINGS ARE MIXED — IT IS THAT THE UPSTREAM CLASS HAS NO DESTINATION.** `manage-lessons add` already carries a cross-repo guard (`error: wrong_store`) that notices a `plan-marshall:*` component does not belong in a client store. It then offers exactly TWO outcomes: **refuse** (the finding is LOST) or **`--allow-foreign-store`** (the finding is STRANDED where nobody can act on it). **Both are failures.** ⇒ A guard that refuses without routing converts a finding into a dead end.
R2. ⛔⛔ **THE DISCRIMINATOR EXISTS AND DISCRIMINATES THE WRONG AXIS — verified first-party.** The `wrong_store` ownership predicate asks *"does `marketplace/bundles/{prefix}` exist in this repo?"* — a question only a marketplace repo can answer yes to. **`API-Sheriff` has NO `marketplace/bundles/` directory at all**, so `api-sheriff:maven-build` — *the client's own build, entirely theirs to fix* — fails the test **exactly as** `plan-marshall:build-maven` does. ⇒ **In a consumer repo EVERY prefixed component is "foreign", including the client's own.** ⚠ The predicate is not wrong in THIS repo, where bundle ownership and actionability coincide — **that coincidence is the trap**, and it is why the defect stayed invisible until a consumer checkout was sampled.
R3. ⛔⛔ **THREE STRANDED UPSTREAM FINDINGS EXIST RIGHT NOW AND NOBODY HERE HAS READ THEM.** `cui-jsf-test-basic/.plan/local/lessons-learned/` holds 4 lessons: 1 local (`cui-jsf-test-basic`) and **3 about plan-marshall** — `recipe-refactor-to-profile-standards`, `build-maven`, `workflow-integration-sonar`. They are real findings about THIS project, in a git-ignored directory, on one developer's machine. ⭐ **PLAN-LR-01 D3 reads them, and that deliverable is the cheapest possible proof the loss matters.** ⚠ Only **2 of 4** known consumer repos were sampled — the population is **at least** five findings over an **unenumerated denominator**.
R4. ⛔ **MULTI-DEVELOPER SHARING IS BLOCKED BY CONSTRUCTION, NOT BY POLICY.** `.gitignore:45` is `.plan/*` with exceptions only for `marshal.json` and `project-architecture/`; `git ls-files .plan` returns **15 tracked files, none under `local/`**. ⇒ `.plan/local/lessons-learned/` is untracked by design, so a lesson is visible to exactly one developer on exactly one checkout, forever. **This is the operator's aspect 4 and it is structural.**
R5. ✅ **THE TRANSPORT ALREADY EXISTS — build a ROUTE, not an integration.** `ci.py` exposes an `issue` subcommand alongside `pr`/`checks`/`branch`/`repo`. ⛔ The hard rule that all CI/Git provider operations go through the abstraction binds here exactly as elsewhere; **no second CI path.** ⚠ **UNVERIFIED and gated at PLAN-LR-03 D0: whether a consumer repo's credentials can open an issue on `cuioss/plan-marshall` ACROSS ORGS.** The surface existing does not answer that. A negative answer re-shapes LR-03 rather than killing it — its D0 prices the alternatives (queued outbox / generated body to paste / operator-provisioned token) so the run does not stall on an undecided fork.
R6. ⭐ **SCOPE DECISIONS TAKEN AT DECOMPOSITION — do not re-derive.** (a) **Issues are DECIDED** as the upstream transport (operator). (b) **Client-local sharing moves to issues LATER** — the operator's *"eventually we should streamline here to issues anyway"* read as sequencing; WS-02 routes upstream now, WS-03 owns client-local durability with the file store as interim. ⚠ **WS-03 has NO plan staged yet, deliberately** — its gate question (issues vs a committable file store) is a function of LR-01's findings, and staging it now would presuppose the answer. (c) **Per-component filing is a MEANS, not the goal** — component is already recorded and already backs the failing guard; what is missing is an **audience**, which component only proxies for.
R7. ⛔ **THE EPIC IS A HARD SERIAL CHAIN: LR-01 → LR-02 → LR-03 → LR-04.** N=1 is set, but **the dependency chain, not the knob, is the binding constraint** — raising N admits nothing. **LR-01 blocks everything** (it derives both populations and settles derived-vs-declared). **LR-04 is deliberately LAST** — migrating a stranded finding before a destination exists moves it from one dead end to another. ⚠ **LR-04 D2 WRITES into consumer repositories**, which every other plan here is forbidden to do; its spec requires operator confirmation of that write scope before execution. ⚠ This epic's corpus has **never** been `corpus cross-check`ed against its four siblings — do that before emitting anything.
R8. ⭐⭐ **`PLAN-LR-05` STAGED 2026-08-24 (operator): the version is MANDATORY on every lesson and SCRIPT-DETERMINED, never caller-supplied.** Verified first-party that a lesson header carries `id`, `component`, `category`, `status`, `created` and **nothing about what was running** — `manage-lessons/SKILL.md` mentions no version field anywhere. ⛔⛔ **THE HARD PART: "the version" IS NOT ONE NUMBER, and this session proved it.** Double-sampled on this machine 2026-08-24: executor `MARSHALL_VERSION` = **0.1.1538**, registry `installPath`/`version` = **0.1.1526**, and the cache dir the SKILL BODIES were seated from = **0.1.1526**. ⇒ **The script that files the lesson and the skill body whose behaviour it describes came from DIFFERENT versions** — twelve releases apart today. A naive `version = MARSHALL_VERSION` stamp attributes a finding about a 1526 body to 1538. **D0 settles which source answers *what was running when this was observed*, and may record more than one value; a field whose single value is under-determined is the token-total-is-a-partition archetype.** ⚠ A consumer checkout has **no `marketplace/bundles/**`**, so any answer that reads the source tree fails there — test the design in the consumer shape.
R9. ⛔⛔ **`LR-03` D1 WAS WRONG WITHOUT `LR-05`, AND IS NOW RE-SEQUENCED.** LR-03 D1 requires the issue body to carry the version the client was running. Without filing-time stamping it could only sample a **live** version at ROUTING time — the version at the moment of routing, not of observation. ⇒ Wrong for **every** finding filed before an upgrade, and the stranded corpus is **two months old** (dated 2026-06-15/16). **LR-05 now lands before LR-03, and LR-03 D1 READS a recorded field rather than sampling one.** ⚠ LR-05 D3: **do NOT backfill a guessed version** onto the pre-existing corpus — a June lesson stamped with today's version is actively false and worse than an absent field. **`absent`, `undetermined` and a real version are THREE states.**
R10. ⛔⛔ **`LR-02` IS THE RESIDUE OF A SHIPPED FIX — READ `truthful-signals/PLAN-103` (#1050, `a7a657b00`) BEFORE TOUCHING THE GUARD.** It merged as *"fix(manage-lessons): **scope the store-ownership guard to prefixed components**"* — i.e. it fixed the **prefix-LESS** case, which is now correct and documented at `SKILL.md:108` and **must be preserved**. ⇒ This epic owns the half it did not reach: for a **PREFIXED** component the ownership test is still *"does `marketplace/bundles/{prefix}` exist here?"*, which in a consumer repo is `no` for the client's own component too. ⛔ **Two live risks: concluding the subject is closed from PLAN-103's TITLE** (read its landing and merge subject instead), and **re-deriving its narrowing as new**. ⚠ PLAN-103 carries recorded **verification debt** and a live watch that a post-merge CodeRabbit re-review of its `from-error` contract change may have left findings **untriaged in `main`** — check #1050's comments before extending that code path. ✅ **SIBLING REGISTRATION DONE**: this epic is the FOURTH owner; `lessons` was removed from `truthful-signals`' column and the discriminator gained a fourth. **The test is DESTINATION, not subject** — a defect *in* `manage-lessons` behaviour stays theirs. ⚠ **Nothing was transferred**: 17 staged rows there, none with a lessons subject; the five historical ones are all shipped.
R11. ⛔⛔ **OPERATOR RULING 2026-08-24 — THE VERSION SOURCE IS SETTLED: `MARSHALL_VERSION`, ALWAYS. DO NOT RE-OPEN.** *"Always use MARSHALL_VERSION. Reasoning: for typical clients, installed locally, this is usually correct."* ⇒ **`LR-05`'s D0 gate is RETIRED and the plan is now 4 deliverables with no gate.** ⭐ **MY OBJECTION IS WITHDRAWN AND THE REASON MATTERS:** I evidenced ambiguity with the live 1538-vs-1526 split on THIS machine — **but that split is the plugin-registry pin / orphan-GC inversion, a pathology of this DEVELOPMENT checkout with a long incident history. A typical client installs the plugin, has one cache version, and never sees it.** I generalized a meta-repo defect to clients who do not have it. ⚠ The residual risk is real but **CONFINED to this machine** — where plan-marshall's own lessons are filed, `MARSHALL_VERSION` can name a version other than the one whose skill bodies ran. **Record it as a known limitation in the shipped docs; do NOT build a second source to chase it.** A field right for every client and occasionally imprecise for one developer is the correct trade.
R12. ⛔ **OPERATOR RULING 2026-08-24 (second): THE PRE-VERSIONING EXECUTOR CASE IS OUT OF SCOPE.** *"That is ok. this is the very old stuff, can be ignored."* ⇒ **`LR-05` D2 is DEMOTED from a designed failure branch to ONE defensive line** — record a sanctioned `undetermined` rather than crash or fabricate, and nothing more. **No signal semantics, no field-population claim, no dedicated fixture.** Any client filing a lesson today has a current executor, because the executor is regenerated by steward / cache-sync. ⭐⭐ **RECORDED BECAUSE I GOT IT WRONG AND THE ERROR IS THE PROJECT'S OWN ARCHETYPE:** I called that branch *"reachable in the field today"* on the evidence of a **SINGLE** stale checkout (`cui-jsf-test-basic`, Jun 15) — **one sample presented as a population**, and a sample of an ABANDONED checkout rather than a live client. The observation was true; the inference was not. ⇒ **`LR-05` is now 3 substantive deliverables + 1 defensive line, no gate.** ⭐ **D4's load-bearing assertion moved**: it is the **no-backfill** case, not the absent-constant one — silently stamping a June lesson with today's version is the failure that is invisible afterwards. ⛔ **D3 unchanged: `absent` / `undetermined` / a real version remain THREE distinct states.** ⚠ **Twice in two turns an over-engineered premise was corrected by the operator** (the version-source gate, then this) — both times I generalized from this development machine to clients who do not share its condition. **Check whether an observation is of a LIVE client before letting it shape a deliverable.**
R13. ✅ **CLEANUP 2026-08-24 — THIS EPIC IS `restart-check` READY** (`verdict: ready`, 5 of 6 signals scored; `registry_parity` excluded as unowned). Corpus 5/5 both directions, 0 unreadable; `compact` idempotent, 3/3 invariants; inbox at the **EMPTY** zero. ⛔⛔ **BUT ALL FIVE SPECS WERE BORN BLIND TO THE ADMISSION GATE AND ARE NOW FIXED — do not assume a freshly-authored spec is conformant.** They carried a self-invented `## Re-grounding` heading with unlabelled `- Claim:` bullets; `_parse_claims` requires `## Claim Labels` **case-sensitively** and returns `[]` silently otherwise, so `corpus verdicts` saw **0 claims across the whole epic** and every spec would have passed the prep-ready gate **vacuously**. ✅ Rewritten as canonical Claim Labels with OBSERVED/HYPOTHESIS labels, file§symbol anchors, verify-at-outline markers and a verify-first clause each: **`claims_scanned` 0 → 30.** ⚠ **`PLAN-LR-02` lost its machine-derived collision map to my own conversion script and was restored** — re-read it if anything downstream depends on that map.
**Phase**: orchestrating
**Inbox (derived)**: 1 queued, 0 archived
**Queue** (staged, in order):
1. PLAN-LR-01 (WS-01)
2. PLAN-LR-02 (WS-01)
3. PLAN-LR-03 (WS-02)
4. PLAN-LR-04 (WS-04)
5. PLAN-LR-05 (WS-01)
6. PLAN-LR-06 (WS-05)
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-LR-01 — the gate. Nothing else in this epic is designed until its two populations land.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug lessons-routing (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug lessons-routing) at
     cleanup. Only the LIVE queue is rendered here. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LR-01 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/** |
| 2 | PLAN-LR-02 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** |
| 3 | PLAN-LR-03 | WS-02 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; test/plan-marshall/manage-lessons/** |
| 4 | PLAN-LR-04 | WS-04 | staged | (prose) |
| 5 | PLAN-LR-05 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** |
| 6 | PLAN-LR-06 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- PLAN-LR-01 — blocks every other row. Its (b) population is a **cross-repo read** of live consumer
  checkouts, which no other plan in this epic performs.
- PLAN-LR-04 — deliberately last. Migrating the stranded corpus before the route exists would move
  findings from one dead end to another.

## Decisions

- 2026-08-24 — **Epic created** on operator direction combining four aspects (per-component filing, a
  separate structure for plan-marshall's own findings, an issue-based upstream channel, and
  multi-developer sharing). Alternative considered: fold into `truthful-signals` as a workstream —
  **rejected**, because that epic's theme is *a confident signal hiding a caveat* and this is a routing
  and durability problem, and because the surfaces (`manage-lessons`, `tools-integration-ci`) are
  disjoint from its live queue.
- 2026-08-24 — **The axis is AUDIENCE, not component.** Grounding fact 3 established that the existing
  guard already keys on component and still cannot answer the question that matters. Recorded so no
  plan re-proposes "add a component field" as the fix.
- 2026-08-24 — **`lessons-handling-26-08-08-01` is NOT the home.** That epic holds 24 staged plans
  drained *from* the lessons corpus — it consumes lessons as input. This epic owns the corpus's routing
  machinery. Different subjects; no merge.

## Open Defects

- ⛔⛔ **Three stranded upstream lessons exist RIGHT NOW** in `cui-jsf-test-basic` — `plan-marshall:recipe-refactor-to-profile-standards`, `plan-marshall:build-maven`, `plan-marshall:workflow-integration-sonar` — in a git-ignored directory, unread by this project. *(source: first-party sample, 2026-08-24. Owned by PLAN-LR-01 (b), routed by PLAN-LR-04.)*
- ⛔ **The `wrong_store` ownership predicate mis-classifies a client's OWN prefixed component as foreign**, because it tests for `marketplace/bundles/{prefix}` which no consumer repo has. Verified against `API-Sheriff` (`api-sheriff:maven-build`, no `marketplace/` directory). *(source: first-party, 2026-08-24. Owned by PLAN-LR-02.)*
- ⚠ **`--allow-foreign-store` is the only escape and it launders the distinction it bypasses** — a lesson filed with it is indistinguishable afterwards from a genuinely local one. *(source: first-party read of `manage-lessons/SKILL.md:108`. Owned by PLAN-LR-02.)*

## Watches

- ⚠ **How the three stranded lessons were filed at all is UNESTABLISHED** — with `--allow-foreign-store`, or before the guard existed. The answer changes whether the guard is being routinely bypassed in practice or was simply added later. *(re-check: PLAN-LR-01 (b), which reads them.)*
- ⚠ **Cross-org issue creation permissions are unverified.** WS-02 assumes a client repo can open an issue on `cuioss/plan-marshall`. The `ci issue` surface exists, but whether a client developer's token can write to a foreign repo is not established. *(re-check: PLAN-LR-03's gate, before any transport is built.)*
- ⚠ **Consumer-repo count is unknown.** Four are named in project memory (`nifi-extensions`, `cui-jsf-test-basic`, `TokenSheriff`, `API-Sheriff`); two were sampled here. The real population bounds how much stranded corpus exists. *(re-check: PLAN-LR-01 (b).)*
