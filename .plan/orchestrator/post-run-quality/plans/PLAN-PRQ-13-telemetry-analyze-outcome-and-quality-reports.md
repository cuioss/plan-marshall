# PLAN-PRQ-13: Re-scope the telemetry `analyze` onto outcomes, and give every plan a unified quality report

epic: post-run-quality
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> ⚠ **MOST OF THIS PLAN'S WORK IS IN ANOTHER REPOSITORY** — the private `cuioss/plan-marshall-telemetry`,
> created by `PLAN-PRQ-07` (PR #1694, landed 2026-10-03). This spec is staged here because this epic owns
> WS-05 and created that repo; the implementing plan must clone or be pointed at it. ⛔ **No checkout of it
> exists on the machine this spec was written on**, so every claim about its *current contents* below is
> labelled `HYPOTHESIS` and D0 exists to settle them. Claims about what was *relocated into* it are
> `OBSERVED` from this repository's own merge diff.

> ⚠ **Scope-bloat guard: eight deliverables, over the ~6 presumption, proceeding unsplit by operator
> decision (2026-10-04).** Recorded rationale: D1–D4 share one subject resolver, one report writer and one
> ontology, and D5's script-plus-manual-fallback structure is a property of the whole skill rather than of
> either report. Splitting would put the shared engine in one plan and its second consumer in another, which
> is the "two independently-authored formatters" failure `PLAN-PRQ-07` deliverable 4 was explicitly written
> to prevent. The alternative offered — a schema-first split — was declined for the same reason.

## Provenance

Operator-directed, 2026-10-04, immediately after `PLAN-PRQ-07` landed. The request has two halves: re-scope
the telemetry `analyze` away from runtime/process aspects and onto **outcomes**, emitting one report file
per plan and per orchestrator; and add a **separate quality file** built on the unified quality ontology
this epic has been circling since it was created.

⛔ **This plan CARRIES the substance of two parked specs rather than waiting on them**, and both are parked
with no path to landing in this repository:

- **`PLAN-PRQ-01` D2 and D3** — the scoring core ("signal presence first, yield second, and the two are
  NEVER folded into one number") and the corpus quality report. `PLAN-PRQ-01` is `parked` under the
  2026-09-26 PM-MCP supersession.
- **`truthful-signals` `PLAN-TRUTH-146`** — the unified findings-ledger vocabulary that `PLAN-PRQ-01` D10
  was to CONSUME and must not re-implement. ⛔ **OBSERVED 2026-10-04: `PLAN-TRUTH-146` is `parked` in its
  own epic**, so that vocabulary will never be built there. D4 below therefore does NOT wait on it and does
  NOT re-derive it from nothing — it extends the ontology that **already exists and already ships**, which
  is the `quality-chain` check's mechanism×resolution classifier (see D4).

## Objective

**The telemetry `analyze` currently inherits a 24-check auditor built to interrogate a RUN — its logs, its
dispatch topology, its lane levers, its process compliance — and almost none of that survives archival or
answers the question the corpus is actually for.** What a corpus of hundreds of archived plans can answer is
about **outcomes**: how long, how many tokens, which PRs, how many lines moved, what kind of project, and —
the part nothing measures today — **how good the result was, on one scale, across plans of very different
shape**.

Two reports per subject, one engine:

1. an **outcome report** — the cheap, durable, mechanically-derivable facts; and
2. a **quality report** — the mechanism×resolution ontology extended to cover every quality gate this
   project actually runs, plus the scope-stability signals the ontology has no home for today.

⭐ **The hard constraint, and the one that shapes the whole design: plan structure has changed over time.**
A corpus spanning months contains plans whose `status.json`, findings families and artifact layout differ.
A script that assumes one shape will silently produce zeros for older plans — which is this epic's founding
defect, applied to the instrument meant to detect it. So D5 makes the skill **script-first but
manual-capable by construction**, and every field distinguishes *not measured* from *not applicable*.

## Deliverables

Eight deliverables. D0 is a gate.

**D0 — GATE: read the telemetry repo and publish the keep/drop partition with its population.** Clone or
open `cuioss/plan-marshall-telemetry` and read (a) its current `analyze` project-level skill, (b) its
`transfer` skill, and (c) the relocated auditor as it now exists there. Then publish, as a table with
counts, which of the relocated checks are KEPT, RE-SCOPED or DROPPED under this plan, over the whole
population — never a sample. ⛔ Nothing downstream starts until this gate has run, because every
`HYPOTHESIS` in this spec is about that repo's current contents and D0 is where they are settled. The
starting partition proposed below is a PROPOSAL from the check names, not a finding:

| Disposition | Checks (names `OBSERVED` from the #1694 merge diff; contents unread) |
|---|---|
| **Keep / re-scope → outcome report** | `metrics`, `token-economics`, `token-efficiency-trend`, `pr-merge-velocity`, `merge-window-accounting`, `scope-estimate-accuracy`, `billing-composition` |
| **Keep / re-scope → quality report** | `quality-chain`, `quality-verification-report`, `cross-check-synthesis`, `recurring-pattern-detector` |
| **Drop — runtime/process, does not survive archival or does not speak to outcome** | `global-log-analysis`, `dispatch-topology`, `execution-context-manifest`, `input-integrity`, `finalize-flow-conformance`, `lane-lever-effectiveness`, `sequence-and-build-minimality`, `task-graph-redundancy`, `task-count-efficiency`, `architecture-lookup-ratio`, `exploration-share`, `track-selection-accuracy`, `preference-pattern-detector` |

That is 7 + 4 + 13 = **24**, which is the whole relocated set — stated so the partition is checkably
exhaustive rather than illustrative. ⚠ **A DROP is not a deletion.** A dropped check's file is retained in
the telemetry repo with a one-line banner naming this plan and the reason; deleting it would destroy the
only record of what the auditor once measured, and this epic's standing rule is that a retired artefact is
the audit record of why it was retired.

**D1 — The outcome report: one JSON file per subject, from a shared engine.** For each archived plan and
each archived orchestrator epic, emit `{subject}/outcome.json`. The format decision is settled: **report
files are JSON** (durable, queryable across a growing corpus, diffable, readable by tooling that knows
nothing about plan-marshall) while the **skill's own stdout stays TOON** per the marketplace convention.
Fields, each carrying its own measurement state per D5:

- `wall_seconds`, `worked_seconds` (⚠ the two are different and the anchors warn that the numerator must be
  worked, not wall — do not fold them)
- `total_tokens`, and a per-phase breakdown
- `prs[]` — every PR the subject recorded as landed, **as a list, never one**; `PLAN-PRQ-07` shipped as two
  (#1692 and #1694, after #1691 closed unmerged), and a one-PR assumption is the exact defect its own
  retrospective reported
- `lines_added`, `lines_modified`, `lines_removed` — ⚠ derived from the merge commits of **every** PR in
  `prs[]` against their first parents, not from a worktree, which no longer exists for an archived plan
- `project_kind` — from D2
- `deliverables_total`, `deliverables_done`

**D2 — Project-kind classification, derived and multi-valued.** Classify each subject's project over a
closed vocabulary — at minimum `skill`, `claude-code`, `java`, `maven`, `javascript` — **derived from
evidence in the subject's own footprint and the project's build files, never from its name**. ⛔ The field
is a SET, not a scalar: a plan touching `marketplace/bundles/**` and `pom.xml` is both, and forcing one
label would make the corpus unqueryable along the axis the classification exists to provide. An
unclassifiable subject reports the empty set with a reason, never a default.

**D3 — The per-orchestrator report, which is NOT a sum of its plans.** Emit `{epic}/outcome.json` for each
archived orchestrator epic. ⚠ It carries the plan roll-up AND the epic-level facts no plan holds: the queue
population by terminal status (`shipped` / `landed` / `superseded` / `transferred` / `retired` /
`resolved`), how many staged specs never launched, and the inbox population drained. ⛔ **A plan that was
`retired` or `superseded` consumed orchestration effort and shipped nothing**, so an epic report that only
sums its shipped plans reports an epic as cheaper than it was.

**D4 — The quality report: `{subject}/quality.json`, extending an ontology that already exists.** ⛔ **Do
NOT invent a new ontology.** `OBSERVED` — the relocated `quality-chain` check already classifies every
`artifacts/findings/*.jsonl` record on two orthogonal axes, and that classifier is the foundation:

- **Mechanism** (ordered by cost and lateness): `build` → `self-review` → `auto-review` → `human-review`,
  plus `other`.
- **Resolution**: `lesson`, `direct_fix`, `loop_back`, `rerun_flake`, `accepted`, `suppressed`, `rejected`,
  `pending` — where `pending` is deliberately split into an **actionable** half (real chain debt) and a
  **structural** half (knowledge-type findings filed to be read, not closed), because counting them
  together produced a population that no defect-fixing work could ever empty.

What this deliverable ADDS, and each addition is a gap in the current axis:

- **Three mechanisms the axis lacks**, each a gate this project actually runs: `simplify`
  (`finalize-step-simplify`), `security-review`, and `sonar`. Today a Sonar finding and a human comment are
  indistinguishable to the classifier, and `simplify` findings have no mechanism at all.
- ⚠ **Separate `auto-review` into its bots.** `OBSERVED`: the current rule classifies a `pr-comment` as
  `auto-review` by substring-matching the detail against `gemini` / `copilot` / `bot` / `automated`.
  CodeRabbit and Sourcery are caught only because their handles happen to contain `bot` — so the axis
  cannot distinguish the bots, and the project's own required/optional bot distinction is invisible to it.
  Carry the bot identity as a field.
- **A scope-stability axis, which the ontology has no home for at all.** Count **requirement changes**
  (post-init edits to the request / refine escalations that changed scope) and **specification changes
  discovered at execute** (deliverables re-scoped, added or dropped after planning closed). These are not
  findings and must not be forced into the findings axes; they are the measure of how much the brief moved
  under the work. `PLAN-PRQ-07` is the worked example — its deliverable 3 was dropped at refine by operator
  ruling, which belongs in this axis and appears in no findings file.
- **The scoring discipline, carried from `PLAN-PRQ-01` D2 and binding:** ⛔ **signal presence first, yield
  second, and the two are NEVER folded into one number.** A gate that was DISABLED and a gate that ran and
  found nothing must be distinguishable in the report. Folding them is what makes a disabled gate read as a
  clean one — this epic's founding defect.

**D5 — Script-first, manual-capable by construction, and every field states its measurement state.** ⭐
**This is the deliverable that makes the other seven survive a heterogeneous corpus.** Plan structure has
changed over time, so a script written against today's layout will meet plans it cannot parse.

- The skill is structured so the **deterministic extraction is one script per field family**, and each
  reports per-subject success or failure rather than failing the whole run.
- Where the script cannot parse a subject, the SKILL.md carries a documented **manual-scan procedure** for
  that field family — what to read, where, and what to write — so an operator or an agent can complete the
  report by hand. ⛔ A manually-completed field is marked as such in the JSON; a hand-derived number that
  is indistinguishable from a machine-derived one is exactly the provenance gap this epic exists to close.
- **Every field carries one of three states, and they are three, not two:** `measured`, `not_measured`
  (the script could not reach it — says WHICH subject and why), `not_applicable` (the subject genuinely has
  no such thing). ⛔ Leaving a field absent, or defaulting it to zero, collapses all three into one and is
  refused. Governing authority: **ADR-019**.

**D6 — De-scope `analyze`, and report what was dropped.** Apply D0's partition: remove the dropped checks
from the `analyze` run, retain their files with the banner, and make the skill's own output state how many
checks ran, how many were dropped by this plan, and how many errored — so a shrinking report is
distinguishable from a silent one.

**D7 — Controls, and they are the deliverable that outlives the rest.** At minimum: a fixture pair of
**two archived plans of DIFFERENT vintage/layout** asserting that the older one yields `not_measured` on
the fields the script cannot reach rather than zeros; a matched positive/negative control for every one of
the three measurement states; a control asserting a multi-PR subject's `lines_*` sums across all its PRs;
a control that `project_kind` returns a SET for a subject touching two kinds; and a control asserting a
disabled gate and a clean gate produce different `quality.json` output.

## Claim Labels

- OBSERVED: the relocated auditor carried exactly 24 checks, named in D0's table — read from the #1694
  merge diff (`git diff --diff-filter=D 2de53ba7c b3aba30aa -- .claude/skills/audit-archived-plan-retrospectives/checks/`).
- OBSERVED: `quality-chain` already classifies `artifacts/findings/*.jsonl` on a mechanism axis
  (`build`/`self-review`/`auto-review`/`human-review`/`other`) and an 8-bucket resolution axis, and already
  splits `pending` into actionable and structural halves — read from
  `git show 2de53ba7c:.claude/skills/audit-archived-plan-retrospectives/checks/quality-chain.md`.
- OBSERVED: that check's `auto-review` rule matches the detail against `gemini` / `copilot` / `bot` /
  `automated`, so it carries no bot identity — same source.
- OBSERVED: `truthful-signals` `PLAN-TRUTH-146` is `parked`, so the unified findings vocabulary
  `PLAN-PRQ-01` D10 was to consume will not be built there — read from that epic's queue 2026-10-04.
- OBSERVED: `PLAN-PRQ-01` is `parked`; its D2 scoring discipline and D3 corpus report are carried by D4
  above rather than awaited.
- ⚠ HYPOTHESIS: the telemetry repo's `analyze` skill today runs the relocated checks substantially as they
  were in this repository — confirm/refute at `plan-marshall-telemetry`'s `analyze` skill entry point
  (verify-at-outline, D0 owns it).
- ⚠ HYPOTHESIS: the relocated `checks/` corpus arrived verbatim and no check was altered during relocation
  — confirm/refute by diffing the telemetry repo's `checks/` against `2de53ba7c`'s tree in this repository
  (verify-at-outline, D0 owns it).
- ⚠ HYPOTHESIS: the telemetry repo is main-only with no PR or review-bot workflow (as `PLAN-PRQ-07`
  deliverable 1 specified), so this plan's finalize lane needs no `create-pr` / `automatic-review` path
  there — confirm/refute at that repo's branch protection and `.plan/marshal.json`, and settle the finalize
  lane at outline before `phase-6-finalize` composes a manifest that assumes a PR.
- ⚠ HYPOTHESIS: `worked_seconds` is recoverable for an archived plan at all. The metrics anchors warn the
  numerator must be worked rather than wall time; if no archived artefact carries it, D1 reports it
  `not_measured` by construction rather than substituting wall time — confirm/refute against an archived
  plan's `metrics` artefacts.

## Expected Surface

⛔ **This surface is almost entirely OUTSIDE this repository**, which has two consequences stated here
rather than discovered: the disjointness gate cannot evaluate out-of-repo paths against this repo's live
plans, and — for exactly that reason — **this plan collides with nothing in this repository by
construction**. It is also the first spec in this epic to declare such a surface, which is itself the
condition `PLAN-PRQ-09`'s folded recurrence describes (a resolver that cannot tell out-of-repo from
untouched).

- OBSERVED (out of repo): `plan-marshall-telemetry/` — the `analyze` skill, its scripts and its SKILL.md: D0, D1, D3, D4, D5, D6
- OBSERVED (out of repo): `plan-marshall-telemetry/` — the relocated `audit-archived-plan-retrospectives` checks corpus: D0, D6 (banners only; no deletions)
- OBSERVED (out of repo): `plan-marshall-telemetry/` — the analysis engine shared by the two report writers: D1, D3, D4
- OBSERVED (out of repo): `plan-marshall-telemetry/` — the test tree: D7
- ⚠ HYPOTHESIS (in repo): `marketplace/bundles/plan-marshall/skills/manage-findings/` — ONLY if D4's three
  new mechanisms require a change to the findings type or source vocabulary on the producing side rather
  than classification on the reading side (verify-at-outline). If they do, that edit lands in THIS
  repository and this plan acquires an in-repo surface it does not otherwise have.

## Dependencies and Sequencing

- **Depends on: `PLAN-PRQ-07` — SATISFIED.** It created the telemetry repo and relocated the auditor
  (PR #1694, landed 2026-10-03). This plan is its direct successor and the second plan in WS-05.
- **Does NOT depend on `PLAN-PRQ-01` or `truthful-signals` `PLAN-TRUTH-146`**, both `parked`. Their
  substance is carried in D4 rather than awaited — see § Provenance. ⛔ If either is ever un-parked, this
  plan's D4 and that spec overlap and must be reconciled before both run.
- **Overlaps with: nothing in this repository**, by construction of the surface above — unless D4's
  `manage-findings` HYPOTHESIS resolves true, in which case re-check against `PLAN-PRQ-09` and
  `PLAN-PRQ-11` (both `parked`, so neither can be in flight) and against the live plan set at outline.
- ⛔ **INHERIT `PLAN-PRQ-03`'s defect rather than reproducing it.** `OBSERVED 2026-10-04`: PRQ-03 declares
  five paths and **four of them no longer exist in this repository** — the whole
  `audit-archived-plan-retrospectives` tree and its test mirror moved to the telemetry repo with PR #1694,
  leaving only `.claude/skills/recipe-plan-review/SKILL.md` behind. Its subject is now split across two
  repositories and it is `parked`, so it will not be fixed where it was staged. The defect it owns is
  directly load-bearing here: **the suspect-zero census excluded itself from its own population**, stated
  outright in the auditor's own SKILL.md — the detector-inside-its-own-population failure, standing
  unresolved in the instrument built to surface it. ⚠ **D1, D3 and D4 emit reports over a corpus that
  includes the subjects that produced them**, so this plan is squarely in that failure's blast radius.
  Whatever D5's measurement-state discipline produces must apply to the analyze run's OWN subject when it
  appears in the corpus, and the report must say so rather than quietly excluding it. PRQ-03's other half —
  `recipe-plan-review` persists nothing, so no corpus question can be asked of its re-check — is adjacent:
  D4's quality report is the obvious place that re-check's result would land, but claiming that surface is
  out of scope here and is **not** folded in.
- ⚠ **Read `code-intelligence-substrate`'s live queue at outline anyway.** Its `PLAN-CIS-036/050/052/054/056`
  declare the relocated auditor's old in-repo paths; those paths no longer exist here, but if that epic
  re-grounds those specs onto the telemetry repo they become live neighbours of this plan. Nothing
  serializes across ledgers.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-13-telemetry-analyze-outcome-and-quality-reports.md"
```

## Write-Boundary

The plan implementing this spec touches the `plan-marshall-telemetry` repository and, only if D4's
`manage-findings` hypothesis resolves true, this repository's own source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns
every other ledger write — and reports its outcome through its PR (or, if the telemetry repo is main-only,
through its landed commits) and its inbox message. The inbox exception's qualifiers and the sole sanctioned
write mechanism are stated in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
