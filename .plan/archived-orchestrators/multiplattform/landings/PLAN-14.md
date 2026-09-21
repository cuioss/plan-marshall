# Landing Analysis: PLAN-14 — Permission web and rule-pack class

epic: multiplattform
workstream: WS-01
pr: #1408 (https://github.com/cuioss/plan-marshall/pull/1408)

> Landing record for one shipped plan. Lives at `landings/PLAN-14.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/permission-web-and-rule-pack-class-001.md`. **This landing completes
WS-01** — the chain PLAN-08 → PLAN-09 → PLAN-14 is closed.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — `permission_web.py` performs no settings I/O and renders no permission-DSL string; **pinned by a test that sets `runtime.target` to a non-Claude value** | ⚠️ **shipped-modified — the substance holds, the PIN does not match the done-condition** | The substance is fully corroborated: a search of the merged file for `WebFetch(`, `settings.json`, `_load_settings`, `_save_settings` and `claude_runtime` returns **nothing**, and the script shed 399 lines. **But the shipped pin is not the pin that was specified.** `test_script_performs_no_settings_io` is a *source-substring assertion* — it calls `inspect.getsource` and asserts strings like `'WebFetch('` and `'write_text'` are absent from its own module text. It never sets `runtime.target`, never drives an OpenCode-target project, and never asserts on the filesystem. The done-condition asked for a behavioural pin; a source-grep is a different and weaker instrument. |
| **D2** — the permission rule-pack class is declared | **shipped-as-specified** | Verified by reading: `permission_doctor.py:11-20` carries a "Claude rule-pack provenance" block naming the exact rule set (`SUSPICIOUS_PATTERNS`, `is_marketplace_permission`, `extract_permission_parts`, `is_covered_by_wildcard`, `skill_permission_covered`, `check_permission`, `cmd_detect_missing_project_step_permissions`) and stating it binds only on a Claude target; per-subcommand markers at :49, :200, :422; `permission-architecture.md:3` carries a `## Provenance: Claude rule-pack` heading; all three standards docs cite `plugin-doctor/references/rule-provenance.md` § "Engine / Claude rule-pack split" as precedent. |
| **D3** — report each inventory row's re-run detection in the PR body | **shipped-as-specified** | Both rows reported. The orchestrator re-derived both independently rather than accepting the report — see Reconciliation Actions. Both verdicts **agree** with the plan's. |

### ⚠️ The D1 pin is the one thing to carry forward

The plan did the work; it did not build the instrument that would catch a regression of the
work. A source-substring pin fails in both directions: it breaks on an innocent rename, and it
passes for any bypass that does not use those literal spellings (an f-string assembling
`"WebFetch("` in parts, a helper in another module, an `os.write`). ⛔ **It also asserts
`'json.loads' not in source` while `test_categorize_invalid_json` exercises JSON input** — the
script parses its domain list by some other spelling today, and the pin will fire on a future
refactor that reaches for the obvious one. It is a tripwire on the current text, not on the
property.

Recorded as a Watch rather than an Open Defect: the *property* D1 asserts genuinely holds at
this HEAD, verified independently above. What is missing is durable enforcement.

### Test population

43 → 15 tests in `test_permission_web.py` (−484 lines). The bulk of that is legitimate —
the settings-I/O and DSL-rendering behaviour those tests covered was **removed**, and tests for
deleted behaviour must go with it. The 15 that remain are coherent (domain categorization,
argument handling, the pin). No coverage claim is made here beyond that; the build gate
reported green at 19,843 tests.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` returns
  `complete: false, missing_keys: [total_tokens]` — the known lane gap, self-disclosed by the
  run. Third consecutive landing with this key missing.
- **Verification:** verifier-clear after 2 rounds (one fix).
- **Build gate:** green, 19,843 tests.

## Routing and Merge Behavior

- **Review:** CodeRabbit obtained — one finding **deferred-with-bound and explicitly
  accepted** on the record. cuioss-review-bot reviewed. Sourcery rate-limited (optional under
  the standing policy) and **disclosed** rather than reported as clean — the same correct
  handling PLAN-09 showed.
- **CI/merge:** squash-merged as `aea95d611`, corroborated via the CI abstraction and against
  `origin/main`. Branch `feature/permission-web-and-rule-pack-class` — canonical prefix.
- **No collision materialized.** Ran solo at `parallelization_scope: 1`. Its one live
  prediction — a 1-path overlap with PLAN-09 on `contract.md` — was already dead (PLAN-09
  landed first), and in the event this landing did not touch `contract.md` at all.
- **Surface fidelity:** all seven touched paths are declared. Three declared paths went
  untouched: `platform-runtime/scripts/**`, `platform-runtime/standards/contract.md`, and
  `test/plan-marshall/tools-permission-doctor/**`. Over-declaration, the safe direction. **No
  under-declaration**, matching PLAN-09 and unlike PLAN-08.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` → `#1408`; `landing` → `landings/PLAN-14.md`;
      `plan_marshall_plan_id` → `n/a` (OpenCode lane)
- [x] **Coupling-inventory `permission_web.py` row RETIRED on re-derivation** — the row named
      `WebFetch({domain})` rendering plus Claude settings I/O performed by the script itself.
      Re-run by the orchestrator over the merged tree: **no hit** for `WebFetch(`,
      `settings.json`, `_load_settings`, `_save_settings` or `claude_runtime`. Deleted per the
      inventory's own closing test.
- [x] **Coupling-inventory `permission_doctor.py` rule-pack row KEPT and NARROWED** — the
      declaration shipped, so the row no longer records an undeclared class; what remains is
      **enforcement**. Narrowed text now states that, and its `Drawn by` is `— (unclaimed)`.
- [x] WS-01 recorded complete in the workstream charter
- [x] START-HERE and Ordered Queue blocks regenerated; `resume_anchor` updated
- [x] Message archived to `inbox/archive/permission-web-and-rule-pack-class/`

## Follow-Ups

- ⛔ **`permission_doctor`'s direct-script `detect-*` route reports a FALSE ZERO on a
  non-Claude target.** Self-disclosed by the run as a deferred follow-up, and it is the
  sharpest finding of this landing. The rule-pack declaration is *structural, not a dispatch
  path* (the module says so in its own docstring), so on OpenCode the Claude rules simply match
  nothing and the route reports zero findings — indistinguishable from a clean audit. The
  documented `platform_runtime permission analyze` path is already honest; the direct route is
  not. **This is precisely the ADR-019 class this epic keeps meeting** — *an audit must
  separate what it could not evaluate from what it evaluated and found wanting* — and it is
  the same shape as the disjointness-gate silence that ADR was written for. → **Open Defect**,
  unclaimed.
- ⚠️ **D1's pin does not enforce D1's property.** → **Watch** (above).
- **The unclaimed `permission_fix.py` DSL residue is untouched, as predicted.** PLAN-14
  excluded it by name. WS-01 is now closed with that row still open, so it cannot be picked up
  by the chain — it needs its own spec.
