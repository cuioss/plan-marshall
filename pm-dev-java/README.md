# Java Expert

Comprehensive Java development expertise bundle providing domain knowledge skills for standards-compliant implementation, testing, and verification.

## Purpose

This bundle provides a complete Java development knowledge base. Skills contain all domain knowledge and standards. Verification and compliance checking flow through the skill-based plan-marshall extension API — the bundle ships no agents.

## Architecture

```
pm-dev-java/
└── skills/                  # 15 domain knowledge skills
    ├── java-core/           # Core Java patterns, modern features
    ├── java-null-safety/    # JSpecify null annotations
    ├── java-lombok/         # Lombok patterns (@Delegate, @Builder)
    ├── java-security/       # Java security standards
    ├── junit-core/          # JUnit 5 testing, AAA structure
    ├── junit-integration/   # Integration testing with Failsafe
    ├── junit-weld-testing/  # CDI unit testing with Weld
    ├── java-cdi/            # Core CDI patterns, constructor injection
    ├── java-quarkus/        # Quarkus-specific CDI, @QuarkusTest
    ├── javadoc/             # JavaDoc documentation standards
    ├── java-maintenance/    # Maintenance prioritization
    ├── arch-gate-java/      # Architectural fitness gate (thin pointer)
    ├── ext-triage-java/     # Triage extension point
    ├── manage-maven-profiles/ # Maven profile classification
    └── plan-marshall-plugin/  # Build system integration
```

## Components

### Skills (15 skills)

**Core Development:**
- **java-core** - Core Java patterns, modern features, performance
- **java-null-safety** - JSpecify null annotations, @Nullable/@NonNull
- **java-lombok** - Lombok patterns (@Delegate, @Builder, @Value)
- **java-security** - Java security standards

**Testing:**
- **junit-core** - JUnit 5 patterns, AAA structure, assertions
- **junit-integration** - Integration testing with Maven Failsafe
- **junit-weld-testing** - CDI unit testing with Weld

**CDI/Quarkus:**
- **java-cdi** - Core CDI patterns, constructor injection, scopes
- **java-quarkus** - Quarkus-specific CDI, @QuarkusTest, native image

**Documentation & Maintenance:**
- **javadoc** - JavaDoc documentation standards
- **java-maintenance** - Maintenance prioritization, refactoring triggers

**Infrastructure:**
- **arch-gate-java** - Architectural fitness gate (thin pointer to `plan-marshall:manage-architecture`)
- **ext-triage-java** - Extension point for Java finding triage
- **manage-maven-profiles** - Maven build profile classification
- **plan-marshall-plugin** - Core build system integration (Maven/Gradle)

> **Note**: Library-specific patterns (CuiLogger, LogRecord, test generators) are in the separate `pm-dev-java-cui` bundle.
>
> **Planning Integration**: Java domain skills are loaded by plan-marshall task executors during plan execution via `task.skills` array.

## Dependencies

- **builder-maven** - For Maven build operations
- Python 3 for automation scripts

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-java/
