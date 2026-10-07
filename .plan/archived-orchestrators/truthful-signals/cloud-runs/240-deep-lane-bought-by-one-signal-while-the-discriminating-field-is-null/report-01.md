# Run report — 240-deep-lane-bought-by-one-signal (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/deep-lane-one-signal-5qyh5k` (harness-assigned)    **PR:** [#1188](https://github.com/cuioss/plan-marshall/pull/1188)    **Outcome:** completed (conditions 1–3 met; auto-merge armed SQUASH; landing delegated to the merge queue)

## Skills loaded

- `cloud-plan-lane` (first action, via `Skill:`)
- `plan-marshall:ref-code-quality` — read from bundle path
- `pm-plugin-development:plugin-script-architecture` — read from bundle path
- `plan-marshall:persona-implementer` — read from bundle path (production-code work identity)
- `pm-dev-python:python-core` — read from bundle path (Python production code)
- `pm-dev-python:pytest-testing` — read from bundle path (Python tests)

All obtained by the bundle-path route (the `plan-marshall` plugin is not installed in this cloud session).

## Deliverables

### D0 — GATE: why is `plan_source` null for an orchestrator-launched plan? (diagnostic, mutates nothing)

**Break located, by symbol: `plan_source` is *never written* to `status.metadata` for the
file-pointer (orchestrator-spec) source branch.**

- The router reads the field at `manage-status/scripts/_cmd_planning_lane.py::_evaluate_signals`
  → `plan_source = metadata.get('plan_source')` (reads `status.metadata.plan_source`).
- phase-1-init seeds `status.metadata.plan_source` at exactly two sites:
  `phase-1-init/SKILL.md` **Step 5b.5** (lesson → raw `lesson_id`) and **Step 5c** (doc-shaped lesson →
  `"recipe"`). Both are `source == lesson`-only.
- The orchestrator-spec source arrives as a **file-pointer `description`** (SKILL.md Step 4:
  `implement {repo-relative-path}`). That branch calls `request create --source-id "{spec_path}"`
  (Step 4/Step 5.1), so the pointer **is** captured — but as `source_id` in `request.md`'s header,
  **a different key in a different file** than the `status.metadata.plan_source` the router reads.
  There is **no** plan_source-seeding step on this branch (no analogue of 5b.5).

So of D0's three candidate breaks — *never populated / populated too late / populated under a different
key* — the answer is a combination: **populated under a different key (`source_id` in `request.md`),
and never bridged to `status.metadata.plan_source`.** It is **not** a late-arrival ordering problem.

**Does it generalise? YES — categorically, not n=1.** Every orchestrator-launched plan ingests a
file-pointer `description`, and that branch categorically lacks the plan_source seeding step. So
`plan_source` is null for *every* orchestrator-launched plan, not just the observed instance. Blast
radius = the whole orchestrated population, exactly as the ⭐ root-cause section anticipated.

**Ordering-versus-scoring verdict (required explicit in the report):** the field is **never written**
(not late) → a *population* fix (D3b), which is a data-layer change, not a scoring change. **But
populating `plan_source` does NOT fix the over-escalation**, and this is the load-bearing part of the
gate: in the recorded vector **S1 did not fire**. S1's predicate is
`s1_deep = free_form_source and s5_deep`, and `s5_deep = not request_concrete`; the recorded
`request_concrete: True` makes `s5_deep = False`, so `s1_deep = False` **regardless of `plan_source`**.
The deep verdict was bought by **S7 (risk_prose) firing alone**. Therefore the scoring change (D2
corroboration) is **independently necessary and correctly targeted** — it is *not* a scoring change
masking a late-arriving field (the failure archetype D0 warns against). The plan_source population
(D3b) is a separate correctness fix whose value is (a) the field reflects real provenance, (b) D1's
confidence report shows it resolved rather than null, (c) it removes a structural null from the vector.

**Token figure:** the "~1.2M dispatched tokens / 29%" figure is **not re-derivable** from any artifact
reachable in this clone (the decision log, orchestrator ledger, and metrics live under `.plan/`, which
is git-ignored and absent). **No token figure is carried into any justification.**

### D1 — make an unresolved signal visible in the decision — DONE (commit `567c703`)

Added a `confidence` block to `evaluate_signals_pure` and the route return/decision-log:
`signals_total` / `signals_resolved` / `signals_null` / `null_signals` / `low_confidence`
(low-confidence = more inputs null than resolved). For the recorded vector this reports 3-of-7
resolved, 4 null — so a 1-of-4 decision no longer reads like a 1-of-7 one. **Asserted-absence check
(claim table):** confirmed the route record carried no prior signal-resolution field (only
`scope_provenance`, which is band observability, not vector confidence), so D1 adds genuinely new
information.

