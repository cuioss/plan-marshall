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

### Core HTTP Handlers

#### HttpHandler

Builder-based HTTP client wrapper with automatic SSL context creation for HTTPS.

* Uses `@Builder` pattern for configuration
* Auto-creates secure SSL context via SecureSSLContextProvider when not provided
* Configurable connection and read timeouts (default: 10 seconds)
* Thread-safe after construction

#### HTTP Adapters (New Architecture)

Async-first HTTP client adapters with composable retry and caching.

* **ETagAwareHttpAdapter**: ETag-based HTTP caching with 304 Not Modified support
* **ResilientHttpAdapter**: Non-blocking retry with exponential backoff
* **HttpAdapter**: Method-specific API (get(), post(), put(), delete(), etc.)
* Composition pattern: Wrap adapters for retry + caching
* Thread-safe async execution with CompletableFuture
* Error categorization and idempotency-aware retry

### SSL/TLS Support

#### SecureSSLContextProvider

Utility for creating TLS 1.2+ SSL contexts.

### HTTP Status Classification

#### HttpStatusFamily

Enum for RFC 7231 HTTP status code classification with static helper methods.

### Content Conversion

#### HttpContentConverter

Interface for converting HTTP response bodies to domain objects.

* Generic type-safe conversion
* Configurable body handlers
* Empty value support for null/empty responses

#### StringContentConverter

Built-in content converter for String responses.

* Identity conversion (no transformation)
* Useful for raw text/JSON responses
* Factory method: `StringContentConverter.identity()`

### Result Handling

#### HttpResult

Sealed interface for HTTP operation results with type-safe pattern matching.

* Success/Failure record types
* ETag support for cache optimization
* HTTP status code tracking
* Error categorization via HttpErrorCategory
* Factory methods for common scenarios

#### HttpErrorCategory

Error categorization for HTTP operations.

* `NETWORK_ERROR` - Connection failures, timeouts
* `SERVER_ERROR` - 5xx responses
* `CLIENT_ERROR` - 4xx responses
* `INVALID_CONTENT` - Content conversion failures
* `CONFIGURATION_ERROR` - Setup/config issues
* Retry eligibility determination

#### HttpResultState

HTTP-specific result states extending CUI result framework.

### Logging

#### HttpLogMessages

Centralized log messages for HTTP operations.

* Structured logging with CuiLogger
* Consistent error codes
* Debug, info, warning, and error levels

## HTTP Result Pattern

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

### HTTP Adapter with Retry and Caching

This example demonstrates the async-first pattern using `HttpAdapter` with ETag-based caching and retry logic.

```java
// Create HTTP handler
HttpHandler httpHandler = HttpHandler.builder()
    .uri("https://api.example.com/data")
    .connectionTimeoutSeconds(10)
    .readTimeoutSeconds(30)
    .build();

// Create adapter with ETag caching and retry
HttpAdapter<String> adapter = ResilientHttpAdapter.wrap(
    ETagAwareHttpAdapter.<String>builder()
        .httpHandler(httpHandler)
        .responseConverter(StringContentConverter.identity())
        .build(),
    RetryConfig.defaults() // 5 attempts, exponential backoff
);

// Execute async-first (returns CompletableFuture)
adapter.get(Map.of("Accept", "application/json"))
    .thenAccept(result -> {
        if (result.isSuccess()) {
            result.getContent().ifPresent(content -> {
                processContent(content);
                // ETag available for cache optimization
                result.getETag().ifPresent(etag -> logger.debug("Cached with ETag: {}", etag));
            });
            // Next load() call may return 304 Not Modified with cached content
        } else {
            // Handle error with detailed information
            result.getErrorMessage().ifPresent(msg -> logger.error("Load failed: {}", msg));
            HttpErrorCategory category = result.getErrorCategory();

            if (result.isRetryable()) {
                logger.info("Retryable error ({}), will retry", category);
            } else {
                logger.error("Non-retryable error ({}), giving up", category);
            }
        }
    });
```

### Custom Response Converter

