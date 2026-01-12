# JavaScript Linting and Formatting Standards Skill

## Overview

This skill provides comprehensive ESLint, Prettier, and StyleLint configuration standards for CUI JavaScript projects. It covers modern ESLint v9 flat configuration, Prettier formatting automation, rule management, build integration, and CSS-in-JS linting for web components.

## What This Skill Provides

### ESLint Configuration
- ESLint v9 flat configuration structure with ES modules
- Required dependencies and plugin management
- Environment configuration (browser, Node.js, Jest)
- Framework-specific extensions (Lit, Web Components)

### ESLint Rules
- Documentation rules for JSDoc validation
- Security rules for vulnerability detection
- Code quality rules with SonarJS integration
- Modern JavaScript patterns and async/await best practices
- Framework-specific rules for Lit and Web Components
- Environment-specific overrides for tests, production, mocks

### Prettier Configuration
- Code formatting automation with Prettier
- Formatting rules (line length, quotes, semicolons, etc.)
- File-specific overrides for production vs test files
- Editor integration (VS Code, IntelliJ) with format-on-save
- Pre-commit hooks with Husky and lint-staged
- ESLint integration for unified workflow

### Build Integration
- npm script configuration (lint, format, quality scripts)
- Maven build integration with frontend-maven-plugin
- CI/CD pipeline integration and quality gates
- Performance optimization (caching, parallel execution)

### StyleLint Configuration
- StyleLint setup for CSS-in-JS patterns
- postcss-lit parser for Lit components
- CSS property ordering and validation
- CSS custom property enforcement
- Environment-specific CSS rules

## Standards Documents

- **eslint-configuration.md** - ESLint v9 flat config setup, dependencies, plugins, environments
- **eslint-rules.md** - Comprehensive rule definitions for all linting categories
- **eslint-integration.md** - Build pipeline, Maven, CI/CD, and development workflow integration
- **prettier-configuration.md** - Prettier formatting setup, rules, editor integration, pre-commit hooks
- **stylelint-setup.md** - StyleLint configuration for CSS-in-JS in web components

## When to Use This Skill

Activate this skill when:

- Setting up ESLint for new JavaScript projects
- Migrating to ESLint v9 flat configuration
- Configuring or modifying ESLint rules
- Setting up Prettier for code formatting automation
- Configuring format-on-save in editors
- Integrating linting and formatting into Maven builds or CI/CD
- Setting up pre-commit hooks for automatic fixing
- Setting up StyleLint for Lit components or CSS-in-JS
- Resolving linting, formatting, or configuration issues
- Adding framework-specific linting (Lit, Web Components)
- Troubleshooting ESLint, Prettier, or StyleLint problems

## Quick Start

### Basic ESLint Setup

1. Install dependencies:
```bash
npm install --save-dev eslint @eslint/js eslint-plugin-jsdoc eslint-plugin-jest eslint-plugin-sonarjs eslint-plugin-security eslint-plugin-unicorn eslint-plugin-promise eslint-plugin-prettier prettier
```

2. Create `eslint.config.js`:
```javascript
import js from '@eslint/js';
import jsdoc from 'eslint-plugin-jsdoc';

export default [
  js.configs.recommended,
  {
    plugins: { jsdoc },
    rules: { /* configuration */ }
  }
];
```

3. Add npm scripts:
```json
{
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js"
  }
}
```

### Prettier Setup

1. Install dependencies:
```bash
npm install --save-dev prettier
```

2. Create `.prettierrc.js`:
```javascript
export default {
  printWidth: 120,
  tabWidth: 2,
  singleQuote: true,
  semi: true,
  trailingComma: 'es5',
  arrowParens: 'always',
};
```

3. Add npm scripts:
```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\"",
    "quality": "npm run lint && npm run format:check",
    "quality:fix": "npm run lint:fix && npm run format"
  }
}
```

### StyleLint Setup (CSS-in-JS)

1. Install dependencies:
```bash
npm install --save-dev stylelint stylelint-config-standard stylelint-order stylelint-declaration-strict-value postcss-lit
```

