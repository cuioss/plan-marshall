envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-24T12:42:40Z

# finding (medium, domain content): `pm-dev-java` guidance gaps for Sonar `S1130`, `S4144` and `S6539`

**Severity:** medium (domain-bundle content, filed at any severity under RULING 2026-10-09 (b)). **Bundle:** `pm-dev-java` (`junit-core`, `ext-triage-java`). Recurrence and reproduction of `lessons-routing-095`'s Sonar-content theme (S1192, `S5778`), which is already stated in the bundle.

**Ground truth.** The drafting leaf searched `marketplace/bundles/` at `3da9e1f44` and found `S1130`, `S4144` and `S6539` named in no file; `S5778` is already stated.

1. **`pm-dev-java:junit-core` (source `libraries-initial-implementation-076`, source lesson `2026-11-19-19-001`, PR #37 of git-document-repository).** The first Sonar round reported 20 issues and the second 2, none caught by `verify -Ppre-commit` or the simplify step: `S5778` (13, one throwing call per `assertThrows` lambda), `S1192` (4), `S1130` (3, a `throws` clause the body can never trigger), `S4144` (2, identical test bodies for the in-memory and local backends). Ask: add the four rules to the junit-core review rules the code review and execute-task profile cite, and a pre-push check or a simplify-step review item.
2. **`pm-dev-java:ext-triage-java` (source `libraries-initial-implementation-077`, source lesson `2026-11-22-13-003`, plan-09).** `S6539` on `StoreWriter` was fixed by extracting `StoreClone`, which was flagged again and extracted into `CloneOpening`, one extra loop-back round; the count cannot be reproduced offline. Ask: an S6539 fix lowers the dependency count of every class it touches rather than moving the dependencies, splits by responsibility so each new class depends on a disjoint subset, and keeps a margin below the threshold when the count cannot be checked locally.
