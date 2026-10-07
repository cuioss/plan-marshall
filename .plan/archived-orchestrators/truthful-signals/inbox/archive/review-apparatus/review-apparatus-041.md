envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-14T19:39:20Z

# Eighteen non-charter items from `PLAN-PR-065`'s landing (PR #1491)

Transferred from `review-apparatus` on 2026-09-14, drained from that epic's inbox as
`pr-065-settings-repo-accumulates-never-lands-001` … `-016`, `-018`, `-019`, `-020`. ⭐ **Routed here
by the standing three-way rule**: none is PR/review subject matter. They are tooling-invocation,
plan-quality, footprint and architecture items — and the largest cluster below is a *measurement and
self-report* theme this epic owns. All are first-party to that plan's own run (merged as #1491).

⚠ **Leads, not instructions.** Each is the sending plan's own observation; none was re-derived in this
checkout.

## A. The invocation-discipline cluster — TEN rejections in one run, and the repeats are the signal

`-005` `manage-findings` rejected three times (an undeclared flag on `list`, then `qgate add` without
its required flags) · `-006` the documented recurrence signature for `architecture --plan-id` points
the WRONG WAY · `-007` **the same invented verb was re-invented three times, hours apart, after the
executor had already printed the registered set** · `-008` `manage-change-ledger` called with an
unregistered verb · `-009` `step-params set --value` failed as *"expected one argument"* and **the
identical call was retried one second later** · `-010` `manage-references get` without its required
`--field` · `-011` `manage-metrics record-dispatch-boundary` rejected at the loop-back re-entry point ·
`-012` the documented signature-4 rejection **recurred verbatim inside finalize** · `-013` `ci_verify`
called with a paraphrased verb against a **one-verb script**.

⛔ **The cluster is worth more than its members.** Three of them are *the same mistake repeated within
one run, after the correct form had already been displayed* — so the existing recurrence checklist is
not changing behaviour, which is the claim `review-apparatus` forwarded from an earlier run at medium
confidence and this run corroborates at volume. The failure is not knowledge; it is that a rejection
costs nothing and is retried faster than it is read.

⛔⛔ **`-014` is different and is NOT agent behaviour**: *the generated executor rejected a flag the
dispatched script declares, and two full regenerations did not clear it.* That is a real tooling defect
and should not be filed under discipline — a correct invocation that the executor refuses is the
one case where reading the registered set does not help.

## B. Footprint and scope

- **`-004` — `affected_files` is never updated as execute discovers new files.** ⛔ **This run makes the
  numbers exact**: 19 declared vs a 13-path realized footprint, **not nested** — 5 realized-but-never-declared
  (including `branch-cleanup.md` and `argument-naming.md`, the targets of fix tasks appended during
  execute) and 4 declared-but-never-realized (`ci_base.py`, `gitlab_ops.py` and their tests — the GitLab
  half of a contract the plan declared and never touched). ⇒ **The divergence runs in BOTH directions**,
  and the over-declaration is the newer half. This is the fourth consecutive landing in
  `review-apparatus` showing the drift; `reconcile-scope` detects it and **nothing in finalize calls it**.
- **`-001` — resolve the foreign-checkout half of a two-repository plan's footprint.** A plan whose work
  lands in another repository has no footprint mechanism for that half at all.
- **`-020` — a footprint path under `.github/**` resolves to NO module, and that silently widens every
  scoped gate to whole-tree.** `architecture which-module --path .github/workflows/…` returns
  `module: null` with the same three attributors every marketplace path returns, so the answer carries
  **no discrimination**. Observed consequences in one run: `pre-push-quality-gate` warned twice
  (*"proceeding whole-tree; scoped coverage for these paths is not determinable"*), and the execute-exit
  freshness gate refused a transition with `build_scope_narrow` / `divergence_possible=true`, demanding a
  whole-tree verify at orchestrator tier (`bash_timeout_seconds=2157`). ⭐ A resolver that cannot answer
  is silently converting scoped gates into whole-tree ones — a cost, not just an imprecision.

## C. Plan-quality and self-report

- **`-002` — `check-manifest-consistency` reports a false empty diff when run post-merge on main.**
  ⚠ **Recurrence**: already transferred from the `PLAN-PR-046` landing as `review-apparatus-038` item 1.
  Second independent sighting; the remedy there stands.
- **`-016` — a deliverable claimed its file list came from a content sweep; re-running the sweep refuted
  it.** ⛔ The claim-of-derivation archetype: a stated method nobody re-ran.
- **`-018` — a deliverable's verification command could not collect the guards it claimed to exercise.**
- **`-019` — an outline Q-Gate reasoned over line ranges execution did not use, and predicted a defect
  that never happened.** ⭐ Worth keeping as the false-positive half: a gate that predicts against a
  surface the run does not touch will generate work that is not real.
- **`-015` — 10 lint findings against 5 files in 4 bundles, ALL FALSE**: the rule read an unconfident
  parser surface as confident. A detector treating an uncertain reading as a settled one.
- **`-003` — the skill advertises "deliverable extraction" but declares `list-deliverables`.** A
  description/interface divergence.
