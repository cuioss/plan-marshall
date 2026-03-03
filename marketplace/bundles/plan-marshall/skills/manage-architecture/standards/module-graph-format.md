# Module Graph Format

Output format for the `architecture graph` command. Returns module dependencies as a tree.

## Purpose

Provides a view of internal module dependencies for:
- Ordering deliverables in multi-module tasks
- Identifying dependency chains
- Detecting circular dependencies

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--full` | Include aggregator modules (pom-only parents with no source paths) |

By default, aggregator modules (pom packaging) are filtered out since they contain no code to implement.

### Filtering Logic

Modules are included in the default view if ANY of these conditions are true:
1. **Non-pom packaging**: jar, war, nar, etc.
2. **is_leaf flag**: Enriched data explicitly marks module as `is_leaf: true`
3. **Leaf purpose**: Enriched data has `purpose` in ["integration-tests", "deployment", "benchmark"]

This allows test modules with pom packaging (like e2e-playwright) to appear in the default view when they have the appropriate purpose set in llm-enriched.json.

## Output Format

### Single Module

For single-module projects, returns just the module name:

```
status: success

module: my-module
```

### Multi-Module (Dependency Tree)

For multi-module projects, shows each leaf module with its dependency tree:

```
status: success

oauth-sheriff-quarkus-deployment
  - oauth-sheriff-core
    - oauth-sheriff-api
  - oauth-sheriff-quarkus
    - oauth-sheriff-core
```

Aggregator modules (pom packaging) are filtered by default. Use `--full` to include them.

The tree shows what each module depends on:
- `oauth-sheriff-quarkus-deployment` depends on `oauth-sheriff-core` and `oauth-sheriff-quarkus`
- `oauth-sheriff-core` depends on `oauth-sheriff-api`
- `oauth-sheriff-quarkus` depends on `oauth-sheriff-core`

## Use Cases

### Ordering Deliverables

Read the tree bottom-up for execution order:
1. `oauth-sheriff-api` - no dependencies, execute first
2. `oauth-sheriff-core` - depends on api
3. `oauth-sheriff-quarkus` - depends on core
4. `oauth-sheriff-quarkus-deployment` - depends on quarkus and core

Modules at the same tree depth with no cross-dependencies can execute in parallel.

### Detecting Circular Dependencies

If circular dependencies exist:

```
status: success

module-a

warning: circular_dependencies_detected
circular_dependencies[2]:
  - module-b
  - module-c
```

## Error Handling

### Data Not Found

```
status: error
error: data_not_found
path: .plan/project-architecture/derived-data.json
message: Run 'architecture discover' first
```

## Related Documents

- [client-api.md](client-api.md) - Full command reference
- [architecture-persistence.md](architecture-persistence.md) - Data storage schema
