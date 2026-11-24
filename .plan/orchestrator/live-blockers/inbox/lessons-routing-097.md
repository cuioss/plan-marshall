envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-24T12:42:34Z

# finding (high, operator): the merge gate treats an optional review bot's structural refusal as `merge_participation_unproven` while `review_completeness` reports `participation_complete=true` on the same head

**Severity:** high (operator-graded 2026-11-24). **Bundle:** `plan-marshall`, component `plan-marshall:phase-6-finalize` (`pre_merge_gate`, `review_completeness`).

**Evidence (sender, plugin 0.1.2184; not reproduced by the orchestrator).** `libraries-initial-implementation-052`: PR 54 (plan-12) and PR 59 (plan-23, head `43dad67`). CodeRabbit (required) participated; Sourcery (optional) answered `refused_structural` (150,000-diff-character cap, 2,913 changed lines). `pre_merge_gate merge --route merge-queue` returned `merge_participation_unproven` (`authorizable=true`, `unproven_bots=sourcery`), while the barrier-side `review_completeness` check had reported `participation_complete=true`. The merge stayed blocked until the operator selected the gate's own option label "Accept the coverage gap (record reason)"; free-text approval was refused by the grant verb.

**Not yet established.** LB-132 (#1952) touched both files after some of these runs. The first step is to reproduce against `pre_merge_gate.py` and `review_completeness.py` at HEAD and stop if the two already agree.

**Ask of `live-blockers`.** (1) One participation predicate decides both gates; an optional bot's refusal (size, quota, unsupported language) reads `not_applicable` at merge. (2) A refusal that needs an override prints the exact accepted option labels. (3) Tests: optional refused, required refused, optional participated.
