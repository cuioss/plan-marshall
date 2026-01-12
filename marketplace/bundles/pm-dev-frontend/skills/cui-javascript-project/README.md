# JavaScript Project Structure and Build Standards Skill

## Overview

This skill provides comprehensive standards for JavaScript project setup, structure, dependency management, and Maven integration in CUI projects. It ensures consistent project organization, reproducible builds, and proper integration with Maven build pipelines across all JavaScript projects.

## What This Skill Provides

### Project Structure Standards
- Standard directory layouts for Maven, Quarkus DevUI, NiFi, and standalone projects
- File naming conventions (kebab-case, framework-specific prefixes)
- package.json configuration with required fields and npm scripts
- Configuration file locations and naming standards
- Git ignore requirements for Node.js and Maven artifacts

### Dependency Management
- Semantic versioning strategies (caret ranges vs exact versions)
- Security management with vulnerability scanning and response timeframes
- Deprecated package identification and replacement strategies
- Dependency conflict resolution (npm overrides, --legacy-peer-deps)
- ES module configuration ("type": "module", configuration syntax)
- Regular update schedules and breaking change management

### Maven Integration
- Frontend Maven Plugin configuration for Node.js management
- Maven phase integration (validate, compile, test)
- npm script mapping to Maven lifecycle
- SonarQube integration for JavaScript coverage analysis
- Build environment standards for reproducible builds
- Project-specific adaptations for different project types

## Standards Documents

- **project-structure.md** - Directory layouts, file naming, package.json configuration
- **dependency-management.md** - Version strategies, security, updates, ES modules
- **maven-integration.md** - Frontend Maven Plugin, phase mapping, SonarQube setup

## When to Use This Skill

Activate this skill when:

- Setting up new JavaScript projects with Maven integration
- Configuring project directory structure and file organization
- Managing npm dependencies and resolving conflicts
- Addressing security vulnerabilities or deprecated packages
- Integrating JavaScript tooling with Maven build pipeline
- Configuring SonarQube for JavaScript code analysis
- Updating Node.js or npm versions
- Troubleshooting Maven/npm integration issues
- Adapting project structure for Quarkus DevUI or NiFi extensions
- Ensuring project follows CUI standards for structure and builds

## Quick Start

### New Standard Maven Project

1. Create project structure:
```
project-root/
├── pom.xml
├── package.json
├── .prettierrc.js
├── eslint.config.js
├── jest.config.js
├── src/
│   ├── main/
│   │   └── resources/
│   │       └── static/
│   │           └── js/           # JavaScript source
│   └── test/
│       └── js/                   # JavaScript tests
└── target/                       # Build outputs
```

2. Create package.json:
```json
{
  "name": "my-project",
  "version": "1.0.0-SNAPSHOT",
  "description": "My JavaScript project",
  "private": true,
  "type": "module",
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js",
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\"",
    "test": "jest",
    "test:coverage": "jest --coverage",
    "test:ci-strict": "jest --ci --coverage --watchAll=false --maxWorkers=2",
    "quality": "npm run lint:js && npm run format:check",
    "quality:fix": "npm run lint:js:fix && npm run format"
  },
  "devDependencies": {
    "eslint": "^9.14.0",
    "@eslint/js": "^9.14.0",
    "prettier": "^3.0.3",
    "jest": "^29.7.0"
  }
}
```

3. Configure Maven (pom.xml):
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
    <execution>
      <id>install-node-and-npm</id>
      <goals><goal>install-node-and-npm</goal></goals>
      <phase>validate</phase>
    </execution>
    <execution>
      <id>npm-install</id>
      <goals><goal>npm</goal></goals>
      <phase>validate</phase>
      <configuration>
        <arguments>install</arguments>
      </configuration>
    </execution>
    <execution>
      <id>npm-format-check</id>
      <goals><goal>npm</goal></goals>
      <phase>compile</phase>
      <configuration>
        <arguments>run format:check</arguments>
      </configuration>
    </execution>
    <execution>
      <id>npm-lint</id>
      <goals><goal>npm</goal></goals>
      <phase>compile</phase>
      <configuration>
        <arguments>run lint</arguments>
      </configuration>
    </execution>
    <execution>
      <id>npm-test</id>
      <goals><goal>npm</goal></goals>
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

