# Maven Integration Standards for JavaScript

## Purpose

This document defines standards for integrating JavaScript tooling with Maven build processes using frontend-maven-plugin, ensuring consistent, reproducible builds across all CUI projects with proper Node.js management, dependency resolution, and quality gate enforcement.

## Frontend Maven Plugin Configuration

### Required Plugin Declaration

All JavaScript projects must use frontend-maven-plugin to manage Node.js installation and npm integration:

```xml
<plugin>
  <groupId>com.github.eirslett</groupId>
  <artifactId>frontend-maven-plugin</artifactId>
  <version>1.15.1</version>
  <configuration>
    <nodeVersion>v20.12.2</nodeVersion>
    <npmVersion>10.5.0</npmVersion>
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

### Configuration Parameters

**nodeVersion**: Node.js LTS version to install
- Required: Node.js `v20.12.2` LTS (exact version)
- Ensures consistent Node.js across all environments
- Downloaded automatically during build

**npmVersion**: npm version to use
- Always: `10.5.0` or compatible (see project-structure.md for version requirements)
- Bundled with Node.js installation
- Supports modern package.json features

**installDirectory**: Where to install Node.js
- Always: `target/` (Maven standard)
- Keeps Node.js installation local to project
- Excluded from version control via .gitignore

## Maven Phase Integration

### Required Phase Mapping

JavaScript tooling must integrate into specific Maven lifecycle phases:

| Phase | Execution | Tool | Purpose |
|-------|-----------|------|---------|
| validate | install-node-and-npm | Node.js installer | Install consistent Node.js/npm versions |
| validate | npm-install | npm | Install all JavaScript dependencies |
| generate-resources | npm-build (optional) | Webpack/bundler | Generate minified/bundled assets |
| compile | npm-format-check | Prettier | Enforce code formatting standards |
| compile | npm-lint | ESLint | Enforce code quality standards |
| test | npm-test | Jest | Run unit tests with coverage |

### Execution Order and Dependencies

Executions run in this order to ensure proper dependency resolution:

1. **validate phase**: install-node-and-npm → npm-install
2. **generate-resources phase**: npm-build (if applicable)
3. **compile phase**: npm-format-check → npm-lint
4. **test phase**: npm-test

**Why this order?**
- Node.js must be installed before npm commands
- Dependencies must be installed before running scripts
- Format checking before linting catches style issues first
- Testing happens after all quality checks pass

### Optional Build Execution

For projects generating bundled or minified JavaScript assets:

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

**When to include**:
- Projects with Webpack bundling
- Projects generating WebJars
- Projects with minification requirements
- Projects building distributable assets

**When to skip**:
- Simple JavaScript without bundling
- Development UI components loaded directly
- Projects using browser-native ES modules

## Node.js Version Management

### Standard Versions

**Node.js v20.12.2 LTS**:
- Long Term Support release for stability
- Consistent across all projects and environments
- Full ES module support
- Updated annually following Node.js LTS schedule

**npm 10.5.0+**:
- Bundled with Node.js installation
- Supports `"type": "module"` in package.json
- Compatible with modern dependency resolution
- Recognizes overrides field

### Installation Directory Strategy

**target/ directory** (recommended):
```xml
<configuration>
  <installDirectory>target</installDirectory>
</configuration>
```

**Benefits**:
- Maven standard location
- Automatically cleaned with `mvn clean`
- Excluded from version control
- No global environment pollution

**CI/CD optimization** (optional):
```xml
<configuration>
  <installDirectory>${user.home}/.m2/frontend</installDirectory>
</configuration>
```

**Benefits**:
- Cached across builds
- Faster CI/CD pipelines
- Reused for multiple projects

### Dependency Resolution Strategies

**Standard installation** (default):
```xml
<configuration>
  <arguments>install</arguments>
</configuration>
```

**Use for**: Modern projects without peer dependency conflicts

**Legacy peer dependencies** (when needed):
```xml
<configuration>
  <arguments>install --legacy-peer-deps</arguments>
</configuration>
```

**Use for**: Projects with unresolved peer dependency conflicts

**Performance optimized**:
```xml
<configuration>
  <arguments>install --prefer-offline --no-audit</arguments>
