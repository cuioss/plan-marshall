envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-16T07:45:25Z

# Domain-bundle content gaps from consumer incidents: one umbrella filing (pm-dev-java, persona-security-expert)

**Severity:** umbrella. The operator directed (2026-11-16 `gather` run) that every domain-content gap of this sweep be filed as ONE filing instead of one per gap. The gradings of the single items are low (the grading leaves marked each BORDERLINE against not-applicable). Under RULING 2026-10-09 (b) a domain-bundle content issue is filed at any severity; `live-blockers`' FOCUS RULE (high and blocking only) may still discard individual items.
**Bundles:** `pm-dev-java` (`ext-triage-java`, `java-core`, `junit-core`, `java-security`), `pm-dev-java-cui` (`cui-logging`), `plan-marshall` (`persona-security-expert`)
**Checked at:** `ee019bf1d` (origin/main). Item 1's cited line was re-read by the orchestrator; every other cited line and every "no such text" statement is the grading leaves' grep and was NOT re-read.

Each item is a content gap that a consumer's incident exposed, written from the lesson's own subject. The full lesson bodies are in the archive copies named under Sources.

## 1. `ext-triage-java`: new-code Sonar findings should be fixed, not suppressed

Lesson TokenSheriff `2026-11-13-14-005`: the unified triage proposed `@SuppressWarnings` for a new-code Sonar S2589 on lines the plan itself wrote, and the dispatcher overrode it with a real fix. Re-read: `pm-dev-java/skills/ext-triage-java/SKILL.md:68` reads `| MAJOR | Fix or suppress with justification |` with no new-code qualifier. Per the leaf: `standards/severity.md:52-59,143-153` already say new code means FIX, but `severity.md:11-12` allows "Suppress if noisy or false positive" for MINOR. Ask: on plan-authored lines propose a code fix first, and allow a suppression only with an explicit false-positive justification plus a statement that no reasonable rewrite exists; suppression is the fallback for legacy or out-of-footprint code.

## 2. `pm-dev-java:java-core` `standards/java-concurrency.md`: async lifecycle, close fencing, stale publishers

Lessons TokenSheriff `2026-10-31-12-001`, `2026-10-31-12-002`, `2026-11-02-10-001` and `2026-11-15-18-001`: consumer races in an async-loading component (close versus in-flight loads, scheduled-retry fencing, a lock released before a result is published, a compare-and-set publication). The generic content they ask for: enumerate every writer and side effect of the state before fixing one race; fence in-flight async work with a generation or epoch so a closed component is never revived; publish inside the lock or re-check after release; and a review/test obligation for the stale-publisher interleaving. Per the leaf: `java-concurrency.md` (lines 1-256) has no generation or epoch fencing, no close-versus-async rule, and its compare-and-set example (about `:212`) carries no stale-publisher test rule; `java-core/SKILL.md:98` covers only the non-atomic check-then-act.

## 3. `pm-dev-java:java-core` (or `ext-triage-java`): Sonar `java:S1192` on a repeated literal

Lesson API-Sheriff `2026-10-12-16-011`: Sonar `java:S1192` on a literal repeated three times in a guard. Per the leaf, neither `java-core/SKILL.md` nor `ext-triage-java` has S1192 guidance (grep, no hits). The open question is whether single-rule Sonar advice belongs in the standards at all.

## 4. `plan-marshall:persona-security-expert`: a hardened check must exist on every sibling input path

Lesson TokenSheriff `2026-11-04-13-002`: the DPoP proof path lacked the algorithm/curve check the access-token path has. The generic form is that a hardening check applied on one input path has to be applied on each sibling path that accepts the same kind of input. Per the leaf, `persona-security-expert/standards/*.md` has nothing on sibling-path parity (grep).

## 5. `pm-dev-java:junit-core`: the `@EnumSource` `EXCLUDE` idiom for mirrored lists

Lesson TokenSheriff `2026-11-15-11-003`: a test enumerating a list that mirrors an enum. Per the leaf, `junit-core/SKILL.md:152` already has the rule that a hardcoded name list or enum-cardinality assertion mirroring a set defined elsewhere goes stale with the test green, but no `@EnumSource` idiom is named (grep of `pm-dev-java` finds no `EnumSource`).

## 6. `pm-dev-java:java-security` / `pm-dev-java-cui:cui-logging`: sanitise every field a parser returns, at every sink

Lesson TokenSheriff `2026-11-10-14-001`: sanitise every attacker-controlled field a parser returns, and every sink (log line and thrown message), with a field x property test matrix. Per the leaf this is largely covered: `cui-logging/standards/logging-standards.md:292-338` (sanitise every channel including the throwable and the cause chain) and `java-security-patterns.md:45-69` (U+2028/2029 and control characters), and `lessons-routing-083` is the neighbour (masking is not sanitising). Not stated: "every field the parser returns, not only the display field", and the field x property matrix. The leaf had it BORDERLINE against already-covered.

## Sources

- TokenSheriff lessons `2026-11-13-14-005`, `2026-10-31-12-001`, `2026-10-31-12-002`, `2026-11-02-10-001`, `2026-11-15-18-001`, `2026-11-04-13-002`, `2026-11-15-11-003`, `2026-11-10-14-001`, archived verbatim under `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-16/TokenSheriff/`.
- API-Sheriff lesson `2026-10-12-16-011`, archived verbatim under `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-16/API-Sheriff/`.
