= Coverage Analysis Pattern
:toc: left
:toclevels: 2
:sectnums:

== Overview

Coverage analysis identifies untested code paths, prioritizes gaps, and guides test improvement efforts.

**Core Principle:** Measure, analyze, prioritize, test. Use coverage data to systematically identify and close testing gaps, focusing on high-value code first.

== Coverage Types and Thresholds

[cols="1,1,1,2"]
|===
|Type |Minimum |Measurement |Use Case

|Line Coverage
|80%
|Lines executed / Total lines
|Basic metric, identifies untested code

|Branch Coverage
|70%
|Branches executed / Total branches
|Ensures both true/false paths tested

|Method Coverage
|100% public, 80% package-private
|Methods executed / Total methods
|Identifies completely untested methods
|===

**Exclusions:** Test classes, test utilities, generated code, configuration classes.

== JaCoCo Integration

=== Maven Configuration

[source,xml]
----
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.10</version>
  <executions>
    <execution>
      <goals><goal>prepare-agent</goal></goals>
    </execution>
    <execution>
      <id>report</id>
      <phase>test</phase>
      <goals><goal>report</goal></goals>
    </execution>
    <execution>
      <id>jacoco-check</id>
      <goals><goal>check</goal></goals>
      <configuration>
        <rules>
          <rule>
            <element>PACKAGE</element>
            <limits>
              <limit>
                <counter>LINE</counter>
                <value>COVEREDRATIO</value>
                <minimum>0.80</minimum>
              </limit>
              <limit>
                <counter>BRANCH</counter>
                <value>COVEREDRATIO</value>
                <minimum>0.70</minimum>
              </limit>
            </limits>
          </rule>
        </rules>
      </configuration>
    </execution>
  </executions>
</plugin>
----

=== Report Generation

[source,bash]
----
mvn clean test jacoco:report

# Report locations
target/site/jacoco/jacoco.xml   # XML for parsing
target/site/jacoco/index.html   # HTML for viewing
----

== Coverage Analysis Workflow

=== Step 1: Generate Report

[source,bash]
----
# Single-module
mvn clean test jacoco:report

# Multi-module
mvn clean test jacoco:report -pl :module-name
----

=== Step 2: Parse Coverage Data

[source,bash]
----
python3 .plan/execute-script.py pm-dev-java:junit-core:coverage gaps \
  --report target/site/jacoco/jacoco.xml \
  --output coverage-gaps.json \
  --pretty
----

**Output Structure:**

[source,json]
----
{
  "summary": {
    "line_coverage": 75.5,
    "branch_coverage": 68.2,
    "method_coverage": 82.3,
    "meets_thresholds": false
  },
  "gaps": [
    {
      "file": "src/main/java/com/example/UserValidator.java",
      "class": "com.example.UserValidator",
      "uncovered_lines": [45, 46, 52],
      "uncovered_branches": [{"line": 34, "missed": 1, "covered": 1}],
      "uncovered_methods": ["validateEmail"],
      "priority": "high"
    }
  ],
  "recommendations": [
    {"gap": "lines 45-46", "strategy": "Test error path", "priority": "high"}
  ]
}
----

=== Step 3: Prioritize Gaps

[cols="1,2,1"]
|===
|Priority |Characteristics |Action

|**High**
|Public methods, error handling, critical paths, validation, security
|Test immediately

|**Medium**
|Package-private methods, helper methods, data transformation
|Test after high priority

|**Low**
|Defensive null checks, impossible branches, logging only
|Test if time permits
|===

=== Step 4: Implement Tests

For each gap, identify strategy and implement:

[cols="1,2"]
|===
|Gap Type |Test Strategy

|Uncovered lines
|Add test case exercising that path; parameterized test for variations

|Uncovered branches
|Test both true/false conditions; test all switch cases

|Uncovered methods
|Add happy path test; add error path tests; add null/invalid input tests
|===

=== Step 5: Verify

Re-run coverage report and verify gaps are closed.

== Gap Analysis Patterns

[cols="1,2,2"]
|===
|Pattern |Symptom |Strategy

|**Error Handling**
|Catch blocks or throw statements uncovered
|Mock dependency to throw exception; verify exception propagation

|**Branch Coverage**
|One branch of if/else covered, other uncovered
|Add test for uncovered branch; parameterized test

|**Method Coverage**
|Public method with 0% coverage
|Add basic test exercising method; verify side effects

|**Complex Conditional**
|`if (a && b && c)` with partial coverage
|Truth table analysis; test relevant combinations
|===

**Example - Error Handling Gap:**

[source,java]
----
// Code: catch block uncovered
try {
    return repository.find(id);
} catch (NotFoundException e) {  // ← Uncovered
    throw new UserNotFoundException(id);
}

// Test: Mock to trigger exception
@Test
void loadUser_whenNotFound_throwsUserNotFoundException() {
    when(repository.find("123")).thenThrow(new NotFoundException());
    assertThrows(UserNotFoundException.class, () -> service.loadUser("123"));
}
----

== JaCoCo XML Structure

[source,xml]
----
<report name="project">
  <package name="com/example">
    <class name="com/example/UserService">
      <method name="validateUser" desc="(Ljava/lang/String;)Z">
        <counter type="LINE" missed="3" covered="8"/>
        <counter type="BRANCH" missed="2" covered="6"/>
        <counter type="METHOD" missed="0" covered="1"/>
      </method>
    </class>
  </package>
</report>
----

**Coverage Calculation:**

* Line: `covered / (covered + missed) * 100`
* Branch: `covered / (covered + missed) * 100`

== Best Practices

**DO:**

* Generate coverage report after every test run
* Focus on high-priority gaps first
* Use coverage to guide test creation (not as goal)
* Test behavior, not implementation

**DON'T:**

* Write tests just to hit coverage targets
* Test private methods directly (test through public API)
* Inflate coverage with trivial tests

== Script Contract

**analyze-coverage-gaps.py**

|===
|Parameter |Description |Default

|report_path
|Path to jacoco.xml
|Required

|threshold_line
|Line coverage threshold
|80

|threshold_branch
|Branch coverage threshold
|70
|===

**Exit Codes:** 0 = success, 1 = error

== References

* https://www.jacoco.org/jacoco/trunk/doc/[JaCoCo Documentation]
* https://www.jacoco.org/jacoco/trunk/doc/maven.html[Maven JaCoCo Plugin]
