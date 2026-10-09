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

⛔⛔ **RULING 2026-09-22 (operator) — SUPERSEDES the "separate dated epic" model below. `lessons-routing`
is ALWAYS the orchestrator used for a lessons-corpus sweep, going forward. No new
`lessons-handling-YY-MM-DD-NN` epic is created.** A sweep runs AS this epic, not as a child of it: read
each lesson, check it against ground truth (still valid vs stale), deduplicate/consolidate, cluster,
and route each cluster via `orchestrator inbox write` to whichever sibling epic actually owns the
subject (or, when a cluster is a tooling defect in the routing/versioning mechanism itself rather than
lesson content, port it directly into `lessons-routing` as a new plan — see the `PLAN-LH2-18`/`PLAN-LR-06`
caution two paragraphs up: check both re-grounding AND the Inbound Routing rule before doing that,
never on the strength of "the sweep found it while reading lesson content" alone). Each handled lesson
is removed from `.plan/local/lessons-learned/` via a sanctioned `manage-lessons remove` call (never a
raw `rm`) once its routing message is queued. **The distribution discipline is unchanged — only the
epic wrapper is retired**: this epic still never accumulates content-derived plans from a sweep: every
cluster's disposition is a routing decision (`## Lesson Sweeps` below) or, rarely, a genuinely new
routing-mechanism infra plan, never a staged plan spec that just restates swept content.

Three epics ran the now-retired separate-epic pattern before this ruling and remain as closed history,
never reopened or reused as a template: `lessons-handling-26-08-08-01`, `lessons-handling-26-08-26-01`,
and the short-lived `lessons-handling-26-09-22-01` (opened and closed the same day this ruling landed —
its full record is inlined at `## Lesson Sweeps § 2026-09-22` below and its tree was removed, per the
operator, once inlined).

⛔⛔ **RULING 2026-10-09 (operator) — the `ingest` command. SUPERSEDES the outward routing of the
2026-09-22 ruling above and the "new lessons go to the PM-MCP carry-over" rule of 2026-09-26.** Context,
operator's words: *"We start creating a new version of plan-marshall, so we only fix either high or
critical issue (plan-marshall module itself) or content issues (domain-bundles)."* What is unchanged:
this epic is still the one orchestrator a lessons sweep runs as, and it still stages no content-derived
plan of its own.

`ingest` is an epic-local command of this epic (`/plan-orchestrator epic=lessons-routing ingest`). It is
defined HERE, not in the `plan-orchestrator` skill source — a new skill verb is itself neither a
high/critical fix nor domain-bundle content. It runs three steps, in order:

1. **Scan and consolidate.** Enumerate the whole corpus through `manage-lessons`, check each lesson
   against ground truth, and cluster duplicates and near-duplicates into ONE consolidated item per
   cluster. Every lesson gets a per-lesson disposition in the sweep record.
2. **File what is applicable into `live-blockers`.** A consolidated item is applicable when it is
   either (a) a defect in the `plan-marshall` bundle itself graded **high** or **critical**, or (b) a
   **content** issue in a domain bundle (every bundle under `marketplace/bundles/` other than
   `plan-marshall`), at any severity. Each applicable item is filed as ONE message:
   `orchestrator inbox write --slug live-blockers --sender-type orchestrator --sender-id lessons-routing
   --kind finding`, the body naming its severity, its bundle, and every source lesson id.
3. **Archive everything else here.** Every other lesson file is copied verbatim to
   `{epic_dir}/lessons-archive/{level}/{lesson-id}.md`, where `{level}` is the graded severity —
   `medium`, `low` — or `stale` for a lesson that is already fixed or that ground truth refutes. The
   files stay one per lesson id; `lessons-archive/INDEX.md` records each cluster, its level and the
   reason. A lesson filed at step 2 is also copied, to `lessons-archive/filed-live-blockers/`, so the
   inbox message can stay short and point at the full body.

