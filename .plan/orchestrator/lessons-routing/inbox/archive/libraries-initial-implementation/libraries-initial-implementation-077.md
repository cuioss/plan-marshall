envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:12:17Z

component=pm-dev-java:ext-triage-java
category=improvement
title=Sonar S6539: lower the dependency count of every touched class, do not move the dependencies into a new class
source_lesson=2026-11-22-13-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# Sonar S6539: lower the dependency count of every touched class, do not move the dependencies into a new class

# Candidate lesson: fixing Sonar S6539 by moving the dependencies into a new class gets the new class flagged again

- Source signal: orchestrator observation in plan plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-009; TASK-015 fixed S6539 11cbdf on `StoreWriter` by extracting `StoreClone`, TASK-016 then fixed S6539 e3e943 on `StoreClone` by extracting `CloneOpening`).

## What happened

S6539 ("monster class", too many class dependencies) on `StoreWriter` was fixed by moving the dependencies into a new class; the next Sonar analysis flagged that class for the same rule, which cost another loop-back round. Sonar counts the dependencies in a way that could not be reproduced offline, so the fix could not be checked before pushing.

## Candidate rule

An S6539 fix lowers the dependency count of every class it touches; it does not move the dependencies along. Split by responsibility so each new class depends on a disjoint subset, count the distinct imported and referenced types of the new class against the threshold before pushing, and, if the count cannot be checked locally, keep a margin well below the threshold. Owning component: `pm-dev-java:ext-triage-java` (the S6539 guidance).
