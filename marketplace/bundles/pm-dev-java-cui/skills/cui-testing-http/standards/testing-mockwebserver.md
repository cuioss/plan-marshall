# HTTP Testing with MockWebServer Standards

## Overview

For testing HTTP client interactions in CUI projects, use the `cui-test-mockwebserver-junit5` framework. This provides a lightweight, in-process HTTP server for mocking HTTP responses and testing client behavior without external dependencies.

## Required Imports

```java
// CUI MockWebServer JUnit 5 Extensions
import de.cuioss.test.mockwebserver.EnableMockWebServer;
import de.cuioss.test.mockwebserver.mockresponse.MockResponseConfig;
import de.cuioss.test.mockwebserver.dispatcher.ModuleDispatcher;
import de.cuioss.test.mockwebserver.TestProvidedCertificate;

// CUI MockWebServer Dispatcher
import de.cuioss.test.mockwebserver.dispatcher.ModuleDispatcherElement;
import de.cuioss.test.mockwebserver.dispatcher.BaseAllAcceptDispatcher;
import de.cuioss.test.mockwebserver.dispatcher.HttpMethodMapper;

// CUI MockWebServer HTTPS/TLS Support
import de.cuioss.test.mockwebserver.tls.KeyMaterialUtil;
import de.cuioss.test.mockwebserver.tls.KeyAlgorithm;

// OkHttp MockWebServer (underlying library - server instance only)
import mockwebserver3.MockWebServer;

// OkHttp TLS Certificates
import okhttp3.tls.HandshakeCertificates;

// CUI URI Builder
import de.cuioss.uimodel.nameprovider.URIBuilder;
```

## Framework Requirements

### Maven Dependency

```xml
<dependency>
    <groupId>de.cuioss.test</groupId>
    <artifactId>cui-test-mockwebserver-junit5</artifactId>
    <scope>test</scope>
</dependency>
```

### Parameter Resolvers

The extension provides automatic parameter injection for test methods:

| Parameter Type | Description |
|----------------|-------------|
| `MockWebServer` | The actual MockWebServer instance for advanced configuration |
| `URIBuilder` | Pre-configured builder for constructing URIs pointing to the mock server |
| `SSLContext` | SSL context (when HTTPS is enabled with `useHttps = true`) |

Always use parameter injection and annotations for clean, modern test code.

## Basic MockWebServer Usage

### Simple Annotation-Based Configuration

Use `@MockResponseConfig` for straightforward mocking scenarios:

```java
@EnableMockWebServer
@MockResponseConfig(
    path = "/api/users",
    method = HttpMethodMapper.GET,
    status = 200,
    jsonContentKeyValue = "users=[]"
)
class SimpleMockWebServerTest {

    @Test
    @DisplayName("Should fetch users from API")
    void shouldFetchUsers(URIBuilder uriBuilder) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(uriBuilder.addPathSegments("api", "users").build())
            .GET()
            .build();

        HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode(), "Should return 200 OK");
        assertEquals("{\"users\":[]}", response.body(), "Should return empty users array");
    }
}
```

### Multiple Mock Responses

The `@MockResponseConfig` annotation is repeatable -- use multiple annotations at class or method level:

```java
@EnableMockWebServer
@MockResponseConfig(path = "/api/users", method = HttpMethodMapper.GET, status = 200,
                    jsonContentKeyValue = "users=[]")
@MockResponseConfig(path = "/api/users", method = HttpMethodMapper.POST, status = 201,
                    textContent = "Created")
class MultipleResponsesTest {
    // Both endpoints are available in all test methods
}
```

Method-level `@MockResponseConfig` extends class-level configuration. Each test method sees only its own method-level annotations plus class-level annotations -- no leaking between methods.

### @MockResponseConfig Options

```java
// Text content (Content-Type: text/plain)
@MockResponseConfig(path = "/api/text", textContent = "Hello, World!")

// JSON content (Content-Type: application/json)
@MockResponseConfig(path = "/api/json", jsonContentKeyValue = "message=Hello,count=42")

// Raw string content (no Content-Type set)
@MockResponseConfig(path = "/api/raw", stringContent = "<custom>content</custom>")

// Custom headers and content type
@MockResponseConfig(
    path = "/api/data", status = 200, jsonContentKeyValue = "key=value",
    headers = {"X-Custom-Header=Custom Value", "Cache-Control=no-cache"},
    contentType = "application/json; charset=utf-8"
)

// HTTP method binding
@MockResponseConfig(path = "/api/resource", method = HttpMethodMapper.POST, status = 201)
@MockResponseConfig(path = "/api/resource", method = HttpMethodMapper.DELETE, status = 204)
```

