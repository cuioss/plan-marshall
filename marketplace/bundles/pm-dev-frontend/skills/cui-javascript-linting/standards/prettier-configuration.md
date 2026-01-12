# Prettier Configuration Standards

## Purpose

This document defines Prettier configuration standards, formatting rules, editor integration, and build automation for consistent code formatting across all CUI JavaScript projects.

## Why Prettier?

Prettier is an opinionated code formatter that enforces consistent style across the codebase:

- **Eliminates style debates** - One consistent format for all code
- **Saves time** - No manual formatting or style discussions
- **Catches errors** - Invalid syntax detected during formatting
- **Integrates with ESLint** - Works seamlessly with linting workflow
- **Editor support** - Format-on-save in all major IDEs

## Required Dependencies

### Prettier Package

Install Prettier as a development dependency:

```json
{
  "devDependencies": {
    "prettier": "^3.0.3"
  }
}
```

### ESLint Integration Dependencies

Prettier must be integrated with ESLint (see eslint-configuration.md):

```json
{
  "devDependencies": {
    "eslint-plugin-prettier": "^5.0.0",
    "eslint-config-prettier": "^9.0.0"
  }
}
```

## Configuration File Structure

### Prettier Configuration File

All projects must use `.prettierrc.js` with ES module syntax:

```javascript
/**
 * Prettier configuration for JavaScript projects
 *
 * This configuration ensures consistent code formatting across
 * JavaScript and CSS-in-JS files with environment-specific overrides for
 * production components and test files.
 */

export default {
  // Basic formatting options
  printWidth: 120,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: true,
  quoteProps: 'as-needed',

  // Object and array formatting
  trailingComma: 'es5',
  bracketSpacing: true,
  bracketSameLine: false,

  // Arrow function parentheses
  arrowParens: 'always',

  // Prose formatting
  proseWrap: 'preserve',

  // HTML formatting
  htmlWhitespaceSensitivity: 'css',

  // End of line
  endOfLine: 'lf',

  // Embedded language formatting
  embeddedLanguageFormatting: 'auto',

  // File-specific overrides
  overrides: [
    {
      files: ['*.js', '*.mjs'],
      options: {
        printWidth: 120,
        singleQuote: true,
        trailingComma: 'es5',
        arrowParens: 'always',
        bracketSpacing: true,
        bracketSameLine: false,
        htmlWhitespaceSensitivity: 'css',
        embeddedLanguageFormatting: 'auto',
      },
    },
    {
      files: 'src/main/resources/components/**/*.js',
      options: {
        printWidth: 120,
        singleQuote: true,
        trailingComma: 'es5',
        bracketSameLine: false,
        singleAttributePerLine: false,
        arrowParens: 'always',
        bracketSpacing: true,
      },
    },
    {
      files: 'src/test/js/**/*.js',
      options: {
        printWidth: 100,
        singleQuote: true,
        trailingComma: 'es5',
        arrowParens: 'avoid',
        bracketSpacing: true,
      },
    },
  ],
};
```

### Configuration Requirements

**File Name**: `.prettierrc.js` (not .prettierrc.json or prettier.config.js)

**Syntax**: ES module format with `export default` (requires `"type": "module"` in package.json)

**Structure**: JavaScript object with formatting options and overrides

## Core Formatting Rules

### Line Length and Spacing

**printWidth**: Maximum line length before wrapping
- Production code: 120 characters
- Test code: 100 characters (better readability)

**tabWidth**: Number of spaces per indentation level
- Always: 2 spaces

**useTabs**: Use tabs instead of spaces
- Always: false (use spaces for consistency)

**endOfLine**: Line ending style
- Always: 'lf' (Unix-style line endings for cross-platform consistency)

### Quote and Semicolon Standards

**singleQuote**: Use single quotes instead of double quotes
- Always: true

**semi**: Print semicolons at ends of statements
- Always: true

**quoteProps**: Quote object properties
- Always: 'as-needed' (only quote when necessary)

### Object and Array Formatting

**trailingComma**: Trailing commas in multi-line structures
- Always: 'es5' (trailing commas where valid in ES5)
- Benefits: Cleaner git diffs, easier reordering

**bracketSpacing**: Spaces inside object literals
- Always: true
- Example: `{ foo: bar }` not `{foo: bar}`

**bracketSameLine**: Put closing bracket on same line
- Always: false (closing bracket on new line for better readability)

### Function Formatting

**arrowParens**: Parentheses around single arrow function parameter
- Production code: 'always' (consistent style)
- Test code: 'avoid' (simpler syntax)

**Examples**:
```javascript
// Production: 'always'
const double = (x) => x * 2;

// Test: 'avoid'
const double = x => x * 2;
```

### Advanced Options

**proseWrap**: Wrap prose text
- Always: 'preserve' (maintain original wrapping)

**htmlWhitespaceSensitivity**: HTML whitespace handling
- Always: 'css' (respect CSS display property)

**embeddedLanguageFormatting**: Format embedded code
- Always: 'auto' (format code in template literals)

