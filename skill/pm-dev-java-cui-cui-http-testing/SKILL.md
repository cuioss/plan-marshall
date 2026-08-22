---
name: pm-dev-java-cui-cui-http-testing
description: CUI MockWebServer standards for HTTP testing with JUnit 5 — @MockResponseConfig setup, request verification, HTTPS/TLS testing, @ModuleDispatcher routing, timeout/resilience testing, and generator-driven adversarial attack-database testing (path/header/query)
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# CUI Testing HTTP Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

CUI-specific HTTP testing standards using `cui-test-mockwebserver-junit5`. Covers MockWebServer configuration, HTTPS testing, and request verification.

## Enforcement

**Execution mode**: Reference library; load standards on-demand for HTTP testing tasks.

**Prohibited actions:**
- Do not use WireMock or other HTTP mocking libraries in CUI projects; must use CUI MockWebServer
- Do not configure MockWebServer manually; use `@EnableMockWebServer` annotation
- Do not load all standards at once; load progressively based on current task

**Constraints:**
- HTTP client tests must use `@EnableMockWebServer` with `@MockResponseConfig` annotations
- HTTPS testing must use the built-in SSL support from MockWebServer
- Request verification must use the MockWebServer assertion API

## Prerequisites

- `de.cuioss.test:cui-test-mockwebserver-junit5`

## Workflow

### Step 1: Load MockWebServer Standards

**CRITICAL**: Load these standards for any HTTP testing work.

```text
Read: standards/testing-mockwebserver.md
```

This provides the complete reference for annotations, dispatchers, HTTPS, and request verification.

### Step 2: Apply the Right Pattern (Based on Task)

**Simple response mocking** — Use `@MockResponseConfig` annotation:
```java
@EnableMockWebServer
@MockResponseConfig(
    path = "/api/users",
    method = HttpMethodMapper.GET,
    status = 200,
    jsonContentKeyValue = "users=[]"
)
class UserClientTest {

    @Test
    void shouldFetchUsers(URIBuilder uriBuilder) throws Exception {
        HttpResponse<String> response = client.send(
            HttpRequest.newBuilder()
                .uri(uriBuilder.addPathSegments("api", "users").build())
                .GET().build(),
            HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode());
    }
}
```

**Complex routing** — Use `@ModuleDispatcher` with `ModuleDispatcherElement`:
```java
@EnableMockWebServer
@ModuleDispatcher
class RoutingTest {

    ModuleDispatcherElement getModuleDispatcher() {
        return new ModuleDispatcherElement() {
            @Override
            public String getBaseUrl() { return "/api"; }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(
                    @NonNull mockwebserver3.RecordedRequest request) {
                return Optional.of(new mockwebserver3.MockResponse.Builder()
                    .code(200).body("{\"status\":\"ok\"}").build());
            }

            @Override
            public @NonNull Set<HttpMethodMapper> supportedMethods() {
                return Set.of(HttpMethodMapper.GET);
            }
        };
    }
}
```

**HTTPS testing** — Add `useHttps = true` and inject `SSLContext`:
```java
@EnableMockWebServer(useHttps = true)
class HttpsTest {

    @Test
    void shouldConnectViaHttps(URIBuilder uriBuilder, SSLContext sslContext) {
        assertEquals("https", uriBuilder.build().getScheme());
        HttpClient client = HttpClient.newBuilder().sslContext(sslContext).build();
        // ...
    }
}
```

**Request verification** — Inject `MockWebServer` and inspect recorded requests:
```java
@Test
void shouldIncludeAuthHeader(MockWebServer server, URIBuilder uriBuilder) throws Exception {
    client.fetchSecure(uriBuilder.addPathSegments("api", "data").build(), "token");

    mockwebserver3.RecordedRequest request = server.takeRequest();
    assertEquals("Bearer token", request.getHeader("Authorization"));
}
```

### Step 3: Drive Adversarial / Negative-Path Tests (For Security-Relevant HTTP Code)

When the task tests code that reads untrusted HTTP input (path segments, query parameters, headers), load the **Adversarial / Negative-Path Testing** section of `standards/testing-mockwebserver.md`. It documents the `de.cuioss.http.security.database` attack databases (`OWASPTop10AttackDatabase`, `ApacheCVEAttackDatabase`, `ModSecurityCRSAttackDatabase`) and the `AttackDatabase.ArgumentsProvider` parameterized-test pattern. Drive adversarial inputs from the curated databases rather than hardcoding a few attack literals.

## Key Rules

- `@MockResponseConfig` is repeatable — use multiple annotations for multiple endpoints
- Method-level `@MockResponseConfig` extends class-level config, no leaking between methods
- Always use `URIBuilder` parameter injection for constructing URIs — never hard-code ports
- Use `@ExplicitParamInjection` when combining with WeldUnit

## Standards Reference

| Standard | Purpose |
|----------|---------|
| `standards/testing-mockwebserver.md` | @EnableMockWebServer, @MockResponseConfig, @ModuleDispatcher, HTTPS, request verification, and adversarial attack-database testing |

## Related Skills

- `pm-dev-java-cui:cui-http` — CUI HTTP client patterns
- `pm-dev-java-cui:cui-testing` — CUI test generator framework
- `pm-dev-java:junit-core` — General JUnit 5 patterns