</configuration>
```

**Use for**: CI/CD environments where speed matters

## Script Integration

### Required npm Scripts

For complete npm script definitions and requirements, see **[project-structure.md](project-structure.md)** section "Required npm Scripts".

Maven executions call these npm scripts from package.json:

| npm Script | Called From | Purpose |
|------------|-------------|---------|
| `format:check` | npm-format-check | Verify code formatting without changes |
| `lint` | npm-lint | Check code quality without modifications |
| `test:ci-strict` | npm-test | Run tests with strict CI settings |
| `build` | npm-build (optional) | Generate production assets |

### Script Behavior Requirements

**format:check**:
- Read-only validation (no file modifications)
- Fails build if formatting is inconsistent
- Uses Prettier configuration from .prettierrc.js

**lint**:
- Read-only code quality checks
- Fails build on linting errors
- Uses ESLint configuration from eslint.config.js

**test:ci-strict**:
- Runs in CI mode (no watch, no interactive)
- Generates coverage reports
- Enforces coverage thresholds
- Limited parallelism for stability

**build**:
- Generates production-ready assets
- Outputs to target/classes/META-INF/resources/
- Minification and optimization enabled

## Environment Variables

### Standard Environment Configuration

Set consistent environment variables for builds:

```xml
<configuration>
  <environmentVariables>
    <CI>true</CI>
    <NODE_ENV>test</NODE_ENV>
  </environmentVariables>
  <arguments>run test:ci-strict</arguments>
</configuration>
```

### Environment Variable Purposes

**CI=true**:
- Disables interactive prompts
- Disables file watching
- Enables CI-specific behavior in tools
- Affects Jest, ESLint, and other tools

**NODE_ENV=test**:
- Sets Node.js environment for tests
- Used by test frameworks and libraries
- Enables test-specific configurations

**Additional variables** (optional):
```xml
<environmentVariables>
  <CI>true</CI>
  <NODE_ENV>test</NODE_ENV>
  <FORCE_COLOR>0</FORCE_COLOR>         <!-- Disable ANSI colors -->
  <NO_UPDATE_NOTIFIER>true</NO_UPDATE_NOTIFIER>  <!-- Disable update checks -->
</environmentVariables>
```

## SonarQube Integration

### Required Maven Properties

Configure SonarQube to analyze JavaScript code and coverage:

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

Ensure Jest outputs coverage in SonarQube-compatible format:

```json
{
  "jest": {
    "coverageDirectory": "target/coverage",
    "coverageReporters": [
      "text",
      "lcov",
      "html",
      "cobertura"
    ]
  }
}
```

**Reporter purposes**:
- `lcov` - SonarQube integration
- `text` - Console output during builds
- `html` - Local coverage visualization
- `cobertura` - CI/CD integration

### Coverage Path Alignment

**Jest configuration**: `coverageDirectory: "target/coverage"`

**SonarQube property**: `<sonar.javascript.lcov.reportPaths>target/coverage/lcov.info</sonar.javascript.lcov.reportPaths>`

**File location**: `target/coverage/lcov.info`

These paths must align for SonarQube to find coverage data.

## Build Environment Standards

### Reproducible Build Requirements

All builds must be reproducible across environments:

**Consistent Node.js**:
- frontend-maven-plugin installs same Node.js version everywhere
- No dependency on global Node.js installation
- Version specified in pom.xml

**Consistent dependencies**:
- package-lock.json committed to version control
- npm install produces identical dependency tree
- No reliance on global npm packages

**Consistent quality standards**:
- Same ESLint rules everywhere
- Same Prettier formatting everywhere
- Same test coverage thresholds everywhere

### CI/CD Integration

Configure CI/CD pipelines to use Maven as the entry point:

```bash
# Standard CI/CD build command
mvn clean verify

# Skip Java tests if JavaScript-only
mvn clean verify -DskipTests=false
```

**CI/CD requirements**:
- Set `CI=true` environment variable
- Use `test:ci-strict` script for strict enforcement
- Fail build on any quality gate violation
- Generate and publish coverage reports

### File Exclusions

For complete .gitignore patterns and explanations, see **[project-structure.md](project-structure.md)** section "Git Ignore Requirements".

**Maven-specific exclusions** to verify:
- `target/node/` - Maven-installed Node.js binaries (platform-specific)
- `target/classes/META-INF/resources/` - Maven-generated build outputs
- `target/dist/` - Webpack build outputs in Maven target directory

**IMPORTANT**: Do NOT exclude `package-lock.json`. For complete lock file requirements and rationale, see **[project-structure.md](project-structure.md)** section "Lock File Requirements"

## Project-Specific Adaptations

### Standard Maven Projects

Use project basedir as working directory:

```xml
<configuration>
  <workingDirectory>${project.basedir}</workingDirectory>
  <installDirectory>target</installDirectory>
