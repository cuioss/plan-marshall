# Verification — 160-empty-skill-resolution-indistinguishable-from-minimal

**Audited:** `plan.md`, `report-01.md` (no other sibling files exist in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `f29e5ce` — `fix(manage-architecture): distinguish unresolved skill profile from declared-minimal (#1220)`, confirmed an ancestor of `origin/main` (`git merge-base --is-ancestor f29e5ce origin/main` → true)
**Overall verdict:** CONFIRMED WITH GAPS

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: re-ground; name the resolution site | Site named (`detect_stale_skills_by_profile`); indistinguishability confirmed | Site correct; pre-fix guard had only the whole-map branch (`git show f29e5ce~1`, line 465). But the asserted absence ("nothing reports the missing skills") is overstated — pre-fix `phase-4-plan` Step 5 already logged a WARNING **and** recorded a Q-Gate triage finding for an empty/missing profile | CONFIRMED (with a report-accuracy defect) |
| D2 | Declarable minimality in the inventory | Boolean `minimal` marker; fail-closed validation; schema documented | Marker read fail-closed (`_cmd_client_query.py:470`), validated on the `enrich skills-by-profile` write path (`_cmd_enrich.py:198`), three-state table in `architecture-persistence.md:455-466`, survives TOON serialization | CONFIRMED (incomplete: no writer-workflow adoption; `enrich add-domain` can produce a contradictory populated+`minimal` block) |
| D3 | Report the named condition at allocation time, non-fatal | Guard emits per undeclared-empty profile; phase-4-plan re-worded; non-fatal | Condition emitted end-to-end (proven by direct call, below) and never raises; phase-4-plan Step 5 carries the LLM-side branch. Three narrowings: the guard is blind to an **absent** profile (the shape the writers actually produce), the message reaches only a log file (never the command's TOON payload), and the emitter drops the condition entirely when the bundles root cannot resolve | PARTIAL |
| D4 | Test failing today, in BOTH directions | Three guard tests + two enrich-validator tests; pre-fix `2 failed, 7 passed` | All five tests exist and pass (9 passed in the guard file, re-measured). Both directions independently proven non-vacuous by mutation; the reported pre-fix signature was reproduced exactly | CONFIRMED (one untested sub-claim: the fail-closed `is True` identity check) |

## Per-deliverable detail

### D1 — GATE: re-ground against the current tree

- **Required (plan):** *"the resolution site is named with its symbol, and the indistinguishability is either confirmed or the plan re-scoped on the refutation."* The plan adds: *"An asserted absence … is verified exactly as an asserted presence — confirm at the allocation site that no such report exists before building one."*
- **Claimed (report):** `detect_stale_skills_by_profile` in `_cmd_client_query.py` (pre-fix lines 448–473), reached via `_emit_skills_by_profile_staleness_warning` (489) on the `get_module_info` (533) read path, exercised by phase-4-plan Step 5's module pre-fetch. Indistinguishability CONFIRMED — a per-profile empty produced *"zero signal"*.
- **Found:** the pre-fix file (`git show f29e5ce~1:…/_cmd_client_query.py`, re-derived line numbers: `448` def, `465` `if not skills_by_profile:`, `489` emitter, `517` `get_module_info`) has exactly two branches — whole-map empty, and stale notations. A present-but-empty profile block returns `[]`. The report's cited line for `get_module_info` (533) is off; the pre-fix symbol is at 517. Every other cited line matches.
- **Checks run:** read the pre-fix and current guard; re-derived the four line numbers with `grep -n` over `git show f29e5ce~1`; read pre-fix `phase-4-plan/SKILL.md` Step 5.
- **Verdict:** CONFIRMED for the resolution site and for the indistinguishability. **But the asserted-absence check was not completed as the plan required:** pre-fix `phase-4-plan/SKILL.md` Step 5 already said *"Log WARNING: … Module {D.module} has empty skills_by_profile.{P} — task will have no domain skills"* and *"Record a Q-Gate triage finding … 'Missing skills_by_profile: {D.module}.{P}'"*. A report of the absence therefore existed at the allocation site before this plan; what did **not** exist was any way to tell a deliberate empty from an unresolved one. The report's framing (*"an empty `skills[]` degrading to the persona floor"*, *"zero signal"*) is true of the script guard and false of the allocation site as a whole, and the discrepancy is not disclosed. → G10.

### D2 — make the two states distinguishable in the inventory

- **Required (plan):** *"the declaration exists in the schema and an undeclared empty is representable as a distinct state"*, settled against the closed-vocabulary posture, with the reasoning recorded, *"including what makes the next unmarked-empty profile detectable."*
- **Claimed (report):** boolean `minimal` on a profile block; reasoning recorded against `resolver_count` / `truncated`-`elided`; fail-closed validation in `_validate_skills_by_profile_structure`; three-state table in `architecture-persistence.md`.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:462-470` — `_profile_declares_minimal`, `profile_data.get('minimal') is True`.
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py:192-202` — non-boolean `minimal` flagged; `enrich_skills_by_profile` (`:469-485`) still persists the block and returns `status: success` with `warnings[]`, so a malformed declaration stays in the undeclared-empty state on read, as claimed.
  - `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/architecture-persistence.md:437-474` — three-state table (Populated / Declared minimal / Undeclared empty) plus the read-path condition.
  - `test/plan-marshall/manage-architecture/test_cmd_enrich.py:469-498` — the two validator tests exist and pass.
- **Checks run:** read all four surfaces; serialized a `minimal: true` profile through the real TOON writer to confirm the declaration reaches a reader —
  `uv run python -c "from toon_parser import serialize_toon; …"` → `module_testing:` / `defaults[0]:` / `optionals[0]:` / `minimal: true`. So the marker is observable in `architecture module` output, which is what phase-4-plan reads.
- **Verdict:** CONFIRMED as specified, with two completeness gaps:
  1. **The ordinary write path can manufacture the contradictory state the report dismissed as "nonsensical input".** `enrich_add_domain` copies the existing block (`_cmd_enrich.py:337` `merged = dict(existing)`) and appends new defaults (`:344`) — a previously declared-minimal profile that a later domain enrichment populates becomes `{"defaults":[x], …, "minimal": true}`. That path never calls `_validate_skills_by_profile_structure`. → G2.
  2. **Nothing in the writer-facing workflow mentions the marker.** `manage-architecture/SKILL.md:306` still requires *"Every module has `skills_by_profile` with at least `implementation` and `module_testing`"* with no declared-minimal alternative, and `marshall-steward/references/skill-domains-setup.md:84` still claims enrich-all makes *"downstream phase-4-plan tasks always receive a non-empty skill list"*. → G7, G8.

### D3 — report the named condition at allocation time (non-fatal)

- **Required (plan):** *"the condition surfaces in allocation output and does not abort the run."*
- **Claimed (report):** the guard emits the named condition per undeclared-empty profile as a non-blocking `[STALENESS]` WARNING on the `architecture module` read exercised by phase-4-plan's pre-fetch; a `minimal: true` profile emits nothing; phase-4-plan Step 5 aligned in lock-step.
- **Found:**
  - `_cmd_client_query.py:496-519` — per-profile branch; message text matches the report verbatim.
  - `_cmd_client_query.py:535-564` — emitter; `:558-564` swallows logging exceptions; `get_module_info` calls it at `:584` and never propagates.
  - `phase-4-plan/SKILL.md:313-320` (Step 5 pseudocode), `:1169-1170` (scenario table), `:1186-1194` ("Profile Not in Module") — declared-minimal short-circuits with no warning and no finding; the undeclared/absent branch logs the UNRESOLVED WARNING and records a Q-Gate triage finding, then continues.
- **Checks run:** executed the emitter directly against a map with a populated `implementation` and an empty, undeclared `module_testing`, with `plan_logging.log_entry` captured:
  → `['[STALENESS] module 'm': profile 'module_testing' resolves no skills and is not declared minimal — set "minimal": true …', '[STALENESS] … absent from the live registry: a:b']`. Non-fatal confirmed (returns `None`, raises nothing).
  Then repeated with `marketplace_bundles.resolve_bundles_root` patched to raise: → `[]`, while the pure core still returned the unresolved-profile message. The control run proves the harness, so the empty result is the code's behaviour, not an artifact.
- **Verdict:** PARTIAL — the condition exists, is named, and is non-fatal, but three narrowings mean it does not fire for the situations most likely to occur:
  1. **Fail-open emitter.** `_cmd_client_query.py:543-549` returns as soon as the bundles root cannot be resolved, discarding the unresolved-profile signal — while the module comment at `:428-431` states the opposite: *"the missing/empty and unresolved-profile checks still fire because they need no registry."* → G1.
  2. **Absent profiles are invisible to the guard.** Both writers omit a profile that resolves nothing rather than writing an empty block (`script-shared/scripts/extension/extension_base.py:1190` `if merged_defaults or merged_optionals:`; `_cmd_enrich.py:329` `if not new_entries: continue`). The guard only inspects blocks that are present, so the shape the machinery actually produces for "the inventory answered nothing" produces no deterministic signal. Only phase-4-plan's LLM-executed prose covers the absent case. → G3.
  3. **The message never enters the structured output.** `log_entry('script', None, …)` writes to a log file under the plans store (`manage-logging/scripts/plan_logging.py:287-314`); the returned `architecture module` dict carries no `warnings` field. The deterministic surface is therefore a side channel no allocation-time consumer reads. → G9.

### D4 — a test that fails today, in BOTH directions

- **Required (plan):** *"both assertions exist and the empty-case assertion is verified to fail before the fix"*; the Verification section adds *"Both, or neither counts."*
- **Claimed (report):** three guard tests (`test_warns_on_unresolved_undeclared_empty_profile`, `test_no_warning_on_declared_minimal_profile`, `test_declared_minimal_and_unmarked_empty_are_distinguishable`); pre-fix run `2 failed, 7 passed` with `AssertionError: []`; post-fix `9 passed`.
- **Found:** `test/plan-marshall/manage-architecture/test_skills_by_profile_staleness_guard.py:122-152` — all three, exactly as named.
- **Checks run:**
  - Baseline: `uv run python -m pytest test/plan-marshall/manage-architecture/test_skills_by_profile_staleness_guard.py -o addopts="" -q` → **9 passed** (matches the report).
  - Mutation M3 — `_profile_declares_minimal` → `return True` (the pre-fix behaviour of never distinguishing): → **2 failed, 7 passed**, failing `test_warns_on_unresolved_undeclared_empty_profile` and `test_declared_minimal_and_unmarked_empty_are_distinguishable` — the report's pre-fix signature reproduced test-for-test.
  - Mutation M2 — `_profile_declares_minimal` → `return False` (the declaration ignored): → **2 failed, 7 passed**, failing `test_no_warning_on_declared_minimal_profile` and the two-directional test. The declared-minimal direction is therefore also non-vacuous.
  - Mutation M1 — `is True` → `bool(...)` (the fail-closed identity check weakened to a truthy check): → **9 passed**. The fail-closed property the report, the docstring (`:465-468`) and `architecture-persistence.md:461-466` all advertise is **not** covered by any guard test. → G4.
  - The mutated file was restored from a byte snapshot taken before mutation (`md5sum` identical: `7af6ab64430af50ff6d71cf847a141cc`) and `git status --porcelain` shows no modification to it.
- **Verdict:** CONFIRMED. Both directions exist and both are load-bearing; the pre-fix failure claim is independently corroborated. The single uncovered sub-claim is the `is True` identity check.

## Correctness review

Read in full: `_cmd_client_query.py:416-599` (guard, emitter, `get_module_info`), `_cmd_enrich.py:169-224`, `:262-372`, `:463-485`, `:625-641`, `extension_base.py:1160-1201`, `_cmd_client_render.py:135-161`, `plan_logging.py:162-315`, `phase-4-plan/SKILL.md:294-327`, `:1159-1195`. Defects found:

1. **Fail-open emitter contradicting its own comment** — `_cmd_client_query.py:543-549`. Condition: `skills_by_profile` non-empty **and** `resolve_bundles_root` raises (any deployment layout the walker does not recognise; `marketplace_bundles.py:200-231` raises `RuntimeError` when no `plan-marshall` bundle ancestor is found). Consequence: every signal is suppressed, including the two the comment at `:428-431` promises need no registry. Proven by execution (§ D3). The pre-fix code had the same early return, but the *claim* that the new signal is registry-independent was added by this plan and is false.
2. **A contradictory populated+`minimal` block is reachable from the ordinary write path** — `_cmd_enrich.py:332-348`. Condition: a profile declared `{"defaults": [], "optionals": [], "minimal": true}` is later populated by `enrich add-domain` / `enrich all`. Consequence: `phase-4-plan/SKILL.md:314-316` tests `minimal` **before** emptiness, so the task is created with `skills: []` although the inventory resolved real skills — a silent skill loss, with the guard silent too (it treats the block as populated). The report dismissed this as "nonsensical input"; the enrichment path makes it ordinary input.
3. **The deterministic guard cannot fire for the writers' actual "nothing resolved" shape** — `extension_base.py:1190` and `_cmd_enrich.py:329` omit empty profiles, and the guard only walks present blocks (`_cmd_client_query.py:502-511`). A module missing `module_testing` entirely — the originating observation's shape — yields no guard message.
4. **A legacy list-shaped profile block is skipped silently** — `_cmd_client_query.py:504-505` `continue`s on any non-dict `profile_data`, so `"module_testing": []` (a shape `_cmd_client_render.py:138` still supports) never surfaces the unresolved condition. The inline justification ("structural defects are the enrich validator's surface") does not hold for `enrich add-domain` / `enrich all`, which never run that validator.
5. No fail-open, off-by-one, unguarded `None`, or order-dependency found in `detect_stale_skills_by_profile` itself: the map-type guard, the whole-map guard, the per-profile loop over a sorted key list, and the stale-notation set are each total over the inputs the tests and the schema admit.

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D2 (schema + fail-closed validation) | `test_cmd_enrich.py:469-498` (`…declared_minimal_persists_without_warnings`, `…warns_on_non_boolean_minimal`) | Non-vacuous for the write path. No test covers `enrich_add_domain` preserving `minimal` while adding skills (the G2 path). |
| D3 (named condition, non-fatal) | `test_skills_by_profile_staleness_guard.py:122-152` — core function only | The emitter `_emit_skills_by_profile_staleness_warning` has **no test at all** (`grep -rn "_emit_skills_by_profile_staleness_warning" test/` → no hits, while the same grep over `marketplace/` finds the definition and its call site, so the search is not silently filtered). Its fail-open branch, its `[STALENESS]` prefix, and its exception swallowing are unexercised. → G5 |
| D4 (both directions) | The three tests at `:122-152` | Non-vacuous in both directions — proven by mutations M2 and M3 (§ D4). |
| Fail-closed `is True` | — | **Vacuous by omission**: mutation M1 (`is True` → truthy) leaves all 9 tests green, so a change that lets `"minimal": "true"` launder the signal ships undetected — the exact laundering the plan's design caveat exists to prevent. → G4 |

## Report accuracy

Claims re-derived against the tree now:

- **Held.** The site names and symbols in D1; the pre-fix line numbers 448/465/489 (`get_module_info` is the exception, see below); the message text in D3; the three test names and the `9 passed` post-fix figure (re-measured); the two enrich-validator test names; the pre-fix `2 failed, 7 passed` signature and which two tests failed (reproduced by mutation M3); "two production scripts and two test files changed" (`git show --stat f29e5ce`: `_cmd_client_query.py`, `_cmd_enrich.py`, `test_cmd_enrich.py`, `test_skills_by_profile_staleness_guard.py`, plus `architecture-persistence.md`, `phase-4-plan/SKILL.md`, the moved `plan.md`, the report); findings 1–4 are all actually fixed in the tree (`_cmd_client_query.py:419-431`, `:476-495`, `:536-539`, `:581-583`; `phase-4-plan/SKILL.md:1169-1170`).
- **Overstated — D1's asserted absence.** *"produces **zero** signal"* / *"an empty `skills[]` degrading to the persona floor"*. Pre-fix `phase-4-plan/SKILL.md` Step 5 already logged a WARNING and recorded a Q-Gate triage finding for an empty or missing profile. Correct statement: the *script-side* guard produced zero signal; the allocation site already reported the absence, but could not distinguish it from a deliberate empty. → G10
- **Overstated — D3's surface.** *"It is surfaced … as a non-blocking `[STALENESS]` WARNING on the `architecture module` read"* implies the condition reaches the caller's output. It reaches a log file only; the returned module payload carries no warning field. → G9
- **Refuted — finding #6's rejection rationale.** *"Rejected (out of scope) — nonsensical input; neither the plan nor the closed-vocabulary posture asks to reconcile a `minimal` flag on a populated profile."* `enrich_add_domain` produces exactly that state from ordinary enrichment (`_cmd_enrich.py:337,344`). → G12, G2
- **Stale line citation.** *"the `architecture module` read path (`get_module_info`, line 533)"* — in the pre-fix file `get_module_info` is at line 517; in the current tree, 567.
- **Structural defect.** The report ends with a duplicate stub block — `## Cost`, `## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue`, each `_pending_` (report lines 251-265) — after the same four sections were already filled in above. → G11
- **Unverifiable.** `./pw verify plan-marshall` = *"16446 passed, 1 skipped"* in `0:08:09`, and the mypy file counts (278 / 588). Not re-run: out of scope per the audit brief and the tree has moved on by ~15 merged PRs since.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing** — auto-merge armed on PR #1220, merge SHA not yet known | **Closed** | `f29e5ce` is an ancestor of `origin/main` (`git merge-base --is-ancestor` → true); commit title carries `(#1220)`. |
| **Out-of-scope (a)** — `_cmd_client_render.py` renders per-profile *counts*, so declared-minimal and undeclared-empty both render `0 skills` | **Still open** | `_cmd_client_render.py:143-160` — `_count_profile_skills` only sums `defaults`+`optionals`; `grep -rn minimal _cmd_client_render.py` → no hits. → G14 |
| **Out-of-scope (b)** — contradictory `{"defaults":[x], "minimal": true}` treated as populated by the guard but emptied by phase-4-plan Step 5 | **Still open, and worse than recorded** | Reachable from `enrich add-domain`, not only from hand-written input (`_cmd_enrich.py:337,344`). → G2 |
| **Contract-change proposal** — name `uv run pytest <file>` in the cloud-plan-lane § Step 5 | **Closed** | `ce57b74` — `chore(cloud-plan-lane): document targeted single-file test command (#1226)`, 13 lines added to `.claude/skills/cloud-plan-lane/SKILL.md`; the note is live at `SKILL.md:528-537`. |

## Out-of-scope and collateral

- **"A consuming project's own inventory gap"** — respected. Nothing in the diff touches consumer data; `git show --stat f29e5ce` lists only bundle sources, tests, one standard, one skill, and the plan's own files.
- **"Hard-failing on an empty resolution"** — respected. The guard returns a list; the emitter swallows exceptions; `get_module_info` continues (`:584`); phase-4-plan continues with `skills: []`. Verified by direct execution (no exception raised).
- **"Inventing a new vocabulary mechanism"** — respected in spirit: the marker is one boolean on the existing profile block, read by the guard that already reports `skills_by_profile` health, with the reasoning tied to `resolver_count` / `truncated`-`elided` (`architecture-persistence.md:450-453`).
- **Collateral:** none undeclared. The eight changed paths in `f29e5ce` are all named in the report (four code/test, two docs, plan move, report). No later commit has modified the guard's minimal-related code (`git diff f29e5ce..HEAD -- _cmd_client_query.py` shows only unrelated graph/command-resolution changes from other plans).

## Method and coverage

Checked:

- Read `plan.md`, `report-01.md`, the epic README, the landed commit (`git show f29e5ce`), and the pre-fix versions of both changed scripts and `phase-4-plan/SKILL.md`.
- Read the shipped guard, emitter, validator, both enrichment write paths, the extension skill-resolution producer, the render path, the TOON writer, and the logging entry point.
- Ran the guard test file three times under mutation plus a clean baseline; restored the mutated file from a pre-mutation byte snapshot and confirmed `md5sum` equality and a clean `git status` for that path.
- Executed the emitter directly (control + fault-injected) to establish both the working signal and the fail-open branch.
- Serialized a `minimal: true` block through the real TOON writer to confirm reader-side observability.
- Re-derived every line number and count quoted above at the moment of writing; nothing is copied from the report as measurement.

Not checked (and why):

- `./pw verify plan-marshall` and its 16446-test figure — excluded by the audit brief; the tree has advanced well past the plan's commit, so a re-run would not test the report's claim anyway. **UNVERIFIABLE.**
- The PR-surface claims (reviewer participation, CI check states, "no inline review threads") — they describe a point in time on PR #1220 and are not re-derivable from the tree. **UNVERIFIABLE.**
- The wall-clock and token figures in § Cost — self-reported session facts, not tree-checkable. **UNVERIFIABLE.**
- The behaviour of phase-4-plan Step 5 itself: it is LLM-executed prose with no automated test, so its conformance can be read but not exercised. Every verdict about it above is a reading of the text, not an execution.
