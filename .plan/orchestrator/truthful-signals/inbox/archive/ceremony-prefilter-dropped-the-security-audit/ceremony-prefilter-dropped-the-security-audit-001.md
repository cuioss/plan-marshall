envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=landing
created=2026-07-29T15:45:32Z

## What landed

PLAN-112 — "The finalize ceremony pre-filter dropped the security audit on a 47-file code change".
PR #1055, merged. Plan id: `ceremony-prefilter-dropped-the-security-audit`.

The finalize ceremony pre-filter silently dropped `finalize-step-security-audit` from a plan whose
delta touched 47 files. The drop was correct-by-code and wrong-by-intent: the gate's `change_type`
leg read a value that described only part of the plan.

### Shipped

- `security_audit_inactive` → `security_class_inactive`. The gate is now a **class** gate, not a
  single-step gate.
- **No `change_type` leg.** The gate fails toward inclusion: it drops only when the declared
  affected files AND the live footprint are **both** empty. A stale or mis-scoped `change_type`
  can no longer suppress a security audit.
- **Protected population is derived, not enumerated.** Membership comes from the step's frontmatter
  `persona: persona-security-expert`, not from a hardcoded step id — so a future security-class step
  is protected on the day it is added, with no edit to the gate.
- **The drop is loud.** `security_audit_omitted: bool` → `security_class_omitted: [{step, reason}]`,
  surfaced by `phase-4-plan` and by a `[STATUS]` decision-log line. A drop that used to be invisible
  now has to be read past.
- `finalize-step-simplify` deliberately left unchanged — see residue.

### On-theme note (a confident signal hid a caveat)

The plan **reproduced its own target defect on itself**. Its phase-4 `execution.toon` carried
`security_audit_omitted=true` and dropped the security audit from its own finalize, despite an
operator-chosen full posture. Re-composing against the fixed composer restored it (23 → 24 steps).

### Residue the epic should track

1. **The real mechanism is broader than this fix.** `phase-4-plan` takes `change_type` from the
   **first deliverable**. A plan that opens with a read-only discovery deliverable reports
   `verification` however much code its later deliverables mutate. This fix removed the
   `change_type` leg from *one* gate; the mis-scoped read itself is still live everywhere else it
   is consumed. See candidate-lesson on first-deliverable scope.
2. **`finalize-step-simplify`'s `simplify_inactive` gate still has the defect.** Lesson
   `2026-07-16-20-001` was **TRIMMED, not removed**, by lessons-housekeeping this run: its
   security-audit leg is fixed here, but its root cause remains live for `simplify_inactive`.
   This is a ready-made follow-up plan.
3. **A third `_resolve_footprint` call site is still deferred** — line ~686 in
   `_apply_canonical_verify_inactive`. CodeRabbit named two call sites; the real count is three.
4. **coderabbit never reviewed the final doc-only head** despite three triggers (account rate
   limits). Operator chose merge-anyway on a documented gap. The PR merged with a known,
   accepted review-coverage hole on its last commit.
5. **No persisted SonarCloud project-key config** — every `sonar-roundtrip` dispatch re-derives
   `cuioss_plan-marshall` ad hoc. See the candidate-lesson.

### Signals

`qgate_pending=3`, `automated_review=1`, `script_failure_clusters=0`.
Review retrospective: 2 reviewers compared, 6 actionable comments, 4 fixed (100% valid),
sourcery quota-exhausted.
