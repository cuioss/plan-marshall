# JavaScript Project Structure Standards

## Purpose

This document defines standards for organizing JavaScript projects including directory layout, file naming conventions, and package.json configuration to ensure consistent, maintainable project structures across all CUI projects.

## Directory Structure Standards

### Standard Maven Project Layout

For typical Maven-based JavaScript projects:

```
project-root/
├── package.json
├── package-lock.json
├── .prettierrc.js
├── eslint.config.js
├── .stylelintrc.js (if using CSS-in-JS)
├── jest.config.js
├── src/
│   ├── main/
│   │   └── resources/
│   │       └── static/
│   │           └── js/           # JavaScript source files
│   └── test/
│       └── js/                   # JavaScript unit tests
├── target/                       # Build outputs (Maven)
│   ├── node/                     # Node.js installation (from frontend-maven-plugin)
│   ├── coverage/                 # Test coverage reports
│   └── classes/
│       └── META-INF/
│           └── resources/        # Compiled/bundled assets
└── node_modules/                 # npm dependencies (gitignored)
```

**Key characteristics**:
- JavaScript source in `src/main/resources/static/js/`
- Tests in `src/test/js/`
- Build outputs in `target/`
- Maven-compatible resource structure

### Quarkus DevUI Project Layout

For Quarkus development UI extensions:

```
project-root/
├── package.json
├── package-lock.json
├── .prettierrc.js
├── eslint.config.js
├── src/
│   ├── main/
│   │   └── resources/
│   │       └── dev-ui/           # Quarkus DevUI components
│   │           ├── qwc-example-component.js
│   │           └── components/   # Sub-components
│   └── test/
│       └── js/                   # Component tests with Lit test utilities
│           ├── qwc-example-component.test.js
│           └── mocks/            # Mock services and data
├── target/                       # Build outputs
└── node_modules/
```

**Key characteristics**:
- DevUI components in `src/main/resources/dev-ui/`
- Lit-based web components with `qwc-` prefix
- Test utilities for Lit component testing
- Mock services for isolated testing

### NiFi Extension Project Layout

For Apache NiFi custom processor UI extensions:

```
project-root/
├── package.json
├── webpack.config.js
├── src/
│   ├── main/
│   │   └── webapp/
│   │       └── js/               # NiFi UI components
│   │           ├── nf-example-config.js
│   │           └── components/
│   └── test/
│       └── js/                   # Tests with NiFi mocks
│           └── mocks/
│               └── nf-common-mock.js
├── target/                       # WAR output
└── node_modules/
```

**Key characteristics**:
- Web application structure for WAR packaging
- NiFi-specific component naming (`nf-` prefix)
- WebJar integration for resource packaging
- Webpack bundling for production assets

### Standalone JavaScript Project Layout

For JavaScript libraries or standalone applications:

```
project-root/
├── package.json
├── package-lock.json
├── .prettierrc.js
├── eslint.config.js
├── src/
│   ├── main/
│   │   └── js/                   # Source files
│   │       ├── index.js
│   │       └── modules/
│   └── test/                     # Tests
│       ├── unit/
│       └── integration/
├── dist/                         # Build output (npm packages)
└── node_modules/
```

**Key characteristics**:
- Simplified structure without Maven integration
- Clear separation of source and tests
- Build outputs in `dist/` for npm publishing
- Standard npm package structure

## File Naming Conventions

### JavaScript Source Files

**General files**: Use kebab-case for all JavaScript files

```
user-service.js
api-client.js
data-transformer.js
utility-functions.js
```

**Test files**: Append `.test.js` suffix

```
user-service.test.js
api-client.test.js
data-transformer.test.js
```

**Mock files**: Use descriptive names indicating mock purpose

```
api-client-mock.js
database-connection-mock.js
user-service-stub.js
```

**Setup/Configuration files**: Use descriptive names

```
jest.setup-dom.js
jest.setup-globals.js
webpack.config.js
babel.config.js
```

### Framework-Specific Naming

**Quarkus DevUI Components**: Prefix with `qwc-` (Quarkus Web Component)

```
qwc-jwt-config.js
qwc-security-settings.js
qwc-dashboard.js
```

**NiFi Components**: Prefix with `nf-` (NiFi)

```
nf-processor-config.js
nf-relationship-settings.js
nf-property-editor.js
```

**Lit Web Components**: Use kebab-case element name matching

```
user-profile-card.js       // <user-profile-card>
navigation-menu.js         // <navigation-menu>
data-table.js              // <data-table>
```

### Configuration Files

**Standard locations and names**:

