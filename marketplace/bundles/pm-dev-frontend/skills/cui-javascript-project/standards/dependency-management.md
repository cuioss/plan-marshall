# JavaScript Dependency Management Standards

## Purpose

This document defines comprehensive standards for managing JavaScript dependencies including version strategies, security practices, ES module configuration, and dependency maintenance to ensure secure, maintainable, and up-to-date codebases.

## Semantic Versioning Strategy

### Version Range Patterns

Use appropriate version patterns based on dependency type and stability requirements:

**Caret ranges (^)**: Allow compatible updates within same major version
```json
{
  "devDependencies": {
    "eslint": "^9.14.0",        // Updates to 9.x.x (not 10.0.0)
    "webpack": "^5.96.1",       // Updates to 5.x.x (not 6.0.0)
    "jest": "^29.7.0"           // Updates to 29.x.x (not 30.0.0)
  }
}
```

**When to use caret ranges**:
- Development tools (ESLint, Prettier, Jest)
- Build tools (Webpack, Babel)
- Test utilities
- Code quality plugins

**Exact versions**: Pin specific versions for critical dependencies
```json
{
  "dependencies": {
    "lit": "3.2.0",             // Exact version, no auto-updates
    "core-js": "3.39.0"          // Polyfills with breaking changes
  }
}
```

**When to use exact versions**:
- Production frameworks with breaking changes between minors
- Security-critical packages
- Packages with unstable APIs
- Known breaking change histories

### Version Update Strategy

**Development Dependencies**: Use caret ranges for flexibility
- Allows automatic patch and minor version updates within same major version
- Enables minor feature updates
- Maintains major version compatibility

**Production Dependencies**: Consider exact versions for stability
- Prevents unexpected breakages
- Requires manual version updates
- Explicit upgrade decisions

**Security Packages**: Always use latest versions
- Apply security patches immediately
- Use caret ranges to allow automatic updates
- Monitor vulnerability databases

## Security Management

### Vulnerability Scanning

#### Required npm Scripts

Every project must implement security audit scripts:

```json
{
  "scripts": {
    "audit:security": "npm audit --audit-level=moderate",
    "audit:fix": "npm audit fix",
    "audit:licenses": "npx license-checker --summary",
    "update:check": "npx npm-check-updates --format group",
    "update:dependencies": "npx npm-check-updates --upgrade"
  }
}
```

**Script purposes**:
- `audit:security`: Check for known vulnerabilities (moderate+ severity)
- `audit:fix`: Automatically fix vulnerabilities where possible
- `audit:licenses`: Verify license compatibility
- `update:check`: Show available dependency updates
- `update:dependencies`: Update all dependencies to latest

#### Vulnerability Response Timeframes

**Critical vulnerabilities**: Fix within 24 hours
- Immediate security risk
- Active exploits possible
- Block deployment until resolved

**High vulnerabilities**: Fix within 1 week
- Significant security risk
- Exploitable with effort
- Priority in sprint planning

**Moderate vulnerabilities**: Fix within 1 month
- Limited security risk
- Difficult to exploit
- Address in regular updates

**Low vulnerabilities**: Address in next release
- Minimal security risk
- Theoretical exploits only
- Batch with other updates

#### Resolution Strategies

1. **Automatic fixes**: `npm audit fix`
   - Safest approach for compatible updates
   - Updates to secure versions within semver range
   - No breaking changes

2. **Force updates**: `npm audit fix --force`
   - May introduce breaking changes
   - Use only when automatic fix unavailable
   - Test thoroughly after applying

3. **Manual updates**: Update package.json directly
   - For packages with major version changes
   - Allows controlled upgrade process
   - Review changelogs before upgrading

4. **Alternative packages**: Replace vulnerable packages
   - For unmaintained or deprecated packages
   - Research replacement options
   - Plan migration timeline

### Deprecated Package Management

#### Common Deprecated Packages and Replacements

| Deprecated Package | Replacement | Reason |
|-------------------|-------------|---------|
| `rimraf` < v4 | `del-cli` or `rimraf` >= v5 | Performance, better API |
| `eslint` < v9 | `eslint` >= v9 | Security, flat config support |
| `abab` | Native `atob()`/`btoa()` | Platform native methods |
| `osenv` | `process.env` or `os` module | No longer maintained |
| `inflight` | `lru-cache` or native | Memory leaks, better alternatives |
| `glob` < v9 | `glob` >= v9 | Security fixes, performance |
| `airbnb-base` | `@eslint/js` | ESLint v9 compatibility |

#### Handling Deprecation Warnings

Monitor and address these npm warnings during builds:

