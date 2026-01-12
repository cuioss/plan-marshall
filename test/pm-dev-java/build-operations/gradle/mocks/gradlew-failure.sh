#!/bin/bash
# Mock gradlew that simulates a failed build

cat << 'EOF'
> Task :compileJava FAILED

/Users/dev/project/src/main/java/com/example/Service.java:45:20: error: cannot find symbol
    private Logger logger = LoggerFactory.getLogger(Service.class);
                   ^
  symbol:   class Logger
  location: class Service

FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':compileJava'.
> Compilation failed; see the compiler error output for details.

BUILD FAILED in 5s
1 actionable task: 1 executed
EOF

exit 1
