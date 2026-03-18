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
    "eslint": "^10.0.0",        // Updates to 10.x.x (not 11.0.0)
    "webpack": "^5.105.4",      // Updates to 5.x.x (not 6.0.0)
    "jest": "^30.0.0"           // Updates to 30.x.x (not 31.0.0)
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
    "lit": "3.3.2",             // Exact version, no auto-updates
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
| `rimraf` < v4 | `del-cli` >= v7 | Performance, better API |
| `eslint` < v9 | `eslint` >= v10 | Security, flat config required |
| `abab` | Native `atob()`/`btoa()` | Platform native methods |
| `osenv` | `process.env` or `os` module | No longer maintained |
| `inflight` | `lru-cache` or native | Memory leaks, better alternatives |
| `glob` < v9 | `glob` >= v11 | Security fixes, performance |
| `airbnb-base` | `@eslint/js` | ESLint v10 flat config compatibility |
| `eslint-config-airbnb-base` | `@eslint/js` + custom rules | Flat config, no legacy shareable config |
| `jest` < v30 | `jest` >= v30 | Performance, better ESM support |
| `babel-jest` < v30 | `babel-jest` >= v30 | Match Jest major version |
| `webpack-cli` < v6 | `webpack-cli` >= v7 | Node.js 24 compatibility |

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
    "eslint": "^10.0.3",
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
- ESLint v10+ with flat configuration
- Prettier v3+ configuration
- StyleLint v17+ configuration
- Jest v30+ with ES module support (or Vitest v4+ for Vite-based projects)
- Babel with ES module support

**Node.js requirements**:
For complete Node.js version requirements, see **[project-structure.md](project-structure.md#node-js-version-requirements)** section "Node.js Version Requirements".

## Modern Alternatives

### Vitest as a Jest Alternative

**Vitest** (`vitest ^4.x`) is a modern test runner built on Vite with native ES module support. Consider it when:

- Starting a new standalone project using Vite as the bundler
- The project is not embedded in a Maven build (frontend-maven-plugin)
- Fast HMR-style test feedback is valuable during development

**Decision guide**:

| Criteria | Use Jest | Use Vitest |
|----------|----------|-----------|
| Maven-integrated project | Yes | No |
| Standalone / library | Optional | Preferred |
| Existing Jest configuration | Yes | No (migration effort) |
| Vite bundler already in use | Optional | Yes |

**Vitest package reference**:
```json
{
  "devDependencies": {
    "vitest": "^4.1.0",
    "@vitest/coverage-v8": "^4.1.0"
  }
}
```

**Note**: For existing Maven-integrated CUI projects, **Jest remains the standard**. Do not switch unless adopting a full Vite-based build for a standalone project.

### Vite as a Webpack Alternative

**Vite** (`vite ^8.0.0`) is the preferred bundler for standalone JavaScript projects and libraries. See [project-structure.md](project-structure.md) "Standalone JavaScript Project Layout" for when to use Vite vs Webpack.

### Bun and Deno Compatibility

**Bun** and **Deno** are alternative JavaScript runtimes that offer improved performance for scripts and local development:

- **Bun** (`bun.sh`): Drop-in npm/Node.js replacement; `bun install` is faster than `npm install`. CUI projects currently target Node.js via frontend-maven-plugin — Bun is not supported in Maven builds.
- **Deno** (`deno.land`): Secure-by-default runtime with native TypeScript support. Not applicable to Maven-integrated projects.

**Stance**: CUI projects use **Node.js** (managed by frontend-maven-plugin) for all Maven-integrated builds. Bun/Deno may be used for standalone developer tooling scripts outside the Maven lifecycle.

## Package Categories

### Core Development Tools

Essential packages for all JavaScript projects:

```json
{
  "devDependencies": {
    // Linting and Formatting
    "eslint": "^10.0.0",
    "@eslint/js": "^10.0.0",
    "prettier": "^3.8.1",
    "eslint-plugin-prettier": "^5.5.5",

    // Testing
    "jest": "^30.0.0",
    "jest-environment-jsdom": "^30.0.0",
    "@testing-library/jest-dom": "^6.9.1",

    // Build Tools (Webpack — NiFi extensions, WAR packaging)
    "webpack": "^5.105.4",
    "webpack-cli": "^7.0.2",
    "terser": "^5.46.1",

    // Babel (required for Jest 30 ES module transformation)
    "@babel/core": "^7.29.0",
    "@babel/preset-env": "^7.29.2",
    "babel-jest": "^30.0.0",

    // Utilities
    "del-cli": "^7.0.0"
  }
}
```

### Code Quality Plugins

ESLint plugins for comprehensive code quality:

```json
{
  "devDependencies": {
    "eslint-plugin-jest": "^29.0.0",
    "eslint-plugin-jsdoc": "^62.8.0",
    "eslint-plugin-unicorn": "^63.0.0",
    "eslint-plugin-security": "^4.0.0",
    "eslint-plugin-promise": "^7.2.1",
    "eslint-plugin-sonarjs": "^4.0.0"
  }
}
```

### Framework-Specific Dependencies

**Web Components (Lit)**:
```json
{
  "devDependencies": {
    "lit": "^3.3.2",
    "eslint-plugin-lit": "^2.2.1",
    "eslint-plugin-wc": "^3.1.0",
    "postcss-lit": "^1.4.1"
  }
}
```

**CSS Processing**:
```json
{
  "devDependencies": {
    "stylelint": "^17.4.0",
    "stylelint-config-standard": "^40.0.0",
    "stylelint-order": "^8.1.1"
  }
}
```

## Update Management

### Regular Update Schedule

- **Security updates**: As needed (follow vulnerability timeframes above)
- **Minor updates**: Monthly -- review, test, apply low-risk updates
- **Major updates**: Quarterly review -- plan migration, test thoroughly
- **Annual audit**: Remove unused packages, evaluate alternatives

### Update Process

1. Run `npm audit` and `npm audit fix` for security patches
2. Run `npx npm-check-updates --format group` to review available updates
3. Apply minor/patch updates: `npx npm-check-updates --target minor --upgrade && npm install && npm test`
4. Apply major updates one at a time: `npm install <package>@latest`, review breaking changes, test thoroughly
5. Verify full build: `npm run lint && npm run test && npm run build`

### Breaking Change Management

For major version updates: review the changelog, update one package at a time, modify configuration files as needed, run the full test suite, and document changes in commit messages.

## Troubleshooting

### npm Install Failures

Clear cache and reinstall: `rm -rf node_modules package-lock.json && npm cache clean --force && npm install`. If peer dependency conflicts persist, try `npm install --legacy-peer-deps` (document the reason in the project README). For Maven builds, see [maven-integration.md](maven-integration.md) "npm Install Failures".

### Dependency Conflicts

1. Update conflicting packages to compatible versions
2. Use npm overrides to force specific versions
3. Remove unused dependencies
4. Check for duplicate installations: `npm ls <package-name>`

### Build Performance

Use `.npmrc` optimizations (`prefer-offline=true`, `audit=false`, `fund=false`) and run `npm prune` regularly to remove unused packages.

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
