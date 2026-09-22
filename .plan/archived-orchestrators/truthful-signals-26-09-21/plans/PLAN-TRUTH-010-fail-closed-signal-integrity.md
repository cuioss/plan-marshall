# PLAN-TRUTH-010: Fail-Closed Signal Integrity — Classifiers & Leaf Returns Must Never Confidently Green

> Renamed from **PLAN-59** on 2026-07-30 (see `plan-id-rename-map.md`). ⛔ **Serialization pair with
> PLAN-TRUTH-019** — its D3 zero-scoped-modules branch is the same conflation as this plan's D4b.

epic: truthful-signals
workstream: WS-01

> Staged plan spec (lessons-triage 2026-07-25). Gathers the epic's flagship
> `confident-signal-hides-a-caveat` / fail-open family: one still-open instance plus a set of
> already-landed fixes whose durable rule must be promoted into a governing "fail-closed classifier"
> standard before the source lessons retire. LARGE by design (few large plans > many small ones).

## Objective

Across the codebase, classifier/adjudicator/leaf-return seams have repeatedly shipped **fail-open**:
returning a clean/green/passing verdict on an undetermined, absent, or error input rather than a
conservative one. Each instance was fixed in-run; nothing generalized the rule. Fix the one open
instance and **promote a single fail-closed-classifier discipline into a governing standard** so the
next new seam inherits it, then retire the source lessons.

## Deliverables

### D1 — GATE: pick the fix for the open instance + the promotion home (mutates nothing)
Confirm the open defect `2026-07-22-16-003`: `execute-script.py.template` gates the `kind=build`
ledger stamp on `_is_build_class_notation` (bundle:skill prefix) with **no subcommand discriminator**,
so a pure query verb (`resolve-test-scope`) writes a `status=success` build row that can flip the
freshness gate stale→fresh with no build run. Decide the discriminator shape. Choose the governing
home for the promoted discipline (a `fail-closed classifier` section — candidate: `script-shared` or
`ref-code-quality`), and which residues fold into it.

### D2 — close the open non-build-inclusion defect

⭐ **CORROBORATED AND WIDENED 2026-07-27 from the PLAN-80 landing (#1021).** Lesson `2026-07-22-16-003`
named `resolve-test-scope` as the query verb writing a false `kind=build` row. Two more verbs now
exhibit the identical shape, first-party: an **npm `--help` invocation** recorded as a successful
`kind=build` (in a repo with no npm build), and **`parse --log`, a pure log reader**, likewise recorded
as a build. **The blast radius is at least three verbs, not one** — which strengthens the case for a
subcommand discriminator over a per-verb exclusion list, since the exclusions would already be three
deep and growing. **Do not scope D2 to `resolve-test-scope`.**

⚠ **Second confirmed sighting: timed-out builds carry `exit_code: 0`.** First observed at the PLAN-55
landing, independently re-confirmed here. Two sightings of the same falsehood, from unrelated runs — a
timeout is recorded as a clean success, so D1 must decide whether the discriminator alone is sufficient
or whether the ledger's success semantics need the same fail-closed treatment. ⚠ **This is a distinct
defect from the notation-prefix one** — do not let the discriminator fix be mistaken for closing it.

⚠ **Consumer half is NOT this plan's:** that the freshness gate *accepts* such a row is **PLAN-82**.
This plan stops the bogus rows being written; PLAN-82 makes the match auditable and cross-checked.
Either fix alone leaves a real hole.
Add the subcommand discriminator so only genuine build-executing invocations stamp a `kind=build`
row; a query verb never writes a build-success entry. Regression test the freshness gate cannot be
flipped by a non-build query.

### D2b — SPLIT OUT TO PLAN-86, NOT IMPLEMENTED HERE

⛔ **Do NOT implement this deliverable.** Split out 2026-07-27 on operator decision to
`plans/PLAN-86-unchecked-finding-persist-loses-the-finding.md`, which sits near the queue head because
the defect is a **live data-loss path** and this plan is large by design and deep in the queue.
PLAN-86 closes the instance; **this plan retains only the promotion** of the durable rule into the
governing standard (see the D3 write-direction clause below). Whichever lands second re-grounds against
the other. The record of the instance is kept here because D3's promoted clause is derived from it:

Folded 2026-07-27 from **API-Sheriff PR #114** (merged, cross-repo — the defect is ours, not theirs).

- OBSERVED (operator narrative, first-party): the phase-5 executor's `manage-findings qgate add` was
  rejected by argparse, the executor **continued past it**, and an escalation finding was silently
  lost — costing an extra orchestrator round-trip. Nothing reported a failure.
- OBSERVED (this repo, first-party): the Step 11c persist contract at
  `phase-5-execute/SKILL.md:870-879` reads *"Persist each failing finding to the Q-Gate findings
  store"* + *"One `qgate add` call per finding"* and **specifies no exit-code check and no on-failure
  behaviour**. The store is the hand-off substrate — `triage_required` tells the orchestrator to read
  findings *by reference* — so a rejected add yields a `triage_required` pointing at a store that never
  received the record, or no signal at all.
- **⇒ Why this is a NEW shape, not a duplicate of D3's clauses.** Every clause D3 promotes governs a
  *classifier reading* an input (fail closed on undetermined, branch on producer status before folding
  payload, exit-0 necessary-not-sufficient). This one is the **write direction**: a producer's own
  persist call fails and the caller proceeds as though the write landed. The existing clause set does
  not cover it — a fail-closed *reader* downstream cannot recover a record that was never written.
- **⇒ D3 gains a clause** (see below). **This is a live data-loss path**, not a latent one: it fired in
  a real run and the loss was invisible until a human noticed a missing escalation.
- Fix shape (settle at D1): the persist must be exit-code-checked, and a failed persist must be loud —
  a leaf that cannot store a finding must not return a clean/`triage_required`-without-content signal.
  ⛔ **The fix shape, the five call sites, and the test contract are NOT restated here — they live in
  PLAN-86**, so there is exactly one source of truth for them.

### D3 — promote the fail-closed-classifier discipline (governing standard)
Author the promoted rule from the landed residues: **a classifier must order specific rows before any
catch-all/deadline fallback, fail closed on undetermined/None/empty state, branch on a dispatched
producer's status BEFORE folding its payload, gate a clean pass on an affirmative success signal (not
absence-of-change), and treat exit-0 from an always-0 wrapper as necessary-not-sufficient.** Cross-link
the shipped instances as worked examples.

