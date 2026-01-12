# Build System Integration

Standards for integrating Cypress E2E tests with NPM scripts, Maven build system, and CI/CD pipelines.

## NPM Scripts Configuration

Add Cypress-specific scripts to `package.json` for convenient test execution.

### Standard Script Configuration

```json
{
  "scripts": {
    "test:e2e": "cypress run",
    "test:e2e:open": "cypress open",
    "test:e2e:chrome": "cypress run --browser chrome",
    "test:e2e:firefox": "cypress run --browser firefox",
    "test:e2e:edge": "cypress run --browser edge",
    "test:e2e:headed": "cypress run --headed",
    "test:e2e:spec": "cypress run --spec",
    "test:e2e:ci": "cypress run --browser chrome --headless --config video=true,screenshotOnRunFailure=true"
  }
}
```

### Script Descriptions

**test:e2e**
- Run all E2E tests headlessly in Electron browser
- Default execution mode for local development
- Fast execution, suitable for quick validation

**test:e2e:open**
- Open Cypress Test Runner GUI
- Interactive test development and debugging
- Visual test execution with time-travel debugging

**test:e2e:chrome / firefox / edge**
- Run tests in specific browser
- Validate cross-browser compatibility
- Test browser-specific behaviors

**test:e2e:headed**
- Run tests with visible browser window
- Useful for debugging test failures
- Observe test execution in real-time

**test:e2e:spec**
- Run specific test file or pattern
- Example: `npm run test:e2e:spec cypress/e2e/auth/login.cy.js`
- Faster feedback during development

**test:e2e:ci**
- CI/CD optimized configuration
- Enables video recording and screenshots
- Uses Chrome for consistency across environments

## Maven Integration

Integrate Cypress tests with Maven build lifecycle using frontend-maven-plugin.

### Maven Plugin Configuration

```xml
<!-- pom.xml -->
<build>
  <plugins>
    <!-- Frontend Maven Plugin for NPM integration -->
    <plugin>
      <groupId>com.github.eirslett</groupId>
      <artifactId>frontend-maven-plugin</artifactId>
      <version>1.15.0</version>

      <configuration>
        <nodeVersion>v20.11.0</nodeVersion>
        <npmVersion>10.2.4</npmVersion>
        <workingDirectory>${project.basedir}/src/main/webapp</workingDirectory>
        <installDirectory>${project.build.directory}</installDirectory>
      </configuration>

      <executions>
        <!-- Install Node and NPM -->
        <execution>
          <id>install-node-and-npm</id>
          <goals>
            <goal>install-node-and-npm</goal>
          </goals>
          <phase>generate-resources</phase>
        </execution>

        <!-- Install NPM dependencies -->
        <execution>
          <id>npm-install</id>
          <goals>
            <goal>npm</goal>
          </goals>
          <phase>generate-resources</phase>
          <configuration>
            <arguments>ci</arguments>
          </configuration>
        </execution>

        <!-- Run Cypress E2E tests -->
        <execution>
          <id>cypress-tests</id>
          <goals>
            <goal>npm</goal>
          </goals>
          <phase>integration-test</phase>
          <configuration>
            <arguments>run test:e2e:ci</arguments>
            <skip>${skipTests}</skip>
          </configuration>
        </execution>
      </executions>
    </plugin>
  </plugins>
</build>
```

### Maven Build Phases

**generate-resources**
- Install Node.js and NPM
- Install project dependencies
- Prepare test environment

**integration-test**
- Execute Cypress E2E tests
- Run after application deployment
- Validate complete application behavior

### Maven Properties

```xml
<properties>
  <!-- Node and NPM versions -->
  <node.version>v20.11.0</node.version>
  <npm.version>10.2.4</npm.version>

  <!-- Skip E2E tests flag -->
  <skipE2ETests>false</skipE2ETests>

  <!-- Frontend directory -->
  <frontend.directory>${project.basedir}/src/main/webapp</frontend.directory>
</properties>
```

