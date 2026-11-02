envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T11:19:22Z

# pm-dev-java: four Java rules consumer runs needed and no standard states

Severity: medium (item 1); low (items 2-4). Domain content, filed under RULING 2026-10-09 (operator-confirmed for this sweep); may be discarded under the `live-blockers` FOCUS RULE.
Bundle: `pm-dev-java` (java-core / java-security / java-null-safety / junit-core).

## Sources (verbatim in `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-02/{repo}/`)

- pm-mcp-core `2026-10-15-06-001` (PLAN-09, PR #69): HMAC input built with `String.formatted`
- TokenSheriff `2026-10-14-06-001` (issue-800, PR #805): a rejection message echoed a URL value carrying user-info
- API-Sheriff `2026-10-15-09-002` (PLAN-V02-24, PR #465): Sonar `java:S2637`/`S2638` flip-flop
- API-Sheriff `2026-10-05-13-001` and cui-jsf-test-basic `2026-06-16-09-001`: malformed `-Dtest` selectors (recurrence of the 2026-11-01 medium API `2026-10-12-07-006`)

## Observation

1. Bytes that are signed, hashed or compared across processes were built with `String.format`/`formatted` under the default locale; under a non-ASCII-digit locale the HMAC no longer matches. Five code-review rounds missed it; a review bot caught it.
2. A validation rejection message echoed the configured value. A URL value can carry `user:password@`, so credentials reached the message.
3. Under `@NullMarked` with a `@Nullable` type argument, Sonar alternated between S2637 and S2638; each reshape fixed one and triggered the other.
4. Surefire `-Dtest` takes comma-separated class patterns (`Class#method` for methods). `A+B` joins and `pkg.*` globs match nothing and fail the build as if it were a test error.

## Ground truth (c431a8193)

- No pm-dev-java standard names `Locale.ROOT` or locale-independent formatting (only an unrelated `Locale.getDefault` example in `java-null-safety/standards/null-safety-patterns.md:51-62`).
- No standard names URL user-info as a secret carrier; general secure-logging guidance exists (java-security, persona-security-expert).
- No standard names S2637/S2638; `null-safety-patterns.md:146-165` covers a different checker false positive.
- `junit-core/standards/test-fork-policy.md:96-106` covers `failIfNoSpecifiedTests` but not the selector grammar.

## What to consider

java-core: signed/hashed/compared text uses `Locale.ROOT` or concatenation. java-security: name the setting, do not echo the value, in rejection messages. java-null-safety: the S2637/S2638 oscillation (suppress with a rationale). junit-core: the `-Dtest` selector grammar.
