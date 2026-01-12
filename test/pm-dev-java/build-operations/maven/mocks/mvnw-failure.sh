#!/bin/bash
# Mock Maven wrapper: Simulate failed build with compilation error
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

# Create realistic failed build output with compilation errors
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
[INFO] Compiling 5 source files to /path/to/target/classes
[ERROR] /src/main/java/com/example/Service.java:[45,20] cannot find symbol
[ERROR]   symbol:   class MissingType
[ERROR]   location: class com.example.Service
[ERROR] /src/main/java/com/example/Handler.java:[78,15] incompatible types: String cannot be converted to int
[INFO] ------------------------------------------------------------------------
[INFO] BUILD FAILURE
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  5.123 s
[INFO] Finished at: 2025-11-25T14:30:22+01:00
[INFO] ------------------------------------------------------------------------
[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.11.0:compile (default-compile) on project test-project: Compilation failure: Compilation failure:
[ERROR] /src/main/java/com/example/Service.java:[45,20] cannot find symbol
[ERROR]   symbol:   class MissingType
[ERROR]   location: class com.example.Service
[ERROR] /src/main/java/com/example/Handler.java:[78,15] incompatible types: String cannot be converted to int
[ERROR] -> [Help 1]
EOF

exit 1