## File-Specific Overrides

The complete configuration shown above includes three override blocks. See the Configuration File Structure section for the complete `.prettierrc.js` file.

### Standard JavaScript Files (*.js, *.mjs)

Default configuration for all standard JavaScript files:
- Print width: 120 characters
- Single quotes, trailing commas (ES5)
- Always use parentheses around arrow function parameters
- Standard bracket spacing and formatting

### Production Component Files (src/main/resources/components/**/*.js)

Enhanced formatting for production components with CSS-in-JS:
- Print width: 120 characters
- Optimized for Lit web component formatting
- CSS-in-JS friendly settings
- Single attribute per line disabled for compact templates

### Test Files (src/test/js/**/*.js)

Relaxed formatting for better test readability:
- Print width: 100 characters (shorter for readability)
- Avoid parentheses around single arrow function parameters
- Simpler syntax optimized for test clarity

## NPM Scripts Integration

For complete npm scripts reference including ESLint, Prettier, and StyleLint integration, see **eslint-integration.md** section "NPM Scripts Integration".

### Prettier-Specific Scripts

The essential Prettier scripts to add to your package.json:

```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\""
  }
}
```

### Script Usage

**format**: Apply formatting to all JavaScript files
- Writes changes to disk
- Use during development or before commit

**format:check**: Verify formatting without changes
- Read-only validation
- Use in CI/CD pipelines

### Integration with Quality Scripts

Prettier integrates with the `quality` and `quality:fix` scripts defined in eslint-integration.md:
- `quality`: Runs linting + formatting checks
- `quality:fix`: Applies linting + formatting fixes

## ESLint Integration

### Prettier as ESLint Plugin

Prettier must be integrated with ESLint for unified workflow:

```javascript
// eslint.config.js
import prettier from 'eslint-plugin-prettier';

export default [
  {
    plugins: {
      prettier,
    },
    rules: {
      'prettier/prettier': 'error',
    },
  }
];
```

### Disable Conflicting ESLint Rules

ESLint style rules must be disabled to avoid conflicts:

```javascript
rules: {
  // Disable style rules handled by Prettier
  'quotes': 'off',
  'semi': 'off',
  'indent': 'off',
  'comma-dangle': 'off',
  'object-curly-spacing': 'off',
  'array-bracket-spacing': 'off',

  // Enable Prettier as ESLint rule
  'prettier/prettier': 'error',
}
```

**Why disable these rules?**
- Prettier handles all formatting decisions
- ESLint focuses on code quality, not style
- Prevents conflicting formatting instructions
- Single source of truth for style

## Maven Integration

### Frontend Maven Plugin Configuration

For complete frontend-maven-plugin configuration including Node.js installation and dependency management, see **eslint-integration.md** section "Maven Integration".

Add these Prettier-specific executions to the plugin configuration:

```xml
<!-- Format check in compile phase -->
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

<!-- Format fix in verify phase -->
<execution>
  <id>npm-quality-fix</id>
  <goals>
    <goal>npm</goal>
  </goals>
  <phase>verify</phase>
  <configuration>
    <arguments>run quality:fix</arguments>
  </configuration>
</execution>
```

### Build Phase Strategy

**compile phase**: Format checking (read-only validation)
- Fails build if files are not formatted
- Catches formatting issues early
- No modifications to source files

**verify phase**: Quality fix (automatic formatting)
- Applies both linting and formatting fixes
- Modifies source files
- Ensures code is clean before packaging

### Why Two Phases?

1. **Early Detection** - compile phase catches issues early
2. **Automatic Fixing** - verify phase applies fixes
3. **Safety** - compile validates, verify modifies
4. **CI/CD Integration** - clear separation of concerns

## Editor Integration