### URIBuilder Usage

```java
@Test
void shouldBuildUri(URIBuilder uriBuilder) {
    // RECOMMENDED - efficient and clean
    URI uri = uriBuilder.addPathSegments("api", "users", "123").build();

    // URIBuilder is immutable - each call returns new instance
    URIBuilder builder1 = uriBuilder.addPathSegment("api");
    URIBuilder builder2 = uriBuilder.addPathSegment("different");
    // builder1 and builder2 are independent
}
```

## @ModuleDispatcher for Complex Scenarios

For advanced request handling logic beyond what `@MockResponseConfig` supports, use `@ModuleDispatcher`. The recommended pattern uses a `getModuleDispatcher()` method on the test class. Alternatively, reference an external dispatcher class (`@ModuleDispatcher(MyDispatcher.class)`) or a factory method (`@ModuleDispatcher(provider = Factory.class, providerMethod = "create")`).

### Complete Example: Path-Based Routing

```java
@EnableMockWebServer
@ModuleDispatcher
class PathBasedDispatcherTest {

    ModuleDispatcherElement getModuleDispatcher() {
        return new ModuleDispatcherElement() {
            @Override
            public String getBaseUrl() {
                return "/api/users";
            }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(
                    @NonNull mockwebserver3.RecordedRequest request) {
                String path = request.getPath();

                if (path.endsWith("/api/users/active")) {
                    return Optional.of(new mockwebserver3.MockResponse.Builder()
                        .code(200)
                        .addHeader("Content-Type", "application/json")
                        .body("{\"users\":[{\"id\":1,\"status\":\"active\"}]}")
                        .build());
                } else if (path.matches(".*/api/users/\\d+")) {
                    String userId = path.substring(path.lastIndexOf('/') + 1);
                    return Optional.of(new mockwebserver3.MockResponse.Builder()
                        .code(200)
                        .body("{\"id\":" + userId + "}")
                        .build());
                }

                return Optional.of(new mockwebserver3.MockResponse.Builder()
                    .code(200)
                    .body("{\"users\":[]}")
                    .build());
            }

            @Override
            public @NonNull Set<HttpMethodMapper> supportedMethods() {
                return Set.of(HttpMethodMapper.GET);
            }
        };
    }
}
```

## HTTPS Support

### Automatic Certificates (Recommended)

Set `useHttps = true` and the extension generates certificates automatically:

```java
@EnableMockWebServer(useHttps = true)
class AutoHttpsTest {

    @Test
    @DisplayName("Should connect via HTTPS with auto-generated certificates")
    void shouldConnectViaHttps(URIBuilder uriBuilder, SSLContext sslContext)
            throws Exception {
        assertEquals("https", uriBuilder.build().getScheme(), "Should use HTTPS");

        HttpClient client = HttpClient.newBuilder()
            .sslContext(sslContext)
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(uriBuilder.addPathSegment("api").build())
            .GET()
            .build();

        HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode());
    }
}
```

For custom certificate control, use `@TestProvidedCertificate(methodName = "createCerts")` with a static method returning `HandshakeCertificates`. For reusable certificate logic across tests, use `@TestProvidedCertificate(providerClass = MyCertProvider.class, methodName = "provide")`.

## Response Mocking Patterns

### Error Responses

```java
@EnableMockWebServer
class ErrorResponseTest {

    @Test
    @MockResponseConfig(path = "/api/resource", status = 404,
                        jsonContentKeyValue = "error=Not Found")
    @DisplayName("Should handle 404 error")
    void shouldHandle404Error(URIBuilder uriBuilder) {
        assertThrows(NotFoundException.class,
            () -> client.fetchResource(uriBuilder.addPathSegments("api", "resource").build()),
            "Should throw NotFoundException for 404 response");
    }

    @Test
    @MockResponseConfig(path = "/api/resource", status = 500,
                        jsonContentKeyValue = "error=Internal Server Error")
    @DisplayName("Should handle 500 server error")
    void shouldHandle500Error(URIBuilder uriBuilder) {
        assertThrows(ServerException.class,
            () -> client.fetchResource(uriBuilder.addPathSegments("api", "resource").build()),
            "Should throw ServerException for 500 response");
    }
}
```

### Delayed Responses (Timeout Testing)

