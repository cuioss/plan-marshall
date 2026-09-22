# PLAN-62: Build-Timeout & Learned-Value Truthfulness

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25). Gathers the build-timeout family where a
> self-rewriting learned value silently caps or mis-reports a build, producing a false `timeout` or
> under-running a passing build. Coordinate with PLAN-57 (which fixes the routing-facing half of
> stale learned values).

## Objective

Adaptive/learned build timeouts silently self-cap below the architecture-resolved bound and are
consumed as ground truth, producing false `status:timeout` on passing builds and under-runs. Make the
learned value never override the resolved bound downward, give every build engine a truthful floor,
and enforce the bounded-wait inner<outer invariant.

## ⚠ Cross-repo live instance + OBSERVED root cause (TokenSheriff, operator-relayed 2026-07-26)

A TokenSheriff session (worktree `issue-597`) passed an explicit **`--timeout 1800`** to a whole-tree
verify. The build was killed at **658 s**. The operator's agent had to read the daemon log to learn
that, because the surfaced signal was **"failed with exit code 1"** / **exit code −1 with duration 0**.

**ROOT CAUSE — OBSERVED first-party at HEAD, and the arithmetic reconciles exactly.**

- `manage-run-config/scripts/run_config.py:243`:
  `timeout = default if persisted is None else int(persisted * SAFETY_MARGIN)`
  **The caller's `default` is DISCARDED outright the moment ANY persisted value exists.** An explicit
  caller-supplied timeout is treated as a *fallback for the unlearned case*, never as a request, a
  floor, or an override. `--timeout 1800` never had a chance.
- `:24` `SAFETY_MARGIN = 1.25`; `:26` `MINIMUM_TIMEOUT_SECONDS = 120`. The floor is applied via
  `max(...)` (`:244`) — so a learned value can only ever be raised to 120 s, **never clamped up to a
  caller's explicit request**.
- **Arithmetic check:** `527 × 1.25 = 658.75 → int() = 658`. The reported cap is exactly a learned
  value of ~527 s put through `SAFETY_MARGIN`, which sits right beside the agent's measured ~538 s
  real build. The 658 s did not come from the request or from any global cap — **it came from the
  learned value, and only the learned value.**
- **HYPOTHESIS (verify-at-outline) — key mismatch explains the 1447 s the operator saw.** The
  operator observed run-config holding **1447 s** while the wrapper used 658 s. Those cannot both be
  the same entry (1447 × 1.25 = 1808, not 658), so the value consulted was stored under a
  **different `command_key`** than the one the operator inspected. Confirm/refute at the
  `command_key` construction in the build engine's `timeout_get` call site versus the keys present in
  the project's run-config. If confirmed, the learned store is keyed finer (or coarser) than the
  command actually executed, so a long whole-tree verify inherits a short module build's learned
  duration.

**The reporting defect is the epic's flagship archetype, and is arguably the more expensive half.**
A timeout is not a build failure, yet it surfaced as `exit code 1` and as `exit −1 / duration 0` —
the "job never ran" signature. Nothing in the returned envelope said *timeout*, *658 s*, or *your
requested 1800 s was discarded*. The operator's agent recovered the truth only by reading the daemon
log, and its first (reasonable) reading was "that's not a build failure, that's the job never
running." **A timeout must be reported AS a timeout, naming the bound that fired and where that
bound came from.**

**Scope note for D1:** this adds an *explicit-request-is-discarded* deliverable beside the existing
learned-value-truthfulness ones. If that pushes the plan past the six-deliverable split guard, split
the reporting half (timeout surfaced as failure) from the resolution half (explicit request ignored,
key mismatch) rather than growing one plan.

## Deliverables

### D1 — GATE: map the timeout-derivation seams + floor shape (mutates nothing)
Confirm each open defect at HEAD; decide the floor derivation (from the architecture-resolved
`bash_timeout`, not a static constant) and the `--timeout` override semantics.

### D2 — `--timeout` is a true override / no silent downward cap
- `2026-07-16-16-003`: `run_config.py` must honor an explicit `--timeout` instead of discarding it when a persisted value exists.
- `2026-07-21-09-001`: the adaptive internal timeout must not self-cap below the architecture-resolved `bash_timeout` (false `status:timeout` on a scoped run).

### D3 — truthful floor across all engines
- `2026-07-22-00-001`: the per-task `bash_timeout_seconds` stamp gets a floor analogous to `PYTEST_OUTER_FLOOR_SECONDS`, derived from the resolved bound, not the volatile learned figure.
- `2026-07-21-09-001` (residue): derive the static floor from architecture `bash_timeout`; pass a `min_timeout` on the Maven/Gradle/npm engines too (Python-only floor today).

### D4 — bounded-wait margin invariant + tests + retire
- `2026-07-21-21-001`: enforce an inner<outer margin on the CI-complete-precondition wait (a bounded-wait script whose inner timeout equals the harness Bash ceiling always loses and auto-backgrounds with zero output).
- Tests: a passing build near the learned value does not report `timeout`; an explicit `--timeout` binds; each engine carries the floor. Finalize retires the carried lessons.

## Lessons Carried (bound 2026-07-25 · lessons-triage) — all OPEN
- `2026-07-16-16-003` — `--timeout` discarded when a value is persisted (D2).
- `2026-07-21-09-001` — adaptive timeout self-caps below resolved `bash_timeout`; static floor + non-Python engines (D2/D3).
- `2026-07-22-00-001` — per-task `bash_timeout_seconds` has no floor, under-ran a passing build by 70s (D3).
- `2026-07-21-21-001` — bounded-wait inner==outer ceiling always loses the race (D4).

## Expected surface
- `manage-run-config` timeout derivation; `build-pyproject` / `build-maven` / `build-gradle` / `build-npm` timeout floors
- `tools-integration-ci` `ci_base.py` bounded-wait margin; tests under `test/plan-marshall/**`

**Disjointness:** run-config + build engines + ci wait. **Coordinate with PLAN-57** (shares the
stale-learned-value theme; PLAN-57 owns the routing-facing `execution_tier` half, this owns the
build-timeout half) and PLAN-42 (landed, ci-wait mechanism).

## Write-Boundary
Repository source + tests only; NO `.plan/local/orchestrator/` writes. See orchestration-model.md § Ledger Write-Boundary.
