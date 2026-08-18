# Gaps — 240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null

**Source:** verification.md (same directory)   **Open items:** 4

All four deliverables landed and are live (mutation-checked). The gaps below are about the *reach* of
D1's flag, the *evidence quality* the D2 rule accepts as corroboration, and two naming/prose sites.

## G1 — Make `low_confidence` reachable for the population the plan was written about

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py:733-745` — `evaluate_signals_pure`, the `confidence` block; test at `test/plan-marshall/manage-status/test_planning_lane_corroboration.py:225-241` — `test_d3c_several_nulls_reported_low_confidence`
- **What is wrong:** `low_confidence = signals_null > signals_resolved` is computed over a
  seven-member vector in which `request_concrete` and `risk_prose` are booleans that are never `None`,
  so the flag needs at least 4 of the 5 nullable fields to be null. Two facts make that unreachable in
  the standard phase-1-init flow: `scope-estimate-heuristic` "never leaves its field unset"
  (`marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md:827`), and this plan's own D3(b)
  bridge resolves `plan_source` for every orchestrator-launched plan. Executed on the plan's own
  motivating vector with `plan_source` bridged: `{'signals_resolved': 4, 'signals_null': 3,
  'low_confidence': False}`. D3(c) passes only because its fixture pins `plan_source=None` — the state
  the same commit's bridge removes for orchestrated plans.
- **Why it matters:** the plan's Verification section prescribed a cold read — "show the Step 6
  verification sub-agent a route record with three nulls and ask how confident the decision was. If it
  reads as confident, the new field is not doing its job." A three-null record is exactly what the
  fixed router now emits for the motivating case, and it reports `low_confidence: false`. The
  resolved/null *counts* still carry the information, but the one-glance boolean an operator or a
  downstream check would key on never fires for orchestrated plans.
- **Fix:** change the `low_confidence` predicate so it keys on the *discriminating* inputs rather than
  a bare majority of the seven-member dict. Concretely: exclude `planning_lane_override` from the
  denominator (its absence is the normal state, not an unresolved read) and flag when two or more of
  the remaining nullable metadata signals (`plan_source`, `scope_estimate`, `change_type`,
  `compatibility`) are null — or, equivalently, lower the threshold to `signals_null >= 3`. Update the
  `confidence` docstring at `:622-626`, the module docstring at `:31-35`, and
  `manage-status/SKILL.md:967` to state the new rule. Add a test that feeds the recorded vector **with
  `plan_source` resolved** (3 nulls) and asserts `low_confidence is True`, so the motivating case is
  pinned post-bridge rather than pre-bridge.
- **Done when:** `evaluate_signals_pure` reports `low_confidence: True` for the plan's recorded vector
  as the fixed router now resolves it (`plan_source` non-null, `scope_estimate='single_module'`,
  `change_type=None`, `compatibility=None`, `override=None`), and a test asserts it.
- **Module/topic:** `plan-marshall:manage-status` — planning-lane router (D1 confidence block)

## G2 — Do not accept a zero-evidence `single_module` band as the signal that contradicts S7

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py:705-713` — `evaluate_signals_pure`, `scope_resolved_noncommittal` / the corroboration branch; band source at `:534` — `classify_scope_pure`, `band_rule='pathless_non_empty_body'`
- **What is wrong:** the corroboration suppresses S7 whenever `scope_estimate == 'single_module'`, but
  `classify_scope_pure` assigns that band to any non-empty body in which **zero** file paths were
  found (`band_rule='pathless_non_empty_body'`, `distinct_path_count=0`), and `_request_is_concrete`
  (`:326-343`) returns True on a bare fenced code block with no path at all. Executed: a body
  containing a fenced block plus "This change is codebase-wide and is the riskiest thing we have
  shipped" bands `single_module` via `pathless_non_empty_body`, scores `request_concrete=True` /
  `risk_prose=True`, and routes **light** with `suppressed_signals=['S7:risk_prose']`. The module
  states its own opposite discipline three hundred lines earlier: "inflation only ever pushes the band
  UP … the error mode is conservative (more planning ceremony), never a silent narrowing" (`:216-219`).
- **Why it matters:** an explicit author scale warning is de-escalated on the strength of a band that
  was derived from no measurement — the sensor's "I found nothing to bound this with" is read as
  "I measured a middle-sized change". That is a false signal shipped in the escalating direction the
  plan's D3(d) control exists to protect, and the control does not catch it because the control's
  vector fires four other signals.
