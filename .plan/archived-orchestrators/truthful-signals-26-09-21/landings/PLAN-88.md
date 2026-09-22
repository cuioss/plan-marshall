# Landing: PLAN-88 — daemon audit logs interactions, not job lifecycles

plan: PLAN-88 · plan_id: `daemon-audit-logs-interactions-not-job-lifecycles` · PR **#1037**
merged: `741a1c99d` · 4/4 deliverables · 21/21 finalize steps

## Deliverable fidelity

4/4 shipped. `_marshalld_audit.py` carries a `kind` discriminator; `outcome` → `request_status`
(request-scoped), plus a `record_job_fate` writer keyed by `job_id` that **coerces any non-terminal
value to `unknown`** — the never-claim-a-fate-you-do-not-know constraint held. Emission wired at both
terminalization seams under the existing best-effort guard. `run_logs` renders `kind` /
`request_status` / `fate` as distinct columns.

**Three spec corrections established from code rather than assumed — all three strengthen the plan:**

1. **D4(b)'s premise was WRONG.** A daemon restart does *not* yield an undeterminable fate —
   `replay_on_restart` renders `killed`. The genuinely unknowable cases are a GC'd journal entry and a
   daemon that died and never returned.
2. **A retention asymmetry that neither the spec nor the module docs surfaced decided the layer
   choice:** terminal journal entries are GC'd after 3600 s while audit rows live 7 days, so a pure
   read-time join can only answer for a row's first hour. **This is the epic's archetype in the
   design space** — a join that looks correct and silently stops answering after an hour.
3. **A real latent bug surfaced in-run:** `_admit_ready` re-executed an already-terminalized job,
   clobbering the terminal journal status back to `running` and appending a duplicate fate record.
   Fixed with a `_is_terminalized` guard.

## ⛔ Review coverage — verified first-party, and this is the headline

`origin/main` at `741a1c99d` corroborates the merge. The review claim corroborates too, and is worse
than a repeat:

| Reviewer | Ground truth (verbatim) |
|---|---|
| **sourcery-ai** | *"rate limit of 500000 diff characters"* — **weekly quota refusal.** |
| **coderabbitai** | *"rate limited by coderabbit.ai"*, *"Review limit reached"*, *"Next review available in: 39 minutes"* — **first observed CodeRabbit refusal in this epic.** |
| **cuioss-review-bot** | *"No major issues detected"* — the only participant, informational only. |

**Two of three core bots refused on the same PR, and the merge gate went green.**

⭐ **THE NEW MECHANISM — the noise pre-filter drops refusals before the recognizer ever sees them.**
Neither refusal reached the findings store. So `automatic-review` reported *"1 comment found"* and
`review-retrospective` reported *"1 reviewer, 0 actionable"*. **This is upstream of the phrasing
problem: a perfect recognizer would not have helped, because the pre-filter discards first.**

⭐ **Both rate-limit SHAPES observed on one PR** — Sourcery a **quota** (not awaitable, no sleep can
recover it) and CodeRabbit a **window** (39 minutes, awaitable). PLAN-92's D2 window-vs-quota split is
now confirmed by a single-PR natural experiment.

⚠ **PLAN-92 defect 6 confirmed live.** The pre-merge comment barrier's only pending finding was this
plan's **own `post_responses` reply**: `fetch_findings` filters bot boilerplate as noise but not its
own RESPOND output, so `fail_into_loopback` manufactures a new blocker every cycle and never
converges. The plan resolved it in place rather than entering a non-converging loop — the right call.

**Precision note:** the report said "essentially zero substantive automated review". Exactly: 2 of 3
refused, 1 posted an informational Guide with no findings. **Substantively zero, participation 1/3.**

## Other residue

- **A `quality-gate` excludes-`test/` gap let three mypy errors through to verify.** → PLAN-60
  (in-house gate ↔ CI parity) — a direct instance of what that plan owns.
- `gh` PATH: the CI layer reported it as *"Not authenticated"*, which is **the wrong cause** — a
  misattributed diagnostic, the epic's archetype in an error message.

## Cost

3.8M tokens / 2h39m worked. **Higher than #1034's 2.7M**, on a 4-deliverable plan.

## Reconciliation

- Row → `shipped`, `pr=1037`, `landing=landings/PLAN-88.md`,
  `plan_marshall_plan_id=daemon-audit-logs-interactions-not-job-lifecycles`.
- 14 candidate-lessons routed to the epic inbox; drained separately.
- PLAN-58 (`marshalld-self-reload`) is unblocked by this landing.