### D2 — require corroboration for prose-only routing — DONE (commit `567c703`)

Chosen lever: **corroboration** (see Design decisions). Implemented in `evaluate_signals_pure`: when
`fired == ['S7:risk_prose']` and `scope_estimate` is the resolved non-committal middle band
(`single_module`), S7 moves to `suppressed_signals` and the lane is `light`. **Rejected alternative
recorded:** provenance-exemption of spec bodies (the verify-first check refuted the "prose fires on
markup" hypothesis — the sensor scores semantic vocabulary, so exemption would suppress genuine
warnings). `surgical` (positively-earned narrow band) is untouched, so the prior false-negative fix's
test is preserved verbatim.

### D3 — tests, each verified red pre-fix — DONE (commit `567c703`)

`test/plan-marshall/manage-status/test_planning_lane_corroboration.py` (12 tests). Red-first verified
by stashing the router change and running the file against the pre-fix router:
- (a) `test_d3a_recorded_vector_does_not_route_deep` — red pre-fix (lane=`deep`), green post-fix.
- (b) `test_d3b_orchestrator_spec_resolves_plan_source_nonnull` — red pre-fix (`plan_source` None),
  green post-fix.
- (c) `test_d3c_several_nulls_reported_low_confidence` — red pre-fix (no `confidence` key), green post-fix.
- (d) `test_d3d_control_deep_warranting_vector_still_routes_deep` — the CONTROL. Pre-fix its lane
  assertion held (deep→deep) but it referenced the new observability keys, so it errored red; post-fix
  green. Its teeth are against an over-de-escalating fix: the deep vector fires S1/S2/S3/S4/S5 — none of
  which the corroboration touches — so a fix that de-escalated it would have to suppress non-prose
  signals, which this one demonstrably does not.
Plus a don't-fight regression (`surgical` + S7-alone still deep), a corroborated-S7-still-deep case,
and the metadata-wins / plaintext-stays-null bridge cases.

## Design decisions (D2 lever choice — recorded per D2's "record the rejected alternative")

**Verify-first result (claim-table HYPOTHESIS "prose fires on markup"): REFUTED.** `_RISK_PROSE_RE`
(`_cmd_planning_lane.py` lines ~172-176) fires on **semantic scale-warning vocabulary** — `multi-PR`,
`codebase-wide`, `largest`, `riskiest`, `expect a split`, `foundation`, `campaign`, and prose `epic`
(the `epic:` metadata-key form is excluded by a `(?!\s*:)` lookahead). It does **not** score the
⛔/⚠/⭐ house markup. Confirmed against `test_planning_lane_risk_prose.py`'s eight-phrase parametrization.

