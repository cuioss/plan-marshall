envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T18:35:36Z

component=plan-marshall:persona-plan-orchestrator
category=anti-pattern

# Orchestrator-authored spec mandated a build flag without checking it against the example's reactor — spec-mandated flags are claims owed verify-first

Routed by the API-Sheriff `deployment-configurability` orchestrator on 2026-09-15 while draining PLAN-24's (`release-docs-and-tls-scenario-guide`, PR cuioss/API-Sheriff#305, squash `fb65222`) epic inbox. The originating plan filed these as `candidate-lesson` messages to its API-Sheriff epic; their remedy lives in the plan-marshall bundle, so they are relocated here — the same routing this epic used for `-001`..`-013`. Not re-verified against plan-marshall source by the orchestrator: each is a lead from one plan run. Original message bodies (envelope stripped) are verbatim below.

Origin messages: `release-docs-and-tls-scenario-guide-006`.

Orchestrator self-report. The flag came from THIS orchestrator's PLAN-24 spec (deliverable 10, carried from a 2026-09-11 lessons-intake finding) and was serialized without checking it against `-pl api-sheriff -am`'s reactor. The Verify-First Contract labels mechanisms, surfaces and counts; a mandated command flag slipped through as none of the three. Candidate home: the orchestration standard's claim classes, or `plan-spec.md` authoring guidance.

---

## Original `release-docs-and-tls-scenario-guide-006`

component=documentation
category=anti-pattern
source_finding=pr-comment d44822 (CodeRabbit, fixed in-run; operator chose to drop the flag)

# Spec mandated -Dsurefire.failIfNoSpecifiedTests=false where it only hides a misspelled selector

## What happened

The plan spec required the targeted-test example (`test -pl api-sheriff -am -Dtest=ConfigLoaderTest`) in AGENTS.md and CLAUDE.md to carry `-Dsurefire.failIfNoSpecifiedTests=false`. Under `-pl api-sheriff -am` the only other reactor module is the pom-packaged root, which binds no surefire execution, so the override prevents no failure — it only lets a misspelled or deleted test name pass with zero tests run. The implementation followed the spec verbatim; CodeRabbit flagged it and the operator dropped the flag, adding a note that it is needed only when the `-pl` target pulls in upstream modules with their own tests (e.g. integration-tests depending on api-sheriff).

## Corrective action

Before writing a spec-mandated build flag into operator-facing command examples, check it against the example's actual reactor: a flag that suppresses a failure mode must name a module in that reactor that would trigger it. Default to the fail-closed surefire behaviour and document the override conditionally.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305)
- Finding hash: d44822, thread PRRT_kwDOPatrT86il0gM
- Ties to the CLAUDE.md principle "A successful build is not evidence that work happened"
