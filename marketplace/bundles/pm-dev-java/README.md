# CUI Java Expert

Comprehensive Java development expertise bundle providing domain knowledge skills for standards-compliant implementation, testing, and verification.

## Purpose

This bundle provides a complete Java development knowledge base. Skills contain all domain knowledge and standards. Verification agents provide autonomous compliance checking via the plan-marshall extension API.

## Architecture

```
pm-dev-java/
├── agents/                  # 2 verification agents
│   ├── java-coverage-agent.md       # Analyze coverage (read-only)
│   └── java-verify-agent.md         # Verify compliance (read-only)
└── skills/                  # 12 domain knowledge skills
    ├── java-core/           # Core Java patterns, modern features
    ├── java-null-safety/    # JSpecify null annotations
    ├── java-lombok/         # Lombok patterns (@Delegate, @Builder)
    ├── junit-core/          # JUnit 5 testing, AAA structure
    ├── junit-integration/   # Integration testing with Failsafe
    ├── java-cdi/            # Core CDI patterns, constructor injection
    ├── java-quarkus/        # Quarkus-specific CDI, @QuarkusTest
    ├── javadoc/             # JavaDoc documentation standards
    ├── java-maintenance/    # Maintenance prioritization
    ├── ext-triage-java/     # Triage extension point
    ├── manage-maven-profiles/ # Maven profile classification
    └── plan-marshall-plugin/  # Build system integration
```

## Components

### Skills (12 skills)

**Core Development:**
- **java-core** - Core Java patterns, modern features, performance
- **java-null-safety** - JSpecify null annotations, @Nullable/@NonNull
- **java-lombok** - Lombok patterns (@Delegate, @Builder, @Value)

**Testing:**
- **junit-core** - JUnit 5 patterns, AAA structure, assertions
- **junit-integration** - Integration testing with Maven Failsafe

**CDI/Quarkus:**
- **java-cdi** - Core CDI patterns, constructor injection, scopes
- **java-quarkus** - Quarkus-specific CDI, @QuarkusTest, native image

**Documentation & Maintenance:**
- **javadoc** - JavaDoc documentation standards
- **java-maintenance** - Maintenance prioritization, refactoring triggers

**Infrastructure:**
- **ext-triage-java** - Extension point for Java finding triage
- **manage-maven-profiles** - Maven build profile classification
- **plan-marshall-plugin** - Core build system integration (Maven/Gradle)

> **Note**: CUI library-specific patterns (CuiLogger, LogRecord, test generators) are in the separate `pm-dev-java-cui` bundle.
>
> **Planning Integration**: Java domain skills are loaded by plan-marshall task executors during plan execution via `task.skills` array.

### Agents (2 verification agents)

**Analysis Agents** (read-only, used by `extension.py:provides_verify_steps()`):
- **java-coverage-agent** - Coverage analysis
- **java-verify-agent** - Standards verification

## Bundle Statistics

- **Agents**: 2 (verification)
- **Skills**: 12 (domain knowledge, testing, CDI, documentation)
- **Scripts**: 3+ (Python automation)

## Dependencies

- **builder-maven** - For Maven build operations
- Python 3 for automation scripts

## Support

- Repository: https://github.com/cuioss/plan-marshall
- Bundle: marketplace/bundles/pm-dev-java/