### D4 — leaf-return contract invariant

⭐ **FRESH RECURRENCE 2026-07-27, with a measured cost** (PLAN-62 landing #1022, inbox `-004`, read
first-party). `pre-submission-self-review` ran ~14 minutes, completed its review, and returned
`status: success` with zero findings — **without ever calling `mark-step-done`**. The post-dispatch
guard (`assert-step-recorded --require-terminal`) worked exactly as designed: recorded `failed`,
halted, and the resumable re-entry re-dispatched, which then recorded correctly.

- **⇒ Detection is solid; PREVENTION is not.** The cause-B (omitted call) class is already documented
  and already guarded, and it still fired. The authoring-side contract — a workflow body MUST
  terminate with `mark-step-done` — is being missed at dispatch time even though the detection-side
  contract holds. D4 should weigh whether an authoring-side structural guarantee is reachable, rather
  than treating the existing backstop as sufficient.
- **⇒ The remedy's cost scales with step runtime.** A full re-dispatch discarded 14 minutes of
  *completed* review work (retry took 4). The guard can detect the missing record but cannot salvage
  the work behind it. **Design option worth D1's judgement, from the message:** have the dispatcher
  record the outcome itself from the returned TOON when the workflow's declared contract maps return
  `status` 1:1 to a `mark-step-done` outcome — turning a discarded 14 minutes into a zero-cost
  reconciliation. ⚠ Weigh it against the contract this plan defends: a dispatcher that *infers* the
  terminal record could mask a leaf that genuinely failed to complete its work, trading a loud
  expensive failure for a quiet cheap one — this epic's own anti-pattern. Neither direction is free.
- **⇒ Theme fit is exact:** the return envelope's `status: success` was a truthful statement about the
  review performed and a completely misleading one about whether the pipeline could proceed.
