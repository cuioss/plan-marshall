# Landing Analysis: PLAN-TRUTH-042 — A rule that is green because it examined nothing

epic: truthful-signals
workstream: WS-01
pr: #1115 (`aa606b617`, merged to main via merge queue)

> Landing record written by the `analyze` verb. Every claim below was corroborated
> first-party before it was recorded; the operator's finalize report is the lead, the
> artifacts and the tree are the evidence. Two of the report's quantitative claims are
> REFUTED here, with the mechanism named.

## Deliverable Fidelity vs Spec

Documentation-only change, 5 files, +82/-4 — corroborated against the merge commit body
and diff of `aa606b617`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1. Re-assert the zero arch-rule population as an execution-time gate | shipped-as-specified | `quality-verification-report.md` `d0_premise_note`: the population premise was re-asserted at execute time and recorded WITH its coverage conjunction rather than as a bare `count:0`. The one place in the run where the anti-vacuity discipline ran end to end. |
| 2. Author the negative-control obligation centrally + cross-reference | shipped-as-specified | `manage-architecture/standards/arch-gate-fitness-functions.md` authors the normative statement; `pm-dev-java/skills/arch-gate-java/SKILL.md` cross-references rather than restating. |
| 3. Document the ArchUnit polarity trap in the Java arch-gate binding | shipped-as-specified | `arch-gate-java/SKILL.md` — hand-written `ArchCondition` reporting via `violated()` under the `no…` form is silently inverted. |
| 4. Author marker-suppression scope + non-idempotent-rewrite property | shipped-as-specified | Named in the merge-commit body as the second documentation item. |

4/4 shipped as specified. No dropped deliverable, no unplanned addition.

## Metrics and Anomalies

- **Tokens**: `metrics.md` Total **5,157,173 (n=5/6)** dispatched-subagent — matches the
  report's "5.16M". 6-finalize is the dominant phase at 3,635,563 (mixed).
- **Duration**: 3h20m worked / 8h56m wall.
- **Billing-weighted 27,226,216** — but `metrics.md` labels this cell **`(n=1/6)`**: it is
  6-finalize's cost alone, not the plan's. The finalize report presents it as the plan
  total with the population label stripped. The labelling shipped by PLAN-TRUTH-035 worked;
  the consuming report discarded it. **C7 recurrence — a partition quoted as a whole.**

**⛔ REFUTED — two retrospective figures the report repeats as item 5.** The retrospective
claims `metrics.md` renders the 6-finalize row as `-` and that the plan total is 1,438,440,
making 6-finalize "2.01× the whole headline". Read against the on-disk `metrics.md`:

- the 6-finalize Tokens cell reads **3,635,563 (mixed)**, not `-`;
- the plan Total reads **5,157,173 (n=5/6)**, not 1,438,440.

The mechanism is the ordering defect this epic already tracks: **plan-retrospective (995)
reads `metrics.md` before record-metrics (998) writes it.** The retrospective measured a
partial file, and 1,438,440 was the plan total *as of 995*. The "2.01×" ratio is therefore a
complete phase figure divided by a partial plan total — an artifact of the read order, not a
finding about finalize cost. This is the first instance where that known ordering defect did
not merely truncate the retrospective but **manufactured two false quantitative findings that
then travelled into the operator report as facts.** It upgrades the ordering item from a
completeness gap to a correctness one.

**Anomalies corroborated in `work/fragment-dispatch-boundaries.toon`:**

- **All 19 dispatch rows carry 0** for `input_tokens` / `output_tokens` /
  `cache_read_input_tokens` / `cache_creation_input_tokens` — `rows_with_nonzero_context_load: 0`.
  The per-dispatch billing-composition columns are wired at no call site. CONFIRMED verbatim.
- **Two 6-finalize dispatches terminated `cause=error`** (14:28:55, 14:35:27) burning
  392,736 tokens, while `status.metadata.phase_steps` records the owning step
  (pre-submission-self-review) as a single clean `done`. **Not in the operator's five items** —
  a failed-reality-under-a-clean-record instance, squarely this epic's theme.
- `metrics.md` reports 6-finalize dispatch coverage as **"19 of 16 dispatch(es) recorded —
  complete"**. A coverage ratio above 1.0 labelled `complete` means the denominator is wrong;
  the label is not load-bearing here but the ratio is not trustworthy as a coverage signal.

## Routing and Merge Behavior

- **Review — all three bots genuinely participated** (via `ci pr comments --pr-number 1115`,
  the only evidence of participation): coderabbitai 25 comments (20 inline, 2 review bodies,
  3 issue comments), cuioss-review-bot (pr-agent) 1, sourcery-ai 1 review body. 48 comments
  total, 13 still unresolved. Required set for this project is `pr-agent` alone ⇒ quorum met
  with genuine redundancy this time, unlike the recent landings.
