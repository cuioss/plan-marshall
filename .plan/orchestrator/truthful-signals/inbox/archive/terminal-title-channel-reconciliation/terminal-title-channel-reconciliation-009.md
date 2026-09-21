envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=finding
created=2026-07-27T20:42:56Z

# Retrospective-machinery and accounting defects observed in one run

**Source**: PLAN-79 plan-retrospective (PR #1023). Each item below was REPRODUCED during the run,
not inferred. Grouped because they share one root: the measuring instruments are not themselves
measured.

## 1. `manage-logging read --phase` is broken in BOTH polarities

- `--type work --phase 1-init` and `--type work --phase 6-finalize` return the **identical 400
  entries** — the filter is vacuous.
- `--type decision --phase 5-execute` and `--phase 6-finalize` return **0** entries, while an
  unfiltered read returns 96.

Both exit `status: success`. A vacuous filter and an over-filter, in the same flag, reporting
success either way. Any consumer that trusts a phase-scoped log read is reading fiction.

## 2. `metrics.md` is a lie by omission, at scale

`metrics.md` was rendered at 15:28:13 — the instant 6-finalize began — and never re-rendered.
`work/metrics-accumulator-6-finalize.toon` holds `total_tokens: 2298324` (written 20:00:29) and is
never folded in.

Four channels report four different totals for the same plan:
`2,506,872` / `2,298,324` / `1,544,340` / reconstructed `4,805,196`. The plan's real total is
~4.81M; `metrics.md` reports 2.51M — under by roughly half.

## 3. Accounting is biased against the expensive tier

`branch-cleanup` ran 18:05 → 20:18 (~2h13m of a ~12h plan) and is recorded as `duration_ms=0`. So
are `pre-push-quality-gate` (~1000s of whole-tree verify), `ci-verify` (~15min), `push`, and
`architecture-refresh`. Only dispatched-envelope steps get real numbers, because only they carry a
`<usage>` tag.

The consequence is directional, not random: the steps that cost the most wall-clock are exactly the
inline ones, so the recorded profile systematically under-weights the expensive tier. Dispatch-
boundary capture for 6-finalize also stops after step 7 of 22, with no gap marker.

## 4. The retrospective is ORDERED to be blind

The manifest places `branch-cleanup` at 19 and `plan-marshall:plan-retrospective` at 20. By the time
the retrospective runs, the worktree is removed and the branch is merged, so live footprint
derivation returns zero. Measured consequence: artifact-consistency reports **0% recall against 37
declared files**; manifest rules M1–M4 all skip for "no diff data"; routing-decisions has no
footprint. Three aspects report clean-or-skipped because they can no longer see anything — a
structurally guaranteed clean, not an earned one.

## 5. `lessons-capture` runs FOUR steps before the retrospective

`lessons-capture` is step 16; `plan-marshall:plan-retrospective` is step 20. No finding the
retrospective produces can reach the epic inbox in the same run. This message exists only because
the orchestrator hand-routed it afterwards. `orchestrator inbox` still exposes only
`write|validate|detect` — no read, no drain.

## 6. Three defects inside the retrospective machinery itself

- `compile-report` **deletes the fragment bundle on the `warning` path** (reproduced twice),
  destroying the evidence its own warning points at — against SKILL.md's stated retain-on-failure
  contract. Each recovery cost an init plus 15 `add` calls.
- `dispatch_boundaries` and `permission-prompt-analysis` are registry-VALID aspect keys with no
  renderer, so they are silently dropped on every compile.
- `## Executive Summary` renders as `_No executive summary provided._` yet is counted in
  `sections_written[14]`. There is no `executive-summary` key in the valid-aspect registry, so the
  section that `report-structure.md` mandates as *"3–5 sentences leading with overall severity"* has
  **no input channel at all** — and the compile status still reports 14 written.

## 7. The self-review's "clean" was structurally guaranteed

`ext-self-review-plan-marshall` advertises a `symmetric_pairs` detector, but its emitted shape is
`{file, line, name, partner, test_present}` — it asserts **test existence**, never **guard parity**,
and only over *named function pairs*. The defect the bots caught (`ef45f5`) is a set/clear guard-
parity defect where one half is a named owner-scoped function and the other is an inline unguarded
`state.pop()`. That pair can never form, so the detector could not have found it at any effort
level. "250 candidates examined" is a volume number being read as a coverage number.

Related, unreconciled: that same step's dispatch envelope carries `termination_cause: error`
(257K tokens, ~8min) and the step still closed `done` with display detail *"self-review clean"* —
having also filed `4031d9`, a warning-severity finding that required fix commit `419f562c4`.