- **Fix:** give the corroboration access to the band's provenance and require a *measured* middle
  band. `classify_scope_pure` already returns `band_rule`; `_evaluate_signals` computes it at `:793`
  but attaches it to the result only after `evaluate_signals_pure` has decided. Add an optional
  `scope_band_rule: str | None = None` parameter to `evaluate_signals_pure`, pass
  `scope_provenance['band_rule']` from `_evaluate_signals`, and require
  `scope_band_rule == 'path_count_middle_band'` (never `pathless_non_empty_body`, never
  `scan_incomplete`, and never `None` for callers that cannot supply it) in addition to the existing
  `scope_resolved_noncommittal` test before suppressing S7. Document the narrowing in the corroboration
  comment (`:696-704`), in `manage-status/SKILL.md:965`, and in the module docstring `:22-30`. Add two
  tests: a `pathless_non_empty_body` + S7-alone vector still routes `deep`, and a
  `path_count_middle_band` + S7-alone vector still routes `light`.
- **Done when:** an S7-alone request whose `single_module` band came from `pathless_non_empty_body` (or
  `scan_incomplete`) routes `deep` with an empty `suppressed_signals`, while the recorded
  `path_count_middle_band` case still routes `light` — both pinned by tests.
- **Module/topic:** `plan-marshall:manage-status` — planning-lane router (D2 corroboration)

## G3 — Rename the test whose name asserts the opposite of its assertion

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `test/plan-marshall/manage-status/test_planning_lane_corroboration.py:89` — `test_recorded_vector_routes_deep_without_the_corroboration_fix`
- **What is wrong:** the name says the recorded vector "routes deep without the corroboration fix",
  but the test asserts `result['lane'] == 'light'` and never runs against a pre-fix router — it flips
  `risk_prose` to `False` on the recorded vector and checks that the lane is light with an *empty*
  suppressed set. The docstring describes the real intent ("Sanity anchor … Flipping `risk_prose` off
  … yields `light`"); only the name is wrong.
- **Why it matters:** a reader scanning test names concludes the suite pins pre-fix behaviour that it
  does not pin, and a future editor may "fix" the assertion to match the name and silently invert the
  test.
- **Fix:** rename to something that states what is asserted, e.g.
  `test_recorded_vector_is_light_when_s7_does_not_fire`, and update the D3-coverage list in the module
  docstring if it names the old identifier.
- **Done when:** the test's name and its assertion agree, and the file's 12 tests still pass.
- **Module/topic:** `plan-marshall:manage-status` — planning-lane tests

## G4 — Correct the `planning-lane` CLI description, which still states an unqualified predicate

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py:699-708` — the `planning-lane` subparser `description=`
- **What is wrong:** the CLI's own `--help` text reads "'route' evaluates the DQ1 signal set (S1-S7):
  default is light; any deep-precondition signal forces deep" with no mention of either the
  narrow-and-concrete carve-out or this plan's prose-only corroboration. Two documented exceptions now
  make the sentence literally false. The run's own verification sub-agent surfaced this and
  dispositioned it "Recorded; no action" on the grounds that it was already an approximation — the D2
  change made it a second-order one. The same unqualified sentence appears at
  `_cmd_planning_lane.py:7` and `manage-status/SKILL.md:945,951`, but in both of those the
  qualification follows within the same document section; the argparse blob is self-contained.
- **Why it matters:** it is a prose-bearing string literal in production code, rendered on
  `manage-status planning-lane --help`, that overstates the predicate. An operator debugging why a
  request with a scale warning routed `light` reads the help and concludes the router is broken.
- **Fix:** in `manage-status.py`, replace "any deep-precondition signal forces deep" with "any deep-
  precondition signal forces deep, except where the narrow-and-concrete carve-out (S3/S4) or the
  prose-only corroboration (S7 alone against a resolved `single_module` scope) applies — see the
  `manage-status` skill § planning-lane". Keep the change to that `description` string; the SKILL.md
  and module-docstring occurrences may be left as-is since each is qualified in place.
- **Done when:** `manage-status planning-lane --help` names both exceptions, and no other argparse
  `help=`/`description=` string in `manage-status.py` states the unqualified predicate.
- **Module/topic:** `plan-marshall:manage-status` — CLI help text