```bash
# Examples of deprecation warnings to resolve:
npm WARN deprecated abab@2.0.6: Use your platform's native atob() and btoa()
npm WARN deprecated rimraf@3.0.2: Rimraf versions prior to v4 are no longer supported
npm WARN deprecated eslint@8.57.1: This version is no longer supported
```

**Resolution process**:
1. Identify deprecated package from warning
2. Research replacement or upgrade path
3. Update package.json to use replacement/newer version
4. Test application thoroughly
5. Commit changes with deprecation note in commit message

## Dependency Conflict Resolution

### Peer Dependency Conflicts

**Primary strategy**: Standard installation without flags
```bash
npm install
```

**Only use --legacy-peer-deps when standard installation fails**:
```bash
npm install --legacy-peer-deps
```

### When to Use --legacy-peer-deps

**ONLY use this flag when**:
1. Standard `npm install` fails with peer dependency errors
2. Updated packages don't resolve conflicts
3. No npm overrides work for the conflict
4. Documented in project README why it's needed

**Before using --legacy-peer-deps, try**:
1. Update packages to latest versions
2. Remove unused dependencies
3. Use npm overrides for specific conflicts
4. Check if packages have been updated to resolve conflicts

### npm Overrides

Use overrides for selective dependency resolution:

```json
{
  "overrides": {
    "eslint": "^9.14.0",
    "some-package": {
      "problematic-dep": "^2.0.0"
    }
  }
}
```

**Override patterns**:
- Direct override: Force specific version globally
- Parent reference: Use parent's version with `$package-name`
- Scoped override: Override only within specific package

## ES Module Configuration

### Package.json Module Type

All projects must configure ES module support:

```json
{
  "name": "project-name",
  "version": "1.0.0",
  "type": "module",
  "private": true
}
```

**Why "type": "module" is required**:
- ESLint v9 flat configuration requires ES modules
- Modern configuration files use import/export syntax
- Enables use of modern JavaScript features
- Compatible with latest tooling (Prettier, StyleLint, Jest)

### Configuration File Syntax

All `.js` configuration files must use ES module syntax:

| Configuration File | Required Syntax |
|-------------------|----------------|
| `eslint.config.js` | `export default [...]` |
| `.prettierrc.js` | `export default { ... }` |
| `.stylelintrc.js` | `export default { ... }` |
| `jest.config.js` | `export default { ... }` |

**Example**:
```javascript
// eslint.config.js
import js from '@eslint/js';
import jsdoc from 'eslint-plugin-jsdoc';

export default [
  js.configs.recommended,
  {
    plugins: { jsdoc },
    rules: { /* rules */ }
  }
];
```

### Tool Chain Compatibility

Ensure all tools support ES modules:

**Required versions**:
- ESLint v9+ with flat configuration
- Prettier v3+ configuration
- StyleLint v16+ configuration
- Jest v29+ with ES module support
- Babel with ES module support

