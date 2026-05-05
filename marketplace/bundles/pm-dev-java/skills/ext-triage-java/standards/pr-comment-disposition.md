# Java PR Comment Disposition

Decision criteria for disposing of automated PR review comments (gemini-code-assist, Copilot, Sonar bots, CodeRabbit, etc.) on Java code. Comments reach this disposition step **after** the validity check from `dev-general-practices` (PR review hard rule): if a suggestion contradicts the plan's stated intent or driving lesson, reply-and-resolve immediately. Use this document when the suggestion is plan-compatible and you must decide between FIX, REPLY-AND-RESOLVE, or ESCALATE.

## Disposition Outcomes

| Outcome | Meaning | Required Output |
|---------|---------|-----------------|
| **FIX** | Apply the suggested change in a follow-up commit | Code change + thread reply linking commit |
| **REPLY-AND-RESOLVE** | Decline the suggestion; explain rationale; mark thread resolved | Reply with template; resolve thread |
| **ESCALATE** | Ambiguous; ask the user via AskUserQuestion before acting | AskUserQuestion call; record decision in lessons |

## FIX-Eligible Categories

Concrete violations of Java standards (see `pm-dev-java:java-core`, `pm-dev-java:java-null-safety`, `pm-dev-java:junit-core`). Always FIX when the comment identifies one of these.

| Category | Example Findings | Authoritative Standard |
|----------|------------------|------------------------|
| Null safety | Missing `@Nullable`/`@NonNull`, NPE on dereference, raw return of nullable | `java-null-safety` |
| Resource leak | Stream/Reader/Connection not closed, missing try-with-resources | `java-core` |
| Equality bug | `==` on `String`/boxed types, missing `equals`/`hashCode` pair | `java-core` |
| Collection misuse | Mutable static collection, modifying list during iteration | `java-core` |
| Concurrency error | Non-atomic check-then-act, unsynchronized shared state, double-checked locking without `volatile` | `java-core` |
| Exception handling | Swallowed exception, `catch (Exception)` without rethrow/log, `throw` of `RuntimeException` without cause | `java-core` |
| Test correctness | Missing assertion, `assertTrue(true)`, hardcoded sleep, test depends on order | `junit-core` |
| Lombok misuse | `@Data` on entity, missing `@EqualsAndHashCode.Include`, `@Builder` on inheritance without `@SuperBuilder` | `java-lombok` |
| JavaDoc gaps | Missing `@param`/`@return` on public API, `@throws` not declared | `javadoc` |
| Logging | `e.printStackTrace()`, `System.out.println` in production, missing log on caught exception | `cui-logging` (when CUI), `java-core` (otherwise) |
| Cognitive complexity | Method exceeds threshold AND suggestion proposes a clean extraction | `severity.md` (Cognitive Complexity table) |

## REPLY-AND-RESOLVE Categories

Decline the suggestion with the corresponding template. Always reply before resolving — never resolve silently.

### False Positive

| Trigger | Reply Template |
|---------|----------------|
| Tool flags safe `unchecked` cast guarded by reflection/type-token | `False positive: cast is type-checked at line {N} via {guard}; suppression with justification is the documented pattern (see suppression.md).` |
| Bot suggests `Optional.get()` is unsafe but presence is asserted on prior line | `False positive: `{var}` presence is asserted at line {N-1} via `{check}`; refactoring to `orElseThrow` here would obscure the invariant.` |
| Tool flags "magic number" for documented protocol constant (HTTP status, port) | `False positive: `{value}` is a protocol constant ({reference}); promoting to a named constant adds noise without semantic gain.` |

### Plan-Intent Contradiction

| Trigger | Reply Template |
|---------|----------------|
| Suggestion reintroduces a deprecation/migration target the plan is removing | `Suggestion contradicts plan intent: this PR removes {pattern} per {plan_id}/{lesson_id}. Reverting would restore the anti-pattern the plan is explicitly eliminating.` |
| Suggestion adds backward-compat shim on a `breaking` plan | `Plan compatibility strategy is `breaking` (see phase-2-refine compatibility field). Backward-compat shim is intentionally out of scope.` |
| Suggestion replaces CUI logger with SLF4J/JUL | `Module enforces CUI logging standards (`cui-logging`). SLF4J/JUL imports are blocked by ArchUnit; CuiLogger is the required logger.` |