2. Create `.stylelintrc.js`:
```javascript
export default {
  extends: ['stylelint-config-standard'],
  plugins: ['stylelint-order', 'stylelint-declaration-strict-value'],
  customSyntax: 'postcss-lit',
  rules: { /* configuration */ }
};
```

3. Add npm scripts:
```json
{
  "scripts": {
    "lint:style": "stylelint src/**/*.js",
    "lint:style:fix": "stylelint --fix src/**/*.js"
  }
}
```

## Integration with Other Skills

This skill complements:

- **cui-javascript** - Core JavaScript development standards
- **cui-jsdoc** - JSDoc documentation standards
- **cui-javascript-unit-testing** - Testing standards and practices
- **cui-css** - CSS development standards

## Common Use Cases

### Use Case 1: Setting Up New Project
1. Refer to **eslint-configuration.md** for initial setup
2. Install all required dependencies
3. Create eslint.config.js with flat configuration
4. Add npm scripts for linting
5. Integrate with Maven build using **eslint-integration.md**

### Use Case 2: Configuring Linting Rules
1. Consult **eslint-rules.md** for rule categories
2. Enable required plugins (JSDoc, Jest, SonarJS, Security, etc.)
3. Configure environment-specific overrides
4. Test configuration with sample files
5. Document any custom rule configurations

### Use Case 3: Build Integration
1. Follow **eslint-integration.md** for Maven setup
2. Configure frontend-maven-plugin in pom.xml
3. Add lint:fix execution in verify phase
4. Set up CI/CD quality gates
5. Enable caching for performance

### Use Case 4: CSS-in-JS Linting
1. Use **stylelint-setup.md** for StyleLint configuration
2. Install StyleLint with postcss-lit parser
3. Configure CSS property ordering
4. Enforce CSS custom property usage
5. Integrate with Maven build

## Best Practices

1. **Use ESLint v9 flat configuration** - Modern ES module-based setup
2. **Include all required plugins** - JSDoc, Jest, SonarJS, Security, Unicorn, Promise, Prettier
3. **Enable Prettier formatting** - Consistent code style across team
4. **Configure format-on-save** - Automatic formatting in VS Code, IntelliJ
5. **Set up pre-commit hooks** - Husky and lint-staged for automatic fixing
6. **Enable SonarJS recommended defaults** - Comprehensive code quality analysis
7. **Configure environment-specific overrides** - Relaxed for tests, strict for production
8. **Integrate with build pipeline** - format:check in compile, quality:fix in verify
9. **Use StyleLint for CSS-in-JS** - When using Lit components
10. **Enable caching** - Faster linting on subsequent runs
11. **Run quality:fix before commits** - Catch and fix all issues early
12. **Configure proper severity** - Error for critical, warn for improvements
13. **Document exceptions** - Comment any rule or format overrides

## Troubleshooting

### Common Issues

**"Cannot use import statement outside a module"**
- Add `"type": "module"` to package.json
- Use `export default` in eslint.config.js

**"Plugin not found"**
- Verify plugin is installed: `npm install --save-dev eslint-plugin-jsdoc`
- Check import statement: `import jsdoc from 'eslint-plugin-jsdoc'`

**"Configuration file not found"**
- Ensure file is named `eslint.config.js` (not .eslintrc.js)
- File must be in project root directory

**StyleLint parse errors**
- Ensure `customSyntax: 'postcss-lit'` is configured
- Verify postcss-lit is installed

## Additional Resources

- ESLint v9 Documentation: https://eslint.org/docs/latest/
- StyleLint Documentation: https://stylelint.io/
- Lit Component Documentation: https://lit.dev/
- SonarJS Rules: https://github.com/SonarSource/eslint-plugin-sonarjs

## Support

For issues or questions:
- Review standards documents in the standards/ directory
- Check troubleshooting sections in each document
- Consult ESLint and StyleLint official documentation
- Review common configuration issues in eslint-configuration.md