**Chosen lever: corroboration (D2 condition 1 — "contradicts a resolved scope estimate").**
S7 does not carry the lane *alone* when the scope estimate resolved to the **non-committal middle band**
(`single_module` — resolved, but neither deep-biasing nor positively-narrow). Implemented via the
module's own frozensets: `fired == ['S7:risk_prose'] and scope_estimate is not None and scope_estimate
not in _DEEP_SCOPE_ESTIMATES and scope_estimate not in _NARROW_SCOPE_ESTIMATES` (the residue is exactly
`single_module`).

**Rejected lever: provenance-exemption (D2 condition 2 — exempting spec-pointer bodies from S7).**
Rejected *because the verify-first check refuted the markup hypothesis*: the sensor scores semantic
vocabulary, so blanket-exempting spec bodies would suppress a **genuine** author scale warning embedded
in a spec ("this really is codebase-wide"), degrading a real signal to placate a measurement artifact —
which the plan's Out-of-scope explicitly forbids ("the markup is load-bearing… the sensor must learn
provenance", not "specs stop firing S7").

**Re-grounding against the prior false-negative fix (claim-table: "the two must not fight").**
The prior fix added S7 so an author's explicit "this is multi-PR" *outranks a positively-earned narrow
band* (`test_s7_is_not_relaxed_by_the_narrow_and_concrete_carve_out`: `surgical` + S7-alone → deep).
The chosen corroboration is scoped to **`single_module` only**, so:
- `surgical` (positively-earned bound, `_NARROW_SCOPE_ESTIMATES`) + S7-alone → **deep**, unchanged — the
  author-override case the prior fix protects survives verbatim (no existing S7 test is modified).
- `single_module` (the router's catch-all "could not concretely bound"; where prose-heavy orchestrator
  specs land) + S7-alone → **light** — the recorded structural false-positive.
The two do not fight: the prior fix's goal (don't under-route genuinely-large changes) is preserved —
a genuinely large change fires a corroborating signal (broad/unknown scope → S2, generative
change_type → S3, breaking compat → S4, or no anchors → S5), and the explicit `--lane-override` (S6)
and mid-execute escalation ratchet remain.

**D3b lever choice: router-side resolution, not write-time seeding.** `plan_source` is resolved at the
router from `request.md` provenance (`source: description` + non-empty `source_id`) when
`status.metadata.plan_source` is null. This deliberately does **not** write `status.metadata`, to avoid
activating phase-2-refine Step 13.5's narrative-vs-code validator (and its extra q-gate) for the entire
orchestrated population — a ceremony increase that would work against this epic's own theme. The fix is
kept inside the defective component (the router / manage-status), the plan's Expected surface.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (`_cmd_planning_lane.py`
and the new test file). Build takes its full path.

- `./pw quality-gate` — clean (`issues[0]`, coverage COMPLETE: mypy/ruff/SPDX/plugin-doctor).
- `./pw verify` — **SUCCESS**: 19243 passed, 14 skipped in 431s; quality-gate + test-compile +
  whole-tree pytest all clean.
- Per-commit gate: the implementation commit was preceded by a clean `./pw quality-gate`.
- No lockfile churn: `git status --porcelain` clean after both `quality-gate` and `verify`; deliverable
  paths were staged explicitly (never `git add -A`).

## Findings

**Step 6 pre-PR verification sub-agent (general-purpose, read-only).** Verdict: implementation
satisfies D0–D3; no blockers, no correctness defects. It independently substantiated each deliverable
against the source (not the report), and surfaced one reinforcing insight: **S1's firing condition is a
strict subset of S5's** (`s1_deep ⟹ s5_deep`), so resolving `plan_source` (dropping S1 from `fired`)
can never change the lane — S5 co-fires in exactly the same cases. That makes the D3b bridge
provably lane-neutral, which is the intended property.

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 1 | sub-agent | Nit — SKILL.md Scripts-table row for `planning-lane route` still described the decision-log line as naming only signal values / predicate / posture / `scope_provenance`, omitting the new `confidence` and `suppressed_signals` (the parallel `**route**` bullet WAS updated). | **Fixed** (commit `a80ae4c`) — row now names both. |
| 2 | sub-agent | Nit — module-docstring S1 row listed the source as only `status.metadata.plan_source`, omitting the `request.md` provenance-header fallback (the SKILL.md S1 row WAS updated). | **Fixed** (commit `a80ae4c`) — row now names `_resolve_orchestrator_plan_source`. |
| 3 | sub-agent (re-sweep) | Nit — `cmd_planning_lane_route`'s function docstring singled out `scope_provenance` as carried by both the return and the decision-log line, now equally true of `confidence` and `suppressed_signals`. Third spot of the same class; the re-sweep confirmed no other stale parallel description remains skill-wide. | **Fixed** (commit `1ec3b77`). |
| — | sub-agent | Observations, not defects: `manage-status.py:679` argparse help ("any deep-precondition signal forces deep") was already an approximation before this change (the carve-out already made it non-literal); D3(d)'s pre-fix red was a missing-key KeyError, which is the correct control property (its lane assertion is stable across the fix); the plan's prose "1-of-4 resolved" is looser than the code's precise 3-resolved/4-null. | Recorded; no action. |

All three were doc-consistency gaps (findings 1–2 introduced by this change; finding 3 predated it but is
the same class); all fixed, and the agent's skill-wide re-sweep confirmed no other stale parallel
description remains. No correctness defects were found. CI/PR-review findings appended below as they
arrive.

## Reviewer participation

Expected reviewer population, derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(cross-named by `.github/workflows/pr-agent.yml`): **`cuioss-review-bot`** (pr-agent.md),
**`coderabbitai`** (coderabbit.md), **`sourcery-ai`** (sourcery.md).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Published a "PR Reviewer Guide" over the diff (issue-comment surface): "PR contains tests / No security concerns identified / No major issues detected." A clean review — no actionable findings. |
| `coderabbitai` | `rate-limited` | Published only a quota notice (issue-comment surface): "Review limit reached… Next review available in 28 minutes." Engaged, did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published only a quota notice (**review-summary body surface — `get_reviews`, not `get_comments`**): "you have reached your weekly rate limit of 500000 diff characters." Did not review this diff. |

**Coverage: 1 of 3** — `cuioss-review-bot` reviewed (clean); `coderabbitai` rate-limited (window reopens
~28 min); `sourcery-ai` rate-limited (weekly quota). **Step 8 shortfall disclosure fired:** stated in
words to the operator before arming auto-merge (below). Rate limits are routine and outside our
control — a disclosure, not a merge block (§ Step 8 condition 4). No inline review threads existed on
any surface; no actionable comment required a fix or reply.

Reading all three surfaces was load-bearing: `sourcery-ai`'s notice lived **only** in the
review-summary body (`get_reviews`), which the issue-comment read (`get_comments`) does not fold in — a
run that skipped `get_reviews` would have recorded `sourcery-ai` as `silent` instead of `rate-limited`.

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness does not surface
  a per-run token count to the running agent, so no figure is reported rather than a guessed one.
- **Wall-clock:** ~20 min of active work (PR #1188 created 2026-08-12T18:01:51Z; merge gate reached
  ~18:20Z), plus one `./pw verify` (~7 min) and CI (~13 min) that overlap the agent's own turns.
  Source: PR/commit timestamps and the local `./pw verify` duration line (431s).
- **Population:** this single Claude Code cloud session's own activity. ⛔ **NOT comparable** to a
  plan-marshall `metrics.toon` total: that counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's per-task billing boundary, which a single interactive cloud session does not share.
  The two figures cannot be made comparable, so none is presented as if they were.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; each step checked against what actually happened and its artifact
confirmed on disk.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | done | Named in § Skills loaded; all via the bundle-path route (plugin not installed). |
| 2 Branch | done | `claude/deep-lane-one-signal-5qyh5k` (harness-assigned) exists on `origin`; pushed before any edit. |
| 3 Plan directory | done | `…/240-…/plan.md` exists; opens with the ⛔ first-instruction block (verified at read). |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; D0–D3 addressed. |
| 4 Per-commit gate | done | Every `*.py`-touching commit was preceded by a clean `./pw quality-gate` (`issues[0]`, coverage COMPLETE). |
| 4 Pushed | done | No unpushed commit (verified `git status -sb` before the merge gate). |
| 5 Build gate | done | Python changed → `./pw verify` SUCCESS (19243 passed, 14 skipped); recorded in § Build gate. |
| 6 Verification sub-agent | done | Dispatched (general-purpose, read-only); 3 doc nits found, all fixed and re-verified; no correctness defects. § Findings. |
| 7 PR cycle | done | PR #1188; all three comment surfaces read; every comment dispositioned (no actionable findings). |
| 8 Merge gate | conditions 1–3 met | verify/conclusion success + `mergeable_state: unstable` (required contexts satisfied); no open comments; report finalized+pushed as the last pre-merge commit; then auto-merge armed (SQUASH). Landing confirmation recorded to the operator. |
| 8 Bridge | done | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; report carries PR # and per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Below. |

GitHub access path: **GitHub MCP server** (the cloud path). Branch form: **harness-assigned**
(`claude/*`). A `/sync-plugin-cache` is **not owed** — it is a machine-local build step a cloud run
never performs or records (§ Scope and precedence).

## What have we learned (Step 9)

**None proposed.** The run exercised the contract end to end and every step's artifact was produced as
written; no step was ambiguous in practice, none failed in this environment, and no command behaved
differently than the contract describes. The one friction — `send_later` returned "requires approval",
so no unattended self-wake was possible — is already covered by the contract: § Step 8 names
manual read-polling for a still-active session as the in-session alternative, and it worked exactly as
described (the read surface `pull_request_read` is not gated, so the whole CI/review/merge gate was
driven by on-demand reads). The three-surface comment read and the registry-derived reviewer
population both behaved as the contract promises — `sourcery-ai`'s rate-limit notice lived only in
`get_reviews`, precisely the false-clean trap § Step 7 warns about. Nothing this run produced is
evidence of a contract gap, so no amendment is proposed (a speculative improvement is not a proposal).

## Residue

- **Owed work (out of scope here, per plan):** the "context helper that can never succeed at the outline
  phase for worktree-using plans" was folded into the source spec as a WEAK merge and is **excluded**
  from this plan. It is a single-site, falsifiable claim ("can never succeed") and deserves its own
  plan. Recorded here so it is not lost as an unowned lead.
- A sibling plan quantifies the same run from the metrics-renderer side; surface-disjoint from this
  router change.
