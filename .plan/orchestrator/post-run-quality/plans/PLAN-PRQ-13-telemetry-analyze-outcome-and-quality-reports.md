# PLAN-PRQ-13: Re-scope the telemetry `analyze` onto outcomes, and give every plan a unified quality report

epic: post-run-quality
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> ⚠ **ALL OF THIS PLAN'S WORK IS IN ANOTHER REPOSITORY** — the private `cuioss/plan-marshall-telemetry`,
> created by `PLAN-PRQ-07` (PR #1694, landed 2026-10-03), checked out at
> `/home/oliver/git/plan-marshall-telemetry`. This spec is staged here because this epic owns WS-05 and
> created that repo; the orchestrator owns the ledger, so the brief lives here and the work happens there.
>
> ✅ **CORRECTED 2026-10-04 (same day, before launch): a local checkout DOES exist** at
> `/home/oliver/git/plan-marshall-telemetry`, and this spec's telemetry-repo claims were read from it
> directly. The first draft asserted no checkout existed and labelled them all `HYPOTHESIS`; that assertion
> was wrong and the claims below are now `OBSERVED`. The corrected readings changed the plan's shape — see
> D1's fix-site correction in particular, which the first draft had pointed at the wrong skill.

> ⛔⛔ **RE-CUT 2026-10-04 (operator): this plan does NOT run as a `/plan-marshall` task. It runs as a
> standalone Claude Code session INSIDE the telemetry repository.** The 2026-10-04 emit of a
> `/plan-marshall` command is **VOID** — do not run it.
>
> ⭐ **The Expected Surface was the diagnostic, and the telemetry repo's own README is the evidence.** That
> README declares, in terms: *"Analysis reads the archived files directly. The skills run on a plain Python
> interpreter with the standard library only, and need neither a plan-marshall checkout nor the
> plan-marshall plugin."* And: *"This repository uses `main` only. Changes are committed directly to `main`;
> there are no feature branches, no pull requests, no branch protection, and no review bots."* The repo is
> **designed** to need no plan-marshall, and it carries no `.plan/` and no `.github/` — so there is no
> `marshal.json`, no generated executor and no CI for a lifecycle to drive.
>
> ⛔ **The decisive argument is first-party, not architectural taste.** `PLAN-PRQ-07` ran exactly this shape
> of cross-repo work *through* this repository's plan lifecycle, and its own retrospective reported the
> result: the footprint resolver saw only the final PR, so **111 declared paths that landed in this very
> telemetry repo were invisible to it**, and three instruments graded a plan in which *every deliverable
> shipped* as a possible silent descope — `affected_files_recall` **27.3%** as an **error** grade, 186
> declared-but-unrealized paths, 185 `include_unrealised`. Running the plan that **builds outcome
> measurement** under a lifecycle whose measurement is known-broken for precisely this shape is both
> wasteful and self-defeating. (That defect is folded into `PLAN-PRQ-09`, which is parked.)
>
> ✅ **One consequence is a strict improvement: the disjointness-gate override is no longer needed.** The
> earlier emit required overriding a fail-closed gate (`candidate_comparison_determinate: false`) on the
> strength of a contingent in-repo surface. Under this lane the in-repo work is **split out** (see D4a), so
> this plan declares **no in-repo surface at all** and collides with nothing in this repository by
> construction rather than by argument.

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

**D0 — GATE: publish the keep/drop partition with its population, and DIFF the relocated corpus.** Open
`/home/oliver/git/plan-marshall-telemetry` and read the engine
(`.claude/skills/audit-archived-plan-retrospectives/`), its `checks/` corpus, and the `analyze` and
`transfer` wrappers. Publish, as a table with counts, which of the 24 checks are KEPT, RE-SCOPED or DROPPED
under this plan, over the whole population — never a sample.

⛔ **The gate's second obligation, and it is not optional: DIFF the relocated `checks/` against this
repository's `2de53ba7c` tree before trusting any of them.** `OBSERVED 2026-10-04` — the corpus did **not**
arrive verbatim. `quality-chain.md` was adapted during relocation at two points: its Tier-1 remedy changed
from *"file (or, on Gate-1 dedup, extend) a lesson"* to *"report a candidate"* (correct — that repo has no
lessons store), and its read-only clause changed from *"never edits `.plan/` files"* to *"never edits the
archive"*, dropping two `.plan/temp/` prototype references. Those edits are sensible, but they prove the
corpus was **edited in transit**, so a check's behaviour here cannot be inferred from its pre-relocation
text. Publish the per-check diff verdict (`identical` / `adapted` / `absent`) over all 24.

The starting partition proposed below is a PROPOSAL from the check names, not a finding:

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

⛔⛔ **WHERE THE REPORT FILES MAY NOT GO — read this before D1 and D3.** The first draft of this spec said
`{subject}/outcome.json`, i.e. inside the subject's own archive directory. ⛔ **That violates an invariant
the telemetry repo's README states outright:** *"Entries under `{project-slug}/` are written only by
`transfer` and are never modified or deleted by analysis."* Writing a report into the archive tree makes
**analysis a writer of the archive**, which is exactly what that sentence forbids — and the invariant is
load-bearing, because an archive that analysis can write is an archive whose contents can no longer be
trusted as the record of what the source project produced.

So D1 and D3 emit into a **separate top-level tree**, proposed as
`reports/{project-slug}/{subject}/outcome.json` and `…/quality.json`, leaving `{project-slug}/` untouched.
⚠ **D0 owns the final call and must make it explicitly**, choosing one of exactly two:
(a) honour the invariant and emit outside `{project-slug}/` — **preferred**; or (b) amend the README's
invariant deliberately, with the reason recorded, if there is a compelling argument for co-locating the
report with its subject. ⛔ What D0 may NOT do is write into `{project-slug}/` while leaving the README
asserting that nothing does.

**D1 — The outcome report: one JSON file per subject, emitted BY THE ENGINE.** For each archived plan and
each archived orchestrator epic, emit an outcome report at the D0-settled location. The format decision is
settled: **report files are JSON** (durable, queryable across a growing corpus, diffable, readable by tooling that knows
nothing about plan-marshall) while the **skill's own stdout stays TOON** per the marketplace convention.

⛔ **CORRECTED 2026-10-04 — the fix site is the ENGINE, not the `analyze` wrapper.** `OBSERVED` from that
repo: `analyze/SKILL.md` declares *"It has no computation and no report format of its own … the engine's
`scripts/audit.py` is the only analysis path in this repository and its report schema is the only report
schema. There is no second formatter, so a figure read here and the same figure read from a direct engine
run are always the same figure."* ⚠ **Writing report files in `analyze` would create exactly the second
formatter that skill was written to forbid** — and it is the same single-engine guarantee `PLAN-PRQ-07`
deliverable 4 was built on. So D1, D3 and D4 all land in `audit-archived-plan-retrospectives`; `analyze`
gains at most a pass-through flag and keeps its no-format-of-its-own property.

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

**D4 — The quality report, at the D0-settled location, extending an ontology that already exists.** ⛔ **Do
NOT invent a new ontology.** The complete closed vocabularies and the file schema are written out below in
§ **The taxonomy**, which is normative — this deliverable implements that section rather than re-deriving
it. `OBSERVED` — the relocated `quality-chain` check already classifies every `artifacts/findings/*.jsonl`
record on two orthogonal axes, and that classifier is the foundation:

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

**D4a — IF the three new mechanisms need a producer-side change in `plan-marshall`, that is NOT this
plan's work.** D4 classifies on the READING side, over records already in `artifacts/findings/*.jsonl`, and
the telemetry repo can do that with no plan-marshall involvement at all. ⚠ But if settling D4 shows that
`simplify`, `security-review` or `sonar` findings are not *distinguishable in the records as written* —
i.e. the producer never recorded enough to tell them apart — then the fix is a vocabulary change in
`plan-marshall`'s `manage-findings`, in **another repository, under a different lane**.

⛔ **Do not do it here, and do not reach across.** Record the requirement, name the fields, and hand it
back to the orchestrator: it becomes its own small `/plan-marshall` task in the `plan-marshall` repo, where
that surface lives and where the disjointness gate can actually see it. That split is what lets this plan
declare no in-repo surface — and it is why this plan no longer needs a gate override. Splitting it also
keeps the two halves honestly sequenced: reading-side classification can ship and be useful on today's
records even if the producer side is never changed.

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
disabled gate and a clean gate produce different quality-report output.

⛔ **Three controls the taxonomy specifically owes**, because each guards a claim § The taxonomy makes
rather than a field it merely lists:
- **Mechanism order agrees with the composed finalize order.** The order is derived from step orders
  (`simplify` 5, `security-review` 7, `self-review` 8, `auto-review` 30, `sonar` 40), so a control asserts
  the two agree and FAILS if a step order moves without the axis following. Without it, "derived" decays
  into "asserted once".
- **`not_measured` and `not_applicable` are never interchangeable.** A matched pair: a subject with no PR
  yields `sonar: not_applicable`; a subject whose findings files are unparseable yields
  `sonar: not_measured`. The control asserts the two outputs differ.
- **`pending` is never summed.** A fixture carrying both halves asserts that no emitted figure equals
  `actionable + structural`.

## The taxonomy

⛔ **NORMATIVE. This section is the taxonomy, written out rather than referenced.** The first draft of this
spec described the ontology as "extend `quality-chain`'s axes" plus a prose delta — which is not a
specification, and the reader this plan hands off to is a session in another repository with none of this
epic's context. Every vocabulary below is CLOSED: a value outside it is `other`, never a new value invented
at implementation time.

### Axis 1 — Mechanism: which gate surfaced the finding

⭐ **The order is DERIVED, not a matter of taste.** It is the composed finalize step order, read from
`manage-config list-finalize-steps` (`OBSERVED 2026-10-04`), which is exactly the cost-and-lateness ordering
`quality-chain` already claims for its four values. A finding's mechanism says how far right in the chain
the defect slipped before anything caught it.

| # | Mechanism | Surfaced by | Step order | Status |
|:-:|---|---|:-:|---|
| 1 | `build` | build/test/compile failure during execute | — (execute) | existing |
| 2 | `simplify` | `finalize-step-simplify` | 5 | **NEW** |
| 3 | `security-review` | `finalize-step-security-audit` | 7 | **NEW** |
| 4 | `self-review` | Q-Gate / assessments / `pre-submission-self-review` | 8 | existing |
| 5 | `auto-review` | PR review bots — carries `bot` (see below) | 30 | existing, refined |
| 6 | `sonar` | `sonar-roundtrip`, PR-scoped new-code issues | 40 | **NEW** |
| 7 | `human-review` | a human PR comment | — (any time, latest) | existing |
| 8 | `other` | classified by none of the above | — | existing |

⚠ `simplify` and `security-review` land at 2 and 3 **because their steps fire at order 5 and 7**, before
self-review at 8 — not because anyone judged them cheaper. If the composed order changes, this order
changes with it, and D7 owns a control asserting the two agree.

⛔ **`bot` is a field on an `auto-review` row, not a mechanism value.** The current classifier
substring-matches `gemini` / `copilot` / `bot` / `automated`, so CodeRabbit and Sourcery are caught only
because their handles contain `bot` and are indistinguishable from each other. Carry the identity
explicitly, over the closed set `coderabbit` / `sourcery` / `cuioss-review-bot` / `copilot` / `gemini` /
`other`, plus `required: true|false|unknown` — the required/optional distinction is this project's own and
is invisible to the axis today. ⚠ **`unknown` is required in that triple**, because for an archived plan the
bot roster at the time it ran is not recoverable from the records.

### Axis 2 — Resolution: what disposition the finding received

Unchanged from `quality-chain`, carried here so the vocabulary is readable without the other repository:

| Bucket | Meaning |
|---|---|
| `lesson` | promoted to the lessons corpus. Checked FIRST — it overrides any `resolution` value |
| `direct_fix` | fixed in place |
| `loop_back` | fix deferred into a later task or deliverable |
| `rerun_flake` | a transient / re-run / flake cause. **Not a real defect** |
| `accepted` | acknowledged, not actioned |
| `suppressed` | suppressed |
| `rejected` | the `ext-point-verify` disposition |
| `pending` | `pending` / `none` / empty, **or any value this table does not name** |

⛔ **`pending` is TWO populations and must never be summed.** `actionable` is a defect-shaped finding
nobody closed — real chain debt. `structural` is a knowledge-type finding (`tip` / `insight` /
`best-practice` / `improvement`) filed to be read, not closed by defect-fixing work. Only the actionable
half is a signal: counting the structural half produced a population no amount of defect-fixing could
empty, and a backlog the chain's own work cannot drive to zero is a mislabelled population, not a backlog.

### Axis 3 — Scope stability: how much the brief moved under the work

⛔ **NEW — the ontology has no home for this today, and these are NOT findings.** They must never be forced
into axes 1 and 2. Two counts, each with its instance list:

| Field | Counts | Discovered at |
|---|---|---|
| `requirement_changes` | changes to what was ASKED FOR after init closed — refine escalations that moved scope, operator rulings that added or removed a requirement | `2-refine` onward |
| `specification_changes` | changes to the DELIVERABLE SET after planning closed — a deliverable added, dropped, or materially re-scoped | `5-execute` onward |

Each instance carries `direction` over the closed set `added` / `dropped` / `rescoped`, the `phase` it was
discovered in, and a one-line `basis` naming the evidence. ⭐ **`PLAN-PRQ-07` is the worked example and the
reason this axis exists**: its deliverable 3 was dropped by an operator ruling recorded in the plan's own
`request.md`, and that event appears in **no findings file at all** — so an ontology built only on findings
cannot see the single largest scope change the plan had.

### The two states that are not values

⛔ **Every field in both reports carries a measurement state, and `not_measured` is NEVER written as a zero
or left absent.** The three states and their discipline are D5's; restated here only as the binding on
these fields: `measured`, `not_measured` (the script could not reach it — name the subject and why), and
`not_applicable` (the subject genuinely has no such thing). A plan with no PR has
`sonar: not_applicable`; a plan whose findings files are unparseable has `sonar: not_measured`. **Those are
different facts and the report must not render them alike.** Governing authority: **ADR-019**.

### The file

One quality report per subject, JSON, at the D0-settled location. Skeleton — field names are normative,
the nesting is the implementer's:

```json
{
  "subject": "2026-10-04-cross-repo-telemetry-archive-and-analyze",
  "subject_kind": "plan",
  "schema": "quality-report/1",
  "mechanism_resolution_matrix": { "<mechanism>": { "<resolution>": 0 } },
  "mechanisms": [
    { "mechanism": "auto-review", "bot": "coderabbit", "required": "unknown",
      "count": 0, "state": "measured" }
  ],
  "pending_split": { "actionable": 0, "structural": 0, "state": "measured" },
  "scope_stability": {
    "requirement_changes": { "count": 0, "state": "measured", "instances": [] },
    "specification_changes": { "count": 0, "state": "measured", "instances": [] }
  },
  "gates": [
    { "mechanism": "security-review", "ran": false, "findings": 0,
      "state": "not_applicable", "basis": "step not in the composed manifest" }
  ]
}
```

⛔ **`gates[]` is the scoring discipline made structural, and it is the reason this file exists at all.**
`ran` is **signal presence**; `findings` is **yield**. They are separate fields and are NEVER folded into
one number, because a gate that was DISABLED (`ran: false`) and a gate that ran and found nothing
(`ran: true, findings: 0`) must be distinguishable at a glance. Folding them is what makes a disabled gate
read as a clean one — this epic's founding defect, carried from `PLAN-PRQ-01` D2.

⚠ **What is PROPOSED rather than OBSERVED here**, and D0 settles each against the real records: that the
three new mechanisms are *distinguishable in the findings records as written* (if not, see D4a); the exact
bot-identity token set; and whether `gates[]` can be populated for an archived plan at all, since it needs
the composed manifest and that may not survive archival.

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
- OBSERVED (2026-10-04, read from `/home/oliver/git/plan-marshall-telemetry`): the repo carries four skills
  under `.claude/skills/` — `analyze`, `audit-archived-plan-retrospectives`, `era-stamp-fill`, `transfer` —
  and all **24** relocated checks are present under the auditor's `checks/`. So `PLAN-PRQ-07`'s
  deliverables 2 and 4 are PRESENT, not merely claimed; the landing record's `unverifiable` reading for
  them is superseded and `landings/PLAN-PRQ-07.md` records the correction.
- OBSERVED: `analyze/SKILL.md` declares itself to have no computation and no report format of its own,
  invoking the engine once and surfacing its report verbatim, with `scripts/audit.py` named as the only
  analysis path and only report schema in that repository. This is what moved D1/D3/D4's fix site to the
  engine.
- ⛔ CONTRADICTED (the first draft's claim that the corpus arrived verbatim): `quality-chain.md` was
  **adapted** during relocation — the Tier-1 remedy became "report a candidate" rather than filing a
  lesson, and the read-only clause dropped its `.plan/` references. The corpus was edited in transit, so
  D0 must diff all 24 rather than assume. Verified by diffing against
  `git show 2de53ba7c:.claude/skills/audit-archived-plan-retrospectives/checks/quality-chain.md`.
- OBSERVED: the repo carries `.coderabbit.yaml`, `.gitignore`, `README.md`, `pyproject.toml` and `test/`,
  and **no `.github/` and no `.plan/`** — so it has no CI workflow, no `marshal.json` and no
  `automatic-review` configuration. ⚠ **Consequence for this plan's finalize lane, settle at outline:**
  `phase-6-finalize` must not compose a manifest that assumes a PR, CI verification or review bots for work
  landing in that repository. CodeRabbit is disabled there by that `.coderabbit.yaml`
  (`reviews.auto_review.enabled: false`) and Sourcery in its dashboard; `cuioss-review-bot` never runs
  there for want of `.github/`.
- ⚠ HYPOTHESIS: the repo is main-only by branch protection as `PLAN-PRQ-07` deliverable 1 specified —
  the absence of `.github/` is consistent with it but does not establish the protection setting itself
  (verify-at-outline; `ci repo` read, or the operator).
- ⚠ HYPOTHESIS: `worked_seconds` is recoverable for an archived plan at all. The metrics anchors warn the
  numerator must be worked rather than wall time; if no archived artefact carries it, D1 reports it
  `not_measured` by construction rather than substituting wall time — confirm/refute against an archived
  plan's `metrics` artefacts.

## Expected Surface

⛔ **This surface is ENTIRELY OUTSIDE this repository, and that is now by construction rather than by
accident.** The one contingent in-repo path the earlier draft declared — `manage-findings` — is split out
to D4a, so this plan touches no path in `plan-marshall` at all. Two consequences, both stated rather than
discovered: **this plan collides with nothing in this repository**, and the disjointness gate has nothing
to evaluate for it — which is the correct reading, not a gap, because there is genuinely no in-repo surface
to compare.

⚠ The parser reports these entries as **unresolved** (4 unresolved spans, 0 resolved), because they name
another repository. That is the honest result and is precisely the condition `PLAN-PRQ-09`'s folded
recurrence describes — a resolver that cannot tell an out-of-repo path from an untouched in-repo one. This
spec is the first in the epic to sit entirely on that side of the line.

⛔⛔ **EVERY entry below is PREFIXED with the repository name, and that prefix is load-bearing — do not
"tidy" it away.** A bare relative path such as `test/` or `README.md` resolves against **this** repository,
where both exist and mean something entirely different; a draft of this section that omitted the prefix
made the parser report `test/` (this repo's whole test tree) as a declared surface. The prefixed form
resolves to nothing instead, which is the honest answer for a path in another repository and is exactly
what `PLAN-PRQ-09`'s folded recurrence is about.

⚠ **The section is read MECHANICALLY: a path-shaped token here is a declaration, whatever the prose around
it says.** An earlier draft carried a `⛔ EXCLUDED` bullet naming `manage-findings`, and the parser
declared it regardless — the annotation excluded nothing. So exclusions are stated in D4a and in prose,
**never as an entry in this section**.

- OBSERVED: `plan-marshall-telemetry/.claude/skills/audit-archived-plan-retrospectives/` — the engine, `scripts/audit.py` and its `checks/` corpus: D0, D1, D3, D4, D5, D6 (banners only on dropped checks; no deletions)
- OBSERVED: `plan-marshall-telemetry/.claude/skills/analyze/` — the wrapper, which keeps its no-format-of-its-own property and gains at most a pass-through flag: D6
- OBSERVED: `plan-marshall-telemetry/reports/` — the new report tree D1 and D3 write, subject to D0's location call: D1, D3, D4
- OBSERVED: `plan-marshall-telemetry/test/` — the pytest suite: D7
- OBSERVED: `plan-marshall-telemetry/README.md` — the Layout and Skills sections, which must describe the new report tree; and its archive-write invariant, amended ONLY under D0 option (b): D0, D1, D3

**Nothing in the `plan-marshall` repository is declared, and that is deliberate** — D4a hands the one
possible in-repo requirement back rather than claiming it.

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

## Hand-Off: a standalone session in the telemetry repo

⛔ **NOT a `/plan-marshall` task.** Start a Claude Code session with its working directory in the telemetry
checkout and hand it this file by absolute path as the brief:

```text
cd /home/oliver/git/plan-marshall-telemetry
```

```text
Implement the plan at
/home/oliver/git/plan-marshall/.plan/orchestrator/post-run-quality/plans/PLAN-PRQ-13-telemetry-analyze-outcome-and-quality-reports.md
Work only in this repository. Read § "What replaces the lifecycle" first.
```

The brief stays in this epic's ledger because the orchestrator owns the ledger and a plan spec is a ledger
document. The implementing session MAY copy it into the telemetry repo for its own convenience; that is its
call, and the ledger copy remains authoritative.

## What replaces the lifecycle

⛔ **Dropping `/plan-marshall` drops real guarantees, and each one is substituted explicitly rather than
quietly lost.** A lane that silently sheds its gates is worse than no lane.

| What the lifecycle would have given | What replaces it here |
|---|---|
| Phased execution with a verification sweep | The deliverable order in this spec, D0 first as a hard gate |
| `pre-push-quality-gate`, build + tests | `python3 -m pytest` from the repo root — the README names it, and `pyproject.toml` carries `testpaths = ["test"]`, `pythonpath = [".", "test"]`. **Green before every commit.** No `./pw`: this repo has stdlib-only deps and no pyprojectx wrapper |
| `pre-submission-self-review` | A deliberate self-review pass before the final commit, against this spec's own D7 controls. ⚠ Not mechanised here — state in the run report that it was done and what it found |
| `create-pr`, `ci-verify`, `automatic-review` | **Nothing, by the repo's design.** Its README: *"`main` only … no feature branches, no pull requests, no branch protection, and no review bots."* Commit directly to `main` and push |
| `plan-retrospective`, `record-metrics` | **Nothing automated.** ⚠ See the irony clause below |
| `emit-landing` → an inbox message to this epic | **Nothing.** The epic reconciles from an operator paste instead — `analyze`'s default input mode |
| `archive-plan` | Not applicable; there is no plan directory |

⚠ **The irony clause, stated because it is a real cost and not a joke.** This is the plan that builds
outcome and quality measurement, and it will itself produce **no measured outcome**: no token figure, no
phase breakdown, no retrospective, no recall grade, and no landing facts block. ⛔ **Mitigation, and it is
an obligation not a suggestion: write a run report in the telemetry repo** naming what shipped, what was
dropped and why, every D0 partition verdict, the self-review findings, and the test result — then paste it
to the orchestrator so this epic's landing record is built from something. **This epic has drained exactly
one complete landing in its life** (PRQ-07's, 2026-10-03, the first that ever arrived through the inbox);
this plan will not produce a second, and the run report is what stands in for it.

⭐ **Keep the one thing the lifecycle was not giving you anyway: the brief.** This spec's verify-first
labels, its D0 gate, its measurement-state discipline and its controls are all stated here and do not
depend on any phase machinery to bind.

## Write-Boundary

⛔ **The implementing session writes ONLY inside `/home/oliver/git/plan-marshall-telemetry`.** It does not
edit the `plan-marshall` repository at all — not its source, not its tests, and **not this ledger**.

⛔ **The inbox carve-out does NOT apply here.** The rule that lets an executing plan file its own
`inbox/{sender}-{seq}` message exists for a plan running under the plan-marshall lifecycle with a sender
identity; this session has neither, and there is no `.plan/` in the telemetry repo to write into. It
reports by landed commits on `main` plus the run report, and the operator pastes that to the orchestrator.

⚠ **One boundary is easy to cross by accident and must not be.** The telemetry repo contains
`{project-slug}/archived-orchestrators/` — transferred orchestrator records, including this project's own.
Those are **archive data**, read-only to analysis per the README invariant, and they are emphatically NOT
this epic's live ledger. Editing them would corrupt the very record this plan exists to measure.

If D4a's producer-side requirement materialises it is recorded and handed back, never reached across to.
The orchestrator owns every ledger write; see
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
