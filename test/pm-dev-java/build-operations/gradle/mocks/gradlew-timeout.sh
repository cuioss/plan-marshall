#!/bin/bash
# Mock gradlew that sleeps to simulate a timeout

echo "> Task :compileJava"
sleep 10
echo "BUILD SUCCESSFUL in 10s"
exit 0
