# PLAN-LB-82: The integrity carry fails safe, the re-freeze authorization is guarded end to end, and the tests that pin them can fail

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-82-lb-77-completion.md` and is queued as one row file, `queue/PLAN-LB-82.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-77 (#1826, `4eb58fbc1`),
> `landings/PLAN-LB-77.md` § Code defects. Priority is **medium**: PLAN-LB-77 met its Done-whens, and every
> defect below is small and either fails closed or sits on a CLI-only or double-fault path. Together they leave
> the integrity record fail-open in two places and the re-freeze authorization half guarded. **Each
> deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge
> them.** A Done-when says "fails at `4eb58fbc1`" only where the behaviour is new at that sha; a clause that
> already holds says "holds at `4eb58fbc1`". A Done-when is never labelled "holds at" while a claim it rests
> on is still a HYPOTHESIS below.

## Objective

PLAN-LB-77 made the integrity record survive stale whole-document writers and made `authorize_change` read,
check and commit under one guard. Its carry-forward treats a failed in-guard read as "the keys are gone" and a
forced re-create as "inherit the old plan's override", `authorize_refreeze` took only the log half of the
treatment, the `kept` double-fault outcome leaves an authorization that has no decision-log line standing, the
validator and the gate disagree on id-bearing rows, and four of the new tests cannot fail for the reason they
name. This plan closes those, in the order of their consequence.

## Deliverables

1. **The protected-key carry fails safe.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_carry_protected_keys` (`_status_core.py`) must not pop a protected key because the in-guard read
     failed or the document was missing, corrupt or unreadable: distinguish "read succeeded and the key is
     absent" from "read failed" and, on a failed read, refuse the write (or keep the caller's copy) rather than
     commit a document without the binding. `create --force` must start a fresh plan from a clean slate: the
     re-seed does not inherit the overwritten plan's `criteria_integrity` or
     `functional_review_override_heads`; decide at outline whether the create seed bypasses the carry or
     `cmd_create` clears the keys inside the guard, and record why. The `write_status` docstring and
     `test_lb77_integrity_carry_d1.py` name every full-document writer, including
     `plan-orchestrator/scripts/orchestrator.py` L6454 (`write_status` imported at L6427), and
     `manage-config/scripts/_cmd_finalize_steps.py` (L273 read, L301 `write_json`) commits through the guarded
     seam instead of writing the whole document unguarded.

   *Done when:* each of these fails at `4eb58fbc1`:
   - a `write_status` whose in-guard read fails (unreadable, corrupt, or missing document) leaves the on-disk
     `criteria_integrity` and `functional_review_override_heads` in place and reports the failure;
   - `manage-status create --force` over a plan carrying both keys yields a status without them;
   - `_cmd_finalize_steps` set to write while a `record_integrity` commits inside the window keeps the
     `criteria_integrity` block.

2. **The re-freeze authorization is guarded end to end and never stands unlogged.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `authorize_refreeze` takes the plan-scoped snapshot guard before its record and holds it through its log
     line and withdrawal, as `authorize_change` does, so a concurrent `write_snapshot` cannot consume an
     authorization whose decision line is never written. A withdrawal removes only the authorization this call
     set: an ownership token (or equivalent) distinguishes it from a newer, logged authorization. The `kept`
     outcome of `_commit_authorization` (double fault: the log fails and the digest re-record fails) no longer
     leaves an authorization standing without a decision-log line: it fails closed (the snapshot reads
     `tampered`, as before `171f9c359`) or records the line out of band; decide at outline and record why, and
     make `review-rubric.md` L42 and the `authorize_change` docstring (`:957-959`) say what the code does. The
     `expected=` content check and its replace run under the same guard hold (not two unguarded steps).

   *Done when:* each of these fails at `4eb58fbc1`:
   - a `write_snapshot` that starts while `authorize_refreeze` holds its record-then-log window waits for the
     guard (or is refused as `snapshot_busy`) and never consumes an unlogged authorization;
   - an older failing log withdraws only its own authorization: a newer, logged authorization survives;
   - a double fault (log fails, digest re-record fails) leaves no standing authorization without a log line;
   - the `authorize_change` docstring and `review-rubric.md` L42 contain no statement the code contradicts
     (a doc-contract test on the outcome vocabulary `withdrawn` / `restored` / `already_consumed` /
     `not withdrawn` / `kept` / `inconsistent`).

3. **The validator and the gate agree on id-bearing rows, and the new tests can fail.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `verdict_row_matches` (`_criteria_snapshot.py:1254-1270`) stops accepting an id-bearing row by text
     where `_graded_status` (`:1299-1304`) skips it, so `_review_support_validate.py:535`
     (`unmatched_criterion`) names the row the gate leaves open. Replace the tests that cannot fail for the
     reason they name: the deliverable-qualified-id test reaches the id-names-another-deliverable branch
     (`:1266-1267`); the rollback test injects the failure into the atomic restore itself (fault at
     `os.replace`) and asserts the snapshot afterwards, and a raw `os.write` regression fails it; the
     refreeze-before-the-guard test's success-arm assertions run in a configuration where they execute or are
     removed; the protected-set test checks which verbs write which top-level keys instead of pinning a
     constant; the `write_snapshot`-site conditional rollback (`:792`) and the `restored` and
     `NOT withdrawn` outcomes get tests. Each replaced test is run against a mutation of the code it names and
     the failing run recorded (`order=mutation-after` acceptable and labelled).

   *Done when:* each of these fails at `4eb58fbc1`:
   - a row with `criterion_id: C9` (or `C2`) whose text equals criterion 1's frozen text produces an
     `unmatched_criterion` finding in the validator;
   - the replaced rollback test fails when `_roll_back_snapshot` regresses to a raw `os.write` replacement;
   - each replaced or new test fails under a mutation of the code it names, run and recorded.

4. **The atomic byte writer is durable.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `file_ops.atomic_write_bytes` (`:1566-1592`), which `atomic_write_file` now delegates to, fsyncs the temp
     file (and its directory) before `os.replace`, keeps the replaced file's permission bits instead of the
     temp file's 0600, and closes the descriptor when `os.fdopen` raises. Pre-existing in
     `atomic_write_file`; PLAN-LB-77 widened its reach by making it the snapshot rollback path.

   *Done when:* each of these fails at `4eb58fbc1`:
   - a file replaced through `atomic_write_bytes` keeps its previous mode;
   - an `os.fdopen` failure leaves no open descriptor and no temp file;
   - the temp file is fsynced before the replace (asserted on call order).

## Claim Labels

- OBSERVED: `_carry_protected_keys` pops a protected key the live document lacks, and `rmw_json` reads a missing, corrupt or unreadable document as `{}` inside the guard — `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py` L229-242, `_locks_core.py` L314-324 (corroboration of the PLAN-LB-77 landing; `_status_core.py` re-read by the orchestrator).
- OBSERVED: the create seed commits through `write_status` — `manage-status/scripts/_cmd_lifecycle.py` L1204 (read by the orchestrator); `create --force` is `manage-status.py` L144 (corroboration, not re-read).
- OBSERVED: `authorize_refreeze` records through `_merge_integrity` (status guard only), logs, then withdraws; it takes no snapshot guard — `manage-solution-outline/scripts/_criteria_snapshot.py` L303-393 (read by the orchestrator).
- OBSERVED: the `kept` outcome re-commits the authorization after a double fault; `criteria_drift` (`:861`) and `open_criteria` (`:1187`) honour it — `_criteria_snapshot.py` L1084-1094 (corroboration; not re-read).
- OBSERVED: `verdict_row_matches` accepts id-bearing rows by text while `_graded_status` skips them — `_criteria_snapshot.py` L1254-1270 vs L1299-1304; consumer `phase-6-finalize/scripts/_review_support_validate.py` L535 (corroboration).
- OBSERVED: `manage-config/scripts/_cmd_finalize_steps.py` reads the status at L273 and writes with `write_json` at L301 with no guard (corroboration; PLAN-LB-77's own landing lists it).
- OBSERVED: `atomic_write_bytes` has no fsync, replaces the target's mode with mkstemp's 0600, and leaks the descriptor if `os.fdopen` raises — `tools-file-ops/scripts/file_ops.py` L1584-1592 (corroboration).
- OBSERVED: the named D3 rollback test sabotages `Path.open`, which the fixed path never calls; the deliverable-qualified-id test is refused by position — `test/plan-marshall/manage-solution-outline/test_lb77_graded_and_rollback_d3.py` L78, L89 (corroboration).
- HYPOTHESIS: a transient in-guard read failure is reachable in practice (EACCES, EIO, a half-written file) — confirm at `_locks_core.py` L314-324 and decide whether `rmw_json` distinguishes the cases before D1 is scoped (verify-at-outline).
- HYPOTHESIS: holding the snapshot guard across the whole `authorize_refreeze` cannot deadlock against `write_snapshot` or `authorize_change` — confirm both acquire snapshot guard then status guard (verify-at-outline; PLAN-LB-77 settled the same for `authorize_change`).
- Verify-first clause: decide for D1 whether the create seed bypasses the carry or `cmd_create` clears the keys, and for D2 which of "fail closed" or "log out of band" the `kept` outcome takes, before those deliverables are scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py` — `_carry_protected_keys`, `write_status` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the create seed (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py` — the unguarded status write (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — `authorize_refreeze`, `_commit_authorization`, `_roll_back_snapshot`, `verdict_row_matches` (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py` — the `criteria-authorize` docstring (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — L42 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py` — the `unmatched_criterion` check (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` — `atomic_write_bytes` (D4)
- OBSERVED: `test/plan-marshall/manage-status/` and `test/plan-marshall/manage-solution-outline/` and `test/plan-marshall/phase-6-finalize/` and `test/plan-marshall/manage-config/` and `test/plan-marshall/tools-file-ops/` — the fixtures of D1 to D4

## Dependencies and Sequencing

- Depends on: PLAN-LB-77 (shipped, `4eb58fbc1`).
- Overlaps with: the staged PLAN-LB-75 (`_criteria_snapshot.py`, `manage-status/scripts/`, `phase-6-finalize/scripts/`) and the staged PLAN-LB-53 and PLAN-LB-55 on `manage-status/scripts/`. The emit gate decides; this plan goes before PLAN-LB-75, because PLAN-LB-75's reach work reads the integrity record this plan repairs, and after PLAN-LB-78 (the lane that runs it).
- Adjacent to: PLAN-LB-49 D1 (the build-server and runtime readers) — no shared file.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-82-lb-77-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
