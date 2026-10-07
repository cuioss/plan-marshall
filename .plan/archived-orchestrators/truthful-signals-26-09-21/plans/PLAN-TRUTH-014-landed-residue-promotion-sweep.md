# PLAN-TRUTH-014: Landed-Residue Promotion Sweep

> Renamed from **PLAN-65** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25). Housekeeping sweep: ~24 lessons whose FIX already
> shipped but whose durable generalizable RULE was never promoted into its governing skill. Promote
> each residue into the owning skill's standards, then retire the lesson (the corpus keeps recent/
> active lessons; permanent rules belong in skills).
>
> ⚠ **Wide surface** — these residues touch ~15 governing skills. The plan does NOT change behaviour
> (docs/standards additions + at most a parity test); its collision risk is broad, so it is
> **low-priority, emit-late**, and its D1 gate MAY split it into per-governing-skill sub-batches
> emitted serially to keep each landable. Operator elected to keep it whole; splitting is a D1 option.

## Objective

Promote each already-landed lesson's generalizable rule into the standards of the skill that owns the
surface, cross-linking the shipped fix as a worked example, then retire the lesson. No production
behaviour changes; the deliverable is durable guidance that makes the next author inherit the rule.

## Deliverables (grouped by governing area — D1 may re-batch)

### D1 — GATE: confirm each residue is still un-promoted + batch (mutates nothing)
For each carried lesson, confirm the fix is in current source (already verified at triage) and the
rule is NOT already in the governing standard. Drop any already-covered residue to a bare retire.
Decide the sub-batch boundaries (by governing skill) and whether to split into serial follow-ons.

### D2 — build & script-shared residues

