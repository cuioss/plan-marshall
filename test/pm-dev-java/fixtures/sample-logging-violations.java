package de.cuioss.tools.sample;

import java.util.logging.Logger;

/**
 * Sample class with logging violations.
 * Demonstrates both types of violations:
 * 1. INFO/WARN/ERROR using direct strings (should use LogRecord)
 * 2. DEBUG/TRACE using LogRecord (should use direct strings)
 */
public class ViolationLogging {

    private static final Logger LOGGER = Logger.getLogger(ViolationLogging.class.getName());

    public void doSomethingWrong() {
        // VIOLATION: INFO with direct string (should use LogRecord)
        LOGGER.info("Starting operation without LogRecord");

        // VIOLATION: WARN with direct string (should use LogRecord)
        LOGGER.warn("This is a warning without LogRecord");

        // VIOLATION: ERROR with direct string (should use LogRecord)
        LOGGER.error("Error occurred: " + errorMessage);

        // VIOLATION: DEBUG with LogRecord (should use direct string)
        LOGGER.debug(INFO.SOME_DEBUG_MESSAGE, "param");

        // This is compliant - DEBUG with direct string
        LOGGER.debug("This debug message is correctly formatted");

        // This is compliant - INFO with LogRecord
        LOGGER.info(INFO.OPERATION_COMPLETED, "result");
    }
}