### Maven Profiles

Create profiles for different test execution modes:

```xml
<profiles>
  <!-- Profile for running E2E tests in Chrome -->
  <profile>
    <id>e2e-chrome</id>
    <build>
      <plugins>
        <plugin>
          <groupId>com.github.eirslett</groupId>
          <artifactId>frontend-maven-plugin</artifactId>
          <executions>
            <execution>
              <id>cypress-tests</id>
              <configuration>
                <arguments>run test:e2e:chrome</arguments>
              </configuration>
            </execution>
          </executions>
        </plugin>
      </plugins>
    </build>
  </profile>

  <!-- Profile for opening Cypress Test Runner -->
  <profile>
    <id>e2e-open</id>
    <build>
      <plugins>
        <plugin>
          <groupId>com.github.eirslett</groupId>
          <artifactId>frontend-maven-plugin</artifactId>
          <executions>
            <execution>
              <id>cypress-open</id>
              <goals>
                <goal>npm</goal>
              </goals>
              <phase>integration-test</phase>
              <configuration>
                <arguments>run test:e2e:open</arguments>
              </configuration>
            </execution>
          </executions>
        </plugin>
      </plugins>
    </build>
  </profile>

  <!-- Profile for skipping E2E tests -->
  <profile>
    <id>skip-e2e</id>
    <properties>
      <skipE2ETests>true</skipE2ETests>
    </properties>
  </profile>
</profiles>
```

### Maven Execution Examples

```bash
# Run full build with E2E tests
mvn clean verify

# Run build skipping E2E tests
mvn clean verify -DskipE2ETests=true

# Run build with Chrome browser
mvn clean verify -Pe2e-chrome

# Open Cypress Test Runner
mvn integration-test -Pe2e-open

# Run only E2E tests (skip unit tests)
mvn integration-test -DskipTests=true
```

## Dependency Management

### Required Dependencies

```json
{
  "devDependencies": {
    "cypress": "^13.0.0",
    "eslint": "^8.0.0",
    "eslint-plugin-cypress": "^3.0.0",
    "eslint-plugin-jsdoc": "^48.0.0",
    "eslint-plugin-sonarjs": "^0.23.0",
    "eslint-plugin-security": "^2.1.0",
    "eslint-plugin-unicorn": "^51.0.0"
  }
}
```

### Version Management

**Cypress:**
- Use latest stable major version (13.x recommended)
- Review release notes for breaking changes
- Test compatibility before upgrading

**ESLint Plugins:**
- Keep plugins synchronized with ESLint version
- Update regularly for latest rules and fixes
- Validate configuration after updates

### Lock File Management

**package-lock.json (NPM) or yarn.lock (Yarn):**
- Commit lock file to version control
- Ensures consistent dependency versions
- Use `npm ci` in CI/CD for reproducible installs

## CI/CD Pipeline Configuration

### GitHub Actions Example

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  cypress-run:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        browser: [chrome, firefox]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Start application
        run: npm run start &

      - name: Wait for application
        run: npx wait-on http://localhost:8080 --timeout 60000

      - name: Run Cypress tests
        uses: cypress-io/github-action@v6
        with:
          browser: ${{ matrix.browser }}
          config: video=true,screenshotOnRunFailure=true

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: cypress-results-${{ matrix.browser }}
          path: |
            cypress/videos
            cypress/screenshots

      - name: Upload coverage (if configured)
        uses: codecov/codecov-action@v4
        if: success()
