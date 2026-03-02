# Integration Test Deliverables

When and how to create separate deliverables for integration tests.

---

## Core Principle

**One deliverable = one module.** Integration tests typically live in a dedicated IT module, so they become a separate deliverable.

---

## Decision Flow

```
1. Does task need IT?
   - Explicit request mentions "integration test", "IT", "E2E"
   - Change is external-facing (API, UI, public library API, config)

   → If NO: Skip IT deliverable

2. Does project have IT infrastructure?
   Run architecture modules --command integration-tests

   → If EMPTY: Skip IT deliverable (no IT module exists)

3. Create IT deliverable
   - Target: IT module from step 2
   - depends: implementation deliverable(s)
```

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests
```

Output format: `plan-marshall:analyze-project-architecture/standards/client-api.md`

---

## When IT is Needed

| Change Type | IT Needed? | Rationale |
|-------------|------------|-----------|
| API endpoint (REST, GraphQL) | **YES** | External contract |
| UI component | **YES** | User-facing behavior |
| Public library API | **YES** | Consumer contract |
| Configuration/properties | **YES** | Runtime behavior |
| Internal implementation | NO | No external impact |
| Refactoring (same behavior) | NO | Behavior unchanged |
| Private/internal classes | NO | Not externally visible |
| Utility/helper methods | NO | Internal tooling |

---

## IT Deliverable Format

Follows the deliverable contract.

```markdown
### {N}. Integration tests for {component}

**Metadata:**
- change_type: feature
- execution_mode: automated
- domain: {domain}
- module: {IT module from architecture}
- depends: {reference to implementation deliverable}

**Profiles:**
- implementation

**Affected files:**
- `{IT module}/src/test/java/{package path}/{ClassName}IT.java`

**Change per file:** {description of IT tests}

**Verification:**
- Command: {IT verification command}
- Criteria: All IT tests pass

**Success Criteria:**
- {IT acceptance criterion 1}
- {IT acceptance criterion 2}
```

---

## Key Points

1. **IT is always a separate deliverable** - not embedded in implementation deliverable
2. **IT targets the IT module** - found via `architecture modules --command integration-tests`
3. **IT depends on implementation** - set `depends:` to reference the implementation deliverable
4. **IT has only `implementation` profile** - IT code is "implementation" of test code (no unit tests for ITs)

---

## Finding IT Module

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests
```

**If modules list is empty**: Skip IT deliverable (no IT module exists).

---

## IT Module Patterns

Common IT module naming patterns:

| Pattern | Example |
|---------|---------|
| Dedicated IT module | `{project}-integration-tests` |
| IT submodule | `{parent}/integration-tests` |
| IT profile in main | `src/it/java/...` (Maven Failsafe) |

The architecture command abstracts these patterns - use it to find the correct module.

---

## IT Package Selection

Within the IT module, select package based on:

1. Mirror the production code package structure (add `.it` prefix or suffix)
2. Group by feature/component being tested
3. Follow existing IT package conventions in the project

**Pattern**:
- Production: `{base.package}.{ClassName}`
- IT: `{base.package}.it.{feature}.{ClassName}IT`

---

## IT Verification Commands

| Build System | IT Command |
|--------------|------------|
| Maven | `mvn verify -pl {it-module}` |
| Maven with profile | `mvn verify -Prun-its -pl {it-module}` |
| Gradle | `gradle integrationTest` |
| npm | `npm run test:e2e` |

Check the project's existing IT setup to use the correct command.
