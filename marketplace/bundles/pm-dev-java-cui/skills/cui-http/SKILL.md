---
name: cui-http
description: CUI HTTP standards for de.cuioss:cui-http — HttpHandler client configuration, HttpResult error handling, async adapters with ETag caching and resilient retry, custom content converters, SSL/TLS context, HTTP status classification, and inbound HTTP security input-sanitization (de.cuioss.http.security validation pipelines)
user-invocable: false
mode: knowledge
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

## Workflow

### Step 1: Load HTTP Client Standards

**CRITICAL**: Load these standards for any HTTP client implementation work.

```
Read: standards/cui-http.md
```

This provides the foundational rules:
- MUST use `HttpHandler` builder for all HTTP client configuration
- MUST use `HttpResult<T>` sealed interface for result handling
- Async adapters with composable retry and caching

### Step 2: Apply the Right Pattern (Based on Task)

**Simple HTTP request** — Use HttpHandler directly:
```java
HttpHandler handler = HttpHandler.builder()
    .uri("https://api.example.com/data")
    .connectionTimeoutSeconds(10)
    .readTimeoutSeconds(30)
    .build();
```

**Resilient HTTP with caching** — Compose ETag + retry adapters:
```java
HttpAdapter<String> adapter = ResilientHttpAdapter.wrap(
    ETagAwareHttpAdapter.<String>builder()
        .httpHandler(httpHandler)
        .responseConverter(StringContentConverter.identity())
        .build(),
    RetryConfig.defaults()
);
```

**Result handling** — Use pattern matching on HttpResult:
```java
return switch (result) {
    case HttpResult.Success<ConfigData>(var config, var etag, var status) -> {
        updateCache(config, etag);
        yield true;
    }
    case HttpResult.Failure<ConfigData> failure -> {
        if (failure.fallbackContent() != null) {
            yield true;  // Graceful degradation
        }
        yield failure.isRetryable();
    }
};
```

### Step 3: Validate Inbound HTTP Input (When Reading Untrusted Requests)

When the task reads HTTP components from an untrusted inbound request (servlet, JAX-RS resource, request filter — path segments, query parameters, header names/values), load the **Inbound HTTP Security** section of `standards/cui-http.md`. It documents the `de.cuioss.http.security` validation pipelines (`PipelineFactory`, `HttpSecurityValidator`, `SecurityConfiguration`) — the server-side counterpart to the client-side adapters above. Validate every externally-sourced HTTP component at the boundary before use.

## Key Concepts

### HttpResult Sealed Interface

Type-safe result handling with exhaustive pattern matching:
- `HttpResult.Success<T>` — Content with ETag and HTTP status
- `HttpResult.Failure<T>` — Error with optional fallback content and error category

### HttpErrorCategory

| Category | Retryable | Examples |
|----------|-----------|----------|
| `NETWORK_ERROR` | Yes | Connection failures, timeouts |
| `SERVER_ERROR` | Yes | 5xx responses |
| `CLIENT_ERROR` | No | 4xx responses |
| `INVALID_CONTENT` | No | Content conversion failures |
| `CONFIGURATION_ERROR` | No | Setup/config issues |

## Standards Reference

| Standard | Purpose |
|----------|---------|
| `standards/cui-http.md` | HttpHandler builder, HttpResult pattern matching, adapters, error categories, and inbound HTTP security (input-sanitization pipelines) |

## Related Skills

- `pm-dev-java:java-core` — General Java patterns
- `pm-dev-java-cui:cui-http-testing` — HTTP testing with CUI MockWebServer
- `pm-dev-java:java-security` — Generic Java security surface (inbound `jakarta.validation`, secure logging, secrets, startup validation). The `de.cuioss.http.security` pipelines above are the CUI-specific HTTP realization; load java-security for the framework-agnostic Java mechanics — see `java-security/SKILL.md`.
- `plan-marshall:persona-security-expert` — Cross-cutting security foundations. cui-http documents an inbound HTTP **trust boundary**; the conceptual architecture behind it (allow-list vs deny-list, canonicalize-before-validate, fail-closed) lives in `plan-marshall:persona-security-expert`'s [`standards/input-validation-trust-boundaries.md`](../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md).