### Scope Out of Bounds

| Trigger | Reply Template |
|---------|----------------|
| Suggestion proposes refactor of a method untouched by this PR | `Out of scope: `{method}` is not modified in this PR. Refactor request belongs in a dedicated maintenance plan (see `java-maintenance` for the trigger criteria).` |
| Suggestion requests new test coverage for unchanged production code | `Out of scope: line is unchanged by this PR. Coverage gap predates this change; tracked separately, not a blocker for merge.` |
| Suggestion proposes architectural change (new interface, package split) | `Architectural change is out of scope for this PR. Will be raised as a separate ADR / refactor plan if accepted by maintainers.` |

### Out of Domain

| Trigger | Reply Template |
|---------|----------------|
| Bot flags a `.kt` / `.groovy` snippet but rule applies to Java only | `Out of domain: file is `{language}`, not Java. Rule `{rule_id}` is configured for Java sources only.` |
| Bot suggests JS/TS-style pattern (`const`, optional chaining) on Java code | `Out of domain: suggestion is JavaScript syntax. Java equivalent (`final`, `Optional`) is already in use at line {N}.` |
| Bot flags Maven `pom.xml` issue inside a Java code review thread | `Out of domain for this thread (Java code review). Build configuration findings are triaged via `manage-maven-profiles`.` |

## Escalation Triggers

Use `AskUserQuestion` when the comment falls into any row below. Do NOT silently FIX or RESOLVE.

| Ambiguity | Why It Needs Escalation |
|-----------|------------------------|
| Suggestion changes a public API signature without a deprecation strategy declared in the plan | Breaking-API decisions require explicit user confirmation per compatibility strategy |
| Suggestion conflicts between two automated reviewers (gemini says A, Copilot says B) | Cannot satisfy both; user must pick a direction |
| Suggestion proposes a security-sensitive change (auth, crypto, input validation) outside this PR's stated scope | Security delta in unrelated code requires explicit go/no-go |
| Suggestion alters concurrency semantics on hot-path code with no benchmark | Performance/correctness tradeoff cannot be assessed by reviewer alone |
| Suggestion contradicts a project-specific lesson learned (CUI HTTP, MockWebServer) but the lesson is not referenced in the plan | Verify the lesson still applies before accepting or rejecting |
| Bot suggestion has 0 reactions from human reviewers AND substantially changes test architecture | Architectural test changes need maintainer sign-off |

## Disposition Flow

```
Bot comment received
  ↓
Plan-intent check (dev-general-practices PR review rule)
  Contradicts plan? → REPLY-AND-RESOLVE (Plan-Intent Contradiction)
  ↓
Match FIX category from table above?
  Yes → FIX (apply change, reply with commit link)
  ↓
Match REPLY-AND-RESOLVE category?
  Yes → reply with template, mark resolved
  ↓
Match Escalation Trigger?
  Yes → AskUserQuestion, record decision in lessons
  ↓
Default → ESCALATE (do not silently fix or resolve unknown categories)
```

## Reply Quality Rules

| Rule | Rationale |
|------|-----------|
| Always cite the standard or line number that justifies the disposition | Reviewers (human and bot) can verify the rationale without context-switching |
| Never reply "won't fix" without a category from this document | Untraceable rejections invite repeated bot suggestions on future PRs |
| Use the closing token expected by the CI provider (GitHub: `Resolve conversation`; GitLab: `Resolve thread`) only after the reply is posted | Resolving without a reply leaves no audit trail |
| Keep replies under 4 lines unless citing multiple standards | Long replies are skipped by reviewers; structured one-liners scale |

## Related Standards

- [severity.md](severity.md) — Severity-to-action mapping for Java findings
- [suppression.md](suppression.md) — `@SuppressWarnings` and NOSONAR syntax
- `pm-dev-java:java-core` — Core Java patterns referenced in FIX-eligible categories
- `pm-dev-java:java-null-safety` — JSpecify null safety conventions
- `pm-dev-java:junit-core` — Test correctness baseline
- `plan-marshall:dev-general-practices` — PR review hard rule (validate bot suggestions against plan intent)