4. Create .gitignore:
```gitignore
# Node.js
node_modules/
target/node/

# npm
.npm/
npm-debug.log*

# Coverage
target/coverage/
coverage/

# Build outputs
target/dist/
dist/
```

### Quarkus DevUI Project Setup

1. Structure:
```
project-root/
├── pom.xml
├── package.json
├── src/
│   ├── main/
│   │   └── resources/
│   │       └── dev-ui/           # Quarkus DevUI components
│   │           ├── qwc-example.js
│   │           └── components/
│   └── test/
│       └── js/
│           └── qwc-example.test.js
```

2. Update package.json paths:
```json
{
  "scripts": {
    "lint:js": "eslint src/main/resources/dev-ui/**/*.js",
    "format": "prettier --write \"src/main/resources/dev-ui/**/*.js\"",
    "test": "jest --testPathPattern=src/test/js"
  }
}
```

3. Use `qwc-` prefix for component names:
```javascript
// qwc-security-config.js
export class QwcSecurityConfig extends LitElement {
  // Component implementation
}
```

### Managing Dependencies

1. Install development dependencies with caret ranges:
```bash
npm install --save-dev eslint@^9.14.0 prettier@^3.0.3 jest@^29.7.0
```

2. Install production dependencies with exact versions:
```bash
npm install --save-exact lit@3.2.0 core-js@3.39.0
```

3. Set up security auditing:
```json
{
  "scripts": {
    "audit:security": "npm audit --audit-level=moderate",
    "audit:fix": "npm audit fix",
    "update:check": "npx npm-check-updates --format group"
  }
}
```

4. Run security checks:
```bash
npm run audit:security
npm run audit:fix
```

### Handling Peer Dependency Conflicts

1. Try standard installation first:
```bash
npm install
```

2. If conflicts occur, use npm overrides:
```json
{
  "overrides": {
    "eslint": "^9.14.0"
  }
}
```

3. Only use --legacy-peer-deps as last resort:
```bash
npm install --legacy-peer-deps
```

## Integration with Other Skills

This skill complements:

- **cui-javascript-linting** - ESLint, Prettier, and StyleLint configuration
- **cui-javascript** - Core JavaScript development standards
- **cui-jsdoc** - JSDoc documentation standards
- **cui-javascript-unit-testing** - Jest testing standards and practices

## Common Use Cases

### Use Case 1: Creating New Maven-Integrated Project

1. Refer to **project-structure.md** for directory layout
2. Create package.json with required fields and scripts
3. Configure frontend-maven-plugin in pom.xml using **maven-integration.md**
4. Set up .gitignore with essential exclusions
5. Initialize npm dependencies
6. Run `mvn clean verify` to validate setup

### Use Case 2: Managing Security Vulnerabilities

1. Run security audit: `npm run audit:security`
2. Review vulnerability report
3. Apply automatic fixes: `npm run audit:fix`
4. For unresolved issues, consult **dependency-management.md** for response timeframes
5. Update vulnerable packages manually if needed
6. Re-run audit to confirm resolution
7. Commit updated package.json and package-lock.json

### Use Case 3: Updating Dependencies

1. Check for available updates: `npm run update:check`
2. Review breaking changes in major updates
3. Apply minor/patch updates: `npx npm-check-updates --target minor --upgrade`
4. Install updated dependencies: `npm install`
5. Run tests to verify: `npm test`
6. Run Maven build: `mvn clean verify`
7. Commit changes with update notes

### Use Case 4: Migrating to ES Modules

1. Add `"type": "module"` to package.json
2. Update configuration files to use ES module syntax:
   - `eslint.config.js`: `export default [...]`
   - `.prettierrc.js`: `export default { ... }`
   - `jest.config.js`: `export default { ... }`
3. Update import statements to include file extensions
4. Test configuration: `npm run lint`, `npm test`
5. Verify Maven build: `mvn clean verify`

### Use Case 5: Configuring SonarQube Integration

