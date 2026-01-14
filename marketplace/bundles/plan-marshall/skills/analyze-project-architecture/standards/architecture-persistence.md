# Architecture Persistence

Storage format for project architecture data with separation of raw and derived data.

## Storage

**Location**: `.plan/project-architecture/`

```
.plan/project-architecture/
├── derived-data.json  # Extension API output (deterministic)
└── llm-enriched.json  # LLM-enriched fields
```

**Benefits of separation:**
- Raw data regenerated independently (re-run discovery)
- Derived data updated without expensive re-discovery
- Clear provenance (tooling vs LLM analysis)
- No field duplication

## derived-data.json

Direct output from `discover_project_modules()`. See [build-project-structure.md](../../extension-api/standards/build-project-structure.md) for full specification.

### Structure

```json
{
  "project": {
    "name": "oauth-sheriff"
  },
  "modules": {
    "oauth-sheriff-core": {
      "name": "oauth-sheriff-core",
      "build_systems": ["maven"],
      "paths": {
        "module": "oauth-sheriff-core",
        "descriptor": "oauth-sheriff-core/pom.xml",
        "sources": ["oauth-sheriff-core/src/main/java"],
        "tests": ["oauth-sheriff-core/src/test/java"],
        "readme": "oauth-sheriff-core/README.adoc"
      },
      "metadata": {
        "artifact_id": "oauth-sheriff-core",
        "group_id": "de.cuioss.sheriff.oauth",
        "packaging": "jar",
        "description": "Core OAuth Sheriff functionality",
        "profiles": [...]
      },
      "packages": {
        "de.cuioss.sheriff.oauth.core": {
          "path": "...",
          "package_info": "..."
        }
      },
      "dependencies": ["de.cuioss:cui-java-tools:compile", ...],
      "stats": {"source_files": 45, "test_files": 38},
      "commands": {
        "module-tests": "python3 ...",
        "verify": "python3 ...",
        "quality-gate": "python3 ..."
      }
    }
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Module name |
| `build_systems` | Array of build systems (e.g., `["maven"]`, `["maven", "npm"]`) |
| `paths` | Module paths (descriptor, sources, tests, readme) |
| `metadata` | Build-system specific metadata |
| `packages` | All packages with paths and package-info |
| `dependencies` | Full dependency list with scopes |
| `stats` | File counts |
| `commands` | Available build commands (see structure below) |

### Commands Structure

Commands can be stored in two formats:

**Single build system** (e.g., Maven-only or npm-only):
```json
{
  "commands": {
    "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module mod --targets test",
    "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module mod --targets verify"
  }
}
```

**Hybrid module** (multiple build systems like Maven + npm):
```json
{
  "commands": {
    "module-tests": {
      "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module mod --targets test",
      "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run --package mod --targets test"
    },
    "verify": {
      "maven": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module mod --targets verify",
      "npm": "python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run --package mod --targets build"
    }
  }
}
```

The `resolve` command in [client-api.md](client-api.md) handles both formats:
- Single build system: Returns single `executable` field
- Hybrid: Returns `executables` table with build_system and command columns

---

## llm-enriched.json

LLM-generated enrichments referencing modules by name.

### Structure

```json
{
  "project": {
    "description": "JWT validation library for Quarkus applications",
    "description_reasoning": "Derived from: root README.md first paragraph"
  },
  "modules": {
    "oauth-sheriff-core": {
      "responsibility": "Core JWT validation logic including claim extraction and signature verification",
      "responsibility_reasoning": "Derived from: README overview, ClaimValidator pattern",
      "purpose": "library",
      "purpose_reasoning": "packaging=jar, no runtime dependencies",
      "key_packages": {
        "de.cuioss.sheriff.oauth.core.pipeline": {
          "description": "JWT validation pipeline components",
          "components": ["ClaimValidator", "JwtPipeline", "ValidationResult"]
        }
      },
      "internal_dependencies": [],
      "key_dependencies": [
        "de.cuioss:cui-java-tools",
        "org.jspecify:jspecify"
      ],
      "key_dependencies_reasoning": "Foundation utilities and null-safety annotations",
      "skills_by_profile": {
        "implementation": [
          "pm-dev-java:java-core",
          "pm-dev-java:java-null-safety",
          "pm-dev-java:java-lombok"
        ],
        "module_testing": [
          "pm-dev-java:java-core",
          "pm-dev-java:junit-core"
        ]
      },
      "skills_by_profile_reasoning": "Plain Java library, no CDI/Quarkus runtime",
      "tips": [
        "Use @ApplicationScoped for singleton services",
        "Prefer constructor injection over field injection"
      ],
      "insights": [
        "Heavy validation happens in boundary layer",
        "Token caching improves performance 10x"
      ],
      "best_practices": [
        "Always validate tokens before extracting claims"
      ]
    }
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `responsibility` | Human-readable module description (1-2 sentences) |
| `responsibility_reasoning` | Sources used for derivation |
| `purpose` | Module classification (see values below) |
| `purpose_reasoning` | Analysis rationale |
| `key_packages` | Important packages with descriptions and components |
| `internal_dependencies` | Dependencies on other project modules |
| `key_dependencies` | Important external dependencies |
| `key_dependencies_reasoning` | Filtering rationale |
| `skills_by_profile` | Skills organized by execution profile (implementation, unit-testing, etc.) |
| `skills_by_profile_reasoning` | Selection and filtering rationale |
| `tips` | Implementation tips for working with the module |
| `insights` | Learned insights from implementation experience |
| `best_practices` | Established best practices for the module |

### Skills by Profile

The `skills_by_profile` field organizes skills by execution profile:

| Profile | Purpose |
|---------|---------|
| `implementation` | Skills for writing production code |
| `unit-testing` | Skills for writing unit tests |
| `integration-testing` | Skills for integration tests (if applicable) |
| `benchmark-testing` | Skills for performance tests (if applicable) |

Skills are derived from configured domain skill sets. Query available domains and their skills via:
```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config get-skills-by-profile --domain java
```

### Purpose Values

| Value | Description |
|-------|-------------|
| `library` | Reusable code, no runtime |
| `extension` | Framework plugin (Quarkus, NiFi) |
| `deployment` | Build-time processing |
| `runtime` | Application entry point |
| `parent` | Aggregator POM (packaging=pom at root) |
| `bom` | Bill of Materials |
| `integration-tests` | Integration test module |
| `benchmark` | Performance testing |

---

## Client API Mapping

The [client-api.md](client-api.md) merges both files for output:

| API Output | derived-data.json | llm-enriched.json |
|------------|-------------------|-------------------|
| `module` (default) | paths, commands | responsibility, purpose, key_packages, internal_dependencies, key_dependencies, skills_by_profile |
| `module --full` | + packages, dependencies | + reasoning fields |
| `info` | project.name | project.description |

---

## Field Summary

| Field | Source | Default Output | Full Output |
|-------|--------|----------------|-------------|
| `name` | derived | Yes | Yes |
| `build_systems` | derived | Yes | Yes |
| `paths` | derived | Yes | Yes |
| `metadata` | derived | Yes | Yes |
| `packages` | derived | No | Yes |
| `dependencies` | derived | No | Yes |
| `stats` | derived | Yes | Yes |
| `commands` | derived | Yes | Yes |
| `responsibility` | llm-enriched | Yes | Yes |
| `responsibility_reasoning` | llm-enriched | No | Yes |
| `purpose` | llm-enriched | Yes | Yes |
| `purpose_reasoning` | llm-enriched | No | Yes |
| `key_packages` | llm-enriched | Yes | Yes |
| `internal_dependencies` | llm-enriched | Yes | Yes |
| `key_dependencies` | llm-enriched | Yes | Yes |
| `key_dependencies_reasoning` | llm-enriched | No | Yes |
| `skills_by_profile` | llm-enriched | Yes | Yes |
| `skills_by_profile_reasoning` | llm-enriched | No | Yes |
| `tips` | llm-enriched | Yes | Yes |
| `insights` | llm-enriched | Yes | Yes |
| `best_practices` | llm-enriched | Yes | Yes |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [build-project-structure.md](../../extension-api/standards/build-project-structure.md) | Raw data field specification |
| [client-api.md](client-api.md) | API for reading merged data |
| [client-view.md](client-view.md) | What consumers need |