```java
// Custom converter for JSON to domain object
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

// Use with adapter
HttpAdapter<User> userAdapter = ResilientHttpAdapter.wrap(
    ETagAwareHttpAdapter.<User>builder()
        .httpHandler(httpHandler)
        .responseConverter(userConverter)
        .build(),
    RetryConfig.defaults()
);

// Execute async-first
userAdapter.get(Map.of("Accept", "application/json"))
    .thenAccept(result -> {
        if (result.isSuccess()) {
            result.getContent().ifPresent(user -> processUser(user));
        }
    });
```

### Retry Configuration

```java
// Default retry: 5 attempts, exponential backoff
RetryConfig defaults = RetryConfig.defaults();

// Custom retry configuration
RetryConfig custom = RetryConfig.builder()
    .maxAttempts(3)
    .initialDelay(Duration.ofMillis(500))
    .multiplier(1.5)
    .maxDelay(Duration.ofSeconds(10))
    .jitter(0.2)  // 20% jitter
    .idempotentOnly(true)  // Only retry GET, PUT, DELETE
    .build();

// Wrap any adapter with retry
HttpAdapter<String> resilientAdapter = ResilientHttpAdapter.wrap(baseAdapter, custom);
```

## HttpResult Usage Patterns

### Traditional Style (Recommended for Simple Cases)

```java
HttpResult<ConfigData> result = handler.load();

// Check success
if (result.isSuccess()) {
    // Access content (Optional)
    result.getContent().ifPresent(config -> {
        processData(config);
        logger.info("Loaded configuration successfully");
    });

    // Access metadata
    result.getETag().ifPresent(etag ->
        logger.debug("Content ETag: {}", etag));

    result.getHttpStatus().ifPresent(status ->
        logger.debug("HTTP Status: {}", status));
}

// Handle errors
if (!result.isSuccess()) {
    result.getErrorMessage().ifPresent(logger::error);
    result.getCause().ifPresent(ex ->
        logger.error("Underlying cause", ex));

    // Check if retryable
    if (result.isRetryable()) {
        scheduleRetry();
    }

    // Use fallback if available
    result.getContent().ifPresent(fallback ->
        logger.warn("Using cached fallback content"));
}
```

### Pattern Matching Style (Recommended for Complex Logic)

```java
HttpResult<ConfigData> result = handler.load();

return switch (result) {
    case HttpResult.Success<ConfigData>(var config, var etag, var status) -> {
        logger.info("Loaded configuration successfully");
        updateCache(config, etag);
        yield true; // Success
    }

    case HttpResult.Failure<ConfigData> failure -> {
        logger.error(failure.errorMessage(), failure.cause());

        // Graceful degradation with fallback
        if (failure.fallbackContent() != null) {
            logger.warn("Using cached configuration");
            yield true; // Degraded but functional
        }

        // Determine if retry should be attempted
        yield failure.isRetryable(); // Retry logic
    }
};
```

### Error Category Based Handling

```java
HttpResult<String> result = handler.load();

result.getErrorCategory().ifPresent(category -> {
    switch (category) {
        case NETWORK_ERROR -> {
            // Transient network issues - retry with backoff
            logger.warn("Network error, will retry");
            retryStrategy.scheduleRetry();
        }
        case SERVER_ERROR -> {
            // Server 5xx errors - may be transient
            logger.warn("Server error (5xx), will retry");
            retryStrategy.scheduleRetry();
        }
        case CLIENT_ERROR -> {
            // Client 4xx errors - permanent, fix configuration
            logger.error("Client error (4xx), check request configuration");
            alertOperations("Invalid HTTP request configuration");
        }
        case INVALID_CONTENT -> {
            // Content validation failed - permanent
            logger.error("Response content invalid");
            useFallbackSource();
        }
        case CONFIGURATION_ERROR -> {
            // Setup/config issue - needs human intervention
            logger.error("Configuration error, check SSL/URL settings");
            alertOperations("HTTP handler misconfigured");
        }
    }
});
```

## HttpResult API Reference

### Common Methods

```java
interface HttpResult<T> {
    // State checks
    boolean isSuccess();
    boolean isRetryable();

    // Content access
    Optional<T> getContent();           // Always present for Success, optional for Failure
    Optional<String> getETag();         // HTTP ETag header
    Optional<Integer> getHttpStatus();  // HTTP status code

    // Error information (Failure only)
    Optional<String> getErrorMessage();      // Human-readable error
    Optional<Throwable> getCause();          // Underlying exception
    Optional<HttpErrorCategory> getErrorCategory(); // Error classification

    // Transformation
    <U> HttpResult<U> map(Function<T, U> mapper);
}
```

