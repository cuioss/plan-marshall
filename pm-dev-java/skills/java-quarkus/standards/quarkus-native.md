# Quarkus Native Optimization Process

Systematic process for optimizing Quarkus applications for native image compilation. For reflection registration rules and patterns, see `quarkus-reflection.md`.

## Pre-Optimization Checklist

1. Ensure application builds and tests pass: `./mvnw clean install`
2. Verify native compilation works: `./mvnw clean package -Dnative`
3. Record baseline metrics (build time, image size, startup time)
4. Create dedicated branch: `git checkout -b native-optimization-[feature-name]`

## Optimization Workflow

### Phase 1: Analysis

Scan the codebase for reflection usage and categorize by need:

```bash
# Find all @RegisterForReflection usage
find . -name "*.java" -exec grep -l "@RegisterForReflection" {} \;

# Find deployment processor registrations
find . -name "*Processor.java" -exec grep -l "ReflectiveClassBuildItem" {} \;
```

Categorize classes by reflection requirements:
- **CDI beans**: Usually auto-registered — check for redundant `@RegisterForReflection` (see decision matrix in `quarkus-reflection.md`)
- **DTOs/Records**: Need explicit registration for JSON serialization
- **Configuration classes**: Assess builder pattern vs property binding
- **Enums**: Minimal reflection (`methods = false, fields = false`)

### Phase 2: Implementation

Apply optimizations following the registration rules in `quarkus-reflection.md`:

1. **Remove redundant registrations** — CDI beans, health checks, qualifiers don't need `@RegisterForReflection`
2. **Narrow reflection scope** — Use fine-grained `methods`/`fields`/`constructors` parameters
3. **Replace string constants** with type-safe class references
4. **Use `AdditionalBeanBuildItem`** for CDI beans instead of reflection registration
5. **Group related classes** in separate `@BuildStep` methods by reflection requirements

Verify after each change:
```bash
./mvnw clean compile -pl [module-name]
./mvnw clean install -pl [module-name]
```

### Phase 3: Verification

1. Run full test suite
2. Build native image: `./mvnw clean package -Dnative`
3. Compare metrics against baseline:
   - Native image size (target 10–20% reduction)
   - Build time (target 5–15% improvement)
   - Startup time (maintain or improve)
4. Run quality checks: `./mvnw -Ppre-commit clean verify -DskipTests -pl [module-name]`

## Risk Assessment

**Low Risk** — Classes you own with no framework interaction:
- Simple domain objects/DTOs, utility classes, value objects (records)

**Medium Risk** — Classes with framework annotations but standard patterns:
- CDI beans with standard injection, JAX-RS resources, simple Jackson/JSON-B classes

**High Risk** — Classes implementing framework SPIs or advanced features:
- Quarkus/CDI SPIs, runtime proxy generation (interceptors, decorators), third-party library classes

## Module-by-Module Strategy

For large projects:
1. Extension modules (deployment processors) first
2. Application modules (core classes) second
3. Integration testing (full native testing) last

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Native compilation failure | Missing reflection registration | Check decision matrix in `quarkus-reflection.md` |
| Runtime `ClassNotFoundException` | DTO/record missing registration | Add `@RegisterForReflection` |
| Runtime method not found | Scope too narrow | Add `methods = true` or `fields = true` |
| Image size regression | Over-registration | Narrow scope or remove redundant registrations |

If optimization causes issues: revert, isolate the problematic change, and apply incrementally.

## References

* [Quarkus Native Applications Guide](https://quarkus.io/guides/writing-native-applications-tips)
