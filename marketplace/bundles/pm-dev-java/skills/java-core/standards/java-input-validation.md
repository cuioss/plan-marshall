# Java Inbound Input Validation

> **Security surface.** This standard is the INBOUND-validation leg of the Java security surface owned by `Skill: pm-dev-java:java-security`. Resolve it through the `security` profile (`skills_by_profile.security`) for security review and hardening tasks.

Framework-agnostic validation of externally-sourced data at the trust boundary, using the `jakarta.validation` (Bean Validation) API. Applies to any Java 21+ project — no web framework required.

**Scope (INBOUND only).** This standard covers validating data that enters the application from outside. It is deliberately disjoint from the related surfaces:

- **Outbound** secure logging, secrets handling, and startup configuration validation live in [`java-security-patterns.md`](java-security-patterns.md) — do not duplicate that guidance here.
- **HTTP request sanitization** (path/parameter/header pipelines) is the `cui-http` skill's `de.cuioss.http.security` surface.
- **REST-resource validation** (`@Valid` on JAX-RS methods) is the `java-quarkus` skill's `quarkus-rest-validation.md` standard.

This standard is the generic, framework-agnostic inbound-validation home for everything else: deserialized payloads, file inputs, CLI arguments, and message-queue bodies.

## Required Dependency

Bean Validation needs an implementation on the classpath (Hibernate Validator is the reference implementation):

```xml
<dependency>
    <groupId>org.hibernate.validator</groupId>
    <artifactId>hibernate-validator</artifactId>
</dependency>
```

## Constraint Annotations

Annotate the fields of an inbound bean with `jakarta.validation.constraints`:

```java
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record ImportJob(
        @NotBlank @Size(max = 200) String source,
        @NotNull @Min(1) Integer batchSize,
        @Pattern(regexp = "[A-Z]{2}") String region,
        @Valid Destination destination) {  // @Valid cascades into the nested bean
}
```

## Programmatic Validation

Without a web framework, drive validation explicitly through a `Validator`. Build the factory once (it is expensive and thread-safe) and reuse it; iterate the returned `ConstraintViolation` set:

```java
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import java.util.Set;

// Build once, reuse — ValidatorFactory and Validator are thread-safe
ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
Validator validator = factory.getValidator();

Set<ConstraintViolation<ImportJob>> violations = validator.validate(job);
if (!violations.isEmpty()) {
    String detail = violations.stream()
        .map(v -> v.getPropertyPath() + " " + v.getMessage())
        .collect(java.util.stream.Collectors.joining("; "));
    throw new IllegalArgumentException("Invalid input: " + detail);
}
// job is guaranteed to satisfy every constraint past this point
```

**Normative rule:** validate externally-sourced data — deserialized payloads, file inputs, CLI arguments, message-queue bodies — at the trust boundary, before the data is used. Reject (do not silently coerce) on any constraint violation.

## Constraint Vocabulary

| Annotation | Enforces |
|------------|----------|
| `@NotNull` | Value is present |
| `@NotBlank` | String is non-null and contains non-whitespace |
| `@Size(min, max)` | Length / collection-size bounds |
| `@Pattern(regexp)` | String matches a regex |
| `@Min` / `@Max` | Numeric bounds |
| `@Valid` | Cascades validation into a nested bean |

Every cited annotation is a real `jakarta.validation` constraint — apply them to inbound beans and run the `Validator` at the boundary.
