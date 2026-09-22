# Epic: Instrumentation Substrate — a measured instruction fleet

slug: instrumentation-substrate

> Ledger document for one epic under `.plan/orchestrator/instrumentation-substrate/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

plan-marshall holds its Python to a quality gate, a test suite, and a coverage number. It holds its
**instruction substrate** — 157 components and ~175k lines of markdown under `marketplace/bundles/**`
— to nothing but assertion. Every hard rule, every `⛔`, every workflow step is a claim about model
behaviour that no harness has ever tested, on a fleet of runtimes of which only one is exercised at
all. This epic closes that asymmetry: a documented rule becomes something that can be shown to hold
or fail under adversarial conditions, on more than one model, at a stated cost.

Done, at the epic level, means three things are true that are false today. A workflow rule can be put
under pressure and produce a three-valued verdict with the population it was scored over. A corpus
edit's effect on a non-Claude runtime is a measured regression signal rather than a hope. And the
price of carrying an instruction is a number somebody can read.

## Non-Goals — the adaptation boundary

⛔ **No upstream artifact is imported.** This epic was seeded by analysis of two external projects —
an agent-skills framework and a workflow-evaluation harness — and carries **ideas only**. No upstream
file, directory layout, prose, configuration schema, or code is copied, vendored, or ported. Every
deliverable is expressed in this repository's own vocabulary: `execution-context-{level}` dispatch,
TOON returns, three-valued verdicts that publish their population, ADR-019's measured-zero-versus-
unobserved-zero discipline, `manage-findings` storage.

⛔ **Convergence is corroboration, not authority.** Where an outside team reached the same shape we
did, that is recorded as independent arrival and nothing more. An outside document with no data is
never cited as evidence for a direction — in either direction.

⛔ **This epic does not run a de-escalation sweep on the shared corpus**, and no plan staged here may
grow into one. That remains gated behind WS-02's evidence and is called out again in every spec that
touches instruction wording.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug instrumentation-substrate
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: RENAMED 2026-09-21 from next-level to instrumentation-substrate (operator decision, pure rename, no content change). RESTART-READY 2026-09-15 state carries over: 5 workstreams, 9 staged/parked plans, scope=1, nothing launched. NEXT ACTION: /plan-orchestrator next slug=instrumentation-substrate. ORDER: PLAN-03 is time-sensitive (antigravity in flight) and its drain-added deliverable 5 says READ arxiv 2605.03353 BEFORE deciding. PLAN-01 carries a mandatory cost-ceiling deliverable plus an early either/or on whether the three-valued verdict or a scored tolerance band holds the three values; that cannot be retrofitted. COLLISIONS RE-READ 2026-09-15: live set fell 5->2; architecture-store-query-truthfulness now hits PLAN-05/06/08/09 (08 and 09 are NEW collisions). Re-run corpus cross-check at emit time, never trust this sentence. PLAN-09/WS-05 reads a git-ignored lessons store the gate CANNOT see; two lessons epics were active pre-consolidation - check lessons-routing post-merge. Routed out: msg 003 to code-intelligence-substrate. Two drained claims were corrected (hook count is 6 events not 1; levels are config-resolved per role) - corrections live in PLAN-08 and the CIS message.
**Phase**: orchestrating
**Inbox (derived)**: 1 queued, 10 archived
**Parked**:
- PLAN-09 (WS-05)
**Queue** (staged, in order):
1. PLAN-01 (WS-01)
2. PLAN-02 (WS-01)
3. PLAN-03 (WS-02)
4. PLAN-04 (WS-02)
5. PLAN-05 (WS-03)
6. PLAN-06 (WS-03)
7. PLAN-07 (WS-04)
8. PLAN-08 (WS-01)
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-03 — the only time-sensitive row in the epic. The `antigravity` target is in flight and
  uncommitted; the calibration-axis question is cheapest to settle before a third runtime ships
  without an answer. It does **not** gate the antigravity work and must not be read as holding it.
- PLAN-05 — sized before staging, per this repository's own rule, and the lever came back **small**:
  26,694 bytes of description across 157 components, median 119 bytes. The spec carries "close it
  unfixed" as a first-class outcome.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug instrumentation-substrate (paste it verbatim after a queue change),
     and rewritten in place by the compact stage at cleanup. Only the LIVE queue is rendered
     here. Per-row notes a reader wants to ADD go in the annotation zone below. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-01 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-findings/; marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 2 | PLAN-02 | WS-01 | staged | marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 3 | PLAN-03 | WS-02 | staged | doc/adr/; doc/developer/marketplace-build.adoc |
| 4 | PLAN-04 | WS-02 | staged | doc/developer/; marketplace/bundles/plan-marshall/skills/eval-cross-model/; test/plan-marshall/eval-cross-model/ |
| 5 | PLAN-05 | WS-03 | staged | marketplace/bundles/; marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/; test/pm-plugin-development/plugin-doctor/ |
| 6 | PLAN-06 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/manage-status/; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 7 | PLAN-07 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/persona-module-tester/; marketplace/bundles/pm-dev-python/skills/pytest-testing/; pyproject.toml; test/pm-dev-python/ |
| 8 | PLAN-08 | WS-01 | staged | CLAUDE.md; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 9 | PLAN-09 | WS-05 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/; test/plan-marshall/manage-lessons/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- PLAN-01 — the seam every other conformance deliverable sits on. Nothing in WS-01 may run before it.
- PLAN-02 — depends on PLAN-01's fixture format. Surfaces overlap with PLAN-01 by construction, so
  the two are sequenced, never paired.
- PLAN-04 — depends on PLAN-03's decision, not merely on its landing: a refused calibration axis
  changes what PLAN-04 is for (it becomes a regression tripwire rather than a calibration instrument)
  without cancelling it.
- PLAN-06 — deliberately staged behind PLAN-05's measurement. If PLAN-05 closes unfixed, re-read
  PLAN-06's premise before launching it; its saving was never independently sized.
- PLAN-07 — surface-disjoint from every other row (it touches the testing standards and
  `pyproject.toml`), so it is the safest candidate to pair if the parallelization scope is ever
  raised above 1.
- **Surfaces were narrowed after the first disjointness check, and the before/after is worth keeping.**
  The first `corpus cross-check` returned **713** file overlaps and collided five of the seven rows
  with live plans. Cause: bundle-wide and `test/`-wide claims that contain every sibling's component by
  containment. Four specs were re-declared at component granularity and four read-only references were
  removed from the declarations entirely. The re-run returns **440** overlaps with only two rows
  touching live plans. ⭐ `source_origin_match_count` was **0** both times — no run of this check has
  ever found duplicate *work*, only over-declared *surface*.
- **PLAN-05 collides with all four live plans, and that collision is real.** It claims
  `marketplace/bundles/` because a description rewrite genuinely reaches repo-wide frontmatter:
  `architecture-store-query-truthfulness` (37 files), `plan-truth-148` (11), `pr-065-settings-repo-
  accumulates-never-lands` (8), `plan-truth-157` (6). ⛔ Do not narrow this declaration to make the
  gate quiet — the claim is honest and narrowing it would be under-declaration, which admits a plan
  that genuinely collides. Sequence PLAN-05 after the live set drains instead, and re-check at emit
  time rather than trusting this note.
- **PLAN-06 collides with `architecture-store-query-truthfulness`** on 5 files under
  `manage-status/`. Also real. Its `manage-status` claim is a HYPOTHESIS that may not survive outline —
  re-check the collision after that hypothesis resolves, since a refuted one removes the overlap.
- **PLAN-08 overlaps PLAN-06** — both declare `platform-runtime/` and its mirror test directory. ⛔
  Sequenced, never paired. PLAN-08 also shares PLAN-02's rule-population hypothesis without sharing its
  surface: reconcile the two enumerations rather than deriving the same population twice and getting two
  answers.
- **PLAN-09 is surface-disjoint from everything, and that reading is partly an illusion.** ⚠ The lessons
  corpus it measures lives in a **git-ignored store outside the inventory**, so `corpus cross-check`
  cannot see it and a concurrent lessons-handling epic working the same store would collide invisibly.
  Two lessons epics are active (`lessons-handling-26-08-26-01`, `lessons-routing`). Check by hand before
  emitting — the gate will not.
- ⭐⭐ **2026-09-15 re-check — the annotations above are already stale, which is the point of re-running.**
  The live-plan set fell from **5 to 2** overnight (three landed: #1488, #1489, #1494). Only
  `architecture-store-query-truthfulness` is comparable now, and it collides with **four** rows:
  PLAN-05 (37 files), PLAN-06 (5), **PLAN-08 (1)** and **PLAN-09 (2)** — the last two are collisions that
  did **not** exist on 2026-09-14, because that plan's realized footprint grew during its own execute.
  ⛔ So "PLAN-09 is surface-disjoint" was true when written and is false now. That plan sits at
  `6-finalize` with its PR already merged to main, so all four collisions should clear once it archives.
  **Re-run the check at emit time regardless — never read these lines as current.**

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`.}

- 2026-09-14 — **Epic created with `parallelization_scope = 1`.** The project default was 1 and the
  operator accepted it unchanged. Alternative considered: 3, matching `truthful-signals`. Rejected
  for now because WS-01's surfaces are not yet cut and a collision would cost more than the
  concurrency buys.
- 2026-09-14 — **`truthful-signals` inbox message 009 absorbed whole.** Its subject — a corpus
  calibrated against one unnamed model, shipped byte-identical to a fleet, with no behavioural eval
  on any non-Claude runtime — is this epic's WS-02 in full. Its own routing note anticipated the
  move, flagging that the mechanism half "may belong with the multi-target generator work instead".
  Retired by supersession rather than archival so it stays resolvable.
- 2026-09-14 — **`truthful-signals` inbox message 010 split, operator-chosen.** Findings 4 (a testing
  standard whose stated precondition was never satisfied) and 5 (a working multi-model evaluation
  harness as prior art) move here; findings 1–3 (doc-drift enforcement placement, approval inferred
  from absence of objection, operator decisions that never reach the spec) stay with
  `truthful-signals`, whose confident-signal-hides-a-caveat theme they match. Alternatives
  considered: absorb wholesale (rejected — findings 1–3 would sit in an epic they do not fit) and
  leave entirely (rejected — finding 5 was filed to answer 009, and splitting the two would strand
  the answer from its question).
- 2026-09-14 — **Inbox drained: 10 messages, all `kind: finding`, all valid, all consumed.** Filed by a
  parallel session from a five-part external course series. Dispositions: 6 folded (001, 005, 007 into
  PLAN-01 and PLAN-02; 006 into PLAN-03; 008 into PLAN-08; 010 into PLAN-09), 2 staged (002 → PLAN-08,
  009 → PLAN-09, opening WS-05), 1 observed as a Watch (004), 1 discarded as out of scope and **routed
  onward** to `code-intelligence-substrate` (003). Alternative considered for 003: keep it here because
  the level ladder is part of the harness this epic measures. Rejected — it is dispatch-tier cost over a
  config surface, which is that epic's charter; and per this repository's own lesson, an offer is not a
  transfer, so it was filed into their inbox rather than named as a destination.
- 2026-09-14 — **Two folded claims were corrected against ground truth rather than absorbed as filed.**
  `next-level-002` claimed one hook family; the machine-local settings declare **six** hook events
  (PreToolUse 3 matcher groups, PostToolUse 2) — the substance survives, the count does not, and PLAN-08
  must derive the enforcer population rather than inherit it. `next-level-003` assumed levels are pinned
  per dispatch site; they are **config-resolved per role**, which shrinks the survey's population and was
  the deciding factor in routing it to `code-intelligence-substrate`. ⭐ Both corrections are recorded in
  the receiving specs, not only here.
- 2026-09-14 — **PLAN-05 sized before staging.** The measurement (26,694 description bytes over 157
  components, median 119) was taken *before* the spec was written, and it argues the lever is small.
  Staged anyway, with "close it unfixed" as a documented outcome, because the measurement itself is
  the deliverable that settles it.

## Open Defects

{Known defects surfaced by landings or observations that are not yet owned by a staged plan.}

- No behavioural or eval harness exists for any non-Claude runtime, while `CLAUDE.md` states plainly
  that "only Claude Code is tested as a runtime" — so a corpus edit lands on the fleet with zero
  regression signal on precisely the models least able to absorb it. — source: absorbed inbox message
  `truthful-signals-009`; **owned by PLAN-04**.
- The generator has no expressive axis below whole-component granularity for instruction calibration,
  and the all-or-nothing `targets:` frontmatter switch is not one (6 components use it, all
  `targets: [claude]`). — source: absorbed inbox message `truthful-signals-009`; **owned by PLAN-03**.
- Property-based testing is documented as a standard in two skills while `hypothesis` appears in no
  source or test file and in no dependency declaration — the standard reads as binding with its own
  stated precondition unmet. — source: absorbed inbox message `truthful-signals-010` finding 4;
  re-verified in this session; **owned by PLAN-07**.

## Watches

{Mid-flight observations that need monitoring but no immediate action.}

- **`next-level-004` — two outside benchmark figures that argue WS-02 and WS-03 are load-bearing, and
  neither is sourced.** An outside whitepaper reframes agent behaviour as `Agent = Model + Harness`,
  dominated by harness quality rather than model quality, and cites two figures for it: a coding agent
  moved from outside the Top 30 into the Top 5 of Terminal Bench 2.0 by changing only the harness, and a
  LangChain study raising a score on the same benchmark by 13.7 points by changing only the system
  prompt, tools and middleware around a fixed model. ⛔ **Both are cited in the body with no matching
  endnote in the paper's own reference list — treat them as unverified secondhand figures.** Why it
  matters: the paper names Claude Code, Antigravity, Codex, OpenCode and Cline as *harnesses*, the same
  axis along which our corpus ships to three runtimes while one is exercised. If the harness genuinely
  dominates, the epic's vision line is not describing a coverage gap at the margin — it is describing a
  gap on the dominant term. ⚠ It sizes nothing for *our* corpus on *our* runtimes, and Terminal Bench
  measures coding agents on coding tasks, not whether a workflow rule survives translation to a
  non-Claude target. Retire this watch if WS-03 sources the figures directly, or if it decides it does
  not need them — trigger: PLAN-04 or PLAN-05 reaching outline.
- The `antigravity` target is uncommitted and in flight. Every claim about it is a snapshot, not a
  contract. Re-check its state before PLAN-03 scopes on it — trigger: PLAN-03 reaching outline.
- The model→target mapping (`opencode` hosting several models; Codex planned) is operator-stated and
  moved during the analysis that produced it. Re-confirm rather than quoting it — trigger: PLAN-03
  or PLAN-04 reaching outline.
- `truthful-signals` was advised to route further fitting deliverables here via the inbox. Watch for
  arrivals and drain them with `analyze` — trigger: next session start.
- Four live plans overlap PLAN-05 and one overlaps PLAN-06. ⚠ The live set is a **moving** population
  — plans land and new ones launch — so this reading is a snapshot and not a standing fact. Re-run
  `corpus cross-check` at emit time rather than reading these annotations — trigger: before emitting
  PLAN-05 or PLAN-06.
- The four specs narrowed to component granularity name directories that **do not exist yet**
  (`instruction-conformance`, `eval-cross-model`). That is correct for a declaration of intent, but it
  means the surface cannot be verified against the tree until the component is created. ⚠ Re-check the
  declared path against what the plan actually creates at its first landing — trigger: PLAN-01 or
  PLAN-04 landing.
