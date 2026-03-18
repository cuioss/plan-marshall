# Maven Integration Standards for JavaScript

Standards for integrating JavaScript tooling with Maven builds using frontend-maven-plugin across all CUI projects.

## Frontend Maven Plugin Configuration

### Required Plugin Declaration

```xml
<plugin>
  <groupId>com.github.eirslett</groupId>
  <artifactId>frontend-maven-plugin</artifactId>
  <version>2.0.0</version>
  <configuration>
    <nodeVersion>v22.22.1</nodeVersion>
    <npmVersion>11.7.0</npmVersion>
    <installDirectory>target</installDirectory>
  </configuration>
  <executions>
    <!-- Node.js installation -->
    <execution>
      <id>install-node-and-npm</id>
      <goals>
        <goal>install-node-and-npm</goal>
      </goals>
      <phase>validate</phase>
    </execution>

    <!-- npm dependencies installation -->
    <execution>
      <id>npm-install</id>
      <goals>
        <goal>npm</goal>
      </goals>
      <phase>validate</phase>
      <configuration>
        <arguments>install</arguments>
      </configuration>
    </execution>

    <!-- Format checking -->
    <execution>
      <id>npm-format-check</id>
      <goals>
        <goal>npm</goal>
      </goals>
      <phase>compile</phase>
      <configuration>
        <arguments>run format:check</arguments>
      </configuration>
    </execution>

    <!-- Code linting -->
    <execution>
      <id>npm-lint</id>
      <goals>
        <goal>npm</goal>
      </goals>
      <phase>compile</phase>
      <configuration>
        <arguments>run lint</arguments>
      </configuration>
    </execution>

    <!-- Unit testing -->
    <execution>
      <id>npm-test</id>
      <goals>
        <goal>npm</goal>
      </goals>
      <phase>test</phase>
      <configuration>
        <environmentVariables>
          <CI>true</CI>
          <NODE_ENV>test</NODE_ENV>
        </environmentVariables>
        <arguments>run test:ci-strict</arguments>
      </configuration>
    </execution>
  </executions>
</plugin>
```

### Node.js and npm Versions

- **Node.js**: `v22.22.1` LTS (exact version, installed automatically)
- **npm**: `11.7.0+` (see [project-structure.md](project-structure.md) for version requirements)
- **installDirectory**: `target/` -- cleaned with `mvn clean`, no global pollution

## Maven Phase Integration

| Phase | Execution | Tool | Purpose |
|-------|-----------|------|---------|
| validate | install-node-and-npm | Node.js installer | Install consistent Node.js/npm versions |
| validate | npm-install | npm | Install all JavaScript dependencies |
| generate-resources | npm-build (optional) | Webpack/bundler | Generate minified/bundled assets |
| compile | npm-format-check | Prettier | Enforce code formatting standards |
| compile | npm-lint | ESLint | Enforce code quality standards |
| test | npm-test | Jest | Run unit tests with coverage |

### Optional Build Execution

For projects with Webpack bundling, WebJar generation, or minification:

```xml
<execution>
  <id>npm-build</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>generate-resources</phase>
  <configuration>
    <arguments>run build</arguments>
  </configuration>
</execution>
```

Skip for simple JavaScript without bundling or projects using browser-native ES modules.

## Script Integration

Maven executions call these npm scripts from package.json. See **[project-structure.md](project-structure.md)** "Required npm Scripts" for full definitions.

| npm Script | Called From | Purpose |
|------------|-------------|---------|
| `format:check` | npm-format-check | Verify code formatting (read-only) |
| `lint` | npm-lint | Check code quality (read-only) |
| `test:ci-strict` | npm-test | Run tests with strict CI settings and coverage |
| `build` | npm-build (optional) | Generate production assets |

## Environment Variables

```xml
<environmentVariables>
  <CI>true</CI>                              <!-- Disable watch/interactive mode -->
  <NODE_ENV>test</NODE_ENV>                  <!-- Test-specific configuration -->
  <FORCE_COLOR>0</FORCE_COLOR>              <!-- Optional: disable ANSI colors -->
  <NO_UPDATE_NOTIFIER>true</NO_UPDATE_NOTIFIER>  <!-- Optional: disable update checks -->
</environmentVariables>
```

## SonarQube Integration

### Required Maven Properties

