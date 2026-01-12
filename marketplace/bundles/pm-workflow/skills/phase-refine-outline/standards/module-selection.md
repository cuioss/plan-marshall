# Module Selection

Advanced guidance for module selection and package placement. Use this standard when SKILL.md's scoring table and decision matrix need deeper context.

---

## Package Placement Details

### key_packages as Semantic Anchors

Architecture provides curated `key_packages` with descriptions. Use these as primary placement targets:

| key_package Pattern | Typical Role |
|---------------------|--------------|
| `...core.pipeline` | Main processing logic |
| `...core.model` | Domain/data classes |
| `...core.util` | Shared utilities |
| `...api` | Public interfaces |
| `...internal` | Implementation details |

### packages vs key_packages

| Attribute | key_packages | packages |
|-----------|--------------|----------|
| Curated | Yes (architecture analysis) | No (all packages) |
| has_package_info | Always true | May be false |
| Use for | Primary placement | Fallback/exploration |

### Placement Validation

Before finalizing package selection:

- [ ] New class follows existing naming patterns (e.g., `*Validator`, `*Handler`)
- [ ] Package aligns with module's responsibility scope
- [ ] Prefer packages with `has_package_info: true` (better documented)

---

## Complex Task Decomposition

For multi-module tasks, decompose BEFORE selecting modules.

### Decomposition Process

1. Identify distinct functional areas in the request
2. Map each area to a module based on responsibility
3. Use `internal_dependencies` from architecture to order deliverables

### Decomposition Pattern

```
**Task**: {multi-module task description}

**Decomposition**:
1. {functional area 1} → {module-1}
2. {functional area 2} → {module-2} (depends on 1)
3. {functional area 3} → {module-3} (depends on 1)

**Dependency Graph** (from architecture):
{module-2}
    ↓
{module-1}
    ↓
{module-3}

**Deliverable Order** (reverse of dependency):
1. {module-3} changes (base layer)
2. {module-1} changes (depends on base)
3. {module-2} changes (depends on core)
```

### Why Reverse Order?

Deliverables are ordered so that dependencies are implemented BEFORE dependents:
- Base modules first (no dependencies)
- Then modules that depend on base
- Finally top-level modules

This ensures each deliverable can be verified independently.