Promote `2026-07-13-12-003`'s residue: landing the terminal `mark-step-done` is a structural invariant
of a dispatched leaf's return (record before composing the return TOON); a `status:success` with
`step_record_missing` is a leaf-contract violation. Note the wrong-key half already landed (#961); the
omitted-call half is the residue to codify (assert-step-recorded backstop).

**D3 additionally promotes the write-direction clause from D2b:** *a producer that persists a finding
MUST check the persist call's exit status, and MUST NOT emit a clean or referral signal
(`triage_required`, zero-findings green) when the persist failed — an unstored finding is a lost
finding, and no downstream fail-closed reader can recover it.* This is the write-side complement to the
read-side clauses above; promote it in the same governing home.

### D4b — `resolve-test-scope` returns a confident docs-only verdict for source it cannot resolve

⭐ **FOLDED IN 2026-07-30** from inbox `audit-report-path-ignores-plan-dir-001` (surfaced first-party by
plan `audit-report-path-ignores-plan-dir`, epic `code-intelligence-substrate` PLAN-11, deliverable 1;
forwarded rather than actioned there, operator-directed here).

⛔ **This is a SECOND, DISTINCT defect at the same verb as D1/D2 — do not conflate them.** D1/D2 concern
`resolve-test-scope` *writing* a false `kind=build` ledger row. D4b concerns what it *returns*. A fix for
one does not close the other, and the shared verb name is exactly what makes the conflation likely.

- **`OBSERVED`** — for changed path `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
  (Python production source with a live pytest module) the verb returns `scoped_modules[0]` /
  `recommended_target: null`. `execute-task` documents that exact shape as the **docs-only
  short-circuit → run NO pytest**.
- **`OBSERVED` — near-miss, not hypothetical.** The executing task deliberately took the
  non-documented path and ran `module-tests plan-marshall` instead. Had it followed the documented
  short-circuit, deliverable 1 would have shipped with **zero test execution**, and the pass would have
  looked clean — a skipped suite and a green suite are reported identically at the task-verification
  layer. Two real defects were caught by the tests the documented path would have skipped: the
  mutation check proving the new regression tests non-vacuous, and a test branch that was initially
  **unconstructible** (pytest's basetemp sits under this project's own `.plan/temp/`, so every
  `tmp_path` has a `.plan/local`-bearing ancestor, making the "no marker anywhere up the tree" branch
  vacuously pass — now `tempfile.TemporaryDirectory()` with an explicit precondition assertion).
  ⇒ This is the **vacuous-guard** archetype co-occurring with the fail-open one.
- **`HYPOTHESIS`** — the resolver maps changed paths to modules via the marketplace bundle layout
  (`marketplace/bundles/**`) plus the registered test tree, and `.claude/skills/**` (project-local
  skills) is outside both; a path matching no module yields empty `scoped_modules`, which the consumer
  reads as docs-only. **Neither the forwarding orchestrator nor this one read the resolver
  implementation.** Confirm/refute artifact: the `resolve-test-scope` verb handler in
  `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` — locate by
  SYMBOL, not line. Verify-at-outline; do not scope a fix on this premise unconfirmed.
- **`HYPOTHESIS` — population, and it must be DERIVED not sampled.** One instance observed.
  `.claude/skills/**` holds several project-local skills with Python scripts and pytest modules, and
  the same null-verdict class may cover other path roots outside the module inventory. ⛔ **Do not fix
  only the observed path** — this epic has been burned four times by a detector built from a sample
  (see the Archetype counters). Enumerate every path root the resolver's module map does not cover.
- **Fix direction (not prescriptive, and it is D3's clause verbatim):** the failure is that *"no module
  matched"* and *"no tests needed"* are **the same signal**. Separating them — an unresolved path fails
  closed with an explicit unknown state rather than a confident docs-only verdict — is precisely the
  fail-closed discipline D3 promotes, which is why this belongs here rather than in a local patch.

### D5 — retire the carried lessons
After D2–D4b land, the finalize `lessons-housekeeping` step retires every lesson in **Lessons Carried**.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

Carry each at phase-1-init via `manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_id}`;
retire at finalize (provenance to tombstone `--reason`, never a lesson-id citation).

- `2026-07-22-16-003` — **OPEN** — build-class stamp keys on prefix not subcommand; query verb writes false-success build row (D1/D2).
- `2026-07-07-17-001` — CI green-gate classifier fail-open (catch-all before specific rows; empty conclusion admitted) — landed, promote.
- `2026-07-16-14-001` — outcome-classifier fail-open on four axes — landed #912, promote.
- `2026-07-24-13-002` — fail-closed consumer folded a dispatched producer's ERROR as a clean zero-findings green — landed #995, promote.
- `2026-06-21-21-001` — re-review matcher fail-open None-wildcard + naive-datetime + paginate-without-slurp — landed #742, promote.
- `2026-07-22-12-003` — routed build reported success while daemon child failed (exit-0 always) — landed #979/#993, promote.
- `2026-07-11-15-001` — detect-and-warn inferred a clean pass from absence-of-change, not an affirmative success signal — landed, promote.
- `2026-07-23-01-001` — reader boundary over a capped store emitted a confident false negative — landed #989, promote.
- `2026-07-23-01-002` — gate keyed on a declaration skipped items lacking the key (`if key is None: continue`) — landed #990, promote (vacuous-guard sub-family).
- `2026-07-13-12-003` — dispatched leaf reached `success` with the terminal `mark-step-done` omitted (D4).

## Expected surface
- `execute-script.py.template` build-class stamp discriminator (D2) + a test
- ⛔ **NOT this plan's surface:** the `phase-5-execute` persist sites moved to PLAN-86 with D2b. This
  plan must not touch `phase-5-execute` — doing so would re-collide with PLAN-86 after the split.
- the chosen governing standard doc for the fail-closed-classifier discipline (D3)
- `manage-status` assert-step-recorded / leaf-return backstop (D4)

**Disjointness:** template + a standards doc + manage-status assert-step. Coordinate at outline with
PLAN-45 (routed-verdict, landed) and any in-flight build-execute plan. Wide-ish but low-collision.

## The launch-abort case — a failure with no verdict at all

Same fail-closed classifier, so it is designed once, here.

**The question.** A per-worktree pyprojectx/uv venv interpreter intermittently dies at launch
with `SIGABRT` / `Namespace DYLD, Code 1, Library missing`, roughly once a day. A process that aborts
in `dyld` produces **no Python traceback, no TOON, and no `status` field** — so the standing rule
that "the wrapper exits 0 on failure and the verdict lives only in the TOON" has a hole: there may be
**no verdict to read at all.** Whether that path fails closed or reads as success is unknown, and it
is exactly this plan's subject.

**Orchestrator-verified 2026-07-28, so nobody re-derives it:**
- The venv is **healthy at rest** — its interpreter returns `Python 3.12.3`, exit 0. Nothing is
  broken; **no worktree repair is owed.**
- `bin/python3.12` is a symlink chain into the uv install; the venv's own `lib/` correctly holds no
  dylib; **both** uv installs carry it. Same layout in a second worktree, so not a one-off.
- HYPOTHESIS: the crash occurs during venv **materialization** on a worktree's first build (fits
  `terminated at launch`, the daily cadence, and `.pyprojectx` existing in only some worktrees).

**Deliverables for this case:**
- **Reproduce a launch-abort against a stub binary — never a live worktree** — and record first-party
  what the caller sees: wrapper exit code, whether any TOON is emitted, what `status`/`errors[]` carry.
- Make an interpreter-launch abort surface as a named failure. ⛔ **Fail closed:** an absent or
  unparseable build result must never resolve to success.
- Decide the retry question explicitly. ⛔ **Any retry must key on the launch-abort signature
  specifically — never a blanket build retry**, which would mask real failures. If the signature
  cannot be distinguished reliably, **do not add the retry** and say so.
- Record the latent `pyvenv.cfg` pointer mismatch: `home` names `cpython-3.12-…` while the symlink
  resolves to `cpython-3.12.3-…`. Both exist today; the venv holds two references that can diverge.
  **Do not "fix" it by rewriting uv's output** — the deliverable is knowing it can diverge.

⛔ **Scope honestly: this may not be our bug.** The abort is in `dyld`, inside a uv/pyprojectx layout.
**Do not attempt to fix uv's materialization** (precedent: harness-killed background jobs are recorded
as UNOWNED-INFRA — we detect and document, we don't fix). **If the launch-abort turns out to be
already legible and already fail-closed, this case is REFUTED** — record the negative result and drop
it. That is a legitimate outcome; do not manufacture work to justify it.

⚠ **Split guard:** this case enlarges an already-substantial plan. If the combined deliverable set
runs past the guard, **split the launch-abort arm out and say so** rather than absorbing silently.

## The guard that reports lost findings can itself be a lost-finding vector

Established by #1038's population sweep, and it is a **design rule this plan must encode, not just an
instance.** All four producer-mismatch emitters — the guards whose entire job is to report that
findings were lost — **were themselves unchecked persists.** They lost the reports they existed to
make.

⛔ **The rule for every fail-closed classifier this plan touches: a reporting path must not depend on
the mechanism it reports about.** A guard that reports store failures must not report *through* the
store; a classifier that reports persist failures must not persist its own verdict unchecked.
Otherwise the failure mode is total and silent — the louder the underlying breakage, the quieter the
report.

⚠ **Check this against the launch-abort case above.** If the launch-abort verdict is written through
the same channel whose failure it describes, that arm inherits the same defect. Verify the reporting
path is independent before designing it.

## Write-Boundary
The implementing plan edits only repository source + tests; it writes NO file under
`.plan/local/orchestrator/`. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