```

### Jenkins Pipeline Example

```groovy
// Jenkinsfile
pipeline {
    agent any

    tools {
        nodejs 'NodeJS 20'
    }

    stages {
        stage('Install Dependencies') {
            steps {
                dir('src/main/webapp') {
                    sh 'npm ci'
                }
            }
        }

        stage('Build Application') {
            steps {
                sh 'mvn clean package -DskipTests'
            }
        }

        stage('Start Application') {
            steps {
                sh 'java -jar target/application.jar &'
                sh 'npx wait-on http://localhost:8080 --timeout 60000'
            }
        }

        stage('Run E2E Tests') {
            steps {
                dir('src/main/webapp') {
                    sh 'npm run test:e2e:ci'
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'src/main/webapp/cypress/videos/**/*.mp4', allowEmptyArchive: true
            archiveArtifacts artifacts: 'src/main/webapp/cypress/screenshots/**/*.png', allowEmptyArchive: true
        }
        failure {
            emailext(
                subject: "E2E Tests Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "E2E tests failed. Check console output and artifacts.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

## Test Reporting

### Cypress Dashboard Integration

```javascript
// cypress.config.js
export default defineConfig({
  projectId: 'your-project-id',
  e2e: {
    // Enable Cypress Dashboard recording
    video: true,
    screenshotOnRunFailure: true
  }
});
```

**Run with Dashboard recording:**
```bash
npx cypress run --record --key <record-key>
```

### Mochawesome Reporter

```bash
npm install --save-dev mochawesome mochawesome-merge mochawesome-report-generator
```

```javascript
// cypress.config.js
export default defineConfig({
  e2e: {
    reporter: 'mochawesome',
    reporterOptions: {
      reportDir: 'cypress/reports/mochawesome',
      overwrite: false,
      html: true,
      json: true
    }
  }
});
```

**Generate combined report:**
```json
{
  "scripts": {
    "test:e2e:report": "npm run test:e2e:ci && npm run merge-reports && npm run generate-report",
    "merge-reports": "mochawesome-merge cypress/reports/mochawesome/*.json > cypress/reports/report.json",
    "generate-report": "marge cypress/reports/report.json -f report -o cypress/reports/html"
  }
}
```

## Environment Configuration

### Environment Variables

```javascript
// cypress.config.js
export default defineConfig({
  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:8080',
    env: {
      apiUrl: process.env.CYPRESS_API_URL || 'http://localhost:8080/api',
      username: process.env.CYPRESS_USERNAME,
      password: process.env.CYPRESS_PASSWORD
    }
  }
});
```

### CI/CD Environment Variables

**GitHub Actions:**
```yaml
env:
  CYPRESS_BASE_URL: http://localhost:8080
  CYPRESS_API_URL: http://localhost:8080/api
```

**Jenkins:**
```groovy
environment {
    CYPRESS_BASE_URL = 'http://localhost:8080'
    CYPRESS_API_URL = 'http://localhost:8080/api'
}
```

## Performance Optimization

### Parallel Test Execution

**Cypress Dashboard (paid):**
```bash
cypress run --record --parallel --ci-build-id $CI_BUILD_ID
```

**GitHub Actions Matrix:**
```yaml
strategy:
  matrix:
    containers: [1, 2, 3, 4]
steps:
  - uses: cypress-io/github-action@v6
    with:
      record: true
      parallel: true
      group: 'E2E Tests'
```

### Caching Strategies

**Cache Cypress binary:**
```yaml
# GitHub Actions
- name: Cache Cypress binary
  uses: actions/cache@v4
  with:
    path: ~/.cache/Cypress
    key: cypress-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
```

**Cache NPM modules:**
```yaml
- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
```

## Best Practices

**Build Integration:**
- Run E2E tests in integration-test phase
- Allow skipping tests via Maven property
- Use consistent browser across environments
- Enable video and screenshots for debugging

**CI/CD Pipeline:**
- Run tests on every pull request
- Test against multiple browsers when critical
- Archive test artifacts on failure
- Implement test result notifications
- Use matrix builds for parallel execution

**Performance:**
- Cache dependencies and Cypress binary
- Run tests in parallel when possible
- Use CI-optimized Cypress configuration
- Monitor test execution time

**Maintenance:**
- Keep dependencies updated
- Review and optimize slow tests
- Monitor flaky tests and fix root causes
- Maintain separate profiles for different execution modes
