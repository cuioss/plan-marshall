#!/bin/bash
# Mock Maven wrapper: Simulate a surefire testFailureIgnore run — Maven exits 0
# and prints BUILD SUCCESS while the test summary reports errored tests and no
# [ERROR]/BUILD FAILURE marker. Reproduces the narrow untruthful-green window
# for the seam-(a) truthful-status regression.

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

cat > "$LOG_FILE" << 'EOF'
[INFO] Scanning for projects...
[INFO]
[INFO] -----------------------< com.example:test-project >-----------------------
[INFO] Building test-project 1.0.0
[INFO] --------------------------------[ jar ]---------------------------------
[INFO]
[INFO] --- maven-surefire-plugin:3.1.2:test (default-test) @ test-project ---
[INFO] Using auto detected provider org.apache.maven.surefire.junitplatform.JUnitPlatformProvider
[INFO]
[INFO] -------------------------------------------------------
[INFO]  T E S T S
[INFO] -------------------------------------------------------
[INFO] Running com.example.ServiceTest
[INFO] Tests run: 5, Failures: 0, Errors: 2, Skipped: 0, Time elapsed: 1.234 s -- in com.example.ServiceTest
[INFO]
[INFO] Results:
[INFO]
[INFO] Tests run: 5, Failures: 0, Errors: 2, Skipped: 0
[INFO]
[INFO] --- maven-jar-plugin:3.3.0:jar (default-jar) @ test-project ---
[INFO] Building jar: /path/to/target/test-project-1.0.0.jar
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  21.635 s
[INFO] Finished at: 2026-07-21T14:30:22+01:00
[INFO] ------------------------------------------------------------------------
EOF

exit 0
