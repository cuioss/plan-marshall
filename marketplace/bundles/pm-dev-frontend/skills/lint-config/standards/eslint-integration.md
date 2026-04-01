# ESLint Build Integration

## Purpose

This document defines integration requirements for ESLint in build pipelines, CI/CD processes, Maven configuration, and development workflows for consistent code quality enforcement.

## NPM Scripts Integration

### Complete Package.json Scripts Reference

All JavaScript projects must include comprehensive linting and formatting scripts. This section consolidates all required npm scripts for ESLint, Prettier, and StyleLint integration.

### Core ESLint Scripts

Essential linting scripts for all projects:

```json
{
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js",
    "lint": "npm run lint:js",
    "lint:fix": "npm run lint:js:fix"
  }
}
```

### Prettier Formatting Scripts

Required formatting scripts (see prettier-configuration.md for details):

```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\""
  }
}
```

### Combined Quality Scripts

Comprehensive quality assurance scripts combining linting and formatting:

```json
{
  "scripts": {
    "quality": "npm run lint && npm run format:check",
    "quality:fix": "npm run lint:fix && npm run format"
  }
}
```

### With StyleLint Integration

For projects using CSS-in-JS (Lit components), add StyleLint scripts:

```json
{
  "scripts": {
    "lint:style": "stylelint src/**/*.js",
    "lint:style:fix": "stylelint --fix src/**/*.js",
    "lint": "npm run lint:js && npm run lint:style",
    "lint:fix": "npm run lint:js:fix && npm run lint:style:fix"
  }
}
```

For projects with StyleLint (CSS-in-JS), add `lint:style` / `lint:style:fix` scripts and compose into `lint` / `lint:fix`.

## Maven Integration

### Frontend Maven Plugin Configuration

Integrate ESLint into Maven build process using frontend-maven-plugin:

```xml
<plugin>
  <groupId>com.github.eirslett</groupId>
  <artifactId>frontend-maven-plugin</artifactId>
  <version>${frontend-maven-plugin.version}</version>
  <executions>
    <!-- Install Node and npm -->
    <execution>
      <id>install-node-and-npm</id>
      <goals>
        <goal>install-node-and-npm</goal>
      </goals>
      <phase>validate</phase>
    </execution>

    <!-- Install npm dependencies -->
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

    <!-- Run ESLint with auto-fix -->
    <execution>
      <id>npm-lint-fix</id>
      <goals>
        <goal>npm</goal>
      </goals>
      <phase>compile</phase>
      <configuration>
        <arguments>run lint:fix</arguments>
      </configuration>
    </execution>
  </executions>
</plugin>
```

Run `lint:fix` in the **compile** phase so issues are caught before tests. Maven lifecycle: validate (install deps) → compile (lint:fix) → test → package.

## Quality Gates

Establish quality gates for successful builds:

1. **No ESLint errors**: All error-level violations must be fixed
2. **Minimize warnings**: Address warnings or document exceptions
3. **Security rules pass**: All security rules must pass
4. **Complexity thresholds**: Functions meet complexity limits

## Performance Optimization

### Caching

Enable ESLint caching for faster subsequent runs:

```json
{
  "scripts": {
    "lint:js": "eslint --cache src/**/*.js",
    "lint:js:fix": "eslint --cache --fix src/**/*.js"
  }
}
```

Add cache file to .gitignore:

```
# .gitignore
.eslintcache
```

### File Exclusions

Exclude unnecessary files from linting:

```javascript
// eslint.config.js
export default [
  {
    ignores: [
      '**/node_modules/**',
      '**/target/**',
      '**/dist/**',
      '**/*.min.js',
      '**/vendor/**'
    ]
  },
  // ... configuration
];
```

## IDE Integration

**VS Code**: Install ESLint extension, enable `source.fixAll.eslint` on save.

**IntelliJ**: Preferences → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint → Automatic configuration + fix on save.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Cannot find module 'eslint' | Not installed | `npm install` or `mvn clean install` |
| Cannot use import outside module | Missing module type | Add `"type": "module"` to package.json |
| Configuration file not found | Wrong filename | Rename to `eslint.config.js` in project root |
| Plugin not found | Not installed | `npm install --save-dev eslint-plugin-{name}` |
| Maven fails with lint errors | ESLint errors | Run `npm run lint:fix` locally first |

## See Also

- [ESLint Configuration](eslint-configuration.md) - Flat config setup and dependencies
- [ESLint Rules](eslint-rules.md) - Rule categories and customization
- [Prettier Configuration](prettier-configuration.md) - Formatting setup and IDE integration