⭐ **ADDED 2026-07-27** (PLAN-62 landing #1022, inbox `-005`, read first-party). The
harness-kills-background-jobs behaviour is already standing knowledge; **these three pieces are NOT,
and they are the durable residue** — promote them alongside the existing rule:

1. **The buffering property that makes the obvious diagnostic vacuous.** The build wrapper's output is
   buffered until completion, so while a job runs the output file is empty — and after a kill it is
   *also* empty. **The two states are byte-identical.** An empty background-job output file is not
   evidence of "still running" and not evidence of "killed"; it carries no information at all, and
   polling it is reasoning from a constant.
2. **The change-ledger is the substitute oracle.** A build that actually ran appends a `kind=build`
   row stamped with the `worktree_sha`; no row means the build did not complete, whatever the output
   file looks like. Same substrate `5-execute` reads for its freshness assertion. ⚠ **Promote this
   with the caveat, not without it** — PLAN-TRUTH-010 / PLAN-82 (the latter now `code-intelligence-substrate`'s) have established that `kind=build` rows are
   themselves currently over-inclusive (a `--help` invocation and a pure log read both stamp one), so
   the ledger is the *best available* oracle, not yet a sound one. Promoting it as unconditionally
   authoritative would create a fresh vacuous-authority instance, which is this epic's n=6 archetype.
3. **The mitigation that actually worked:** foreground + explicit Bash `timeout` of 600000ms, letting
   the harness auto-background at its own ceiling. Observed asymmetry — harness-initiated
   auto-backgrounding preserved the job every time; caller-initiated `run_in_background` was killed
   twice on the same ~640s build.

Evidence basis: run-observation during #1022's finalize (two kills, zero output, no ledger row;
subsequent foreground invocations all completed). **Not derivable from the shipped diff** — label it
as run-observation when promoting.
`06-21-00-001` (internal-id→config-namespace audit), `06-30-15-001` (sort traversal at source),
`07-07-10-001` (anchor summary line first), `07-15-22-001` (finally swallows own exception),
`07-19-16-002` (footprint classifier fail-safe both directions), `07-21-17-001` (mypy_path dual-reg),
`07-22-07-002` (daemon re-entrancy emission gate), `07-22-20-005` (empirical interpreter parity).

### D3 — finalize / manifest / executor / status residues
`07-14-16-002` (per-branch merge-helper test + provenance granularity), `07-14-17-002` (regenerate
with post-merge script + py_compile self-check), `07-17-09-003` (return-then-persist), `07-21-12-001`
(canonicalize-and-migrate key seam), `07-13-00-001` (a Task-dispatching step can't be a dispatched
leaf), `07-19-12-001` (archived-store read fallback ⇒ sibling mutation guards + output-contract).

### D4 — git / github / providers / io residues
`07-17-08-001` (git porcelain column-sensitivity), `07-14-17-001` (full-shape identity check + filter
external list elements), `06-22-11-001` (document the exact async completion condition), `07-21-12-002`
(quote possibly-empty shell placeholders), `07-08-09-001` (unlink-before-copy CWE-59).

### D5 — init / phase-1 / testing residues + owed promotion + retire
`07-22-10-001` (placeholder names the field), `07-23-10-002` (classify-by-syntax-before-existence),
`07-23-10-003` (enumerate missing/unreadable/undecodable refusal branches), `07-23-10-001` (isolation
tests must not assume tmp outside repo), `07-21-15-002` (**owed** fail-closed-guard-can-actually-fail
section into persona-module-tester). Retire each carried lesson as its promotion lands.

## Lessons Carried (bound 2026-07-25 · lessons-triage) — all fix-landed; promote-then-retire
`06-21-00-001`, `06-22-11-001`, `06-30-15-001`, `07-07-10-001`, `07-08-09-001`, `07-13-00-001`,
`07-14-16-002`, `07-14-17-001`, `07-14-17-002`, `07-15-22-001`, `07-17-08-001`, `07-17-09-003`,
`07-19-12-001`, `07-19-16-002`, `07-21-12-001`, `07-21-12-002`, `07-21-17-001`, `07-22-07-002`,
`07-22-10-001`, `07-22-20-005`, `07-23-10-001`, `07-23-10-002`, `07-23-10-003`, `07-21-15-002`.

Carry each at phase-1-init (`convert-to-plan`); retire ONLY once its promotion lands (a residue whose
D1 gate finds it already covered is bare-retired instead).

## Expected surface
Standards docs across `build-pyproject`, `script-shared`, `manage-config`, `manage-execution-manifest`,
`tools-script-executor`, `manage-status`, `automatic-review`, `marshall-orchestrator`,
`workflow-integration-git`/`-github`, `manage-providers`, `phase-1-init`, `manage-plan-documents`,
`persona-module-tester`, `pm-dev-python:pytest-testing`; at most parity tests, no behaviour change.

**Disjointness:** WIDE (docs-only across ~15 skills). Emit LAST among the lessons-triage plans, after
the behaviour-changing ones (the former PLAN-59..64 band — now PLAN-TRUTH-010 / TRUTH-011 here, the rest
transferred or moved) land, to minimize rebase churn. D1 may serialize sub-batches.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -021

**Component:** `manage-execution-manifest (compose inputs nobody writes)` · **Deliverables after merge: 12** (raised cap is 12).

Exactly 12 — at the raised cap.

- **`-021`** — `PLAN-202` shipped the immunity **channel**, **both** compose-side readers and a manual CLI
  writer, but **no caller writes the `phase-1-init` posture answer**. ⭐ A **producerless contract row**:
  a field with two readers and no producer, which is the archetype `-012` and `-040` also carry.
- **`-014`** — promote each landed lesson's generalizable rule into the standards of the skill that owns
  the surface, cross-linking the shipped fix. Its consumers are compose-side too.

⚠ **This is the weakest merge in the set and is recorded as such.** The tie is the component and the
compose-input surface, not a shared mechanism. ⛔ **If outline finds the deliverables do not interlock,
split it back** — a 12-deliverable plan that reads as two plans stapled together has not been merged,
and that failure mode is explicitly permitted to be undone here.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary
Repository source (standards docs) + parity tests only; NO `.plan/local/orchestrator/` writes. See
orchestration-model.md § Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
