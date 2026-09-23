# PLAN-LR-05: A lesson does not record what was running when it was observed

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance and the settled decision

Staged 2026-08-24 on operator direction: *"it is mandatory to file the version as part of each lesson
as well (should be part of the script — determining the version)."*

⛔⛔ **THE SOURCE IS SETTLED — `MARSHALL_VERSION`, ALWAYS. DO NOT RE-OPEN IT.** Operator ruling,
2026-08-24: *"Always use MARSHALL_VERSION. Reasoning: for typical clients, installed locally, this is
usually correct."* The first draft of this spec opened with a gate asking *which* version source
answers the question. **That gate is retired and its reasoning is recorded below so the run inherits
the answer rather than re-deriving the doubt.**

### ⭐ Why the orchestrator's objection was withdrawn

The objection was that "the version" is ambiguous, evidenced by a live split on the plan-marshall
development machine: executor `MARSHALL_VERSION` **0.1.1538** against registry `installPath`
**0.1.1526**, with the skill bodies seated from 1526 — twelve releases apart.

⛔ **That generalized a META-REPO PATHOLOGY to clients who do not have it.** The split arises from the
plugin-registry pin / orphan-GC inversion, a defect of *this* development checkout with a long incident
history. **A typical client installs the plugin, has one cache version, and never sees it.** The
operator's reading is correct and the objection was over-fitted to the machine it was measured on.

⚠ **The residual risk is real but CONFINED and is NOT a reason to add a source.** On this development
machine — the one place plan-marshall's own lessons are filed — `MARSHALL_VERSION` can name a version
other than the one whose skill bodies ran. **Record that as a known limitation in the shipped
documentation; do not build a second source to chase it.** A field that is right for every client and
occasionally imprecise for one developer is the correct trade.

## Objective

**A lesson records `id`, `component`, `category`, `status`, `created` — and nothing about what was
running when the behaviour was observed.** Verified first-party against a live consumer-repo lesson
(`cui-jsf-test-basic/.plan/local/lessons-learned/2026-06-15-15-001.md`) and against
`manage-lessons/SKILL.md`, which mentions no version field anywhere.

For a lesson read on its own machine a week later that is an inconvenience. For a finding **leaving the
machine** — this epic's whole point — it is disqualifying: **a report about behaviour that has since
changed costs a maintainer a reproduction attempt against a moving target, and is worse than no
report.** ⭐ The stranded corpus proves it: the three `plan-marshall:*` lessons in `cui-jsf-test-basic`
are dated **2026-06-15/16** and nobody can now identify what they were filed against.

## Deliverables

Three substantive deliverables plus one defensive line. **No gate** — the source question is settled above.

**D1 — stamp `MARSHALL_VERSION` on every newly filed lesson, determined by the script.** ⛔ **No
`--version` argument.** A caller-supplied version is a claim, and this epic exists because findings
outlive the context that would let anyone check a claim. ⚠ If a test override proves unavoidable it
must be **visible on the stored lesson**, for the same reason `--allow-foreign-store` should be
(PLAN-LR-02 D3): an override that leaves no trace produces a corpus that looks clean.

⛔⛔ **COST MODEL INVERTED — corrected at cleanup 2026-09-23. R11's ruling (always use `MARSHALL_VERSION`)
is UNCHANGED and NOT re-opened; only the effort estimate for reaching it was wrong.** The original "the
read is nearly free" paragraph below assumed the executor process reads the constant and files the
lesson in the same process. It does not: `execute-script.py.template:1616` dispatches every script as a
**subprocess** (`subprocess.run(['python3', script_path] + script_args, env=env)`), and the env export
at `:1591-1612` passes only `PYTHONPATH`, `PLAN_DIR_NAME`, and colour vars — `MARSHALL_VERSION` is never
exported. `architecture search --content --pattern MARSHALL_VERSION` returns ZERO hits under
`manage-lessons/**`. D1 therefore needs REAL plumbing (export the value into the child's env at dispatch
time, or have `manage-lessons` parse the executor file directly) — it is not a one-line read. Size this
properly at outline rather than inheriting the "nearly free" framing below, which is now known wrong.

~~⭐ The read is nearly free and nearly always succeeds, which is what makes this cheap: the constant
lives in the generated executor, and the executor is *the thing that ran the script*. If the filing
call is executing at all, the file carrying `MARSHALL_VERSION` has already been loaded.~~ *(struck
2026-09-23 — false across the subprocess boundary; see above.)*

**D2 — a missing constant defaults defensively and says so; it is NOT a designed feature.**
⛔ **OPERATOR RULING 2026-08-24 — do not build this out.** An executor without `MARSHALL_VERSION`
predates the constant, and *"this is the very old stuff, can be ignored"*. Any client filing a lesson
today has a current executor, because the executor is regenerated by steward / cache-sync.

⛔⛔ **D2's branch was mis-sized alongside D1 — corrected at cleanup 2026-09-23.** This deliverable was
scoped as "the rare degraded case" (pre-versioning executor, out of scope per R12). That ruling still
holds for the PRE-VERSIONING case. But until D1's plumbing lands, the UNPLUMBED case — `MARSHALL_VERSION`
simply not reaching `manage-lessons` at all, on a perfectly current executor — is the ONLY reachable
branch today, not a rare edge case. D2's defensive `undetermined` line is still correct and still
minimal; what changes is that D1 cannot ship without it, since D1's own happy path does not exist yet
without the plumbing D1 must add.