</configuration>
```

**Structure**:
```
project-root/
├── pom.xml
├── package.json
├── src/main/resources/static/js/
└── target/
```

### Multi-Module Maven Projects

Configure working directory for frontend module:

```xml
<configuration>
  <workingDirectory>${project.basedir}/src/main/frontend</workingDirectory>
  <installDirectory>${project.basedir}/target</installDirectory>
</configuration>
```

**Structure**:
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

Use standard configuration with DevUI-specific paths in package.json:

```xml
<!-- No special Maven configuration needed -->
<configuration>
  <nodeVersion>v20.12.2</nodeVersion>
  <npmVersion>10.5.0</npmVersion>
  <installDirectory>target</installDirectory>
</configuration>
```

**package.json paths**:
```json
{
  "scripts": {
    "lint": "eslint src/main/resources/dev-ui/**/*.js"
  }
}
```

### NiFi Extension Projects

Add WebJar packaging for NiFi integration:

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

**package.json build script**:
```json
{
  "scripts": {
    "build:webjars": "webpack --config webpack.config.js --output-path target/classes/META-INF/resources/webjars"
  }
}
```

## Troubleshooting

### Node.js Installation Failures

**Symptom**: frontend-maven-plugin cannot download Node.js

**Common causes**:
- No internet connectivity
- Proxy configuration missing
- Insufficient disk space in target/
- Firewall blocking Node.js download

**Solutions**:
1. Check internet connection
2. Configure Maven proxy settings:
```xml
<settings>
  <proxies>
    <proxy>
      <host>proxy.example.com</host>
      <port>8080</port>
    </proxy>
  </proxies>
</settings>
```
3. Verify disk space: `df -h`
4. Try alternative Node.js mirror:
```xml
<configuration>
  <downloadRoot>https://nodejs.org/dist/</downloadRoot>
</configuration>
```

### npm Install Failures

**Symptom**: npm install fails during Maven build

**Solution**: See [dependency-management.md](dependency-management.md) "npm Install Failures" section for comprehensive troubleshooting steps including cache clearing, legacy peer deps configuration for Maven, and lock file regeneration.

### Test Failures in CI

**Symptom**: Tests pass locally but fail in CI

**Common causes**:
- Missing CI=true environment variable
- Watch mode enabled in CI
- Coverage thresholds not met
- Race conditions in tests

**Solutions**:

1. Ensure CI environment variable:
```xml
<environmentVariables>
  <CI>true</CI>
</environmentVariables>
```

2. Use CI-specific test script:
```json
{
  "scripts": {
    "test:ci-strict": "jest --ci --coverage --watchAll=false --maxWorkers=2"
  }
}
```

3. Check coverage thresholds:
```bash
npm run test:coverage
# Review coverage report in target/coverage/
```

4. Increase test timeouts:
```javascript
// jest.config.js
export default {
  testTimeout: 10000, // 10 seconds
};
```

### Format Check Failures

**Symptom**: Maven build fails on npm-format-check

**Cause**: Code not formatted according to Prettier rules

**Solutions**:

1. Run format locally:
```bash
npm run format
git add .
git commit -m "style: apply Prettier formatting"
```

2. Enable format-on-save in editor (VS Code):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

3. Add pre-commit hook:
```bash
npm install --save-dev husky lint-staged
npx husky install
npx husky add .husky/pre-commit "npx lint-staged"
```

### Linting Failures

**Symptom**: Maven build fails on npm-lint

**Cause**: ESLint errors or warnings

**Solutions**:

1. View linting errors:
```bash
npm run lint
```

2. Auto-fix where possible:
```bash
npm run lint:fix
```

3. Review unfixable issues manually

4. Consider adjusting rules if too strict:
```javascript
// eslint.config.js
export default [
  {
    rules: {
      'problematic-rule': 'warn', // Downgrade to warning
    }
  }
];
```

## Performance Optimization

### Cache Node.js Installation

Share Node.js installation across projects:

```xml
<configuration>
  <installDirectory>${user.home}/.m2/frontend</installDirectory>
