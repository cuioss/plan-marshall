envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-13T08:10:58Z

# Recurrences of earlier filings — new evidence only, no new item

- Severity: each inherits the grade of the filing it adds to.
- Source: 13 messages from the pm-mcp-core epic (plans PLAN-13 `workflow-engine` #45, PLAN-18 `verify-not-resolve` #43, PLAN-44 #38 under opencode, plus lesson `2026-10-11-07-001`). Full bodies at `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-NNN.md`.
- Asked: append the evidence to the matching Open Defect or staged plan. No new work is requested by this message.

| Earlier filing (Open Defect / owner) | New messages | What is new |
|---|---|---|
| `lessons-routing-013` — zero tokens recorded as real, harness never recorded (critical) | 148 | Same gaps under **opencode** (PLAN-44): `total_tokens=0`, wall time covers 1-init only, no `client.toon`. New detail: the five finalize builds' logs are missing from the archived `build-results/` (only execute builds up to 14:46Z), so the gates on the pushed head cannot be shown — bears on `lessons-routing-016`. |
| `lessons-routing-018` — sibling-repository deliverable has no lifecycle (critical/high) | 168, 175, 176, 181 | Two more plans (PLAN-13, PLAN-18). Retrospective footprint reports every `../plan-marshall-documentation/` or absolute sibling path as declared-but-unrealised; M6 fails by construction (168, 181). Relative sibling paths break under `use_worktree` (175). A sibling deliverable has no module name in the architecture (176). |
| `lessons-routing-019` — red CI has no triage route (high) | 153, 189 | PLAN-13 (2026-10-12T19:38Z): `ci-verify-policy` refused `unknown_producer`, re-dispatched as `finalize-feedback`. 189 (lesson `2026-10-11-07-001`, plan-06): a SonarCloud gate failure inside the `build / sonar-build` Maven job filed 5 `ci_policy_failure` findings instead of deferring to sonar-roundtrip. |
| `lessons-routing-020` — fix task under deliverable 0 rejected by `commit-add` (PLAN-LB-26) | 183 | PLAN-18: both triage runs hit it; leaves filed fix tasks under deliverables 3 and 4 they do not belong to. |
| `lessons-routing-021` — consumer-repo leaf cannot resolve its workflow doc (high) | 182 | PLAN-18: the 4-plan leaf and two sonar-roundtrip leaves read the doc from `/Users/oliver/git/plan-marshall/target/claude/...` instead. |
| `lessons-routing-022` — deep-lane outline writes no assessments (high) | 162, 174 | PLAN-13 (Q-Gate 447991) and PLAN-18 (Q-Gate 0feabd, accepted by the operator). Ninth and tenth plans. |
| `lessons-routing-023` — 4-plan Q-Gate hash skip; no verb computes the hashes (high) | 185 | PLAN-18: both Q-Gate runs skipped `deliverable-hashes.toon` (16 hashes over 2 runs); the 4-plan leaf had no shell at all. Asks for `manage-solution-outline deliverable-hashes`. |
| `lessons-routing-024` — `pm-dev-java` Quarkus/Weld skills attached ungated (medium, domain) | 173 | PLAN-18: phase-4 persona augmentation attached `java-quarkus` / `java-cdi` in pm-mcp-core, whose `CLAUDE.md` says "No Quarkus, no CDI" and whose enforcer bans them. |
