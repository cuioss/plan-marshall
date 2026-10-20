# PLAN-LB-77: The integrity record cannot be lost and the re-freeze authorization is read and committed under one guard

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-77-lb-74-completion.md` and is queued as one row file, `queue/PLAN-LB-77.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-74 (#1822, `e1481166c`),
> `landings/PLAN-LB-74.md` § Code defects. Priority is **high**: PLAN-LB-74 shipped D3 without achieving
> what D3 was for, and shipped a re-freeze fix (`c83f8b793`) that nobody reviewed. **Each deliverable is its
> own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A Done-when
> says "fails at `e1481166c`" only where the behaviour is new at that sha; a clause that already holds says
> "holds at `e1481166c`". Grade each deliverable against THIS spec's Done-when text; an outline that
> rewrites a Done-when must say so and why. A Done-when is never labelled "holds at" while a claim it rests
> on is still a HYPOTHESIS below.

## Objective

PLAN-LB-74 serialised the integrity record behind the status writers' lock, but the lock only orders two
writes: a status writer that read the document before the integrity record was committed still writes its
stale copy afterwards and drops the `criteria_integrity` block. The re-freeze authorization has the same
shape one level down: it reads the snapshot and checks for tampering before taking the new snapshot guard,
then commits from the stale copy. This plan makes both read-modify-write sequences atomic, and closes the
smaller matching and protection defects found in the same review.

## Deliverables

1. **A status writer cannot overwrite the integrity record.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_status_core.write_status` commits the caller's whole document as it read it before taking the
     guard, refreshing only `title_token`. Inside the guard it must carry the protected integrity keys
     (`criteria_integrity`, `functional_review_override_heads`) forward from the document on disk, or
     re-read and merge the document the way `rmw_json` writers do; choose at outline, record why, and
     name every `require_status` → `write_status` caller the choice covers.

   *Done when:* each of these fails at `e1481166c`:
   - a status writer that read the document, then waited while `record_integrity` committed a
     `criteria_integrity` block, then wrote, leaves the block present after the write;
   - the same for `functional_review_override_heads` appended by `loop-back close` while a
     `mark-step-done` writer was waiting on the guard;
   - the D3 lock test of PLAN-LB-74 (`test_record_integrity_waits_for_the_status_guard`) still passes
     (holds at `e1481166c`).

2. **The re-freeze authorization is read, checked and committed under one guard, and logs only on commit.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - In `_criteria_snapshot.py`, `authorize_change` (`read_snapshot` / `snapshot_state` at `:888-896`, guard
     at `:942`, `_commit_authorization` `:953-999`) takes the plan-scoped snapshot guard before it reads
     the snapshot or checks tampering, and writes its decision-log line only after the commit succeeds.
     `authorize_refreeze` (`:311-329`) has the same log-before-record shape and gets the same treatment.

   *Done when:* each of these fails at `e1481166c`:
   - a re-freeze that commits between the authorization's read and its guard is not reverted: the
     refrozen snapshot and its digest survive, and the authorization either applies to the refrozen
     snapshot or is refused;
   - two concurrent `authorize_change` calls both leave their `authorized_changes` entry;
   - a `snapshot_busy` result writes no decision-log line.

3. **The smaller matching, protection and rollback defects.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_graded_status`'s text arm must not close a criterion when the row carries a `criterion_id` that
     names a different criterion; a `D{n}.C{m}`-qualified row refused by the id arm must not match by text.
   - `metadata --set` protects the key that is actually written at the top level of `status.json`
     (`criteria_integrity`); `snapshot_frozen` is an inner key of it, so its top-level protection is
     removed or documented as a guard on a name no verb writes — choose at outline and record why.
   - The snapshot rollback restores the prior bytes atomically (write-and-replace), not by
     `path.write_bytes`, and the `_merge_integrity` docstring and the stale `#:` comment above
     `FUNCTIONAL_REVIEW_STEP` in `_cmd_loop_back.py` say what the code does.

   *Done when:* each of these fails at `e1481166c`:
   - a verdict row carrying `criterion_id: C2` whose text equals criterion 1's frozen text grades C2 and
     leaves C1 open;
   - a failure injected during the rollback write leaves the prior snapshot bytes intact (no truncated
     file);
   - the protected top-level key list names no key that no verb writes at the top level.

## Claim Labels

- OBSERVED: `write_status` commits the caller's whole document as read before the guard and refreshes only `title_token` — `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py` L142-185 (landing analysis of PLAN-LB-74, read at `e1481166c`).
- OBSERVED: the writers `require_status` → `write_status` include `metadata --set/--append`, `mark-step-done` and the phase writes — `manage-status/scripts/_status_query.py` L116/158, L180/199, L386/412 (landing analysis of PLAN-LB-74).
- OBSERVED: `authorize_change` reads the snapshot and checks tampering before taking the snapshot guard, then rewrites from the stale dict and re-records the digest — `manage-solution-outline/scripts/_criteria_snapshot.py` L888, L896, L942, L953-999.
- OBSERVED: the decision-log line is written before the guard in `authorize_change` (L928-940) and `authorize_refreeze` (L311-329).
- OBSERVED: `_graded_status`'s text arm grades a row by text even when its `criterion_id` names another criterion — `_criteria_snapshot.py` L1159 and the second loop.
- OBSERVED: `SNAPSHOT_FROZEN_KEY` is an inner key of `criteria_integrity` (L110) and its top-level protection is a no-op — `manage-status/scripts/_status_query.py` L72.
- OBSERVED: the rollback writes with a non-atomic `path.write_bytes` — `_criteria_snapshot.py` L625.
- OBSERVED: lock order is always snapshot guard → status guard and no reverse path exists; only `manage-solution-outline.py` L1268 and L1281 call `write_snapshot` / `authorize_change`.
- HYPOTHESIS: carrying the protected keys forward inside `write_status` covers every writer that can interleave with `record_integrity` — confirm against every `write_status` call site in `manage-status/scripts/` (verify-at-outline).
- HYPOTHESIS: taking the snapshot guard before the read in `authorize_change` cannot deadlock against `write_snapshot` — confirm both acquire in the order snapshot guard then status guard (verify-at-outline).
- Verify-first clause: decide whether D1 carries the keys forward or re-reads and merges, before D1 is scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py` — `write_status` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` — protected keys (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — the stale comment, and the override-head writer under D1 (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — `authorize_change`, `authorize_refreeze`, `_graded_status`, the rollback (D2, D3)
- OBSERVED: `test/plan-marshall/manage-status/` and `test/plan-marshall/manage-solution-outline/` and `test/plan-marshall/phase-6-finalize/` — the fixtures of D1 to D3

## Dependencies and Sequencing

- Depends on: PLAN-LB-74 (shipped, `e1481166c`).
- Overlaps with: the staged PLAN-LB-75 (`_criteria_snapshot.py`, `manage-status/scripts/`,
  `phase-6-finalize/scripts/`) and the staged PLAN-LB-53 and PLAN-LB-55 on `manage-status/scripts/`. The
  emit gate decides; this plan is **high** and goes before PLAN-LB-75, because it repairs the integrity
  record PLAN-LB-75's reach work reads.
- Adjacent to: `phase-6-finalize/scripts/_review_support_validate.py` (PLAN-LB-74 D4, clean) — untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-77-lb-74-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
