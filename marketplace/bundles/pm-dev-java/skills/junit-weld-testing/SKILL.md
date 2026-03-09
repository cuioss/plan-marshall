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
- Injection patterns in test classes
- Common pitfalls and troubleshooting
