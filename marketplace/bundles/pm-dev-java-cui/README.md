# pm-dev-java-cui

CUI-specific Java development standards bundle providing opinionated patterns for CUI Open Source projects.

## Overview

This bundle contains CUI library-specific standards that complement the general Java standards in `pm-dev-java`. Use this bundle when developing CUI projects that depend on CUI libraries.

## Skills

### cui-logging
CuiLogger and LogRecord standards for structured logging in CUI projects.

**Key patterns:**
- CuiLogger instead of SLF4J/Log4j
- LogRecord for INFO/WARN/ERROR/FATAL levels
- DSL-style LogMessages classes
- LogRecord identifier organization by severity

**Library**: `de.cuioss.tools.logging.*`

### cui-testing
CUI test library standards for test data generation and contract testing.

**Key patterns:**
- Mandatory `Generators.*` for ALL test data
- `@EnableGeneratorController` annotation
- `ShouldHandleObjectContracts<T>` for value objects
- `@EnableTestLogger` for log verification

**Libraries**:
- `de.cuioss.test.generator.*`
- `de.cuioss.test.valueobjects.*`
- `de.cuioss.test.juli.*`

### cui-http
CUI HTTP client patterns for HTTP operations.

**Key patterns:**
- HttpHandler builder pattern
- HttpResult sealed interface
- ETagAwareHttpAdapter for caching
- ResilientHttpAdapter for retry logic

**Library**: `de.cuioss.http.client.*`

### cui-testing-http
CUI MockWebServer wrapper for HTTP testing.

**Key patterns:**
- CUI MockWebServer usage
- HTTP test patterns

## Usage

Load skills based on project needs:

```yaml
# Full CUI project
skills:
  # General (from pm-dev-java)
  - pm-dev-java:java-core
  - pm-dev-java:java-null-safety
  - pm-dev-java:junit-core
  # CUI-specific (from this bundle)
  - pm-dev-java-cui:cui-logging
  - pm-dev-java-cui:cui-testing
```

## Dependencies

This bundle complements `pm-dev-java` and should be used together with it:
- General Java standards: `pm-dev-java`
- CUI-specific standards: `pm-dev-java-cui` (this bundle)

## CUI Libraries

| Library | Maven Coordinates | Purpose |
|---------|------------------|---------|
| cui-java-tools | `de.cuioss:cui-java-tools` | Logging (CuiLogger, LogRecord) |
| cui-test-generator | `de.cuioss.test:cui-test-generator` | Test data generation |
| cui-test-value-objects | `de.cuioss.test:cui-test-value-objects` | Contract testing |
| cui-test-juli | `de.cuioss.test:cui-test-juli` | Log testing |
| cui-http-client | `de.cuioss:cui-http-client` | HTTP client utilities |