A lesson is removed from the corpus only AFTER its inbox message or its archive file exists, and only
through `manage-lessons remove` (never a raw `rm`). Severity is the orchestrator's graded judgement,
recorded with a one-line reason per item; a lesson whose grade is genuinely borderline between `medium`
and `high` is put to the operator rather than guessed. Nothing is routed to any other sibling epic, and
nothing is added to the PM-MCP carry-over by this command.

## Lesson Sweeps

One dated subsection per sweep, append-only, newest last. This is where a sweep's disposition record
lives now that a sweep runs AS this epic rather than as a separate dated epic (see the Standing Rule
above) — never in the generated START-HERE/Ordered-Queue blocks, which stay reserved for this epic's
own PLAN-LR-NN queue.

> ↪ Relocated to `settled.md` § "Lesson Sweeps — 2026-09-22" — closed: the sweep completed, routed to
> its 6 destination epics, and retired all 44 lessons; no longer live working material. (Cleanup,
> 2026-09-24, operator-confirmed relocation.)

> ↪ Relocated to `settled.md` § "Lesson Sweeps — 2026-09-26" — closed: every swept lesson was retired (2026-09-27) and its content carried to PM-MCP.

### 2026-10-09 — first `ingest` run

Corpus at start: 34 lessons, all about the `plan-marshall` bundle or this repository's own tooling;
none was a domain-bundle content issue. Also graded: the six PLAN-09 carry-over rows held as a Watch.
Per-lesson dispositions, clusters and reasons: `lessons-archive/INDEX.md`.

| Disposition | Lessons | Where |
|---|---|---|
| high, filed to `live-blockers` | 9 (in 4 messages, `lessons-routing-001`..`-004`), plus carry-over row 3 | `live-blockers/inbox/`; bodies in `lessons-archive/filed-live-blockers/` |
| medium, archived | 16, plus carry-over rows 1, 2, 4 | `lessons-archive/medium/` |
| low, archived | 7, plus carry-over rows 5, 6 | `lessons-archive/low/` |
| stale, archived | 2 | `lessons-archive/stale/` |

All 34 were removed through `manage-lessons remove` after their copy existed (verdict `superseded` for
the filed ones, `obsolete` for the rest; `2026-09-27-19-001` needed `--allow-unreadable`). Corpus after
the run: 0.

Grading basis: `live-blockers` `backlog.md` had already graded this corpus when that epic was cut, so
its grade was used wherever it lists the subject. Every high lesson turned out to be owned by a
`live-blockers` plan already (PLAN-LB-22/32, -27, -24/25, -31), so each message asks that epic to check
for a residual rather than to open new work. Only the filed and stale lessons were checked against code
or ledger at this run; the medium and low grades rest on the lesson text and the backlog.

### 2026-10-09 — second `ingest` run

Corpus at start: 76 active lessons, none of them seen by the first run. 74 are about the
`plan-marshall` bundle or this repository's tooling; two are about a domain bundle
(`pm-plugin-development`) and both describe a defect already fixed. Per-lesson dispositions, clusters
and reasons: `lessons-archive/INDEX.md`.

| Disposition | Lessons | Where |
|---|---|---|
| high, filed to `live-blockers` | 12 (in 6 messages, `lessons-routing-005`..`-010`) | `live-blockers/inbox/`; bodies in `lessons-archive/filed-live-blockers/` |
| medium, archived | 29 | `lessons-archive/medium/` |
| low, archived | 27 | `lessons-archive/low/` |
| stale, archived | 8 | `lessons-archive/stale/` |

All 76 were removed through `manage-lessons remove` after their copy existed (verdict `superseded` for
the filed ones, `obsolete` for the rest; `2026-09-24-05-001` and `2026-09-24-10-001` needed
`--allow-unreadable`). Corpus after the run: 0 active.

