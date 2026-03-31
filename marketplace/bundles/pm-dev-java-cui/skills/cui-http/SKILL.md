---
name: cui-http
description: CUI HTTP client standards with HttpHandler, HttpResult pattern, and async-first adapters
user-invocable: false
---

# CUI HTTP Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

CUI-specific HTTP client standards for projects using `de.cuioss:cui-http`. Covers HttpHandler, HttpResult sealed interface, and async-first adapters.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for HTTP client implementation tasks.

**Prohibited actions:**
- Do not use raw HttpClient or OkHttp directly; always use CUI HttpHandler abstraction
- Do not implement custom retry or error handling; use HttpResult sealed interface pattern matching
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- All HTTP implementations must use `de.cuioss:cui-http` library
- Error handling must use HttpResult sealed interface (not exceptions)
- Async operations must use the async-first adapter pattern

## Prerequisites

- `de.cuioss:cui-http` (HttpHandler, HttpResult, HttpAdapter)

## Standards

| Standard | Purpose |
|----------|---------|
| `standards/cui-http.md` | HttpHandler builder, HttpResult pattern matching, adapters, error categories |

## Related Skills

- `pm-dev-java:java-core` — General Java patterns
- `pm-dev-java-cui:cui-http-testing` — HTTP testing with CUI MockWebServer