```xml
<properties>
  <!-- JavaScript source and test paths -->
  <sonar.sources>src/main/resources/static/js,src/main/resources/dev-ui</sonar.sources>
  <sonar.tests>src/test/js</sonar.tests>

  <!-- Coverage reporting -->
  <sonar.javascript.lcov.reportPaths>target/coverage/lcov.info</sonar.javascript.lcov.reportPaths>

  <!-- File patterns -->
  <sonar.javascript.file.suffixes>.js</sonar.javascript.file.suffixes>

  <!-- Coverage exclusions -->
  <sonar.coverage.exclusions>
    **/*.test.js,
    **/test/**/*,
    **/mocks/**/*,
    **/jest.setup*.js
  </sonar.coverage.exclusions>

  <!-- Coverage thresholds -->
  <sonar.javascript.coverage.overall_condition.branch>80</sonar.javascript.coverage.overall_condition.branch>
  <sonar.javascript.coverage.new_condition.branch>80</sonar.javascript.coverage.new_condition.branch>
</properties>
```

### Jest Coverage Configuration

Ensure Jest outputs in SonarQube-compatible format. The `coverageDirectory` must align with `sonar.javascript.lcov.reportPaths`.

```json
{
  "jest": {
    "coverageDirectory": "target/coverage",
    "coverageReporters": ["text", "lcov", "html", "cobertura"]
  }
}
```

## Dependency Resolution Strategies

**Standard** (default):
```xml
<arguments>install</arguments>
```

**Legacy peer dependencies** (when peer conflicts exist):
```xml
<arguments>install --legacy-peer-deps</arguments>
```

**CI/CD optimized**:
```xml
<arguments>install --prefer-offline --no-audit</arguments>
```

### CI/CD Caching

Share Node.js installation across builds by using a persistent directory:

```xml
<configuration>
  <installDirectory>${user.home}/.m2/frontend</installDirectory>
</configuration>
```

## Project-Type Adaptations

### Standard Maven Projects

```xml
<configuration>
  <workingDirectory>${project.basedir}</workingDirectory>
  <installDirectory>target</installDirectory>
</configuration>
```

### Multi-Module Maven Projects

```xml
<configuration>
  <workingDirectory>${project.basedir}/src/main/frontend</workingDirectory>
  <installDirectory>${project.basedir}/target</installDirectory>
</configuration>
```

Structure:
```
parent-project/
├── pom.xml
├── backend-module/
└── frontend-module/
    ├── pom.xml
    ├── src/main/frontend/
    │   └── package.json
    └── target/
```

### Quarkus DevUI Projects

Standard plugin configuration; DevUI-specific paths go in package.json:

```json
{
  "scripts": {
    "lint": "eslint src/main/resources/dev-ui/**/*.js"
  }
}
```

### NiFi Extension Projects

Add WebJar packaging execution:

```xml
<execution>
  <id>npm-build-webjars</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>generate-resources</phase>
  <configuration>
    <arguments>run build:webjars</arguments>
  </configuration>
</execution>
```

```json
{
  "scripts": {
    "build:webjars": "webpack --config webpack.config.js --output-path target/classes/META-INF/resources/webjars"
  }
}
```

## Troubleshooting

### Node.js Installation Failures

If frontend-maven-plugin cannot download Node.js, check proxy settings and try an alternative mirror:

```xml
<configuration>
  <downloadRoot>https://nodejs.org/dist/</downloadRoot>
</configuration>
```

### npm Install Failures

See [dependency-management.md](dependency-management.md) "npm Install Failures" for cache clearing, legacy peer deps, and lock file regeneration.

### Test Failures in CI

- Verify `CI=true` is set in `<environmentVariables>`
- Use `test:ci-strict` script (disables watch mode, limits workers)
- Check coverage thresholds in `target/coverage/`
- Increase `testTimeout` in jest.config.js if timing out

### Format/Lint Failures

- Run `npm run format` then commit to fix formatting
- Run `npm run lint:fix` for auto-fixable lint issues
- Review remaining issues manually

## File Exclusions

Maven-specific entries for .gitignore (see [project-structure.md](project-structure.md) for full patterns):

- `target/node/` -- Maven-installed Node.js binaries
- `target/classes/META-INF/resources/` -- generated build outputs
- `target/dist/` -- Webpack outputs

Do **not** exclude `package-lock.json`. See [project-structure.md](project-structure.md) "Lock File Requirements".
