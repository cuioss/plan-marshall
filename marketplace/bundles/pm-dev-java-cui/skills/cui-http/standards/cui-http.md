# CUI HTTP Client Standards

## Required Imports

```java
// CUI HTTP Client Core
import de.cuioss.http.client.handler.HttpHandler;
import de.cuioss.http.client.handler.SecureSSLContextProvider;

// HTTP Adapters
import de.cuioss.http.client.adapter.HttpAdapter;
import de.cuioss.http.client.adapter.ETagAwareHttpAdapter;
import de.cuioss.http.client.adapter.ResilientHttpAdapter;
import de.cuioss.http.client.adapter.RetryConfig;

// HTTP Result Pattern (sealed interface)
import de.cuioss.http.client.result.HttpResult;
import de.cuioss.http.client.result.HttpErrorCategory;
import de.cuioss.http.client.result.HttpResultState;

// Content Conversion
import de.cuioss.http.client.converter.HttpRequestConverter;
import de.cuioss.http.client.converter.HttpResponseConverter;
import de.cuioss.http.client.converter.StringContentConverter;
import de.cuioss.http.client.ContentType;

// HTTP Status Classification
import de.cuioss.http.client.handler.HttpStatusFamily;

// Logging
import de.cuioss.http.client.HttpLogMessages;
```

## Maven Coordinates

```xml
<dependency>
    <groupId>de.cuioss</groupId>
    <artifactId>cui-http</artifactId>
</dependency>
```

## Overview

HTTP client utilities for request execution, SSL/TLS context management, and HTTP status classification. Provides async-first HTTP adapters with composable retry and caching, plus the HttpResult pattern for type-safe error handling.

## Components

### HttpHandler

Builder-based HTTP client wrapper with automatic SSL context creation for HTTPS.

* Uses `@Builder` pattern for configuration
* Auto-creates secure SSL context via SecureSSLContextProvider when not provided
* Configurable connection and read timeouts (default: 10 seconds)
* Thread-safe after construction

### HTTP Adapters

Async-first HTTP client adapters with composable retry and caching.

* **HttpAdapter**: Method-specific API (get(), post(), put(), delete(), etc.)
* **ETagAwareHttpAdapter**: ETag-based HTTP caching with 304 Not Modified support
* **ResilientHttpAdapter**: Non-blocking retry with exponential backoff
* Composition pattern: Wrap adapters for retry + caching
* Thread-safe async execution with CompletableFuture
* Error categorization and idempotency-aware retry

### SecureSSLContextProvider

Utility for creating TLS 1.2+ SSL contexts.

### HttpStatusFamily

Enum for RFC 7231 HTTP status code classification with static helper methods.

### Content Conversion

**HttpContentConverter** - Interface for converting HTTP response bodies to domain objects. Generic type-safe conversion with configurable body handlers and empty value support for null/empty responses.

**StringContentConverter** - Built-in converter for String responses. Factory method: `StringContentConverter.identity()`.

### HttpLogMessages

Centralized log messages for HTTP operations with structured logging via CuiLogger.

## HttpResult Pattern

`HttpResult<T>` is a sealed interface for HTTP operation results with type-safe pattern matching.

### Design Principles

* **Sealed Types**: Exhaustive pattern matching with compile-time guarantees
* **Optional Pattern**: Explicit content absence instead of mandatory defaults
* **Plain Strings**: Error messages without i18n framework dependencies
* **HTTP Semantics**: Native support for ETag, status codes, retry classification
* **Immutability**: Records ensure thread-safe results

### Sealed Interface Hierarchy

```java
public sealed interface HttpResult<T>
    permits HttpResult.Success, HttpResult.Failure {

    // Success: HTTP operation completed successfully
    record Success<T>(T content, String etag, int httpStatus) { }

    // Failure: HTTP operation failed (with optional fallback)
    record Failure<T>(
        String errorMessage,
        Throwable cause,
        T fallbackContent,
        HttpErrorCategory category,
        String etag,
        Integer httpStatus
    ) { }
}
```

### Result States

| Type | State | Description |
|------|-------|-------------|
| `Success<T>` | Fresh content | HTTP 200 OK with newly loaded content and ETag |
| `Success<T>` | Cached content | HTTP 304 Not Modified, using cached content with ETag |
| `Failure<T>` | Error with fallback | HTTP error occurred but cached content available for graceful degradation |
| `Failure<T>` | Error without fallback | HTTP error occurred with no cached content available |

### HttpErrorCategory

Error categorization for HTTP operations:

* `NETWORK_ERROR` - Connection failures, timeouts (retryable)
* `SERVER_ERROR` - 5xx responses (retryable)
* `CLIENT_ERROR` - 4xx responses (not retryable)
* `INVALID_CONTENT` - Content conversion failures (not retryable)
* `CONFIGURATION_ERROR` - Setup/config issues (not retryable)

### Factory Methods

| Method | Use Case | Example |
|--------|----------|---------|
| `success(content, etag, status)` | Successful HTTP operation | 200 OK with fresh content |
| `failure(message, cause, category)` | Error without fallback | Network timeout, no cache |
| `failureWithFallback(message, cause, fallback, category, etag, status)` | Error with cached fallback | Server error, using stale cache |