```java
@EnableMockWebServer
@ModuleDispatcher
class TimeoutTest {

    ModuleDispatcherElement getModuleDispatcher() {
        return new ModuleDispatcherElement() {
            @Override
            public String getBaseUrl() { return "/api"; }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(
                    @NonNull mockwebserver3.RecordedRequest request) {
                return Optional.of(new mockwebserver3.MockResponse.Builder()
                    .code(200)
                    .setBodyDelay(5, TimeUnit.SECONDS)
                    .build());
            }

            @Override
            public @NonNull Set<HttpMethodMapper> supportedMethods() {
                return Set.of(HttpMethodMapper.GET);
            }
        };
    }

    @Test
    @DisplayName("Should handle connection timeout")
    void shouldHandleTimeout(URIBuilder uriBuilder) {
        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(2))
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(uriBuilder.addPathSegments("api", "test").build())
            .GET()
            .build();

        assertThrows(HttpTimeoutException.class,
            () -> client.send(request, HttpResponse.BodyHandlers.ofString()),
            "Should throw TimeoutException when server response is delayed");
    }
}
```

## Request Verification

Use the `MockWebServer` parameter to inspect recorded requests:

```java
@EnableMockWebServer
@MockResponseConfig(path = "/api/users", status = 200)
class RequestVerificationTest {

    @Test
    @DisplayName("Should include authorization header")
    void shouldIncludeAuthHeader(MockWebServer server, URIBuilder uriBuilder)
            throws Exception {
        client.fetchSecureResource(uriBuilder.addPathSegments("api", "users").build(),
                                   "token123");

        mockwebserver3.RecordedRequest request = server.takeRequest();
        assertEquals("Bearer token123", request.getHeader("Authorization"),
            "Authorization header should be included");
        assertEquals("GET", request.getMethod(), "Should use GET method");
        assertTrue(request.getPath().endsWith("/api/users"), "Path should match");
    }

    @Test
    @MockResponseConfig(path = "/api/users", method = HttpMethodMapper.POST, status = 201)
    @DisplayName("Should send correct request body")
    void shouldSendCorrectBody(MockWebServer server, URIBuilder uriBuilder)
            throws Exception {
        client.createUser(uriBuilder.addPathSegments("api", "users").build(), user);

        mockwebserver3.RecordedRequest request = server.takeRequest();
        String body = request.getBody().readUtf8();
        assertTrue(body.contains(user.getName()), "Request body should contain user name");
    }
}
```

Verify request count with `server.getRequestCount()` and dequeue multiple requests sequentially with repeated `server.takeRequest()` calls.

## Retry Logic Testing

```java
@EnableMockWebServer
@ModuleDispatcher
class RetryLogicTest {

    ModuleDispatcherElement getModuleDispatcher() {
        return new ModuleDispatcherElement() {
            private int callCount = 0;

            @Override
            public String getBaseUrl() { return "/api"; }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(
                    @NonNull mockwebserver3.RecordedRequest request) {
                callCount++;
                if (callCount == 1) {
                    return Optional.of(new mockwebserver3.MockResponse.Builder()
                        .code(500).build());
                }
                return Optional.of(new mockwebserver3.MockResponse.Builder()
                    .code(200)
                    .body("{\"status\":\"success\"}")
                    .build());
            }

            @Override
            public @NonNull Set<HttpMethodMapper> supportedMethods() {
                return Set.of(HttpMethodMapper.GET);
            }
        };
    }

    @Test
    @DisplayName("Should retry on server error")
    void shouldRetryOnServerError(MockWebServer server, URIBuilder uriBuilder)
            throws Exception {
        Response response = resilientClient.fetchData(
            uriBuilder.addPathSegments("api", "test").build());

        assertTrue(response.isSuccess(), "Should succeed after retry");
        assertEquals(2, server.getRequestCount(),
            "Should have made 2 requests (initial + retry)");
    }
}
```

## Integration with CUI Test Generator

Combine MockWebServer with the generator framework for parameterized HTTP testing. For detailed generator usage patterns and requirements, see `pm-dev-java-cui:cui-testing` skill.

## Troubleshooting

* **Use parameter injection**: Always inject `URIBuilder`, `MockWebServer`, or `SSLContext` -- never construct manually
* **WeldUnit compatibility**: Add `@ExplicitParamInjection` when combining with WeldUnit
* **Handle InterruptedException**: Required when using `server.takeRequest()`
* **Context awareness**: Method-level `@MockResponseConfig` annotations do not leak between test methods

## Additional Resources

* CUI MockWebServer JUnit5: https://github.com/cuioss/cui-test-mockwebserver-junit5
* Complete Documentation: https://gitingest.com/github.com/cuioss/cui-test-mockwebserver-junit5
* OkHttp MockWebServer: https://github.com/square/okhttp/tree/master/mockwebserver