```
.prettierrc.js             # Prettier configuration (ES module)
eslint.config.js           # ESLint v9 flat configuration
.stylelintrc.js            # StyleLint configuration (if using CSS-in-JS)
jest.config.js             # Jest testing configuration
webpack.config.js          # Webpack bundling (if applicable)
babel.config.js            # Babel transpilation (if applicable)
.gitignore                 # Git exclusions
.npmrc                     # npm configuration (optional)
```

## Package.json Configuration

### Essential Structure

Every JavaScript project must have a properly configured package.json:

```json
{
  "name": "project-name",
  "version": "1.0.0-SNAPSHOT",
  "description": "Brief project description",
  "private": true,
  "type": "module",
  "scripts": {
    "lint:js": "eslint src/**/*.js",
    "lint:js:fix": "eslint --fix src/**/*.js",
    "format": "prettier --write \"src/**/*.js\"",
    "format:check": "prettier --check \"src/**/*.js\"",
    "test": "jest",
    "test:watch": "jest --watch",
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

### Required Fields

**name**: Project identifier (kebab-case)
- Format: `kebab-case` matching artifact ID
- Example: `cui-jwt-extension`, `nifi-custom-processor-ui`

**version**: Semantic version matching Maven version
- Development: `1.0.0-SNAPSHOT`
- Release: `1.0.0`

**description**: Brief one-line project description

**private**: Always `true` for internal projects
- Prevents accidental npm publication
- Indicates project is not for public distribution

**type**: Module system configuration
- Always `"module"` for ES module support
- Required for ESLint v9 flat config
- Enables modern JavaScript tooling

### Required npm Scripts

Every project must implement these scripts:

**Linting scripts**:
```json
"lint:js": "eslint src/**/*.js",
"lint:js:fix": "eslint --fix src/**/*.js"
```

**Formatting scripts**:
```json
"format": "prettier --write \"src/**/*.js\"",
"format:check": "prettier --check \"src/**/*.js\""
```

**Testing scripts**:
```json
"test": "jest",
"test:watch": "jest --watch",
"test:coverage": "jest --coverage",
"test:ci-strict": "jest --ci --coverage --watchAll=false --maxWorkers=2"
```

**Quality scripts**:
```json
"quality": "npm run lint:js && npm run format:check",
"quality:fix": "npm run lint:js:fix && npm run format"
```

### Optional Build Scripts

For projects generating bundled or minified assets:

**Build scripts**:
```json
"build": "webpack --mode production",
"build:dev": "webpack --mode development",
"build:watch": "webpack --mode development --watch",
"clean": "del-cli target/classes/META-INF/resources target/dist"
```

**Development server** (if applicable):
```json
"dev": "webpack serve --mode development --open"
```

### CSS-in-JS Projects

Add StyleLint scripts for projects using CSS-in-JS:

```json
"lint:style": "stylelint src/**/*.js",
"lint:style:fix": "stylelint --fix src/**/*.js",
"lint": "npm run lint:js && npm run lint:style",
"lint:fix": "npm run lint:js:fix && npm run lint:style:fix"
```

### Script Patterns and Conventions

**Naming patterns**:
- Use colons to namespace related scripts: `lint:js`, `lint:style`
- Use `:fix` suffix for auto-fixing variants
- Use `:check` suffix for validation-only variants
- Use `:ci` suffix for CI/CD-specific configurations
- Use `:watch` suffix for file-watching variants

**Composition pattern**:
- Combine related checks in `quality` script
- Combine all fixes in `quality:fix` script
- Keep technology-specific scripts separate

## Project Type Adaptations

### Determining Your Project Type

Choose the structure that matches your project's integration:

**Standard Maven Project**: Java application with embedded JavaScript
- Use `src/main/resources/static/js/` structure
- Target outputs to `target/classes/META-INF/resources/`
- Integrate with Maven resource processing

**Quarkus DevUI Extension**: Quarkus development UI
- Use `src/main/resources/dev-ui/` structure
- Follow `qwc-` component naming convention
- Include Lit web component dependencies

**NiFi Extension**: Apache NiFi processor UI
- Use `src/main/webapp/` structure
- Follow `nf-` component naming convention
- Include Webpack bundling for WAR packaging

**Standalone Project**: Pure JavaScript library/application
- Use `src/main/js/` structure
- Output to `dist/` for npm publishing
- Standard npm package conventions

### Path Configuration by Project Type

Adjust paths in npm scripts based on project type:

**Standard Maven**:
```json
"lint:js": "eslint src/main/resources/static/js/**/*.js",
"test": "jest --testPathPattern=src/test/js"
```

**Quarkus DevUI**:
```json
"lint:js": "eslint src/main/resources/dev-ui/**/*.js",
"test": "jest --testPathPattern=src/test/js"
```

**NiFi Extension**:
```json
"lint:js": "eslint src/main/webapp/js/**/*.js",
"test": "jest --testPathPattern=src/test/js"
```

**Standalone**:
```json
"lint:js": "eslint src/**/*.js",
"test": "jest"
```

## Git Ignore Requirements

### Essential Exclusions

All JavaScript projects must exclude these paths in `.gitignore`:

```gitignore
# Node.js runtime and dependencies
node_modules/
target/node/

