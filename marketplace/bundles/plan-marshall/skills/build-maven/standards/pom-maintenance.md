# POM Maintenance Standards

Pure reference for POM structure, dependency management, and quality requirements.

---

## BOM (Bill of Materials) Standards

### Structure Requirements

**Mandatory elements for BOM POMs:**
- `<packaging>pom</packaging>`
- All versions in `<dependencyManagement>` section
- No `<dependencies>` section (BOMs don't declare direct dependencies)
- Property-based versions for all artifacts

### Usage Rules

**If project provides a BOM:**
1. ALL modules MUST import or inherit from the BOM
2. ALL dependency management MUST reside in the BOM
3. Child modules MUST NOT override BOM-defined versions
4. BOM is the single source of truth for versions

### Implementation Pattern

```xml
<!-- BOM POM -->
<properties>
    <version.quarkus>3.5.0</version.quarkus>
    <version.cui.test.generator>2.4.0</version.cui.test.generator>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>io.quarkus</groupId>
            <artifactId>quarkus-bom</artifactId>
            <version>${version.quarkus}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

```xml
<!-- Consuming module -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>de.cuioss</groupId>
            <artifactId>cui-project-bom</artifactId>
            <version>${project.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

---

## Property Naming Conventions

### Version Properties

```xml
<properties>
    <!-- Project version -->
    <revision>1.0.0-SNAPSHOT</revision>

    <!-- CUI dependency versions: version.cui.* -->
    <version.cui.core.ui.model>2.3.0</version.cui.core.ui.model>
    <version.cui.java.tools>2.5.1</version.cui.java.tools>

    <!-- External dependency versions: version.* -->
    <version.quarkus>3.5.0</version.quarkus>
    <version.junit.jupiter>5.9.3</version.junit.jupiter>
    <version.lombok>1.18.38</version.lombok>

    <!-- Maven plugin versions: maven.*.plugin.version -->
    <maven.compiler.plugin.version>3.14.0</maven.compiler.plugin.version>
    <maven.surefire.plugin.version>3.5.3</maven.surefire.plugin.version>

    <!-- Non-maven plugin versions: *.maven.plugin.version -->
    <jacoco.maven.plugin.version>0.8.13</jacoco.maven.plugin.version>
    <lombok-maven-plugin.version>1.18.20.0</lombok-maven-plugin.version>

    <!-- Configuration properties -->
    <maven.compiler.source>21</maven.compiler.source>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
</properties>
```

---

## Dependency Management Standards

### General Rules

1. ALL versions MUST use properties (no hardcoded versions)
2. ALL versions MUST be in `<dependencyManagement>` or inherited from BOM
3. ALWAYS check parent/imported BOMs before adding new version properties
4. Version updates are handled by Dependabot - focus on structure only

### Aggregation Criteria

| Condition | Action |
|-----------|--------|
| ALL sub-modules use dependency | Move to parent `<dependencies>` |
| SOME sub-modules use dependency | Keep in individual modules |
| Dependency unused | Remove after verification |

### Verification Command

```bash
./mvnw dependency:analyze
```

Reports:
- Used undeclared dependencies (add explicit declaration)
- Unused declared dependencies (consider removal)

---

## Scope Assignment Rules

### Scope Definitions

| Scope | Compilation | Runtime | Test | Use Case |
|-------|-------------|---------|------|----------|
| `compile` | Yes | Yes | Yes | Default, required everywhere |
| `provided` | Yes | No | Yes | Container-provided (servlet-api, lombok) |
| `runtime` | No | Yes | Yes | Runtime-only (JDBC drivers) |
| `test` | No | No | Yes | Test code only |
| `import` | - | - | - | BOM imports in dependencyManagement |
| `system` | Yes | Yes | Yes | **AVOID** - indicates design problem |

### Scope Optimization Questions

For each dependency:
1. **compile -> provided**: Is this provided by runtime container?
2. **compile -> runtime**: Is this only needed at runtime?
3. **compile -> test**: Is this only used in test code?
4. **provided -> test**: Is this provided dependency only for tests?

---

## Multi-Module Standards

### Parent POM Rules

- Universal dependencies in parent `<dependencies>`
- Version control in `<dependencyManagement>` only
- Plugin versions in `<pluginManagement>`
- Clear separation: aggregation vs inheritance

### Inter-Module Dependencies

- Use `${project.version}` for internal dependencies
- Let Maven Reactor determine build order
- Explicitly declare all direct dependencies

---

## Quality Criteria

### Mandatory Checks

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Build | `./mvnw clean install` | SUCCESS |
| Dependencies | `./mvnw dependency:analyze` | No warnings |
| Enforcer | `./mvnw enforcer:enforce` | No violations |
| OpenRewrite | `./mvnw -Prewrite-maven-clean rewrite:run` | No changes needed |

### Prohibited Patterns

- Hardcoded versions (use properties)
- System scope dependencies
- Version overrides in child modules (when BOM exists)
- Unused dependencies
- Undeclared direct dependencies

---

## Best Practices Summary

| Do | Don't |
|----|-------|
| Use properties for ALL versions | Hardcode versions |
| Check BOM before adding versions | Duplicate version definitions |
| Use appropriate scopes | Default everything to compile |
| Verify after scope changes | Change scopes without testing |
| Let Dependabot handle updates | Manually update versions |