**Node.js requirements**:
For complete Node.js version requirements, see **[project-structure.md](project-structure.md#node-js-version-requirements)** section "Node.js Version Requirements".

## Package Categories

### Core Development Tools

Essential packages for all JavaScript projects:

```json
{
  "devDependencies": {
    // Linting and Formatting
    "eslint": "^9.14.0",
    "@eslint/js": "^9.14.0",
    "prettier": "^3.0.3",
    "eslint-plugin-prettier": "^5.0.0",

    // Testing
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "@testing-library/jest-dom": "^6.6.3",

    // Build Tools
    "webpack": "^5.96.1",
    "webpack-cli": "^5.1.4",
    "terser": "^5.36.0",

    // Babel
    "@babel/core": "^7.26.0",
    "@babel/preset-env": "^7.26.0",
    "babel-jest": "^29.7.0",

    // Utilities
    "del-cli": "^6.0.0"
  }
}
```

### Code Quality Plugins

ESLint plugins for comprehensive code quality:

```json
{
  "devDependencies": {
    "eslint-plugin-jest": "^28.8.3",
    "eslint-plugin-jsdoc": "^46.8.0",
    "eslint-plugin-unicorn": "^48.0.0",
    "eslint-plugin-security": "^1.7.1",
    "eslint-plugin-promise": "^6.1.1",
    "eslint-plugin-sonarjs": "^2.0.3"
  }
}
```

### Framework-Specific Dependencies

**Web Components (Lit)**:
```json
{
  "devDependencies": {
    "lit": "^3.0.0",
    "eslint-plugin-lit": "^1.10.1",
    "eslint-plugin-wc": "^2.0.4",
    "postcss-lit": "^1.0.0"
  }
}
```

**CSS Processing**:
```json
{
  "devDependencies": {
    "stylelint": "^16.10.0",
    "stylelint-config-standard": "^36.0.1",
    "stylelint-order": "^6.0.3"
  }
}
```

## Update Management

### Regular Update Schedule

Maintain dependencies with consistent schedule:

**Security updates**: As needed (follow vulnerability timeframes)
- Monitor security advisories
- Apply patches immediately
- Test thoroughly

**Minor updates**: Monthly
- Review available updates
- Test compatibility
- Apply low-risk updates

**Major updates**: Quarterly review
- Review breaking changes
- Plan migration
- Schedule dedicated testing

**Annual audit**: Complete dependency review
- Remove unused packages
- Evaluate alternatives
- Update project dependencies strategy

### Update Process

#### 1. Security Audit

Check for vulnerabilities:
```bash
npm audit
npm audit fix
```

#### 2. Check Available Updates

Review what updates are available:
```bash
npx npm-check-updates --format group
```

**Output interpretation**:
- **Patch**: Bug fixes only (safe to update)
- **Minor**: New features, backward compatible (usually safe)
- **Major**: Breaking changes (review carefully)

#### 3. Apply Minor Updates

Update minor and patch versions:
```bash
npx npm-check-updates --target minor --upgrade
npm install
npm test
```

#### 4. Test Updates

Verify application works after updates:
```bash
npm run lint
npm run test
npm run build
```

#### 5. Apply Major Updates

Handle major updates individually:
```bash
# Update one package at a time
npm install eslint@latest
# Review breaking changes
# Update configuration if needed
# Test thoroughly
npm test
```

### Breaking Change Management

For major version updates:

1. **Review changelog**: Understand what changed
   - Read CHANGELOG.md or release notes
   - Identify breaking changes
   - Note new features

2. **Update in isolation**: One major update at a time
   - Prevents multiple breaking changes at once
   - Easier to identify issues
   - Simpler rollback if needed

3. **Update configuration**: Modify config files
   - ESLint flat config for ESLint v9
   - Jest configuration for Jest v29
   - Webpack config for Webpack v5

4. **Test thoroughly**: Run full test suite
   - Unit tests
   - Integration tests
   - Build process
   - Linting and formatting

5. **Document changes**: Update project docs
   - README.md
   - Migration guides
   - Team communication

## Troubleshooting

### npm Install Failures

**Symptom**: npm install fails in development or during Maven build

**Common causes**:
- Corrupted npm cache
- Peer dependency conflicts
- Outdated or corrupted package-lock.json
- Network timeouts

**Resolution steps**:

1. Clear npm cache and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm cache clean --force
   npm install
   ```

2. Use legacy peer deps (if modern dependency resolution fails):
   ```bash
   npm install --legacy-peer-deps
   ```

   For Maven builds, configure in pom.xml:
   ```xml
   <configuration>
     <arguments>install --legacy-peer-deps</arguments>
   </configuration>
   ```

3. Regenerate lock file if corrupted:
   ```bash
   rm package-lock.json
   npm install
   git add package-lock.json
   git commit -m "chore: regenerate package-lock.json"
   ```

4. Check for conflicting global packages:
   ```bash
   npm list -g --depth=0
   ```

### Dependency Conflicts

**Common solutions**:
1. Update conflicting packages to compatible versions
2. Use npm overrides to force specific versions
3. Remove unused dependencies
4. Check for duplicate installations: `npm ls <package-name>`

### Inconsistent Dependencies Across Environments

**Cause**: Missing or outdated package-lock.json

**Solution**:
```bash
# Generate fresh lock file
rm package-lock.json
npm install
# Commit lock file
git add package-lock.json
git commit -m "chore: update package-lock.json"
```

**Important**: Always commit package-lock.json to ensure consistent installs across all environments.

### Build Performance

**Optimization strategies**:

1. Use .npmrc optimizations:
   ```
   prefer-offline=true
   audit=false
   fund=false
   ```

2. Use npm install flags:
   ```bash
   npm install --prefer-offline --no-audit
   ```

3. Regular dependency cleanup:
   ```bash
   npm prune
   ```

## Best Practices

1. **Use caret ranges for dev dependencies** - Allow automatic updates within major version
2. **Audit security regularly** - Run `npm audit` weekly
3. **Update dependencies monthly** - Keep packages current
4. **Test after updates** - Run full test suite
5. **Commit package-lock.json** - See **[project-structure.md](project-structure.md)** section "Lock File Requirements"
6. **Configure "type": "module"** - Enable ES module support
7. **Review deprecation warnings** - Address before they become critical
8. **Use overrides for conflicts** - Better than --legacy-peer-deps
9. **Document major updates** - Note breaking changes in commits
10. **Monitor security advisories** - Subscribe to security mailing lists