- **⛔ The post-rebase re-review was a non-review — CORROBORATED and sharper than reported.**
  CodeRabbit's last real review body is 16:12:44Z. `finalize-step-sync-baseline` then rebased
  onto 5 upstream commits. The `@coderabbitai review` at 17:37:17Z drew, at 17:37:28Z:
  *"⚠️ Action not completed — No files to review … does not re-review already reviewed
  commits."* The registry recorded `matched: true` with `head_sha_verified: false`. **The bot
  said "not completed" and the registry recorded a match** — the merged tree carries no
  CodeRabbit review of the head that merged.
- **False `review_completeness` verdict — CORROBORATED.** The first check passed bare bot
  names where `bot_kind:evidence_kind` pairs are required, so all three bots read absent
  against a PR where all three demonstrably participated. Self-corrected to
  `participation_complete: true`. Had it been trusted, the barrier would have blocked a
  mergeable PR — a fail-closed false negative in the barrier's argument shape.
- **CI/merge**: all checks green, merged via merge queue, worktree removed (confirmed absent
  from `git worktree list`). The removal timeout that deleted LICENSE.md / build.py / pw /
  pw.bat was restored from git and retried non-force — correct call; no `--force` residue,
  all four files present in the tree.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-042 --status shipped`
- [x] row `pr` stamped `1115`
- [x] row `landing` stamped `landings/PLAN-TRUTH-042.md`
- [x] row `plan_marshall_plan_id` stamped `a-rule-that-is-green-because-it-examined-nothing`
- [x] epic.md queue reconciled from status.json
- [x] Open Defects opened: guard `.plan/` blind spot; retrospective-before-record-metrics
      upgraded to correctness; re-review match over a "not completed" reply; dispatch
      billing-composition columns unwired; error-dispatches under a clean step record
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

**1. `post_run_source_guard` `.plan/` exclusion has a tracked-file hole — CORROBORATED, and
broader than reported.** Verified by symbol: `_PLAN_STATE_PREFIX = '.plan/'`, and
`filter_tracked_source()` drops every path with that prefix *after* the porcelain run has
already restricted to tracked files. So `tracked ∧ under .plan/ ⇒ silently exempt`, always.
The report names 2 files; `git ls-files .plan/` returns **14 tracked files**, including
**`.plan/marshal.json`** — the project config — and all 13 `project-architecture/*/enriched.json`.
The guard cannot report a dirty edit to any of them. The two dirty files are exactly the
4 architecture hints described (3 in `default`, 1 in `plan-marshall`), left uncommitted —
correct call, no push to main outside a PR. **→ staged as a new plan spec (below).**

**2. Retrospective vacuity instances — CORROBORATED, five named, and the plan reproduced its
own target defect.** From `quality-verification-report.md`:
   - `shape_violation` detector: 0 violations over an **empty** Surface B (0 `resolve-target`
     rows) against 25 `[DISPATCH]` lines — "a rule that is green because it examined nothing",
     verbatim this plan's own title. The inverse condition actually present (25 dispatches, 0
     recorded resolves) has no category at all.
   - `check-manifest-consistency` skipped `tests_only_diff` as "not applicable" on a
     **namespaced-vs-bare mismatch** (`verify:module-tests` vs `[module-tests]`) — silently
     skipping the ONE rule the decision log records as having fired — then summarised
     `failed:0 findings:0`.
   - `agent-initiated-redispatch`: declared population is the 5-execute boundaries file alone,
     1 row of the 19 recorded ⇒ a 0.00 share computed over **5.3% of the evidence**.
   - `artifact-consistency`: `affected_files_recall` / `exact_match` inconclusive because the
     worktree was gone at branch-cleanup — while the footprint was trivially recoverable from
     `status.metadata.head_at_completion` (`aa606b617`).
   - `settings_review`: steps 2–4 skipped as not-applicable on a zero-prompt input.
   **→ folded into PLAN-TRUTH-045** (the dispatch-audit spec, which already owns the empty
   primary surface and the retry-blind secondary).

**3. ⛔ Plugin-registry marker survey — DONE, and it INVERTS the current anchor.** The anchor
records `unmarked == ['0.1.1304']` with the pin at 1304, i.e. invariant holds. Re-surveyed
first-party at this analysis:
   - 9 version dirs; **`UNMARKED == ['0.1.1240', '0.1.1304']`** — **two** unmarked, not one.
     The invariant is `unmarked == [pin]`; the actual state is `[stale, pin]`, which is the
     exact configuration that seated a session 48 versions backward on 08-07.
   - `.plan/execute-script.py` pins **`0.1.1325`**, which **is** orphan-marked
     (`.orphaned_at = 1786215201115`, epoch-ms) and is not in the registry at all.
   - This landing's own `sync-plugin-cache` step is what regenerated the executor to 1325 —
     the #896 trap re-armed by the finalize that reported it.
   **→ recorded as a finding on PLAN-TRUTH-049, which owns the mechanism.** Repair stays
   operator-only. No independent action taken.

**4. Re-review match over an explicit "not completed" reply → routed to `review-apparatus`**
(PR/review subject wins the routing test outright), together with the `review_completeness`
bare-name-vs-evidence-pair argument-shape defect from item 3 of the report.
