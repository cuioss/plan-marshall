package de.cuioss.portal.sample;

import de.cuioss.tools.logging.CuiLogger;
import static de.cuioss.portal.sample.SampleLogMessages.INFO;
import static de.cuioss.portal.sample.SampleLogMessages.WARN;
import static de.cuioss.portal.sample.SampleLogMessages.ERROR;

/**
 * Sample class demonstrating valid CUI logging patterns.
 * All LOGGER statements in this file are compliant with CUI standards.
 */
public class ValidLoggerUsage {

    private static final CuiLogger LOGGER = new CuiLogger(ValidLoggerUsage.class);

    public void processUser(String userId) {
        // Valid: INFO level uses LogRecord
        LOGGER.info(INFO.USER_PROCESSING_STARTED, userId);

        try {
            performProcessing(userId);
            // Valid: INFO level uses LogRecord
            LOGGER.info(INFO.USER_PROCESSING_COMPLETED, userId);
        } catch (Exception e) {
            // Valid: ERROR level uses LogRecord with exception first
            LOGGER.error(e, ERROR.USER_PROCESSING_FAILED, userId, e.getMessage());
        }
    }

    public void debugOperation(String data) {
        // Valid: DEBUG level uses direct string (no LogRecord)
        LOGGER.debug("Processing data: %s", data);

        // Valid: TRACE level uses direct string (no LogRecord)
        LOGGER.trace("Detailed trace for data processing");
    }

    public void warnOnCondition(boolean condition) {
        if (condition) {
            // Valid: WARN level uses LogRecord
            LOGGER.warn(WARN.CONDITION_TRIGGERED);
        }
    }

    private void performProcessing(String userId) {
        // Processing logic here
        LOGGER.trace("Internal processing step for user: %s", userId);
    }
}
