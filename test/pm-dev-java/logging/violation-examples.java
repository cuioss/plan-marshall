package de.cuioss.portal.sample;

import de.cuioss.tools.logging.CuiLogger;
import static de.cuioss.portal.sample.SampleLogMessages.INFO;
import static de.cuioss.portal.sample.SampleLogMessages.ERROR;

/**
 * Sample class demonstrating logging violations.
 * This file contains intentional violations for testing detection.
 */
public class ViolationExamples {

    private static final CuiLogger LOGGER = new CuiLogger(ViolationExamples.class);

    public void methodWithViolations(String userId) {
        // VIOLATION: INFO level with direct string (should use LogRecord)
        LOGGER.info("User %s started processing", userId);

        // VIOLATION: WARN level with direct string (should use LogRecord)
        LOGGER.warn("Warning: unusual activity detected for %s", userId);

        // VIOLATION: ERROR level with direct string (should use LogRecord)
        LOGGER.error("Error processing user %s", userId);
    }

    public void debugWithLogRecord() {
        // VIOLATION: DEBUG level using LogRecord (should use direct string)
        LOGGER.debug(INFO.USER_PROCESSING_STARTED, "test");

        // VIOLATION: TRACE level using LogRecord (should use direct string)
        LOGGER.trace(INFO.USER_PROCESSING_COMPLETED, "test");
    }

    public void mixedViolations(String data) {
        // Valid: DEBUG with direct string
        LOGGER.debug("Starting operation with data: %s", data);

        // VIOLATION: INFO without LogRecord
        LOGGER.info("Operation started");

        // VIOLATION: ERROR without LogRecord
        LOGGER.error("Operation failed for data: %s", data);

        // Valid: TRACE with direct string
        LOGGER.trace("Trace: operation details for %s", data);
    }

    public void exceptionHandlingViolations(Exception e) {
        // VIOLATION: ERROR with exception but direct string (should use LogRecord)
        LOGGER.error(e, "Exception occurred: %s", e.getMessage());

        // VIOLATION: WARN with exception but direct string (should use LogRecord)
        LOGGER.warn(e, "Warning with exception");
    }
}
