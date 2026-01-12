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

// CUI Test Generators (optional - for test data generation)
import de.cuioss.test.generator.Generators;
import de.cuioss.test.generator.junit.EnableGeneratorController;
import de.cuioss.test.generator.junit.GeneratorsSource;
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

### When to Use MockWebServer

* Testing HTTP client implementations
* Testing API integrations
* Testing retry logic and error handling
* Testing HTTP request/response handling
* Testing timeout behaviors
* Testing different HTTP status codes and responses

### When NOT to Use MockWebServer

* Integration tests with real HTTP services (use Testcontainers or similar)
* Testing HTTP server implementations (use different approach)
* End-to-end tests requiring real network calls

## Modern API Approach

### Parameter Resolvers

The MockWebServer extension provides automatic parameter injection for test methods:

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

The `@MockResponseConfig` annotation is repeatable:

```java
@EnableMockWebServer
@MockResponseConfig(
    path = "/api/users",
    method = HttpMethodMapper.GET,
    status = 200,
    jsonContentKeyValue = "users=[]"
)
@MockResponseConfig(
    path = "/api/users",
    method = HttpMethodMapper.POST,
    status = 201,
    textContent = "Created"
)
class MultipleResponsesTest {
    // Both endpoints are available in all test methods
}
```

### Method-Level Configuration

Override or extend class-level configuration:

```java
@EnableMockWebServer
@MockResponseConfig(path = "/api/users", status = 200, textContent = "Class level")
class MethodLevelConfigTest {

    @Test
    @MockResponseConfig(path = "/api/special", status = 200, textContent = "Method level")
    @DisplayName("Should have access to both class and method level mocks")
    void shouldAccessBothConfigurations(URIBuilder uriBuilder) {
        // This test can access:
        // - /api/users (from class annotation)
        // - /api/special (from method annotation)
    }
}
```

## @MockResponseConfig Options

### Content Types

```java
// Text content (Content-Type: text/plain)
@MockResponseConfig(
    path = "/api/text",
    textContent = "Hello, World!"
)

// JSON content (Content-Type: application/json)
@MockResponseConfig(
    path = "/api/json",
    jsonContentKeyValue = "message=Hello,count=42"
)

// Raw string content (no Content-Type set)
@MockResponseConfig(
    path = "/api/raw",
    stringContent = "<custom>content</custom>"
)
```

### Custom Headers

```java
@MockResponseConfig(
    path = "/api/data",
    status = 200,
    jsonContentKeyValue = "key=value",
    headers = {"X-Custom-Header=Custom Value", "Cache-Control=no-cache"},
    contentType = "application/json; charset=utf-8"
)
```

### HTTP Methods

```java
@MockResponseConfig(
    path = "/api/resource",
    method = HttpMethodMapper.POST,
    status = 201
)

@MockResponseConfig(
    path = "/api/resource",
    method = HttpMethodMapper.DELETE,
    status = 204
)
```

## URIBuilder Usage Patterns

### Recommended: Using addPathSegments

```java
@Test
void shouldBuildUriWithMultipleSegments(URIBuilder uriBuilder) {
    // RECOMMENDED - efficient and clean
    URI uri = uriBuilder.addPathSegments("api", "users", "123").build();

    // Less efficient - multiple builder calls
    URI uri2 = uriBuilder
        .addPathSegment("api")
        .addPathSegment("users")
        .addPathSegment("123")
        .build();
}
```

### URIBuilder Features

```java
@Test
void shouldDemonstrateUriBuilderFeatures(URIBuilder uriBuilder) {
    // Build complete URI
    URI baseUri = uriBuilder.build();
    assertEquals("http", baseUri.getScheme());

    // Add path segments
    URI withPath = uriBuilder.addPathSegments("api", "v1", "users").build();

    // URIBuilder is immutable - each call returns new instance
    URIBuilder builder1 = uriBuilder.addPathSegment("api");
    URIBuilder builder2 = uriBuilder.addPathSegment("different");
    // builder1 and builder2 are independent
}
```

## @ModuleDispatcher for Complex Scenarios

For advanced request handling logic, use `@ModuleDispatcher`.

### Pattern 1: Using Test Class Method (Recommended)