</configuration>
```

**Benefits**:
- Faster builds (Node.js already installed)
- Reduced bandwidth usage
- Consistent version across projects

### Optimize npm Install

Use offline mode and skip audit:

```xml
<configuration>
  <arguments>install --prefer-offline --no-audit</arguments>
</configuration>
```

**Benefits**:
- Faster dependency installation
- Reduced network requests
- Skip security audit during install (run separately)

### Parallel Test Execution

Optimize Jest performance:

```json
{
  "scripts": {
    "test:ci-strict": "jest --ci --coverage --watchAll=false --maxWorkers=50%"
  }
}
```

**maxWorkers options**:
- `--maxWorkers=2` - Stable for CI (default)
- `--maxWorkers=50%` - Use half CPU cores
- `--maxWorkers=4` - Fixed worker count

## Build Validation

### Required Quality Gates

A successful Maven build must satisfy these requirements:

1. **Node.js installation**: Correct version installed in target/
2. **Dependency installation**: No critical npm warnings
3. **Formatting**: All JavaScript files properly formatted
4. **Linting**: All ESLint rules pass without errors
5. **Testing**: All tests pass with ≥80% coverage
6. **Security**: All critical/high vulnerabilities resolved
7. **Deprecations**: All deprecated package warnings addressed

### Validation Commands

Verify build quality manually:

```bash
# Complete build verification
mvn clean verify

# Check Node.js version
target/node/node --version

# Check npm dependencies
npm list

# Verify formatting
npm run format:check

# Verify linting
npm run lint

# Verify tests
npm run test:coverage

# Check security
npm audit
```

### Quality Gate Enforcement

Configure Maven to fail fast on quality issues:

```xml
<!-- Fail on format violations -->
<execution>
  <id>npm-format-check</id>
  <phase>compile</phase>
  <configuration>
    <arguments>run format:check</arguments>
    <failOnError>true</failOnError>
  </configuration>
</execution>

<!-- Fail on linting errors -->
<execution>
  <id>npm-lint</id>
  <phase>compile</phase>
  <configuration>
    <arguments>run lint</arguments>
    <failOnError>true</failOnError>
  </configuration>
</execution>

<!-- Fail on test failures -->
<execution>
  <id>npm-test</id>
  <phase>test</phase>
  <configuration>
    <arguments>run test:ci-strict</arguments>
    <failOnError>true</failOnError>
  </configuration>
</execution>
```

## Best Practices

1. **Use frontend-maven-plugin for Node.js** - Ensures consistent versions across environments
2. **Commit package-lock.json** - Reproducible dependency trees
3. **Set CI=true in test execution** - Disables watch mode and interactive prompts
4. **Map scripts to appropriate phases** - validate for setup, compile for checks, test for testing
5. **Use standard directory structure** - target/ for Node.js, node_modules/ gitignored
6. **Configure SonarQube integration** - Enable JavaScript coverage analysis
7. **Optimize for CI/CD** - Use --prefer-offline and cache Node.js installation
8. **Fail fast on quality issues** - Set failOnError=true for all quality executions
9. **Document project-specific configuration** - Note any deviations from standards
10. **Keep versions current** - Regularly update Node.js, npm, and frontend-maven-plugin

## Summary

Maven integration provides:
- **Consistent Node.js** across all environments through frontend-maven-plugin
- **Reproducible builds** with locked dependency versions
- **Quality enforcement** through Maven lifecycle phases
- **CI/CD integration** with proper environment configuration
- **SonarQube analysis** of JavaScript code and coverage
- **Project flexibility** supporting various project types

Key configuration points:
- Node.js and npm versions (see [project-structure.md](project-structure.md#node-js-version-requirements) for exact versions)
- Install directory: `target/` (or `~/.m2/frontend` for caching)
- Phase mapping: validate (install), compile (format/lint), test (tests)
- Environment variables: CI=true, NODE_ENV=test
- SonarQube coverage: target/coverage/lcov.info