# npm cache and logs
.npm/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Test coverage
target/coverage/
coverage/

# Build outputs
target/dist/
dist/
build/

# IDE files (optional but recommended)
.idea/
.vscode/
*.iml

# OS files (optional but recommended)
.DS_Store
Thumbs.db
```

**Critical exclusions**:
- `node_modules/` - npm dependencies (can be hundreds of MB)
- `target/node/` - Maven-installed Node.js (platform-specific binaries)
- `target/coverage/` - Test coverage reports (generated files)

### Why These Exclusions Matter

**node_modules/**:
- Can contain thousands of files
- Averages 100-500 MB per project
- Automatically regenerated via `npm install`
- Platform-specific native modules

**target/node/**:
- Platform-specific Node.js binaries
- Installed by frontend-maven-plugin
- Different per OS (Linux, Mac, Windows)
- Automatically downloaded during build

**Coverage and build outputs**:
- Generated during test and build phases
- Can be recreated from source
- Often large file sizes
- Not needed in version control

## Node.js Version Requirements

### Required Versions

**Node.js**: v20.12.2 LTS (exact version)
- LTS (Long Term Support) for stability
- Exact version managed by frontend-maven-plugin
- Consistent across all environments (development, CI/CD, production)
- Updated periodically following Node.js LTS schedule

**npm**: 10.5.0 or compatible
- Bundled with Node.js installation
- Supports modern package.json features
- Compatible with `"type": "module"`

### Lock File Requirements

**Always commit package-lock.json**:
- Ensures consistent dependency versions across environments
- Documents exact dependency tree
- Critical for reproducible builds
- Prevents "works on my machine" issues

**Never commit**:
- `node_modules/` directory
- `yarn.lock` (if using npm)
- Platform-specific lock files

## Environment Configuration

### Development Environment Setup

**Required tools**:
1. Node.js v20.12.2 LTS (via nvm or direct install)
2. npm 10.5.0+ (bundled with Node.js)
3. Git with proper `.gitignore` configuration
4. IDE with ESLint/Prettier extensions (VS Code, IntelliJ)

**Environment consistency**:
- All team members use same Node.js version
- Lock file committed and up to date
- Configuration files (.prettierrc.js, eslint.config.js) in sync
- Maven frontend-maven-plugin installs consistent Node.js version

### CI/CD Environment

**Requirements**:
- Use frontend-maven-plugin for Node.js installation
- Set `CI=true` environment variable for test execution
- Enable test coverage reporting
- Configure Maven to run quality scripts

For complete environment variable configuration and purposes, see **[maven-integration.md](maven-integration.md)** section "Environment Variable Purposes".

## Best Practices

1. **Follow project type conventions** - Use appropriate structure for Maven/Quarkus/NiFi/Standalone
2. **Use kebab-case naming** - Consistent file naming across all JavaScript files
3. **Configure type: "module"** - Enable ES module support in package.json
4. **Commit package-lock.json** - Ensure reproducible builds
5. **Exclude node_modules/** - Never commit dependencies
6. **Implement all required scripts** - lint, format, test, quality scripts
7. **Use framework-specific prefixes** - `qwc-` for Quarkus, `nf-` for NiFi
8. **Organize by feature** - Group related components in subdirectories
9. **Separate tests from source** - Clear src/test directory separation
10. **Document project structure** - Update README.md with structure explanation

## Common Issues

### Issue: node_modules/ committed to Git

**Symptoms**: Large repository size, many untracked files

**Solution**:
```bash
# Remove from Git
git rm -r --cached node_modules/
# Add to .gitignore
echo "node_modules/" >> .gitignore
# Commit changes
git add .gitignore
git commit -m "fix: remove node_modules from Git"
```

### Issue: Inconsistent dependencies across environments

**Cause**: Missing or outdated package-lock.json

**Solution**: See [dependency-management.md](dependency-management.md) "Inconsistent Dependencies Across Environments" section for complete troubleshooting steps.

### Issue: Wrong project structure for framework

**Symptoms**: Files not found during build, tests fail to locate sources

**Solution**:
- Verify project type (Maven/Quarkus/NiFi/Standalone)
- Use appropriate directory structure for project type
- Update npm script paths to match structure
- Update Jest configuration testMatch patterns

### Issue: Configuration files not loading

**Cause**: Missing `"type": "module"` in package.json

**Solution**:
```json
{
  "type": "module"
}
```
Then update all configuration files to use ES module syntax (export default).