```java
@EnableMockWebServer
@ModuleDispatcher // Looks for getModuleDispatcher() method
class TestMethodDispatcherTest {

    // This method provides the dispatcher
    ModuleDispatcherElement getModuleDispatcher() {
        return new BaseAllAcceptDispatcher("/api");
    }

    @Test
    @DisplayName("Should use dispatcher from test method")
    void shouldUseDispatcher(URIBuilder uriBuilder) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(uriBuilder.addPathSegments("api", "test").build())
            .GET()
            .build();

        HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode());
    }
}
```

### Pattern 2: Using Dispatcher Class

```java
@EnableMockWebServer
@ModuleDispatcher(UserApiDispatcher.class)
class DispatcherClassTest {
    // Dispatcher is defined in separate class
}

// Separate dispatcher implementation
class UserApiDispatcher implements ModuleDispatcherElement {
    @Override
    public String getBaseUrl() {
        return "/api/users";
    }

    @Override
    public Optional<mockwebserver3.MockResponse> handleGet(@NonNull mockwebserver3.RecordedRequest request) {
        return Optional.of(new mockwebserver3.MockResponse.Builder()
            .addHeader("Content-Type", "application/json")
            .body("{\"users\":[]}")
            .code(200)
            .build());
    }

    @Override
    public @NonNull Set<HttpMethodMapper> supportedMethods() {
        return Set.of(HttpMethodMapper.GET);
    }
}
```

### Pattern 3: Using Provider Method

```java
@EnableMockWebServer
@ModuleDispatcher(provider = DispatcherFactory.class, providerMethod = "createApiDispatcher")
class ProviderMethodTest {
    // Factory creates the dispatcher
}

class DispatcherFactory {
    public static ModuleDispatcherElement createApiDispatcher() {
        return new BaseAllAcceptDispatcher("/api");
    }
}
```

