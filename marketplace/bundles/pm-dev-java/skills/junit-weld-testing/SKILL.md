---
name: junit-weld-testing
description: Weld Testing standards for CDI unit testing with @EnableAutoWeld, @AddBeanClasses, and auto-discovery patterns
user-invocable: false
---

# JUnit Weld Testing Skill

**REFERENCE MODE**: This skill provides reference material. Load specific standards on-demand based on current task.

Standards for CDI unit testing using [weld-testing](https://github.com/weld/weld-testing). This skill covers auto-weld configuration, bean class management, and CDI test patterns using JUnit 5.

## Prerequisites

This skill applies to Java projects using Weld Testing with JUnit 5:
- `org.jboss.weld:weld-junit5` (Weld JUnit 5 extension)
- `org.jboss.weld:weld-junit-parent` (parent module)

## Maven Dependencies

```xml
<dependency>
    <groupId>org.jboss.weld</groupId>
    <artifactId>weld-junit5</artifactId>
    <scope>test</scope>
</dependency>
```

## Workflow

### Step 1: Load Weld Testing Standards

**Important**: Load this standard for any CDI unit testing work with Weld.

```
Read: standards/weld-testing-autowired.md
```

This provides rules for:
- `@EnableAutoWeld` annotation and auto-discovery
- `@AddBeanClasses` / `@AddPackages` for explicit bean registration
- `@ActivateScopes` for scope management in tests
- `@ExcludeBeanClasses` for swapping implementations with test doubles
- `@EnableWeld` with `WeldInitiator` for manual control
- Injection patterns in test classes
- Common pitfalls and troubleshooting

## Quick Reference

### Annotation Decision Guide

| Scenario | Annotation | Example |
|----------|-----------|---------|
| Simple service test | `@EnableAutoWeld` | Auto-discovers injected beans |
| Need producers/interceptors | `+ @AddBeanClasses` | Beans not directly injected |
| Many beans from one package | `+ @AddPackages` | Package-level registration |
| Replace with test double | `+ @ExcludeBeanClasses` + `@AddBeanClasses` | Swap real for mock |
| Scoped beans (Request, Session) | `+ @ActivateScopes` | Scope not active by default |
| Full manual control | `@EnableWeld` + `@WeldSetup` | WeldInitiator configuration |

### Common Error Quick Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `UnsatisfiedResolutionException` | Bean not discovered | Add via `@AddBeanClasses` |
| `ContextNotActiveException` | Missing scope activation | Add `@ActivateScopes` |
| `AmbiguousResolutionException` | Multiple implementations | Use `@ExcludeBeanClasses` |
| Test passes alone, fails in suite | Shared static state | Ensure proper scoping |

## Templates

**CDI test class** — starting point for new Weld-based test classes:
```
Read: templates/cdi-test-class.java.tmpl
```

Replace `${PACKAGE}`, `${CLASS_UNDER_TEST}`, `${METHOD_1}`, and placeholder comments. Uncomment `@AddBeanClasses` or `@ActivateScopes` as needed.

## Related Skills

- `pm-dev-java:java-cdi` - CDI patterns (injection, scopes, producers, events)
- `pm-dev-java:junit-core` - JUnit 5 core testing patterns
- `pm-dev-java:java-quarkus` - Quarkus-specific testing with `@QuarkusTest`
