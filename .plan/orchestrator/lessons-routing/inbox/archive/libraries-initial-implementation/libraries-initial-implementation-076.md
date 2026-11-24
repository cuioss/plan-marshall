envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:12:16Z

component=pm-dev-java:junit-core
category=improvement
title=junit-core: the Sonar test smells (one throwing call per assertThrows lambda, unreachable throws, repeated literals, copied test bodies) cost a Sonar round per new test class, catch them before the push
source_lesson=2026-11-19-19-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# junit-core: the Sonar test smells (one throwing call per assertThrows lambda, unreachable throws, repeated literals, copied test bodies) cost a Sonar round per new test class, catch them before the push

# Candidate lesson: Sonar flagged the same JUnit smells across every new test class, and no pre-push check caught them

- Source signal: plan plan-05-git-core-merge-read-notes (inbox plan-05-git-core-merge-read-notes-005), automated review (22 sonar-issue findings remediated in the run), component `pm-dev-java:junit-core` review rules.
- Evidence: the first Sonar round on PR #37 reported 20 issues, all fixed inline; the second round added 2. None were caught by `verify -Ppre-commit` or by the finalize simplify step before the push.

## What happened

- `java:S5778` (13 issues, MAJOR): an `assertThrows` lambda holding more than one call that could throw, in three new test classes. The fix moves the setup out of the lambda.
- `java:S1192` (4 issues, CRITICAL): a literal repeated three times in a class (`"repository"`, `"refName"`, `": not found"`).
- `java:S1130` (3 issues): a `throws` clause the method body can never trigger.
- `java:S4144` (second round, 2 issues): the in-memory and local copies of the symbolic-reference tests had identical bodies; they became one test that runs a shared helper on both backends.

## Candidate rule

Put the four rules into the junit-core review rules the code review and the execute-task profile cite: exactly one call that can throw inside each `assertThrows` lambda; no `throws` the body cannot reach; a named constant for any literal used three or more times in a class; one shared helper when the same test runs on two backends. Add a pre-push check (a Sonar-equivalent rule in the pre-commit profile, or a review item in the simplify step) so the smells cost no Sonar round.
