#!/bin/bash
# Mock Maven wrapper: Simulate successful build
# Used for testing execute-maven-build.py

# Extract log file from -l argument
LOG_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        -l) LOG_FILE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [[ -z "$LOG_FILE" ]]; then
    echo "Error: No log file specified with -l flag" >&2
    exit 1
fi

# Create realistic successful build output
cat > "$LOG_FILE" << 'EOF'
[INFO] Scanning for projects...
[INFO]
[INFO] -----------------------< com.example:test-project >-----------------------
[INFO] Building test-project 1.0.0
[INFO] --------------------------------[ jar ]---------------------------------
[INFO]
[INFO] --- maven-clean-plugin:3.2.0:clean (default-clean) @ test-project ---
[INFO] Deleting /path/to/target
[INFO]
[INFO] --- maven-resources-plugin:3.3.1:resources (default-resources) @ test-project ---
[INFO] Copying 3 resources
[INFO]
[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ test-project ---
[INFO] Nothing to compile - all classes are up to date
[INFO]
[INFO] --- maven-resources-plugin:3.3.1:testResources (default-testResources) @ test-project ---
[INFO] Copying 1 resource
[INFO]
[INFO] --- maven-compiler-plugin:3.11.0:testCompile (default-testCompile) @ test-project ---
[INFO] Nothing to compile - all classes are up to date
[INFO]
[INFO] --- maven-surefire-plugin:3.1.2:test (default-test) @ test-project ---
[INFO] Using auto detected provider org.apache.maven.surefire.junitplatform.JUnitPlatformProvider
[INFO]
[INFO] -------------------------------------------------------
[INFO]  T E S T S
[INFO] -------------------------------------------------------
[INFO] Running com.example.ServiceTest
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 1.234 s -- in com.example.ServiceTest
[INFO]
[INFO] Results:
[INFO]
[INFO] Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
[INFO]
[INFO] --- maven-jar-plugin:3.3.0:jar (default-jar) @ test-project ---
[INFO] Building jar: /path/to/target/test-project-1.0.0.jar
[INFO]
[INFO] --- maven-install-plugin:3.1.1:install (default-install) @ test-project ---
[INFO] Installing /path/to/target/test-project-1.0.0.jar to ~/.m2/repository
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  21.635 s
[INFO] Finished at: 2025-11-25T14:30:22+01:00
[INFO] ------------------------------------------------------------------------
EOF

exit 0
