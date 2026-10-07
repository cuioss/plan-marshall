envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=landing
created=2026-08-01T19:14:15Z

## What landed

Plan `marketplace-dependency-resolver` — PR #1074 (merge pending at finalize time).

Six declared deliverables shipped, plus one operator-approved scope deviation:

- **D1** — `component_refs` materialized into module discovery (`plugin_discover.py`).
- **D2** — markdown derivation resolver on `pm-plugin-development`.
- **D3** — python-import derivation resolver on `pm-dev-python`.
- **D4** — end-to-end proof that `architecture impact` returns non-empty over the marketplace.
- **D5** — extension-api contract docs (`ext-point-derivation-resolver`, `module-discovery`).
- **D6** — `doc/concepts/extension-architecture.adoc`.
- **Scope deviation (operator-approved)** — fix to `build.py`'s mypy scope-emptiness guard.

## Decisions the epic should carry forward

1. **The Axis-C seam allows exactly ONE resolver id per bundle.** The plan spec's
   "two resolvers from `pm-plugin-development`" was therefore not implementable as
   written. The python resolver went to `pm-dev-python` instead. The follow-on
   concern that a domain bundle is "not guaranteed active" was verified
   **UNFOUNDED**: `discover_derivation_resolvers` walks `discover_all_extensions`,
   which is explicitly unfiltered by project applicability. **Do not re-derive
   this** — it is settled.

2. **Proceeding unsplit at 6 deliverables was recorded as the spec required.**
   D2/D3 depend on D1's materialization field, which has no standalone value, and
   D5 is only truthful once both resolvers exist. Splitting would have produced
   plans that could not individually pass their own verification.

3. **The python resolver never produces an edge ALONE.** Every pair its import
   join derives is also derived by the markdown resolver. The D4 test was rewritten
   to assert three things that are actually true, rather than the false claim
   "some edge has `producers == [python]`".

4. **D4's non-empty assertion is only reachable for THE plan-marshall marketplace.**
   `plugin_discover` early-returns `[]` unless `marketplace.json` name ==
   `plan-marshall`. The fixture requirement is now an explicit, separately-failing
   precondition rather than a silent gate on the assertion.

## Residue the epic should track

Five defects were found **outside this plan's footprint**. One was fixed here under
an accepted scope deviation; the other four are unrouted and owed to whichever epic
owns them:

1. **FIXED HERE (scope deviation).** `pyproject.toml [tool.mypy] exclude` made a
   scoped `compile {bundle}` unsatisfiable for EVERY thin bundle whose only `.py`
   is `plan-marshall-plugin/extension.py`. Reproduced class-wide on the untouched
   `pm-dev-frontend-cui`. Operator elected to fix it in this plan rather than defer.

2. **OPEN.** `verification-feedback.md` line 185 carries stale count-prose — "only
   the security-audit pilot declares one" — while `ext-point-verify.md` now declares
   4 implementors. Pre-existing on `main`, not introduced by this plan.

3. **OPEN.** `triage.md` Step 3c instructs fix-task bodies to write `deliverable: 0`,
   but `manage-tasks commit-add` rejects `0` as a falsy missing field. Every fix task
   allocated by following that workflow verbatim hits it.

4. **OPEN.** The plugin-doctor wrapper `SKILL.md` Step 5 WARNING template contains a
   literal semicolon, which the project's one-command-per-Bash hook rejects, so the
   documented command is not emittable as written.

5. **OPEN.** `manage-solution-outline get-module-context` is structurally unreachable
   during `phase-3-outline` for every `use_worktree=true` plan (the worktree does not
   exist yet), so the Architecture Hints section can never render for such plans.

## Review-quality caveat (load-bearing)

This PR shipped with **ONE participating reviewer**. `pr-agent` posted an intent-echo
("no major issues detected"); `coderabbit` refused (rate limit) and `sourcery` refused
(hard quota). The operator explicitly elected to merge anyway.

If a defect later surfaces in this change set, **"the bots passed it" is NOT
counter-evidence** — the bots did not read it. Any post-merge finding against
PR #1074 should be treated as a first-look review finding, not as a review escape.

## Signal tally at finalize

- Q-Gate findings raised-and-resolved: 8 (3-outline 4, 5-execute 1, 6-finalize 3).
- Automated-review promoted comments: 1.
- Script-failure clusters: 0.