⚠ **This deliverable is therefore ONE defensive line, not a subsystem**: if the constant is absent,
record a sanctioned `undetermined` rather than crashing or fabricating — the ordinary robustness a
script owes a constant it reads. **No signal semantics, no field-population claim, no dedicated
fixture beyond the trivial one.**

⭐ **Recorded because the orchestrator got this wrong:** the first draft called this branch
*"reachable in the field today"* on the evidence of a **single** stale consumer checkout
(`cui-jsf-test-basic`, Jun 15). **One sample is not a population** — the parent project's own standing
rule — and the sample was of an abandoned checkout, not of a live client. The evidence was real; the
inference from it was not.

**D3 — the pre-existing corpus has no version and must not pretend otherwise.** Every lesson already on
disk predates this field. ⛔ **Do NOT backfill a guessed value.** A lesson dated 2026-06-15 stamped with
today's version would be **actively false** and worse than an absent field. ⇒ **`absent`,
`undetermined` and a real version are THREE distinct states, not two**, and each must stay
distinguishable: *never carried the field* · *carried it and could not resolve it* · *resolved it*.
⚠ PLAN-LR-04 migrates that corpus and reads this distinction; it must not be forced to infer it.

**D4 — tests.** Assert the stamp on a normal filing, and that a pre-existing lesson is **NOT**
retroactively stamped. ⭐ **The no-backfill assertion is the load-bearing one** — it is the case that
silently corrupts provenance, and it is the only one of the three whose failure is invisible
afterwards. A trivial absent-constant case may ride along; it carries no weight.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**`
- `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md`
- `test/plan-marshall/manage-lessons/**`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⚠ **`PLAN-LR-02` — SERIALIZE.** Same scripts, same SKILL.md, and both add a field to the filing path.
  Either order works; concurrent does not.
- ⛔⛔ **`PLAN-LR-03` DEPENDS ON THIS, and its D1 is WRONG WITHOUT IT.** LR-03 D1 requires the issue body
  to carry the version the client was running. Without filing-time stamping it could only sample a
  **live** version at routing time — the version at the moment of routing, not of observation — which is
  wrong for every finding filed before an upgrade, and the stranded corpus is two months old.
  ⇒ **LR-05 lands before LR-03**, and LR-03 D1 then READS a recorded field instead of sampling one.
- ⚠ **`truthful-signals/PLAN-TRUTH-091`** touches `manage-lessons/SKILL.md` (doc surfaces). Ordering
  constraint only, as recorded on LR-02.

## Claim Labels

- OBSERVED: the lesson header carries `id`, `component`, `category`, `status`, `created` and no version — read at `~/git/cui-jsf-test-basic/.plan/local/lessons-learned/2026-06-15-15-001.md` § header, and `manage-lessons/SKILL.md` names no version field.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: confirmed still true for lessons filed TODAY under executor 0.1.1753 (API-Sheriff 2026-09-23-07-001.md header); SKILL.md add Parameters/Output name no version field; _lessons_io._build_lesson_content renders metadata.items() only
- OBSERVED: `MARSHALL_VERSION` is a literal in the generated executor (value drifts release to release — `0.1.1753` re-checked 2026-09-23, was `0.1.1538` at staging) — read at `.plan/execute-script.py` § `:80`.
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: value drifted: MARSHALL_VERSION = 0.1.1753, not 0.1.1538 (215 releases since staging). Symbol/line still correct at .plan/execute-script.py:80; only the pinned example value was stale. Not otherwise load-bearing
- OBSERVED: `cui-jsf-test-basic/.plan/execute-script.py`, dated Jun 15, carries no `MARSHALL_VERSION` — an ABANDONED checkout, ruled explicitly out of scope by the operator; recorded so the absence is not re-discovered as new.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: ~/git/cui-jsf-test-basic/.plan/execute-script.py:33-40 imports go straight to PLAN_DIR_NAME; the provisioning-stamps block present in every current executor is absent entirely
- OBSERVED: the three stranded `cui-jsf-test-basic` lessons are dated 2026-06-15/16 — read at their `created=` headers. This is why D3 forbids backfill.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: created= headers confirmed: 2026-06-15 (18-001), 2026-06-16 (09-001), 2026-06-16 (09-002). No-backfill rationale intact
- HYPOTHESIS: `MARSHALL_VERSION` is readable at every filing call site, making the degraded branch near-unreachable in practice — confirm/refute at `manage-lessons/scripts/**` § the import path (verify-at-outline).
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: REFUTED at the process boundary: execute-script.py.template:1616-1621 dispatches manage-lessons as a child subprocess; env export at :1591-1612 exports PYTHONPATH/PLAN_DIR_NAME/colour vars ONLY, never MARSHALL_VERSION; architecture search --content confirms zero references under manage-lessons/**. D1/D2 rewritten to reflect the degraded branch being the ONLY reachable one until plumbing is added
- Verify-first clause: `absent` / `undetermined` / a real version must remain three DISTINGUISHABLE states after this lands, since PLAN-LR-04 reads that distinction and cannot infer it.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: still required and unimplemented; precedent for the three-state discipline already lives in the same module - _lessons_io.STORE_RESOLUTIONS (main_anchored/override/unresolved) and LessonRead.state (found/absent/unreadable) - D3 has a house pattern to follow
