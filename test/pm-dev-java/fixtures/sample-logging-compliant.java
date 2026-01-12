package de.cuioss.tools.sample;

import java.util.logging.Logger;
import de.cuioss.tools.logging.LogRecord;

/**
 * Sample class with compliant logging.
 * INFO/WARN/ERROR/FATAL use LogRecord
 * DEBUG/TRACE use direct strings
 */
public class CompliantLogging {

    private static final Logger LOGGER = Logger.getLogger(CompliantLogging.class.getName());

    public void doSomething() {
        // DEBUG uses direct string - COMPLIANT
        LOGGER.debug("Starting operation with value: " + value);

        // TRACE uses direct string - COMPLIANT
        LOGGER.trace("Detailed trace for debugging");

        // INFO uses LogRecord - COMPLIANT
        LOGGER.info(INFO.OPERATION_STARTED, "operation-123");

        // WARN uses LogRecord - COMPLIANT
        LOGGER.warn(WARN.VALIDATION_FAILED, "field-name");

        // ERROR uses LogRecord - COMPLIANT
        LOGGER.error(ERROR.PROCESSING_FAILED, exception);
    }
}
