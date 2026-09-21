# Landing Analysis: PLAN-18 — merge-queue-coexistence

epic: plan-optimization
workstream: WS-09
pr: 952 — https://github.com/cuioss/plan-marshall/pull/952 (merged `464f53ec1`)

> Landing record for one shipped plan. Claims verified against ground truth: PR #952 confirmed
> `state: merged` via the CI abstraction; merge commit `464f53ec1` on `origin/main`; the merged diff
> inspected (`git show --stat`) — 10 files corroborate all four deliverables (github_ops probe/enable
> discriminator, merge-queue-setup steward flow, manage-config defer signal, +2 new test files).
> **This is the LAST plan of WS-09 and of the epic's original Wave-2 queue.**

## Deliverable Fidelity vs Spec

The spec carried A/B/C plus the never-mutate-foreign invariant. At outline the **central premise of A was
falsified**: A claimed the queue-create path omits `bypass_actors` — true of the standards doc
(`github-impl.md`), false of the code (`github_ops.py`), where bypass-actor support was already shipped.
Refine verified A against the doc and passed the bad premise through; **outline caught it against source**
and rescoped A to its genuine residual (the silent bypass-less-create arm + the stale doc). The
re-grounding this plan's own spec instructed ("re-ground citations at outline") did its job.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| A — bypass actors on create (release-safe) | shipped-modified (premise re-grounded: support already shipped) | collapsed to D1 — warn loudly on bypass-less mandatory-queue create + stale-doc reconcile (`github-impl.md`, `merge-queue-setup.md`) |
| B — detect external queue regardless of ruleset name; treat as authoritative | shipped-as-specified | `github_ops.py` (+53) `externally_managed` discriminator on probe+enable; zero-mutation asserted at argv (`test_repo_merge_queue.py` +93) |
| C — project-config defer signal | shipped-as-specified | `merge_queue_managed_externally` in `_config_defaults.py` + `_cmd_quality_phases.py` probe short-circuit + `test_use_merge_queue_validation.py` (+71); `data-model.md`/`api-reference.md` reconciled |
| Steward flow consuming A/B/C | shipped-added (decomposed) | `merge-queue-setup.md` (+77) MQ-0 defer gate + externally-managed branch + `warnings[]` surfacing |
| Invariant — never mutate a foreign ruleset | shipped (verified) | security-audit verified the never-mutate-foreign invariant in code |

Net: **4/4 (A re-grounded, B/C as specified, steward flow decomposed).** WS-09 desired outcomes A/B/C
complete; D was PLAN-19 (shipped #944). **WS-09 COMPLETE.**

## Metrics and Anomalies

- Tokens: ~2.4M
- Duration: 1h41m worked / 7h52m wall
- Anomalies:
  - **Spec's central premise (A) was wrong and the pipeline caught it** — the marquee event. Refine
    verified a behavioural claim against a STANDARDS DOC and passed a false premise; outline caught it
    against SOURCE. Produced this run's one new lesson: **verify behavioural claims against source, not
    standards docs.** This is the Nth confirmation of the epic-wide docs-drift pattern (PLAN-06/14/17/19
    all re-grounded stale citations) — see Follow-Ups; it directly motivates PLAN-24's "reproduce, don't
    fix on the doc" and PLAN-25's inventory.
  - **marshalld stopped for the pre-push gate** (735s clean) — the known build-queue-unit-test
    contamination (lesson 22-001, plan-server epic surface). Handled, not a defect.

## Routing and Merge Behavior

- Review: **Gemini drove all review value — while pruned (sunset 07-17).** It caught a REAL bug:
  `dict.setdefault('project', {})` returns `None` on a present-but-`None` key → fixed. Sourcery was
  rate-limited (the 13-21-001 class again). Pre-submission self-review caught 1 contract-source drift
  (`data-model.md`) and fixed it. **Vindicates the standing rule: never ignore a pruned bot's output**
  ([[feedback_infra_steps_must_be_opt_in]]) — and sharpens PLAN-21 D3 (removing gemini from defaults must
  NOT mean ignoring its findings).
- CI/merge: 24/24 finalize steps; squash-merged via the queue. **Fitting proof: at merge time the probe
  reported `externally_managed: true`** — this plan's own D2 code correctly classifying the org-managed
  queue it was built to coexist with. CI green at `0c662a1` then 11 checks at merge HEAD.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-18 → shipped, pr 952, plan_marshall_plan_id `merge-queue-coexistence`, landing recorded
- [x] epic.md queue reconciled (WS-09 row 18); **WS-09 marked complete** (PLAN-18 + PLAN-19)
- [x] 2 config observations opened as Watches (adr-propose lane-vs-manifest; CI-wait-budget)
- [x] docs-drift meta-pattern reinforced (new lesson; ties to PLAN-24/25)
- [x] resume_anchor updated — original Wave-2 queue fully DRAINED; only WS-10 (6 follow-ups) remains
- [x] START-HERE block regenerated

## Follow-Ups

- **Meta-lesson: verify behavioural claims against SOURCE, not standards docs** (new this run) — the
  epic-wide docs-drift pattern, now confirmed a 5th time (PLAN-06/14/17/19 + PLAN-18). The pipeline's
  refine→outline re-ground gate is what catches it every time; the standing gap is that refine trusts
  standards docs. Candidate to fold into PLAN-25 D4's inventory (docs that assert behaviour the code
  contradicts are a species of the same core-vs-reality drift) OR a standalone refine-hardening item.
- **⚠ Owed operator action COMPOUNDED: `/marshall-steward` + session restart.** `marshal.json` was stale
  at start (the PLAN-13 debt, still unpaid), the executor regenerated (session-pinned agent set may have
  changed — this is exactly PLAN-13 D5's reload-directive territory), and merged commits bumped to
  **0.1.1162**. A steward pass + restart before the next plan is now advisable, not merely owed.
- **NEW Watch — `adr-propose` lane-vs-manifest precedence gap:** `adr-propose` carries `lane: off` yet the
  composer still emits it into the manifest; the run honoured the opt-out manually. A lane opt-out that
  the composer ignores is a real precedence defect. Plan-worthy on recurrence — candidate fold into
  PLAN-20 (execution-accounting) or a config-precedence item.
- **NEW Watch — CI-wait budget too small:** the 600s CI-wait budget is consistently exceeded by this
  repo's ~13-min verify job, so every CI wait costs two polls. A cheap config tune (raise the budget or
  make it adaptive, cf. the plan-14 adaptive `ci:wait` work #877). Logged; act on convenience.
- **Sourcery rate-limit (13-21-001) recurred again** — already owned by PLAN-21 D1; recurrence noted.