## Usage Examples

### Basic HTTP Handler

```java
HttpHandler handler = HttpHandler.builder()
    .uri("https://api.example.com/data")
    .connectionTimeoutSeconds(10)
    .readTimeoutSeconds(30)
    .build();

HttpClient client = handler.createHttpClient();
HttpRequest request = handler.requestBuilder()
    .GET()
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

if (HttpStatusFamily.isSuccess(response.statusCode())) {
    processData(response.body());
}
```

### Adapter with Retry and Caching

```java
HttpHandler httpHandler = HttpHandler.builder()
    .uri("https://api.example.com/data")
    .connectionTimeoutSeconds(10)
    .readTimeoutSeconds(30)
    .build();

// Compose: ETag caching wrapped with retry
HttpAdapter<String> adapter = ResilientHttpAdapter.wrap(
    ETagAwareHttpAdapter.<String>builder()
        .httpHandler(httpHandler)
        .responseConverter(StringContentConverter.identity())
        .build(),
    RetryConfig.defaults()
);

// Async execution returns CompletableFuture<HttpResult<String>>
adapter.get(Map.of("Accept", "application/json"))
    .thenAccept(result -> handleResult(result));
```

### Custom Response Converter

```java
HttpResponseConverter<User> userConverter = new HttpResponseConverter<User>() {
    @Override
    public Optional<User> convert(Object rawContent) {
        if (rawContent instanceof String json) {
            try {
                return Optional.of(objectMapper.readValue(json, User.class));
            } catch (Exception e) {
                return Optional.empty();
            }
        }
        return Optional.empty();
    }

    @Override
    public HttpResponse.BodyHandler<?> getBodyHandler() {
        return HttpResponse.BodyHandlers.ofString();
    }

    @Override
    public ContentType contentType() {
        return ContentType.APPLICATION_JSON;
    }
};
```

### Retry Configuration

```java
// Default retry: 5 attempts, exponential backoff
RetryConfig defaults = RetryConfig.defaults();

// Custom retry
RetryConfig custom = RetryConfig.builder()
    .maxAttempts(3)
    .initialDelay(Duration.ofMillis(500))
    .multiplier(1.5)
    .maxDelay(Duration.ofSeconds(10))
    .jitter(0.2)
    .idempotentOnly(true)  // Only retry GET, PUT, DELETE
    .build();

HttpAdapter<String> resilientAdapter = ResilientHttpAdapter.wrap(baseAdapter, custom);
```

### HttpResult with Pattern Matching (Recommended)

```java
HttpResult<ConfigData> result = handler.load();

return switch (result) {
    case HttpResult.Success<ConfigData>(var config, var etag, var status) -> {
        logger.info("Loaded configuration successfully");
        updateCache(config, etag);
        yield true;
    }

    case HttpResult.Failure<ConfigData> failure -> {
        logger.error(failure.errorMessage(), failure.cause());

        // Graceful degradation with fallback
        if (failure.fallbackContent() != null) {
            logger.warn("Using cached configuration");
            yield true;
        }

        yield failure.isRetryable();
    }
};
```

For simple cases, `isSuccess()` and `getContent()` accessor methods are also available. Pattern matching is preferred for branching logic as it provides compile-time exhaustiveness checks.

### Content Transformation

```java
// Transform content while preserving metadata (ETag, status, error info)
HttpResult<String> jsonResult = handler.load();
HttpResult<Config> configResult = jsonResult.map(json -> parseConfig(json));
```

## Troubleshooting

**Content is empty even though isSuccess() returns true**

```java
// Wrong: Assuming content is always present
result.getContent().get(); // May throw NoSuchElementException

// Right: Handle Optional properly
result.getContent().orElseThrow(() ->
    new IllegalStateException("Expected content not present"));
```

**Pattern matching not exhaustive**

```java
// Wrong: Missing case — compiler error
return switch (result) {
    case Success<T> success -> handleSuccess(success);
};

// Right: All cases covered
return switch (result) {
    case Success<T> success -> handleSuccess(success);
    case Failure<T> failure -> handleFailure(failure);
};
```

## Related Documentation

**Sources:**
* [Client Handlers Documentation](https://github.com/cuioss/cui-http/blob/main/doc/client-handlers-readme.adoc)
* [HTTP Result Pattern Documentation](https://github.com/cuioss/cui-http/blob/main/doc/http-result-pattern.adoc)

**Additional References:**
* [RFC 7231 - HTTP/1.1 Semantics](https://tools.ietf.org/html/rfc7231)
* `de.cuioss.http.client.result.HttpResult` - API documentation
* `de.cuioss.http.client.result.HttpErrorCategory` - Error categories
* `de.cuioss.http.client.adapter.ResilientHttpAdapter` - Retry decorator with exponential backoff
* `de.cuioss.http.client.adapter.ETagAwareHttpAdapter` - ETag caching with 304 Not Modified support
