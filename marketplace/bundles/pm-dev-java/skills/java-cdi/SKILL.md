---
name: java-cdi
description: Core CDI patterns including constructor injection, scopes, producers, events, observers, and interceptors
user-invocable: false
---

# Java CDI Skill

Core CDI (Contexts and Dependency Injection) standards applicable to any CDI container. Covers dependency injection patterns, scopes, producer methods, events/observers, and interceptors.

## Prerequisites

This skill applies to Jakarta CDI projects:
- `jakarta.inject:jakarta.inject-api`
- `jakarta.enterprise:jakarta.enterprise.cdi-api`

## Required Imports

```java
// CDI Core
import jakarta.inject.Inject;
import jakarta.inject.Named;
import jakarta.inject.Singleton;

// CDI Scopes
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.context.RequestScoped;
import jakarta.enterprise.context.SessionScoped;
import jakarta.enterprise.context.Dependent;

// CDI Producers and Optional Dependencies
import jakarta.enterprise.inject.Produces;
import jakarta.enterprise.inject.Instance;

// CDI Events
import jakarta.enterprise.event.Event;
import jakarta.enterprise.event.Observes;
import jakarta.enterprise.event.ObservesAsync;

// CDI Interceptors
import jakarta.interceptor.AroundInvoke;
import jakarta.interceptor.Interceptor;
import jakarta.interceptor.InterceptorBinding;
import jakarta.interceptor.InvocationContext;

// Quarkus Configuration
import org.eclipse.microprofile.config.inject.ConfigProperty;
```

## References

* [Jakarta CDI 4.1 Specification](https://jakarta.ee/specifications/cdi/4.1/)
* [Jakarta EE CDI Tutorial](https://jakarta.ee/learn/docs/jakartaee-tutorial/current/cdi/cdi-basic/cdi-basic.html)
* [Quarkus CDI Guide](https://quarkus.io/guides/cdi)

## Standards

- `standards/basic.md` — Injection, scopes, scope mismatch rule, optional dependencies, producers, error handling
- `standards/advanced.md` — Events, observers, interceptors

## Templates

- `templates/cdi-bean.java.tmpl` — ApplicationScoped bean with constructor injection and Instance<T> for optional dependencies
- `templates/cdi-producer.java.tmpl` — Producer method with Null Object pattern (never returns null)

## Quality Rules

- Constructor injection used (never field/setter injection)
- Final fields for all injected dependencies
- Single constructor (no `@Inject` needed) or `@Inject` on injection constructor
- Appropriate scope selected for each bean
- Never inject shorter-lived scopes into longer-lived beans — use `Instance<T>`
- `Instance<T>` used for optional dependencies (not `Provider<T>`)
- Producer methods never return null
- Event payloads are immutable records
- Interceptors declare `@Priority` for deterministic ordering

## Related Skills

- `pm-dev-java:java-quarkus` — Quarkus-specific CDI patterns, container/Docker config, security
- `pm-dev-java:java-core` — Core Java patterns
- `pm-dev-java:junit-core` — CDI testing patterns