Grading basis: the `live-blockers` `backlog.md` grade where it lists the subject, and that epic's
Open Defects for the two unowned ones. Two lessons were put to the operator as borderline
medium/high: `2026-10-05-17-002` was graded high and filed; `2026-10-09-13-003` stayed medium. 20 of
the 76 had been promoted to the corpus by `live-blockers` itself as "no owning plan here"; five of
those are filed back as high because their subject is a staged plan or an Open Defect there. Checked
against `main` at this run: the eight stale lessons' fixing PRs, and three "still live" notes in the
index. Nothing else was re-checked in code.

The `live-blockers` inbox now holds six undrained messages from this epic. Not landed by this run.

## START HERE

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-LR-01 — the gate. Nothing else in this epic is designed until its two populations land.

## Ordered Queue

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
- 2026-09-22 — **Operator-directed audit: are PLAN-LR-01..06 real work or an accident of
  over-decomposition?** Answer, verified against ground truth (all six spec bodies read, `corpus
  cross-check` run for the first time, and the two named plans' fate checked against `git log`): five
  of six are correctly homed here per this epic's own Inbound Routing rule above (no sibling owns
  audience/ownership classification, the upstream route, provenance, or corpus migration — that is
  *why* this epic exists) and were kept staged, untouched. **PLAN-LR-06 (`manage-lessons-corpus-integrity`,
  WS-05) was RETIRED**, not transferred: its subject (a `remove` call that destroys a lesson while
  reporting `not_found`, with no tombstone) is not a destination question at all — it is exactly the
  "confident signal hides a caveat" pattern this epic's own routing rule assigns to `truthful-signals` —
  and, independently, the fix had *already shipped* the same day the finding was ported in here
  (`truthful-signals-26-09-21/PLAN-TRUTH-144`, PR #1560, `05b5d1ac4`). Filing it as a new finding would
  have duplicated shipped work rather than routed a live one. WS-05 now has zero live plans.
- 2026-09-22 — **OPERATOR RULING: `lessons-routing` is ALWAYS the orchestrator used for a
  lessons-corpus sweep; the separate-dated-epic model is retired.** A sweep just ran as a fresh dated
  epic (`lessons-handling-26-09-22-01`, per the then-current Standing Rule) and completed — 44 lessons
  routed to 5 sibling epics, corpus emptied (full record: `## Lesson Sweeps § 2026-09-22` above). The
  operator then directed: inline that epic's full record into this one and remove its tree, and
  document that this epic is always used going forward. Alternative considered and rejected: keep
  opening a fresh dated epic per sweep — **rejected** by direct operator instruction, not by this
  epic's own reasoning; the Standing Rule section above is amended accordingly. The two PRIOR dated
  epics (`lessons-handling-26-08-08-01`, `26-08-26-01`) are NOT retroactively inlined — this ruling is
  prospective, and reopening closed history to backfill it would be pure churn with no reader benefit.
- 2026-09-23 — **PLAN-LR-07 SHIPPED (PR #1584, `179d4f7f3`), making R15's operator ruling structural in
  the `plan-orchestrator` skill source itself, not just this epic's prose.** Verified: the mode contract
  now states the Fixed-epic-sweep rule, `workflow/lessons-handling.md` routes clusters via `inbox write`
  instead of self-staging (one design refinement over the original spec: cluster routing uses
  `kind=finding`, not `candidate-lesson`, since a bundle isn't one lesson body), and the two stale
  `SKILL.md` cross-references are gone. Bundled an operator-directed `max_iterations: 20 → 5` fix (fully
  disclosed, confirmed as the sole undeclared-surface addition). The run itself cost ~8x its error
  anchor (10.46M tokens, 79% in `6-finalize`, 8 self-review loop-backs) — two off-subject
  candidate-lessons from it were PROMOTED to the global corpus (`2026-09-23-07-001/-002`) rather than
  staged here, since neither is this epic's own subject; the next sweep (now the shipped route-not-stage
  mechanism) carries them to `truthful-signals` and `process-compliance`. Full detail: `landings/PLAN-LR-07.md`.
- 2026-09-23 — **`cleanup` verb: full A1 re-grounding of all 30 claims across PLAN-LR-01..05 against
  HEAD `14d8f3ccd`** (dispatched to an `execution-context-level-5` leaf per the Dispatch Decision Rule —
  213,570 tokens, 103 tool uses). 18 corroborated, 8 contradicted, 4 unverifiable; every contradiction
  was absorbed into its spec (`rescoped: yes`) rather than left blocking. Four load-bearing findings:
  (1) **PLAN-LR-01 D2 is now SETTLED** — the `wrong_store` guard was introduced 2026-07-17, a month
  after the three `cui-jsf-test-basic` lessons were filed, so they predate it and were never routed
  through `--allow-foreign-store`; only `nifi-extensions`' own same-day-adjacent stranded lesson remains
  genuinely ambiguous. (2) **PLAN-LR-04's population claims were fully stale** — `API-Sheriff` moved
  2→16 live lessons (its two originally-named ones are both retired), and `nifi-extensions` (never
  sampled at staging) holds 2 more stranded `plan-marshall:*` findings; D0 must re-derive fresh at
  outline rather than inherit any count on record, including this one. (3) **PLAN-LR-05's cost model
  was INVERTED**, not merely imprecise — `MARSHALL_VERSION` cannot reach `manage-lessons` at all today
  across the executor's subprocess dispatch boundary, so D2's "rare degraded case" is the ONLY reachable
  branch until D1 adds real plumbing; **R11's version-SOURCE ruling is unchanged and was not re-opened**
  — only the effort estimate for reaching it was wrong. (4) **PLAN-LR-02's stale collision map and its
  `PLAN-TRUTH-091` ordering constraint are inert** (that epic closed, the constraint superseded), and
  its `#1050` CodeRabbit-findings caution is discharged (both findings resolved, re-review complete).
  A4 duplication reviewed 376 raw file-overlap rows across 24 active/archived sibling epics — all
  incidental broad-glob coincidences (LR-01's own `manage-lessons/**` recursive glob matching unrelated
  doc-sweep plans); nothing genuinely duplicates this epic's work, so nothing was superseded. A3
  (ambiguity) and A5 (distribution) were clean — no spec missing a required section, no redistribution
  needed. Settled-narrative relocation deferred this pass (no candidate confirmed with the operator) per
  the safe default. Ledger compacted, idempotent. `restart_verdict: not_ready` — 3 new inbox messages
  (sender `api-sheriff-deployment-configurability`) arrived mid-pass, unanalyzed, and this pass's own
  spec edits left 29 uncommitted paths; neither blocks, both are routine follow-ups.
- 2026-09-26 — **THE WHOLE STAGED QUEUE IS PARKED — superseded by PM-MCP** (operator decision relayed by
  `review-apparatus-001`, amended same day). `PLAN-LR-01`…`-05` → `parked`, each spec bannered "Do NOT emit".
  Extraction: 5 specs / 22 rows → 17 carried (12 gap / 5 partial / 0 covered), filed in PM-MCP as
  `doc/known-defects/lessons-routing-carry-over.md` (the one operator-authorized write; operator commits it).
  No emission exception applies (none is foreign-repo config, a PM-MIG enabler, or delivery-breaking). No
  emitted-but-not-launched command existed to void.
  **Is this epic still valid at all?** Its *queue* — no: every plan is Python/prose on `manage-lessons` and the
  lessons workflow, both replaced. Its *subject* — yes, and PM-MCP does not yet own it: PM-MCP covers lesson
  capture and consumption, but places no lesson store, defines no lesson schema, and has no audience /
  upstream route / version provenance / promotion provenance. Those are recorded as structural gaps in the
  carry-over, plus contradiction 1 (`manage-lessons` "Ported" under differential equivalence would port the
  `wrong_store` predicate this epic declared wrong). The lesson SWEEP is also no longer worth running as
  outward inbox routing: its destinations have parked their queues under the same ruling; new lessons belong
  in the PM-MCP carry-over directly. Open operator decisions: (a) retire the 36 carried + 1 stale lessons
  from the corpus; (b) fix the 5 legacy-blocking lessons in legacy under the narrow exception, or accept them;
  (c) the unreadable `2026-09-22-12-001`; (d) close this epic.
- 2026-09-27 — **Operator decisions (a)–(d) settled.** (a)+(c) all 43 swept lessons retired with tombstones;
  (b) the legacy-blocking defects fixed in #1636 (`075ffbb68`), `2026-09-23-23-001` re-verified stale;
  (d) epic stays OPEN — the `lessons` verb resolves to this fixed slug for future sweeps. Cleanup relocated
  the 2026-09-26 sweep record, Open Defects and Watches to `settled.md` (operator-confirmed).
- 2026-10-09 — **Operator ruling: the `ingest` command replaces outward sweep routing.** With a new
  plan-marshall version under way, only high/critical defects in the `plan-marshall` bundle and content
  issues in the domain bundles are still worth fixing; those go to the `live-blockers` inbox, and every
  other lesson is archived in this epic under `lessons-archive/{level}/`. Full rule: § Standing Rule,
  RULING 2026-10-09. Alternative considered: a real `ingest` verb in the `plan-orchestrator` skill —
  not taken, because it would be a feature change to a bundle now limited to high/critical fixes.
- 2026-10-09 — **Inbox drained (2 messages), queue re-parked.** `process-compliance-001` (observed):
  its claim that #1641 (`945e59287`) reverted this epic's PM-MCP-supersession state was verified against
  `88fcfc9ef` — the five `PLAN-LR-01..05` rows read `staged`, the five spec banners were stripped, and
  `inbox/archive/review-apparatus/review-apparatus-001.md` was deleted. Restored: rows transitioned back
  to `parked` (operator-confirmed), the five specs and the archived message checked out from `88fcfc9ef`
  (the only difference was the banner). `orchestrator-refactor-001` (observed): item 1, lesson
  `2026-09-27-07-001`, verified fixed by #1685 (`8aa33cfe1`, on `origin/main`) and retired with a
  tombstone; item 2, six PLAN-09 carry-over rows, held as a Watch below for the next `ingest`.

## Open Defects

> ↪ Relocated to `settled.md` § "Open Defects — superseded by PM-MCP" — every defect was owned by a now-parked plan and is carried to PM-MCP `lessons-routing-carry-over.md`.

## Watches

> ↪ Relocated to `settled.md` § "Watches — superseded by PM-MCP" — every watch re-checked on a now-parked plan; carried to PM-MCP.

- **Six PLAN-09 (#1652) lesson carry-over rows await `ingest` grading** (from `orchestrator-refactor-001`,
  2026-10-09). They are not in the lessons corpus, so the next `ingest` run grades them alongside it
  under RULING 2026-10-09: truncated-payload budget gate; keyless dispatch-boundary records; coverage-gap
  verdict instead of a spent loop-back; outline excluded-vs-declared path reconciliation; merge-commit
  fact from the PR merge record; dedicated refusal for a reserved never-removed resource. Full rows and
  fixtures: `inbox/archive/orchestrator-refactor/orchestrator-refactor-001.md`; source file at the
  archived `orchestrator-refactor` epic, `findings/2026-09-28-plan-09-lesson-carry-over.md`. The sender
  flags possible overlap with lessons `2026-09-23-05-001`/`-002`/`-007` — dedupe at ingest. Retire this
  watch once all six are filed to `live-blockers` or archived.
  **Retired 2026-10-09:** all six graded by the first `ingest` run — row 3 filed in
  `lessons-routing-001`, the other five recorded in `lessons-archive/INDEX.md`. The three lessons the
  sender named for dedup were no longer in the corpus.