1. Add SonarQube properties to pom.xml:
```xml
<properties>
  <sonar.javascript.lcov.reportPaths>target/coverage/lcov.info</sonar.javascript.lcov.reportPaths>
  <sonar.coverage.exclusions>**/*.test.js,**/test/**/*,**/mocks/**/*</sonar.coverage.exclusions>
  <sonar.javascript.coverage.overall_condition.branch>80</sonar.javascript.coverage.overall_condition.branch>
</properties>
```

2. Configure Jest to output lcov format:
```json
{
  "jest": {
    "coverageDirectory": "target/coverage",
    "coverageReporters": ["text", "lcov", "html"]
  }
}
```

3. Run tests with coverage: `npm run test:coverage`
4. Verify lcov.info exists: `ls target/coverage/lcov.info`
5. Run SonarQube analysis: `mvn sonar:sonar`

## Best Practices

1. **Follow project type conventions** - Use appropriate directory structure for your project type
2. **Use kebab-case for all files** - Consistent naming across JavaScript files
3. **Configure "type": "module"** - Enable ES module support in package.json
4. **Commit package-lock.json** - Ensure reproducible builds across environments
5. **Use caret ranges for dev dependencies** - Allow automatic updates within major version
6. **Use exact versions for critical deps** - Pin production dependencies prone to breaking changes
7. **Implement all required npm scripts** - lint, format, test, quality scripts
8. **Map scripts to correct Maven phases** - validate for setup, compile for checks, test for testing
9. **Set up security auditing** - Regular vulnerability scanning with response procedures
10. **Use Node.js LTS** - Consistent version managed by frontend-maven-plugin (see standards/project-structure.md for exact version)
11. **Configure SonarQube coverage** - JavaScript code quality and coverage reporting
12. **Handle deprecations promptly** - Replace deprecated packages before critical
13. **Document project structure** - Update README with setup and organization
14. **Never commit node_modules/** - Always gitignore dependencies
15. **Set CI=true for tests** - Disable watch mode in CI/CD environments

## Troubleshooting

### Common Issues

**Issue: node_modules/ committed to Git**

Symptoms: Large repository size, many untracked files

Solution:
```bash
git rm -r --cached node_modules/
echo "node_modules/" >> .gitignore
git add .gitignore
git commit -m "fix: remove node_modules from Git"
```

**Issue: npm install failures during Maven build**

Symptoms: Build fails during npm-install execution

Solutions:
1. Clear npm cache: `rm -rf node_modules package-lock.json && npm cache clean --force`
2. Regenerate lock file: `npm install`
3. Use legacy peer deps if needed: Update Maven config with `<arguments>install --legacy-peer-deps</arguments>`

**Issue: Tests pass locally but fail in CI**

Cause: Different behavior between local and CI environments

Solution:
- Ensure `CI=true` environment variable set in Maven config
- Use `test:ci-strict` script with `--watchAll=false`
- Check for race conditions or timing issues in tests

**Issue: Maven build fails on format check**

Cause: Code not formatted according to Prettier rules

Solution:
```bash
npm run format
git add .
git commit -m "style: apply Prettier formatting"
```

**Issue: Inconsistent builds across environments**

Cause: Missing package-lock.json or different Node.js versions

Solution:
- Commit package-lock.json to version control
- Use frontend-maven-plugin for consistent Node.js installation
- Verify Node.js version in plugin config matches expected version

**Issue: SonarQube not detecting JavaScript coverage**

Symptoms: No JavaScript coverage shown in SonarQube

Solution:
1. Verify Jest outputs lcov.info: Check `target/coverage/lcov.info` exists
2. Check SonarQube property: `<sonar.javascript.lcov.reportPaths>target/coverage/lcov.info</sonar.javascript.lcov.reportPaths>`
3. Ensure paths match between Jest config and SonarQube property
4. Run tests before SonarQube analysis: `mvn clean test sonar:sonar`

## Additional Resources

- Node.js Documentation: https://nodejs.org/docs/
- npm Documentation: https://docs.npmjs.com/
- Frontend Maven Plugin: https://github.com/eirslett/frontend-maven-plugin
- Maven Lifecycle Reference: https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html
- Semantic Versioning: https://semver.org/

## Support

For issues or questions:
- Review standards documents in the standards/ directory
- Check troubleshooting sections in each document
- Consult official documentation for Node.js, npm, and Maven
- Review common configuration issues in project-structure.md and maven-integration.md
