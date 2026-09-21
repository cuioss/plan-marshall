# PLAN-TRUTH-098: A plan's realized footprint is unknowable to the graders whose job is to grade it

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged by `analyze` on 2026-08-22 from PLAN-TRUTH-074's inbox messages `-001` and `-002`.

## Objective

Two independent mechanisms currently prevent a plan's own retrospective from knowing which files
the plan actually changed. The footprint **resolver** has no tier that can read a squash landing,
which is this repository's only merge shape — so every post-merge retrospective here grades blind.
And `references.affected_files`, the declared-footprint side, is written once early and never
reconciled, so scope added after that write is invisible to it. Close both, so the graders that
already report their blindness honestly can stop being blind.

## Problem

**Arm 1 — the resolver cannot see a squash landing.** PLAN-TRUTH-074's retrospective ran after
`branch-cleanup` removed the worktree and after #1134 landed on `main`. All four resolver tiers
failed: no live worktree diff, no realized-footprint capture, no merge-commit, no legacy
`references.modified_files`. `check-artifact-consistency` returned `inconclusive` for both
`affected_files_recall` and `affected_files_exact_match`, and `analyze-logs` emitted
`ARTIFACT_COVERAGE_UNMEASURABLE`.

The footprint was never lost. `git show --name-only c0bbd2d8b` returns the exact 16-file realized
footprint, and feeding that list via `--diff-file` made both `check-manifest-consistency` and
`check-routing-decisions` produce real verdicts instead of `indeterminate`.

The post-landing tier looks for a **merge commit**. This repository merges through a GitHub merge
queue with `pr_merge_strategy: squash`, so a landing produces a single-parent commit and that tier
**can never fire here**. It is not unlucky — it is structurally dead for this repository's merge
strategy, for every plan, permanently.

**Arm 2 — declared scope is never reconciled with added scope.** PLAN-TRUTH-074's deliverable 9
was created mid-finalize by the operator's "Fix it in this plan" disposition of finding `5b1178`.
Its two files are in the solution outline, in the tasks, and in the landing. Neither is in
`references.json`. Measured against the realized 16-file landing:

| Direction | Count |
|-----------|------:|
| Outline declared, absent from `references` | 2 |
| In `references`, absent from the landing | 1 (`manage-status/SKILL.md`, declared `intent: read`) |
| In the landing, absent from `references` | 3 |

`references.affected_files` recall against the actual landing: **13/16 = 81.25%**. A second defect
rides along: the list does not carry declared intent, so a `read`-intent path is indistinguishable
from a mutation-intent one and permanently depresses any recall measured against a diff.

⭐ **The honest reporting is already right and MUST be preserved.** `inconclusive` is correctly
distinguished from a clean pass, and `ARTIFACT_COVERAGE_UNMEASURABLE` correctly refuses to present
an un-run check as a passing one. **The defect is the missing capability, not the labelling** — do
not "fix" this by making an unmeasurable check report a pass.

## Deliverables

### D1 — add a squash-landing tier to the shared footprint resolver

Ordered **after** the merge-commit tier, so the existing tier keeps precedence where it does fire:

1. Read the PR number from `status.metadata` (PLAN-TRUTH-074 carried it at
   `phase_steps["6-finalize"]["create-pr"].display_detail`; `branch-cleanup` records the landing).
2. Resolve the landing SHA through `plan-marshall:tools-integration-ci:ci` — ⛔ never `gh` directly.
3. Read the file list from that single-parent commit.

⛔ **A tier that cannot resolve MUST still return `inconclusive`, never an empty file list.** An
empty list is indistinguishable from "the plan changed nothing", which is exactly the false-zero
this epic exists to prevent.

### D2 — write post-outline scope back into `references.affected_files`

Make the fix-in-plan disposition path union its new deliverable's **mutation-intent** files into
`references.affected_files`. The data is already structured — `manage-solution-outline
list-deliverables` emits per-path `intent` — so this is a set union over machine-readable input,
not a judgement.