### Visual Studio Code

Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "prettier.configPath": ".prettierrc.js",
  "prettier.requireConfig": true
}
```

**Required Extension**: [Prettier - Code formatter](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)

**Features**:
- Format on save
- Format on paste (optional)
- Format selection
- Show formatting errors

### IntelliJ IDEA / WebStorm

**Configuration Steps**:
1. Go to Settings → Languages & Frameworks → JavaScript → Prettier
2. Enable "Run for files" pattern: `{**/*,*}.{js,mjs}`
3. Set Prettier package path
4. Set configuration file: `.prettierrc.js`
5. Enable "On save" formatting

**Features**:
- Format on save
- Format on commit
- Format manually (Ctrl+Alt+Shift+P)
- Show formatting errors inline

### Common Editor Settings

All editors should:
- **Format on save** - Automatically format when saving files
- **Require config** - Only format if .prettierrc.js exists
- **Show errors** - Highlight formatting inconsistencies
- **Respect ignore** - Honor .prettierignore file

## Ignore Files

### .prettierignore

Exclude files from formatting:

```
# Build artifacts
target/
dist/
build/

# Dependencies
node_modules/

# Generated files
*.min.js
*.bundle.js

# Lock files
package-lock.json
yarn.lock

# Coverage
coverage/
```

## Pre-commit Hooks

### Husky Configuration

Enforce formatting before commits using Husky:

```json
{
  "devDependencies": {
    "husky": "^8.0.0",
    "lint-staged": "^13.0.0"
  }
}
```

### Lint-Staged Configuration

Configure lint-staged in package.json:

```json
{
  "lint-staged": {
    "*.js": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

### Pre-commit Hook

Create `.husky/pre-commit`:

```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
```

**Benefits**:
- Prevents committing unformatted code
- Automatic fixing before commit
- Consistent style across team
- Catches issues early

## Formatting Examples

### Object Literals

Correct Prettier formatting:

```javascript
// Single-line objects
const config = { apiEndpoint: 'https://api.example.com', timeout: 5000 };

// Multi-line objects
const config = {
  apiEndpoint: 'https://api.example.com',
  timeout: 5000,
  retries: 3,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer token',
  },
};

// Arrays
const items = ['first-item', 'second-item', 'third-item'];
```

### Function Definitions

Consistent function formatting:

```javascript
// Arrow functions (production: always use parens)
const processData = (input, options = {}) => {
  return input.map((item) => transform(item, options));
};

// Arrow functions (tests: avoid parens for single param)
const double = x => x * 2;

// Regular functions
function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Async functions
const fetchUserData = async (userId) => {
  const response = await api.get(`/users/${userId}`);
  return response.data;
};
```

### Template Literals

Proper template formatting:

```javascript
// Inline templates
const message = `Hello, ${user.name}! You have ${count} messages.`;

// Multi-line HTML templates
const template = html`
  <div class="container">
    <h1>${title}</h1>
    <p>${description}</p>
  </div>
`;
```

### Import Statements

Consistent import formatting:

```javascript
// Single-line imports
import { html, css, LitElement } from 'lit';

// Multi-line imports (auto-wrapped at 120 chars)
import {
  verylongfunctionname,
  anotherlongfunctionname,
  yetanotherlongfunctionname,
} from './utilities.js';
```

### CSS-in-JS Formatting

Proper formatting for Lit component styles:

```javascript
static styles = css`
  .container {
    display: flex;
    flex-direction: column;
    max-width: 1200px;
    padding: 1rem;
  }

  .header {
    align-items: center;
    background-color: var(--primary-color);
    display: flex;
    justify-content: space-between;
    margin-bottom: 1rem;
  }

  .button {
    background-color: var(--button-bg-color);
    border: none;
    border-radius: 4px;
    color: var(--button-text-color);
    cursor: pointer;
    padding: 0.5rem 1rem;
  }

  .button:hover {
    background-color: var(--button-hover-bg-color);
  }
`;
```

## Troubleshooting

### Common Issues

**Issue: "No parser could be inferred for file"**

Cause: File type not recognized by Prettier

Solution: Ensure file has .js or .mjs extension, or add parser explicitly:
```javascript
{
  files: '*.specialjs',
  options: {
    parser: 'babel',
  },
}
```

**Issue: Prettier not formatting on save**

Cause: Editor not configured or extension not installed

Solution:
- Install Prettier extension for your editor
- Enable format-on-save in editor settings
- Verify `.prettierrc.js` exists in project root

**Issue: Formatting conflicts with ESLint**

Cause: ESLint style rules not disabled

Solution: Ensure these rules are set to 'off' in ESLint config:
- quotes, semi, indent, comma-dangle, object-curly-spacing, array-bracket-spacing

**Issue: "Cannot use import statement outside a module"**

Cause: Missing `"type": "module"` in package.json

Solution:
```json
{
  "type": "module"
}
```

### Validation

Verify Prettier configuration works:

```bash
# Check formatting of all files
npm run format:check

# Format a specific file
npx prettier --check src/main/resources/example.js

# Show what would be formatted
npx prettier --list-different "src/**/*.js"

# Format and show changes
npx prettier --write src/main/resources/example.js
```

## Best Practices

1. **Run format:check in CI** - Fail builds if formatting is inconsistent
2. **Enable format-on-save** - Automatic formatting during development
3. **Use pre-commit hooks** - Prevent committing unformatted code
4. **Integrate with ESLint** - Single workflow for quality and style
5. **File-specific overrides** - Different settings for tests vs production
6. **Consistent configuration** - One .prettierrc.js for entire project
7. **Ignore generated files** - Use .prettierignore for build artifacts
8. **Document exceptions** - Comment any unusual overrides
9. **Keep Prettier updated** - Regular updates for latest features
10. **Team agreement** - Ensure all developers use same Prettier version

## Summary

Prettier provides:
- **Consistent formatting** across entire codebase
- **Automatic fixing** eliminating manual formatting
- **Editor integration** for format-on-save workflow
- **ESLint integration** for unified quality checking
- **Build integration** for CI/CD enforcement
- **Reduced debates** about code style

Key configuration points:
- Use `.prettierrc.js` with ES module syntax
- 120-character line width for production, 100 for tests
- Single quotes, semicolons, trailing commas
- Always use parentheses in production arrow functions
- File-specific overrides for different contexts
