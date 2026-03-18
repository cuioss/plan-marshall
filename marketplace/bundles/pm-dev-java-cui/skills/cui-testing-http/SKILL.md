---
name: cui-testing-http
description: CUI MockWebServer standards for HTTP client testing with JUnit 5 integration
user-invocable: false
---

# CUI Testing HTTP Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

CUI-specific HTTP testing standards using `cui-test-mockwebserver-junit5`. Covers MockWebServer configuration, HTTPS testing, and request verification.

## Prerequisites

- `de.cuioss.test:cui-test-mockwebserver-junit5`

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/testing-mockwebserver.md` | @EnableMockWebServer, @MockResponseConfig, @ModuleDispatcher, HTTPS, request verification |

## Related Skills

- `pm-dev-java-cui:cui-http` — CUI HTTP client patterns
- `pm-dev-java-cui:cui-testing` — CUI test generator framework
- `pm-dev-java:junit-core` — General JUnit 5 patterns