### Factory Method Reference

| Method | Use Case | Example |
|--------|----------|---------|
| `success(content, etag, status)` | Successful HTTP operation | 200 OK with fresh content |
| `failure(message, cause, category)` | Error without fallback | Network timeout, no cache |
| `failureWithFallback(message, cause, fallback, category, etag, status)` | Error with cached fallback | Server error, using stale cache |

### Transformation Example

```java
// Transform content while preserving metadata
HttpResult<String> jsonResult = handler.load();

HttpResult<Config> configResult = jsonResult.map(json -> {
    return parseConfig(json);
});

// Metadata (ETag, status, error info) automatically preserved
configResult.getETag().ifPresent(cache::updateETag);
```

## Integration Examples

### Generic Data Loader Pattern

```java
public class GenericHttpLoader<T> {

    public CompletableFuture<Boolean> loadData() {
        return CompletableFuture.supplyAsync(() -> {
            HttpResult<T> result = resilientHandler.load();

            return switch (result) {
                case HttpResult.Success<T>(var data, _, var status) -> {
                    updateCache(data);
                    logger.info("Loaded data successfully");

                    if (status == 304) {
                        logger.debug("Data unchanged (304 Not Modified)");
                    }

                    yield true; // Success
                }

                case HttpResult.Failure<T> failure -> {
                    logger.error(failure.errorMessage(), failure.cause());

                    // Use fallback if available
                    if (failure.fallbackContent() != null) {
                        updateCache(failure.fallbackContent());
                        logger.warn("Using cached data as fallback");
                        yield true; // Degraded but functional
                    }

                    // Retry if transient error
                    if (failure.isRetryable() && backgroundRefreshEnabled) {
                        scheduleRetry();
                    }

                    yield false; // Failure
                }
            };
        });
    }
}
```

### Cached Data Resolver Pattern

```java
public class CachedHttpResolver<T> {

    private HttpResult<T> cachedResult;

    public Optional<T> getData() {
        return ensureLoaded();
    }

    private Optional<T> ensureLoaded() {
        if (cachedResult == null) {
            cachedResult = httpHandler.load();
        }

        // Return content if successful, empty otherwise
        return cachedResult.isSuccess() ?
            cachedResult.getContent() : Optional.empty();
    }
}
```

## Best Practices

### Do's ✅

* **Use pattern matching** for complex success/failure branching logic
* **Check isSuccess()** before accessing content in traditional style
* **Handle Optional** - content is not always present
* **Use isRetryable()** to determine retry strategy
* **Log error messages** - they're already human-readable
* **Provide fallback content** when using cached data during errors
* **Use map()** for content transformations to preserve metadata

### Don'ts ❌

* **Don't call getContent().get()** without checking - use `orElseThrow()` with message
* **Don't ignore error messages** - they provide valuable debugging information
* **Don't assume Failure has content** - fallback content is optional, check before using
* **Don't mix state checking styles** - choose pattern matching OR traditional, not both
* **Don't retry non-retryable errors** - check `isRetryable()` first
* **Don't discard error causes** - propagate exceptions for debugging

## Performance

* Records have minimal memory overhead
* No i18n runtime message resolution
* JVM can optimize sealed type switch expressions
* Immutable results can be cached and reused

## Thread Safety

* Records with final fields are thread-safe
* Results can be accessed from multiple threads
* No synchronization needed for reading state and content
* Use AtomicReference for cached result storage

## Troubleshooting

### Common Issues

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
// Wrong: Missing case
return switch (result) {
    case Success<T> success -> handleSuccess(success);
    // Compiler error: missing Failure case
};

// Right: All cases covered
return switch (result) {
    case Success<T> success -> handleSuccess(success);
    case Failure<T> failure -> handleFailure(failure);
};
```

**Error message is null**

```java
// Wrong: Not handling Optional
String msg = result.getErrorMessage().get(); // May throw

// Right: Provide default
String msg = result.getErrorMessage().orElse("Unknown error");
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