### Path-Based Routing with Custom Dispatcher

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
            public Optional<mockwebserver3.MockResponse> handleGet(@NonNull mockwebserver3.RecordedRequest request) {
                String path = request.getPath();

                // Route based on path patterns
                if (path.endsWith("/api/users/active")) {
                    return Optional.of(new mockwebserver3.MockResponse.Builder()
                        .code(200)
                        .addHeader("Content-Type", "application/json")
                        .body("{\"users\":[{\"id\":1,\"status\":\"active\"}]}")
                        .build());
                } else if (path.matches(".*/api/users/\\d+")) {
                    // Extract ID from path
                    String userId = path.substring(path.lastIndexOf('/') + 1);
                    return Optional.of(new mockwebserver3.MockResponse.Builder()
                        .code(200)
                        .body("{\"id\":" + userId + "}")
                        .build());
                }

                // Default response
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

### Extension-Provided Certificates (Automatic)

The simplest approach - let the extension generate certificates:

```java
@EnableMockWebServer(useHttps = true)
class AutoHttpsTest {

    @Test
    @DisplayName("Should connect via HTTPS with auto-generated certificates")
    void shouldConnectViaHttps(URIBuilder uriBuilder, SSLContext sslContext)
            throws Exception {
        assertNotNull(sslContext, "SSLContext should be injected");

        URI uri = uriBuilder.build();
        assertEquals("https", uri.getScheme(), "Should use HTTPS");

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

### Custom Certificates with @TestProvidedCertificate

For custom certificate control:

```java
@EnableMockWebServer(useHttps = true)
@TestProvidedCertificate(methodName = "createTestCertificates")
class CustomCertificateTest {

    // This method provides custom certificates
    public static HandshakeCertificates createTestCertificates() {
        return KeyMaterialUtil.createSelfSignedHandshakeCertificates(
            7, // validity in days
            KeyAlgorithm.RSA_2048);
    }

    @Test
    @DisplayName("Should use custom certificates")
    void shouldUseCustomCertificates(SSLContext sslContext) {
        assertNotNull(sslContext, "Custom SSLContext should be injected");
        // Use the custom SSLContext
    }
}
```

### Using Certificate Provider Class

For reusable certificate logic:

```java
@EnableMockWebServer(useHttps = true)
@TestProvidedCertificate(
    providerClass = TestCertificateProvider.class,
    methodName = "provideHandshakeCertificates"
)
class CertificateProviderTest {
    @Test
    void shouldUseCertificatesFromProvider(SSLContext sslContext) {
        assertNotNull(sslContext);
    }
}

// Reusable certificate provider
class TestCertificateProvider {
    private static HandshakeCertificates certificates;

    public static HandshakeCertificates provideHandshakeCertificates() {
        if (certificates == null) {
            certificates = KeyMaterialUtil.createSelfSignedHandshakeCertificates(
                1, KeyAlgorithm.RSA_2048);
        }
        return certificates;
    }
}
```

## Response Mocking Patterns

### Success Responses

```java
@EnableMockWebServer
@MockResponseConfig(
    path = "/api/data",
    status = 200,
    jsonContentKeyValue = "status=success,data=value"
)
class SuccessResponseTest {

    @Test
    @DisplayName("Should handle successful JSON response")
    void shouldHandleSuccessResponse(URIBuilder uriBuilder) throws Exception {
        HttpClient client = HttpClient.newHttpClient();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(uriBuilder.addPathSegments("api", "data").build())
            .GET()
            .build();

        HttpResponse<String> response = client.send(request,
            HttpResponse.BodyHandlers.ofString());

        assertEquals(200, response.statusCode());
        assertTrue(response.body().contains("success"));
    }
}
```

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
            public String getBaseUrl() {
                return "/api";
            }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(@NonNull mockwebserver3.RecordedRequest request) {
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
        // Client with 2-second timeout
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

## Request Verification with MockWebServer Parameter

Use the `MockWebServer` parameter for advanced verification:

### Verifying Request Details

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
        assertTrue(request.getPath().endsWith("/api/users"),
            "Path should match");
    }
}
```

### Verifying Request Body

```java
@Test
@MockResponseConfig(path = "/api/users", method = HttpMethodMapper.POST, status = 201)
@DisplayName("Should send correct request body")
void shouldSendCorrectBody(MockWebServer server, URIBuilder uriBuilder)
        throws Exception {
    User user = User.builder()
        .name(Generators.strings().next())
        .email(Generators.emailAddress().next())
        .build();

    client.createUser(uriBuilder.addPathSegments("api", "users").build(), user);

    mockwebserver3.RecordedRequest request = server.takeRequest();
    String body = request.getBody().readUtf8();

    assertTrue(body.contains(user.getName()),
        "Request body should contain user name");
    assertTrue(body.contains(user.getEmail()),
        "Request body should contain user email");
}
```

### Verifying Multiple Requests

```java
@Test
@MockResponseConfig(path = "/api/users/1", status = 200, textContent = "{\"id\":1}")
@MockResponseConfig(path = "/api/users/2", status = 200, textContent = "{\"id\":2}")
@DisplayName("Should handle multiple sequential requests")
void shouldHandleMultipleRequests(MockWebServer server, URIBuilder uriBuilder)
        throws Exception {
    client.getUser(uriBuilder.addPathSegments("api", "users", "1").build());
    client.getUser(uriBuilder.addPathSegments("api", "users", "2").build());

    assertEquals(2, server.getRequestCount(), "Should have made 2 requests");

    mockwebserver3.RecordedRequest request1 = server.takeRequest();
    assertTrue(request1.getPath().endsWith("/api/users/1"));

    mockwebserver3.RecordedRequest request2 = server.takeRequest();
    assertTrue(request2.getPath().endsWith("/api/users/2"));
}
```

## Retry Logic Testing

### Testing Retry on Failure

```java
@EnableMockWebServer
@ModuleDispatcher
class RetryLogicTest {

    ModuleDispatcherElement getModuleDispatcher() {
        return new ModuleDispatcherElement() {
            private int callCount = 0;

            @Override
            public String getBaseUrl() {
                return "/api";
            }

            @Override
            public Optional<mockwebserver3.MockResponse> handleGet(@NonNull mockwebserver3.RecordedRequest request) {
                callCount++;
                if (callCount == 1) {
                    // First request fails
                    return Optional.of(new mockwebserver3.MockResponse.Builder().code(500).build());
                }
                // Second request succeeds
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
        // Client configured with retry logic
        Response response = resilientClient.fetchData(
            uriBuilder.addPathSegments("api", "test").build());

        assertTrue(response.isSuccess(), "Should succeed after retry");
        assertEquals(2, server.getRequestCount(),
            "Should have made 2 requests (initial + retry)");
    }
}
```

## Integration with CUI Test Generator

Combine MockWebServer with generator framework for comprehensive testing.

For detailed generator usage patterns and requirements, see `pm-dev-java-cui:cui-testing` skill.

```java
@EnableMockWebServer
@EnableGeneratorController
@MockResponseConfig(path = "/api/users", status = 200)
class ComprehensiveHttpTest {

    @ParameterizedTest
    @DisplayName("Should handle various user IDs")
    @GeneratorsSource(generator = GeneratorType.INTEGERS, low = "1", high = "100", count = 5)
    void shouldFetchVariousUsers(Integer userId, URIBuilder uriBuilder) throws Exception {
        // Generate mock response data using generators
        String userName = Generators.strings().next();
        String userEmail = Generators.emailAddress().next();

        // Configure response with generated data
        String responseBody = String.format(
            "{\"id\": %d, \"name\": \"%s\", \"email\": \"%s\"}",
            userId, userName, userEmail);

        // Test with parameterized data
        User user = client.getUser(
            uriBuilder.addPathSegments("api", "users", userId.toString()).build());

        assertNotNull(user, "User should not be null");
        assertNotNull(user.getName(), "User name should not be null");
        assertNotNull(user.getEmail(), "User email should not be null");
    }
}
```

## Context-Aware Behavior

`@MockResponseConfig` annotations are context-aware for test isolation.

Each test method only has access to:
1. Its own method-level `@MockResponseConfig` annotations
2. Class-level `@MockResponseConfig` annotations from its containing class and parent classes
3. For nested test classes, only annotations from the class hierarchy up to the test method's class

This prevents unintended interactions between test methods.

```java
@EnableMockWebServer
@MockResponseConfig(path = "/class-level", status = 200, textContent = "Class Level")
class ContextAwareTest {

    @Test
    @MockResponseConfig(path = "/method-a", status = 200, textContent = "Method A")
    void testMethodA(URIBuilder uriBuilder) {
        // Can access: /class-level, /method-a
        // Cannot access: /method-b (from different method)
    }

    @Test
    @MockResponseConfig(path = "/method-b", status = 200, textContent = "Method B")
    void testMethodB(URIBuilder uriBuilder) {
        // Can access: /class-level, /method-b
        // Cannot access: /method-a (from different method)
    }
}
```

## Best Practices

### Clear Test Structure

* Follow AAA pattern (see `pm-dev-java:junit-core` skill for details)
* Use `@MockResponseConfig` for simple mocking scenarios
* Use `@ModuleDispatcher` for complex routing or reusable dispatchers
* Always use parameter injection (URIBuilder, MockWebServer, SSLContext)
* Prefer `URIBuilder.addPathSegments()` over chaining multiple calls

### Meaningful Assertions

* Verify response data correctness
* Use MockWebServer parameter to check request headers, body, and parameters
* Validate retry behavior and error handling
* Use descriptive assertion messages
* Verify request count matches expectations

### Realistic Test Data

* Use CUI generators for test data creation
* Test with various response codes and payloads
* Include edge cases (empty responses, large payloads)
* Test error scenarios comprehensively
* Use HTTPS when testing production-like scenarios

### Avoid Common Pitfalls

* **Use parameter injection**: Always inject URIBuilder, MockWebServer, or SSLContext
* **WeldUnit compatibility**: Add `@ExplicitParamInjection` when using WeldUnit
* **Handle InterruptedException**: Properly handle when using `server.takeRequest()`
* **Context awareness**: Remember method-level annotations don't leak between tests

## Common HTTP Status Codes to Test

* **200 OK** - Successful GET/PUT requests
* **201 Created** - Successful POST requests
* **204 No Content** - Successful DELETE requests
* **400 Bad Request** - Invalid request data
* **401 Unauthorized** - Missing or invalid authentication
* **403 Forbidden** - Insufficient permissions
* **404 Not Found** - Resource not found
* **500 Internal Server Error** - Server errors
* **503 Service Unavailable** - Temporary service issues

## Additional Resources

* CUI MockWebServer JUnit5: https://github.com/cuioss/cui-test-mockwebserver-junit5
* Complete Documentation: https://gitingest.com/github.com/cuioss/cui-test-mockwebserver-junit5
* OkHttp MockWebServer: https://github.com/square/okhttp/tree/master/mockwebserver
