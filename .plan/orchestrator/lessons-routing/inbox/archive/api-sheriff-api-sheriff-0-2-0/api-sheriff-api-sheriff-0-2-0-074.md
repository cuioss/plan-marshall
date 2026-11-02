envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T06:51:21Z

# CodeRabbit finished-review summary no longer credits participation (automatic-review + pre-merge barrier)

**Component:** `plan-marshall:automatic-review` (`standards/coderabbit.md`, `bot_registry.py` participation marker) and the `phase-6-finalize` pre-merge barrier / `pre_merge_gate merge`.

**What happened (API-Sheriff PR #537, plan `plan-v02-07-threat-classification`, 2026-10-29/30).** CodeRabbit reviewed two successive heads (54a3af18 and 5988f533) and found nothing: its `CodeRabbit` check completed `success`, and its summary comment names the head as `final_review_risk_coverage ... "kind":"reviewed"` with "No actionable merge-blocking issue". But the rewritten summary comment carries **no** `<!-- recent_review_start -->` marker (the new format uses `final_review_risk_*` / `change_assessment_*` markers instead), and the registry only credits an `issue_comment` that carries that marker. Result: `participation_complete: false`, `bot_states: coderabbit:refused_awaitable`.

**Second effect.** An older `Review rate limited.` reply (an earlier quota refusal on the same PR) stays on the PR and is still counted as a refusal on every later pass, even though a later review of a newer head completed. A later completed review does not cancel an earlier refusal.

**Consequence.** `automatic-review` could not close honestly: it needed a WARNING-logged force-done, twice, and the pre-merge barrier (`merge_participation_unproven`, `authorizable: true`) needed an operator `barrier-ask-override` grant before the merge-queue enqueue. The review was real; the gate could not see it. A clean CodeRabbit review can therefore never be proven by the gate in its current format.

**Suggested fix.** Treat `final_review_risk_coverage` with `coveredCommitId == merge-candidate head` and `kind: reviewed` (and/or the completed `CodeRabbit` check-run bound to that head) as the participation evidence; and let a completed review of the current head supersede an earlier `Review rate limited` refusal. Provenance for the marker format: the summary comment body of cuioss/API-Sheriff#537 at 2026-10-30T01:50:10Z.
