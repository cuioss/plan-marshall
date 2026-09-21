envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:06:00Z

component=plan-marshall:manage-execution-manifest
category=bug
bundle=plan-marshall

# The finalize ceremony pre-filter dropped the security audit on a 47-file code change, gated on a stale change_type and a partial file list

## Observation

At manifest-compose time (`decision.log`, 14:13:57Z and again 14:14:28Z) the ceremony pre-filter
logged:

```
finalize-step-simplify omitted — change_type=analysis affected_files_count=21
finalize-step-security-audit omitted — change_type=analysis affected_files_count=21
```

Both inputs were wrong at the moment they were read:

**`change_type=analysis` was stale.** `phase-1-init`'s heuristic detected `change_type=analysis`
with `confidence=1.0` (`work.log:4`), and `phase-3-outline` corrected it to `enhancement` at
12:30:53Z (`work.log:34`). `status.metadata.change_type` reads `enhancement` today. The composer
ran at 14:13 — nearly two hours after the correction — and still gated on `analysis`.

**`affected_files_count=21` was a partial list.** `references.affected_files` holds 21 paths, and
they are the affected files of deliverables 4-7 only. The outline's union across all 8 deliverables
is 59 paths; the realized merged footprint is 47. So the gate saw 21 of a 47-file change.

The net effect: `finalize-step-security-audit` was dropped from a plan that rewrote PR-comment
ingestion, GitHub API call paths, and a cross-plan lock store — precisely the surface a security
audit exists for. A third signal shows the composer knew the footprint was untrustworthy:
`pre-push-quality-gate omitted — plan footprint is empty — no changed files to build`. The quality
gate survived only because a separate ceremony rule (`finalize.qgate=always`) added it back; a
project without that setting would have shipped with no gate at all.

## Do this instead

- **Read `change_type` at compose time from `status.metadata`, not from a phase-1 snapshot.** A
  value corrected in a later phase must win; the correction is exactly the signal the gate needs.
- **Gate on the outline deliverable union (or the live footprint), not `references.affected_files`.**
  That field is demonstrably not the plan footprint. Either fix it to be the union or stop reading
  it for gating decisions.
- **An empty/absent footprint must not read as "small".** `footprint is empty` at phase-4 means
  "not yet executed", not "nothing to build". A ceremony gate whose input is structurally
  unavailable must fail closed (keep the step), never omit.
- Add a regression asserting that a plan whose realized footprint exceeds N files cannot have
  `finalize-step-security-audit` pre-filtered out on a `change_type` that a later phase overwrote.

## Recurrence context

Epic theme `truthful-signals`: three separate confident gate decisions
(`change_type=analysis`, `affected_files_count=21`, `footprint is empty`) each logged a precise
justification, and all three were reading stale or partial state. The plan shipped safely only
because an unrelated `qgate=always` rule happened to compensate.
