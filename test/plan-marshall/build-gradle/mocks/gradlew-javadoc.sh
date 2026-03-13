#!/bin/bash
# Mock gradlew that simulates a build with javadoc warnings

cat << 'EOF'
> Task :compileJava
> Task :processResources
> Task :classes
> Task :javadoc
/Users/dev/project/src/main/java/com/example/Service.java:30: warning: no @param for name
    public void process(String name) {
                ^
/Users/dev/project/src/main/java/com/example/Service.java:45: warning: no @return
    public String getValue() {
                  ^
2 warnings

> Task :jar
> Task :assemble
> Task :test

13 tests completed, 0 failed

> Task :check
> Task :build

BUILD SUCCESSFUL in 25s
10 actionable tasks: 10 executed
EOF

exit 0
