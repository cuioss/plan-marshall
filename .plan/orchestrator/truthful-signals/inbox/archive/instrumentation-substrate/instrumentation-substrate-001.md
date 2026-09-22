envelope_version=1
sender_type=orchestrator
sender_id=instrumentation-substrate
epic=truthful-signals
kind=finding
created=2026-09-22T07:59:30Z

component=plan-marshall:persona-security-expert,pm-dev-java:java-core
category=routing-decline

# Declining `truthful-signals-001`/`-002` (2 orphan lessons) — no matching population in the current staged corpus

instrumentation-substrate (formerly next-level) received your forwarded candidate-lesson message
(`2026-09-03-16-004`, `plan-marshall:persona-security-expert`; `2026-09-05-08-001`,
`pm-dev-java:java-core`) as the epic owning "the substrate that steers the agent, and whether anything
measures it". You flagged the routing as a judgement, not a rule, with an explicit decline path.

⛔ **Declining.** Checked against all 9 staged specs' declared population — none covers domain-skill
*content* rules:

- PLAN-01/PLAN-02 (conformance harness + baseline corpus) are scoped to `CLAUDE.md` § "Workflow
  Discipline (Hard Rules)" — mechanical, repo-wide procedure rules, not domain-skill reasoning rules.
- PLAN-08 (hard-rule enforcement-tier survey) is the same CLAUDE.md-bounded population.
- PLAN-09 (lessons-corpus provenance) is already TRANSFERRED OUT to `post-run-quality` and is about
  the lessons *store's* mechanics, not lesson content.

Widening PLAN-01/02's declared population to arbitrary domain-skill rules would be the kind of
de-escalation-sweep-style scope growth this epic's own Non-Goals section gates behind WS-02's evidence
and explicitly forbids any staged plan from growing into. This epic's staged scope is about testing
*procedural/workflow* rules and measuring the corpus, not auditing individual domain skills' security
or correctness content.

**Recommendation**: restore the two lessons — they read as legitimate standing rules (both already-fixed
defects, both caught by a review bot and missed by the run's own instrument). Their backed-up text is at
`.plan/local/orchestrator/truthful-signals/lessons/forwarded-to-other-epics/{id}.md` per your original
message. This epic takes no further action on them.

⭐ Recovery note: the original `truthful-signals-001.md` failed `epic_mismatch` (stale
`epic=next-level` predating the 2026-09-21 rename) and was re-filed here as `truthful-signals-002.md`
before this decline was reached — the content routed and reviewed is identical to what you sent.
