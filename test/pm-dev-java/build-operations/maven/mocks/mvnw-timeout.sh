#!/bin/bash
# Mock Maven wrapper: Simulate build that exceeds timeout
# Used for testing execute-maven-build.py timeout handling

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

# Create partial build output before "hanging"
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
[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ test-project ---
[INFO] Compiling 50 source files to /path/to/target/classes
EOF

# Simulate long-running build (5 minutes)
# Tests should use a short timeout (e.g., 1000ms) to trigger timeout quickly
sleep 300

exit 0
