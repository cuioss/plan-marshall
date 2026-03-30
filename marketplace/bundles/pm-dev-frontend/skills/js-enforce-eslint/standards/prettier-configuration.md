# Prettier Configuration Standards

## Purpose

Prettier configuration standards, editor integration, and build automation for consistent code formatting.

## Required Dependencies

```json
{
  "devDependencies": {
    "prettier": "^3.0.3",
    "eslint-plugin-prettier": "^5.0.0"
  }
}
```

## Configuration File

All projects must use `.prettierrc.js` with ES module syntax (requires `"type": "module"` in package.json):

```javascript
/**
 * Prettier configuration for JavaScript projects
 */
export default {
  printWidth: 120,
  tabWidth: 2,
  useTabs: false,
  semi: true,
  singleQuote: true,
  quoteProps: 'as-needed',
  trailingComma: 'es5',
  bracketSpacing: true,
  bracketSameLine: false,
  arrowParens: 'always',
  proseWrap: 'preserve',
  htmlWhitespaceSensitivity: 'css',
  endOfLine: 'lf',
  embeddedLanguageFormatting: 'auto',

  overrides: [
    {
      files: 'src/test/js/**/*.js',
      options: {
        printWidth: 100,
        arrowParens: 'avoid',
      },
    },
  ],
};
```

The base config applies to all `*.js` and `*.mjs` files including production components. Only test files override defaults (shorter line width, no arrow-function parentheses for single params).

## NPM Scripts

```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\""
  }
}
```

These integrate with the `quality` and `quality:fix` scripts defined in eslint-integration.md.

## ESLint Integration

Prettier must run as an ESLint plugin for a unified workflow:

```javascript
// eslint.config.js
import prettier from 'eslint-plugin-prettier';

export default [
  {
    plugins: {
      prettier,
    },
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
    },
  }
];
```

## Maven Integration

For base frontend-maven-plugin setup, see **eslint-integration.md** section "Maven Integration". Add these Prettier-specific executions:

```xml
<!-- Format check in compile phase (read-only, fails on violations) -->
<execution>
  <id>npm-format-check</id>
  <goals><goal>npm</goal></goals>
  <phase>compile</phase>
  <configuration>
    <arguments>run format:check</arguments>
  </configuration>
</execution>

<!-- Format fix in verify phase (writes corrections) -->
<execution>
  <id>npm-quality-fix</id>
  <goals><goal>npm</goal></goals>
  <phase>verify</phase>
  <configuration>
    <arguments>run quality:fix</arguments>
  </configuration>
</execution>
```

## Editor Integration

### Visual Studio Code

`.vscode/settings.json`:

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

Required extension: [Prettier - Code formatter](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)

### IntelliJ IDEA / WebStorm

Settings -> Languages & Frameworks -> JavaScript -> Prettier:
- Run for files: `{**/*,*}.{js,mjs}`
- Configuration file: `.prettierrc.js`
- Enable "On save"

## Ignore Files

### .prettierignore

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

## Troubleshooting

**"No parser could be inferred for file"** -- Ensure `.js`/`.mjs` extension, or add an explicit `parser: 'babel'` override.

**Not formatting on save** -- Install the Prettier editor extension, enable format-on-save, verify `.prettierrc.js` exists.

**Conflicts with ESLint** -- Disable ESLint style rules (`quotes`, `semi`, `indent`, `comma-dangle`, `object-curly-spacing`, `array-bracket-spacing`).

**"Cannot use import statement outside a module"** -- Add `"type": "module"` to package.json.

### Validation

```bash
npm run format:check
npx prettier --list-different "src/**/*.js"
npx prettier --write src/main/resources/example.js
```
