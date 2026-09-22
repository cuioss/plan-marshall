# PLAN-60: In-House Gate ↔ CI/PR-Bot Coverage Parity

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25). Gathers the "all in-house gates green, only the PR
> bot / CI caught it" family: gaps where a local gate structurally cannot see a defect that CI or a
> review bot does. Fix the open coverage gaps and promote the landed residues. LARGE.

## Objective

Repeatedly, a defect passed every in-house gate and was caught only by CI or a PR bot — because the
local gate's scope or ruleset omits the class. Close the concrete open gaps and codify the
coverage-parity rule so a new gate declares what it structurally cannot evaluate rather than passing
silently.

## Deliverables

### D1 — GATE: enumerate the open parity gaps + fix shapes (mutates nothing)
Confirm each open gap against source and decide fix shape + promotion home (candidate:
`phase-6-finalize/standards/pre-push-quality-gate.md` + `ref-code-quality`).

### D2 — ruleset parity (in-house lint/typecheck matches CI)
- `2026-06-22-13-001`: add the `RUF` family to `pyproject.toml` `select=` so RUF002/RUF059 fail locally, not only at the PR bot.
- `2026-07-24-13-001`: `pre-push-quality-gate` runs `mypy test` (test-compile) so test-tree type errors fail before CI.

### D3 — scope parity (gate footprint matches CI footprint)
- `2026-07-21-11-003`: add a zero-scoped-modules / docs-only branch to the module-tests divergence gate (no null `recommended_target`).
- `2026-07-21-21-002`: escalate non-bundle root footprint (`marketplace/targets/**`, module `default`) to the whole-tree gate instead of falling through the per-bundle sweep.

### D4 — new in-house detectors for PR-bot-only classes
- `2026-06-25-02-001`: a body-prose non-portable-token detector (dated/versioned/machine-path tokens) as an in-house gate.
- `2026-07-21-10-002`: automatic-review completeness guard distinguishes a structurally-absent bot (no check-run) from an in-progress one via a checks-status presence probe before `loop_back`.
- `2026-07-17-09-001`: a same-run reconciliation contract between an automatic-review-committed line and finalize-step-simplify dead-code removal (honor the in-run reviewer commitment, not ad-hoc judgment).

### D5 — promote residues + retire
Promote the return-contract-completeness and blast-radius-surfacing residues; retire all carried lessons at finalize.

## Lessons Carried (bound 2026-07-25 · lessons-triage)
Carry each at phase-1-init (`convert-to-plan`); retire at finalize.

- `2026-06-22-13-001` — **OPEN** — RUF family absent from local ruff select (D2).
- `2026-07-24-13-001` — **OPEN** — pre-push-quality-gate lacks test-compile mypy parity (D2).
- `2026-07-21-11-003` — **OPEN** — quality-gate divergence gate has no zero-scoped-modules branch (D3).
- `2026-07-21-21-002` — **OPEN** — marketplace/targets root footprint un-gated (D3).
- `2026-06-25-02-001` — **OPEN** — no in-house dated/versioned/machine-path token detector (D4).
- `2026-07-21-10-002` — **OPEN** — completeness guard conflates absent bot with in-progress (D4).
- `2026-07-17-09-001` — **OPEN** — no simplify↔automatic-review same-run reconciliation contract (D4).
- `2026-06-20-16-002` — docs-only footprint needs a green freshness path (consume build-decision not_necessary) — landed #899, promote.
- `2026-07-17-09-002` — scoped finalize plugin-doctor now surfaces (warn/widen) whole-tree rule class — landed #915, promote.
- `2026-07-23-02-001` — a documented return-contract field must be in the return dict on every path, not only a side-effect sink — landed #988, promote.

## Expected surface
- `pyproject.toml` (ruff select); `phase-6-finalize/standards/pre-push-quality-gate.md` + gate script
- automatic-review completeness guard; a new token detector (plugin-doctor or self-review)
- finalize-step-simplify reconciliation contract; a governing coverage-parity standard

**Disjointness:** finalize-gate + pyproject + automatic-review. Adjacency: `phase-6-finalize` shared
with PLAN-52 (baseline-reconcile, different file) and PLAN-59 — coordinate at outline.

## A green `quality-gate` is a strictly weaker gate than `verify`

Message-supplied, HYPOTHESIS until re-verified at outline. **`quality-gate` excludes `test/`, so it
says nothing about type errors in tests.** On #1037 it passed green and **three mypy errors reached
`verify`** — the in-house gate cleared work CI then rejected.

This is the exact parity gap this plan owns, with a measured instance: the gate is not *weaker in
degree* but **weaker in domain**, and its green carries no signal about the excluded domain. ⚠ The
fix is not necessarily "include `test/`" — that may be a deliberate speed trade. **The defect is that
the gate's green reads as whole-tree assurance when it is scope-limited by construction.** Either
extend the domain or make the exclusion visible in the verdict; do not leave a green that means less
than it appears to.

## The whole-tree test-compile gate sees what mypy-over-test-only cannot

Message-supplied, HYPOTHESIS until re-verified at outline. **A whole-tree test-compile gate catches
errors that running mypy over `test/` alone cannot see.** Together with the #1037 finding above
(`quality-gate` excludes `test/`, so three mypy errors reached `verify`), this settles the shape of
the parity fix: **the gap is not one missing directory but two different analyses**, and adding
`test/` to the existing gate would still not reach what the whole-tree compile reaches.

⚠ **Do not treat "include `test/` in quality-gate" as the fix and close the parity question.** D1
must state which analysis each gate performs and what each therefore cannot see — a gate whose green
is scope-limited must say so in its verdict.

## CodeRabbit found two real defects EVERY in-house gate passed

On #1039 the in-house gates all went green — `pre-push-quality-gate` (bundle + whole-tree,
test-compile and module-tests), `plugin-doctor` (3 skills, 30 rules, 0 issues),
`pre-submission-self-review` (125 candidates, 1 finding), `finalize-step-simplify` (0 findings) — and
**CodeRabbit still found two real defects**: a negative `--max-per-component` producing a
spuriously-truncated result, and a duplicated disposition table.

⛔ **This is the parity question stated as an outcome rather than a mechanism.** The gaps already
recorded here (`quality-gate` excludes `test/`; whole-tree test-compile sees what mypy-over-`test/`
cannot) are *specific*; this is the general measurement: **a full green in-house sweep is not
evidence of correctness, and today nothing quantifies the residual.**

⚠ **D1 should treat "what did review catch that the gates did not" as a measurable, recurring
signal** rather than a one-off — it is the only direct read on parity we get, and it arrives free on
every PR. ⚠ But note the confound now recorded across four PRs: **the bots are frequently refusing**,
so an absence of review findings is often an absence of *review*, not of defects. Any parity metric
must exclude PRs where the reviewer refused, or it will report improving parity as coverage collapses.

## Write-Boundary
Repository source + tests only; NO `.plan/local/orchestrator/` writes. See orchestration-model.md § Ledger Write-Boundary.