### D3 — carry or exclude `intent: read` paths

Either exclude `intent: read` paths from `affected_files`, or carry the intent alongside each path
so consumers can filter. A path the plan declared it would only read must never be counted as an
expected modification.

### D4 — a deterministic three-way reconcile verb

Set-diff `references.affected_files` against the union of every deliverable's declared paths,
partitioned by intent, and report the three-way divergence in the table above. This check would
have caught PLAN-TRUTH-074's gap at plan time; instead it took a hand comparison during the
retrospective. Every count publishes its population.

### D5 — matched controls for both arms

Per the epic's standing rule: each new detector proves it fires on a seeded instance **and** stays
silent on a legitimate near-miss. For D1 the negative control is a genuine merge-commit landing
(the existing tier must still win); for D4 it is a plan whose declared and realized footprints
legitimately agree.

## Claim Labels

- **OBSERVED (first-party, this orchestrator, at HEAD `31211a99b`)**: that #1134 landed as the
  single-parent squash `c0bbd2d8b` on `main` — verified via `git log --grep="#1134"`.
- **OBSERVED (from PLAN-TRUTH-074's own retrospective artifacts)**: the four-tier resolver failure,
  the `ARTIFACT_COVERAGE_UNMEASURABLE` emission, the 81.25% recall figure, and the three-way
  divergence counts. These are the retrospective's measurements, drained via inbox `-001`/`-002`.
- **OBSERVED**: that this repository's `branch-cleanup` step params carry `pr_merge_strategy:
  squash` — read from PLAN-TRUTH-074's own execution manifest.
- **HYPOTHESIS**: that the merge-commit tier is the ONLY tier needing a sibling, i.e. that no other
  tier is also structurally dead here. Confirm/refute against the shared footprint resolver's tier
  list — **verify-at-outline**. The asserted absence is the higher-risk half: an unverified
  "only one tier is broken" ships a partial fix that still grades blind on some path.
- **HYPOTHESIS**: that `references.affected_files` has exactly one writer, so D2's write-back has a
  single site. Confirm/refute against `manage-references` — **verify-at-outline**. ⚠ This epic has
  already been bitten by "a reviewer's list of call sites is a SAMPLE, not an enumeration"; derive
  the writer set from the population, not from a reading.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — the shared footprint resolver
  and the aspects that consume it (`check-artifact-consistency`, `analyze-logs`,
  `check-manifest-consistency`, `check-routing-decisions`)
- `marketplace/bundles/plan-marshall/skills/manage-references/**` — `affected_files` write path and
  the new reconcile verb
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/**` — per-path `intent` read
  (read-only unless D3 lands the intent carry here)
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — the fix-in-plan disposition path
  that must write scope back
- `test/plan-marshall/plan-retrospective/**`, `test/plan-marshall/manage-references/**`

⚠ Paths are full repo-relative, per the R7 standing correction: the disjointness gate cannot
resolve abbreviated or bare surface entries, and 34 such entries already exist in this corpus.

## Dependencies and Sequencing

- **Depends on**: none.
- **Overlaps with**: PLAN-TRUTH-088 (metrics/ledger readers) touches
  `plan-marshall:manage-change-ledger` and the metrics readers, **not** the footprint resolver —
  disjoint on current reading, but ⛔ re-check at emit: both plans read `analyze-logs` output, and
  if either mutates that aspect they collide.
- **Adjacent to**: PLAN-TRUTH-097 (dispatch contract + measurement gates) — also a measurement
  plan, but its surface is the dispatch-boundary recorder and the effort-resolve emission, which
  this plan does not touch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-098-plan-footprint-is-unknowable-to-its-own-graders.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated
in `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Ownership and corroborating evidence — 2026-08-23

⭐ **OWNERSHIP SETTLED BY THE OPERATOR: this epic keeps `-098` and owns BOTH arms.** The subject was
briefly forwarded to `code-intelligence-substrate` in error (a spec with no queue row was invisible to the
dedup check); that message is amended to revision 2 as a **notification only**, and CIS takes no action.
⛔ Do not re-open the ownership question. ⚠ The **base-ref** arm of the same derivation path
(`resolve_base_ref` returning a bare local branch name) IS still CIS's, via `truthful-signals-043.md` —
this spec does not claim it. If a re-derivation shows the two cannot be separated, **record it and
serialize**, do not absorb.

### Independent corroboration from PR #1332 (foreign machine, 2026-08-23)

Both arms were independently re-observed on another machine and filed there as lessons `L2` and `L3`.
⚠ Their figures are that machine's ledger and were NOT reproduced here; the landings were
(`be2a030e9`, `51ff9e59e`, both verified on `origin/main`). Use this as **evidence the arms reproduce**,
not as measurement.

**Arm 1 (squash-blind resolver) — new supporting detail:**
- The retrospective's own honest output: `affected_files_recall,inconclusive,"Plan footprint could not be
  resolved from any tier (no live worktree diff, no realized-footprint capture, no merge-commit, no
  modified_files key) — recall is unmeasurable, not 0%"` — **while the merge commit's diff was exactly the
  20 files `references.json` declared**, i.e. 100 % precision and recall, unstatable.
- ⭐ **The same blindness fires EARLIER in the run, at manifest-compose time** — `pre_push_quality_gate_inactive`,
  *"plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed."*
  ⇒ This arm is **not only a retrospective defect**; it also degrades a live gate decision. Widen the
  verification to cover both consumers.
- **Second remedy shape worth preferring**, from that run: persist a realized-footprint capture at
  `branch-cleanup` **before** the worktree is removed — the `{base}...HEAD` diff is authoritative there, it
  populates tier 2 (which they believe is never written at all), and it survives any future change of merge
  strategy. The PR-number-matching remedy fixes only the squash shape.

**Arm 2 (`affected_files` never reconciled) — new supporting detail:**
- It drifted **twice in one run**, and one drift was **BIDIRECTIONAL** (17 → 19): it under-reported two
  files that WERE modified **and** over-reported three **read-intent** entries that were never modified.
  ⇒ ⭐ **Read-intent contamination is a SEPARABLE SECOND DEFECT** on the writer side and is not covered by
  "re-derive on every commit" alone — entries annotated as read-only intent were written into
  `affected_files` as though modified. Add it to this arm explicitly.
- The second drift (19 → 20) was a **strict subset** missing exactly the file the last commit touched — the
  diagnostic case: the writer simply did not run after that commit.
- **Both reads returned `status: success`**, so no indeterminate-read branch fired; the input looked healthy
  while being wrong.
- ⭐ **`plugin-doctor` survived both ONLY because it cross-checks git and gates the UNION.** That makes it
  the model for the fail-closed read, and it is first-party evidence that consumers without a git
  cross-check read an incomplete set twice in one run.

⚠ **Re-ground every claim above at this plan's own HEAD before acting** — they are a foreign machine's
observations, corroborated in shape but not re-measured here.

---

## Arm 1 — THIRD data point, with the proof this arm was missing (2026-08-24, from PLAN-TRUTH-075 inbox `-004`)

R32 settled that this plan owns both arms. Arm 1 (the squash-blind footprint resolver) now has a
**first-party causal proof** it previously lacked, drained from PLAN-TRUTH-075's own landing:

⭐⭐ **`git log --format="%h %p" 77c9dc70a` returns `77c9dc70a 2cd1a19c8` — ONE parent.** This
repository merges through a **merge queue with squash**, so a landed commit never has two parents. ⇒
**The merge-commit tier can never fire here — not "rarely", NEVER.** Combined with worktree removal at
`branch-cleanup` (order below the retrospective's 995), the resolver is **guaranteed** empty-handed for
every merged plan in this repository. The earlier framing of this arm as a *degradation* understated
it: it is total and structural.

**The measured consequence on PLAN-TRUTH-075 — three deterministic aspects degraded at once:**

| Aspect | Degraded to |
|---|---|
| `check-artifact-consistency` | `affected_files_recall` and `affected_files_exact_match` both `inconclusive` — *"no live worktree diff, no realized-footprint capture, no merge-commit, no modified_files key"* |
| `analyze-logs` | emitted `ARTIFACT_COVERAGE_UNMEASURABLE` |
| `check-routing-decisions` / `check-manifest-consistency` | no footprint against which to test the prune predicates |

⭐ **The footprint was TRIVIALLY available the whole time**: `git show --name-only 77c9dc70a` returns
the 3 files, and supplying it by hand via `--diff-file` produced `files_kept: 3` and real verdicts from
both conditional aspects. **The data existed; only the resolver could not reach it.**

⭐ **Preserve what already works:** the aspects degrade **honestly** — `inconclusive`, never a false
clean. ⛔ **That behaviour is correct and must survive this plan.** The defect is that the degradation
is universal rather than exceptional, NOT that it is reported.

**Two remedies, and the second is cheaper than the first:**

1. Add a **landed-commit tier** to the shared resolver: when no worktree and no merge commit exist,
   resolve the recorded PR number — `status.metadata.phase_steps["6-finalize"]["create-pr"].display_detail`
   carries `#1336` — or the `pr_title`, to its squashed commit on the base branch, then
   `git show --name-only`.
2. ⭐ Have **`branch-cleanup` persist the realized-footprint capture BEFORE it removes the worktree.**
   *That tier already exists in the resolver and is simply never populated.* ⇒ This is a call-site fix
   against existing machinery rather than new resolution logic, and it should be priced first.

⚠ **Sequencing with R33 stands:** Arm 1 is not only a retrospective defect — the same blindness fires
EARLIER at manifest-compose time (`pre_push_quality_gate_inactive`, *"plan footprint unresolvable"*),
degrading a LIVE GATE decision. Verification must cover **both** consumers, and this third data point
does not change that.

## Arm 1 — SECOND independent plan confirms it, and names the missing tier (2026-08-24, PLAN-TRUTH-095 inbox `-006`)

PLAN-TRUTH-075 supplied the causal proof (a squash-merged commit has one parent, so the merge-commit
tier can **never** fire here). **PLAN-TRUTH-095 reproduces the whole failure independently** — *"on this
plan **all four** returned unresolvable"* — and adds two things that plan did not.

⭐ **1. It names the tier that is missing, keyed on data already recorded.** *"Add a post-merge tier to
the footprint resolver keyed on the recorded PR number."* The four existing tiers are: live worktree
diff, persisted realized-footprint capture, merge-commit fallback, legacy `references.modified_files`.
By retrospective time the worktree is gone (`branch-cleanup`) and the squash merge left one parent ⇒
all four are structurally dead **for every merged plan in this repository**. **The PR number is already
in `status.metadata.phase_steps["6-finalize"]["create-pr"].display_detail`**, and resolving it to its
squashed commit makes `git show --name-only` available. ⇒ ⭐ *"the answer was one deterministic call
away the whole time."*

⭐⭐ **2. It confirms R33's plan-time consequence with a first-party observation.** R33 recorded that
Arm 1 is *not only* a retrospective defect — it fires earlier at manifest-compose time. **`-095` saw
it**: `manage-execution-manifest compose` logged
`pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan
footprint unresolvable` **twice**. ⇒ A LIVE GATE decision was degraded, on this plan, twice, by the same
unresolvable footprint. **Verification must cover both consumers — that is now observed, not inferred.**

**The full downstream degradation on `-095`**, wider than `-075`'s:

- `check-artifact-consistency` — both `affected_files_recall` and `affected_files_exact_match`
  `inconclusive`; **the deterministic half of the thoroughness dial simply not measured**
- `analyze-logs` — `ARTIFACT_COVERAGE_UNMEASURABLE`, **disabling the `[ARTIFACT]` emission floor**
- `check-routing-decisions` / `check-manifest-consistency` — needed a footprint fed in by hand
- `manage-execution-manifest compose` — the two `pre_push_quality_gate_inactive` entries above

⭐ **Preserve the honest degradation.** The message says it plainly: *"Every one of these components
failed safe and said so plainly, which is the system working."* ⛔ **The defect is that the degradation
is universal, not that it is reported** — unchanged from `-075`'s framing, and now confirmed on a second
plan.

## Arm 2 — ⛔⛔ A MATCHED-LENGTH DIVERGENCE, WHICH DEFEATS A SIZE CHECK ENTIRELY (2026-08-24, PR #1340 run)

Arm 2 (`affected_files` never reconciled) has a new instance, and it is **qualitatively worse than the
19-vs-37 under-recording already on record**:

> The stored list and the live footprint **disagree on 7 entries each way while both being exactly 29
> long — so a size check reports agreement.**

⛔ **A length comparison — the cheapest and most likely reconciliation anyone would write — returns
CLEAN on a list that is wrong in 14 places.** The previous instance (19 vs 37) is detectable by
counting; **this one is not detectable by any check that does not compare membership.**

⭐ **The consequence was live, not hypothetical.** The disagreeing entry that mattered was the
**rule-catalog path, present ONLY in the live footprint** — and it is the trigger that flips
`plugin-doctor` from scoped to whole-tree mode. ⇒ *"Reading `affected_files` literally would have gated
scoped and left that change ungated across every skill it re-classifies."* **A gate would have run in
the narrower mode against a change that re-classifies rules across the whole tree.**

⭐⭐ **What caught it was the re-fire, not a check.** The run reports `plugin-doctor` flipped
scoped → whole-tree **because the re-fire recomputed the footprint live** rather than reading the
stored list. ⛔ **That is the same accidental protection `PLAN-TRUTH-107` D3 is about to remove**: the
re-fire was doing reconciliation work nothing else does. ⇒ **Arm 2's fix and `-107` D3 are coupled** —
if `affected_files` is not reconciled before D3 lands, a gate that currently self-corrects on re-fire
will stop doing so. **Record the dependency; do not let either land assuming the other.**

⇒ **Verification obligation for this arm:** a membership comparison with a **matched-length negative
control** — two 29-entry lists differing in 7 members each way must FAIL the check. ⛔ A count or
size assertion is not a reconciliation and must not be accepted as one.

---

## ⭐⭐ ARM 3 (NEW, 2026-08-24) — the outline's own scope decision is never compared to what shipped

**This arm is the EARLIEST of the three and the only one nobody has looked at.** Arms 1 and 2 concern a
*resolver* that cannot produce a footprint. **Arm 3 concerns a comparison that is never made at all.**

`phase-3-outline`'s component analysis files a `manage-findings assessment` per candidate file —
`CERTAIN_INCLUDE` / `CERTAIN_EXCLUDE`, with a confidence and evidence. `manage-findings/SKILL.md:32`
classifies the store as **"Working data, read-only after outline"**. ⇒ **It is written at outline,
frozen, and read by NOTHING afterwards.** The diff lands at finalize and the two are never reconciled.

### Measured first-party on `PLAN-TRUTH-095` (merged `b95d78437`)

| | Count |
|---|---:|
| `CERTAIN_INCLUDE` assessed | 22 |
| `CERTAIN_EXCLUDE` assessed | 7 |
| Files actually changed | 26 |
| **`CERTAIN_INCLUDE` assessed, never touched** | **1** |
| **Touched, never assessed at all** | **5** |
| `CERTAIN_EXCLUDE` assessed but touched anyway | **0** |

⭐ **PRESERVE THIS: the `EXCLUDE` discipline held perfectly.** Not one file the outline ruled out was
touched. ⛔ **Whatever this arm builds must not read as a criticism of outline's judgement** — the
judgement was sound; **nothing checks whether the work matched it.**

⚠ The 5 unassessed files are not trivia: they include two test modules and
`script-shared/scripts/_step_completion_marker.py` — **production code changed inside a plan whose
outline never considered it.** And the 1 unrealised `CERTAIN_INCLUDE` was assessed at high confidence
with nothing recording why it was dropped. **Neither is visible anywhere today.**

### ⛔⛔ Two constraints on the remedy, both learned the hard way THIS session

**1. DO NOT give assessments a resolution lifecycle.** They have no `resolution` field **by design** —
they are scope *inputs*, consumed by the decision they informed, not defects awaiting closure. ⛔ This
orchestrator counted a missing `resolution` as `pending` across 29 assessment records, reported *"29
findings never resolved"*, and staged a gate on it; **the claim was false and was retracted** (see
`PLAN-TRUTH-110` § Provenance and epic Watch `W-VIS-a`). **The fix here is a RECONCILIATION REPORT, not
a lifecycle.**

**2. ONE PLAN IS NOT A POPULATION.** The figures above are `-095` alone. ⇒ **D0 must derive the
distribution across archived plans before anyone sizes a fix**, and must publish the denominator — the
archived stores are git-ignored, so state which plans were reachable. ⚠ *Some* divergence is expected
and legitimate: execute discovers surface outline could not have known about, and that is the system
working. **The question is not whether divergence exists but whether it is VISIBLE.**

### What this arm owes

- A reconciliation of the assessment set against the realized footprint, available after the plan lands.
- **Three distinguishable outcomes**, not one number: `INCLUDE` unrealised · touched-but-unassessed ·
  `EXCLUDE` violated. ⭐ **They mean different things** — the third would be a genuine scope breach, the
  second is ordinary discovery, the first may be a silent descope. Collapsing them into a
  "divergence count" would hide the only one that is unambiguously bad.
- ⛔ **Report, do not gate** — for the same reason `-110` D1 was deleted: no failure has been
  demonstrated, only an absence of visibility.

⚠ **Depends on the same footprint resolution Arms 1 and 2 fix** — a reconciliation needs a realized
footprint, and today all four resolver tiers return unresolvable post-merge. **Arm 3 is unbuildable
until Arm 1 lands**; sequence accordingly rather than treating the three as parallel.

## Folded from the PLAN-TRUTH-096 drain (2026-08-24)

Two inbox messages land on this spec's two existing arms. Both are RECURRENCES with fresh
measurements, not new arms — record them as evidence, do not widen the deliverable set.

**Arm 1 — the footprint resolver (inbox `-001`).** All four resolver tiers were unavailable at
retrospective time and **five independent consumers each degraded to unmeasurable on the same
missing derivation**:

| Consumer | How it degraded |
|---|---|
| `manage-execution-manifest compose` | `pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable` (twice, at 4-plan) |
| `check-artifact-consistency` | `inconclusive` for both `affected_files_recall` and `affected_files_exact_match` |
| `check-manifest-consistency` rule M4 | skipped, `base: unknown`, `diff_available: false` |
| `check-routing-decisions` | no footprint until the retrospective hand-supplied one |
| `analyze-logs` | `ARTIFACT_COVERAGE_UNMEASURABLE`, disabling the `[ARTIFACT]`-emission floor |

⭐ **The finding that is new, and it is not about the resolver.** Each of the five reported its own
degradation **honestly and independently**, and **nothing aggregated them**. No surface anywhere said
*"this plan shipped with zero coverage measurement."* Five truthful local signals summed to a silent
global one. ⇒ The arm needs an **aggregation** obligation, not only a fourth resolver tier: when N
consumers of one derivation all report unmeasurable, that fact must surface once, at plan level.

This also confirms R33's prediction first-party: the blindness fires at manifest-compose time, not
only at retrospective time. The `pre_push_quality_gate_inactive` string is the one R33 named.

**Arm 2 — `affected_files` is not a diff in either direction (inbox `-003`).** Measured against the
landing commit range `9999f4d87..77db1a0d3`:

- Declared (`references.affected_files`): **13**. Landed (`git diff --name-only`): **16**.
- **Declared but never landed: 3** — `persona-plan-orchestrator/standards/orchestration-model.md`,
  `manage-execution-manifest/scripts/manage-execution-manifest.py`,
  `test/plan-marshall/manage-execution-manifest/test_reconcile.py`.
- **Landed but never declared: 6** — including `extension-api/standards/ext-point-finalize-step.md`
  and `extension-api/standards/marshal-json-reference.md`.

⛔ The divergence is **bidirectional**, which is the case the aspect's own documentation says cannot
occur (*"`affected_files` is a diff, so a path the deliverable declared it would only read can never
appear in it"*). A one-directional reconciliation would leave the other half live.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24) — the two arms gain their METHOD

Where the `-096` drain supplied evidence, this one supplies the **remedy shape** for both arms. Two
messages, and each names the wrong method the current code uses.

**Arm 2 gains its validation rule (inbox `-004`): validate a footprint ledger by SYMMETRIC
DIFFERENCE, never by cardinality.** A count check passes whenever `|declared| == |landed|` even when
the two sets are disjoint — and `-096`'s drain measured exactly the case that defeats a count
(13 declared / 16 landed, with **3 unlanded AND 6 undeclared**, so no cardinality rule and no
one-directional rule sees both halves). ⇒ The reconciliation must publish **both difference
directions and their sizes**, and a passing verdict must be expressible only as `declared △ landed =
∅`.

**Arm 1/3 gains its input rule (inbox `-003`): derive declared files from the STRUCTURED
deliverables, not by scraping outline prose.** The current derivation reads the outline's
`Files expected to mutate` prose, so a deliverable that states its surface in a table, a nested list,
or a sentence contributes nothing — and contributes nothing SILENTLY, which is why the declared side
of Arm 2's divergence is systematically under-populated. ⭐ This is the same failure mode as
`D-096-d`'s claim parser, in a second component: **a reader that recognises one authoring shape
reports the others as absent.** Fix the two together or the second will be re-discovered.

⛔ **Do not treat the two arms as independently closable any more.** Arm 2's symmetric-difference
check over Arm 1's under-populated declared set would report confident divergence that is partly an
artifact of the scrape. The input rule lands first.

## Folded from the PLAN-TRUTH-086 drain (2026-08-26) — inbox `-004` and `-006`

**`-004` re-confirms Arm 1 VERBATIM, from a third independent run.** *"Footprint resolver has no
squash-commit tier, so a squash-merging repo is uncoverable post-cleanup."* That is this spec's Arm 1
word for word, observed again — first on PLAN-TRUTH-074, now here. ⇒ **Not new scope; it is the
third data point, and it retires any remaining doubt that the post-landing tier is structurally dead
for this repository.** Do not re-derive the mechanism; it is already in § Problem.

**`-006` is NEW and sharper than either arm as written.** *"Three finalize steps derived three
different footprints in one run and each proceeded on its own."*

⛔ This spec's two arms both assume **one** footprint that is wrong. The real state is **three
disagreeing derivations inside a single run**, each feeding a different consumer, none reconciled
against the others, and **each step proceeding on its own answer without noticing the disagreement**.
⇒ A remedy that fixes the resolver (Arm 1) and reconciles `affected_files` (Arm 2) still leaves three
consumers free to disagree, because nothing compares them.

⭐ **D0 must therefore enumerate the DERIVATION SITES, not just measure one footprint's error.**
Publish, per finalize run: how many distinct footprint derivations occurred, which steps consumed
which, and whether they agreed. A single reconciled number is the goal; **the count of derivations is
the thing currently unmeasured.**

⚠ Adjacent and deliberately not merged: `PLAN-TRUTH-113` owns the *declared* surface at the
orchestrator tier. This is the *realized* surface at the plan tier. Three landings now show the
declared side wrong in both directions (`-094`, `-087`, `-086`), so the two arms are converging on
one question — **if outline finds a single mechanism serves both, say so rather than building two.**
