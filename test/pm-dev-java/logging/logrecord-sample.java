package de.cuioss.portal.sample;

import de.cuioss.tools.logging.LogRecord;
import de.cuioss.tools.logging.LogRecordModel;
import lombok.experimental.UtilityClass;

/**
 * Sample LogMessages holder class for testing documentation generation.
 * Follows CUI DSL-style constants pattern.
 */
@UtilityClass
public final class SampleLogMessages {

    /** Module prefix for all log messages */
    public static final String PREFIX = "SAMPLE";

    /**
     * INFO level log messages (identifiers 001-099).
     */
    @UtilityClass
    public static final class INFO {

        /** Logged when user processing begins */
        public static final LogRecord USER_PROCESSING_STARTED = LogRecordModel.builder()
            .template("User processing started for user %s")
            .prefix(PREFIX)
            .identifier(1)
            .build();

        /** Logged when user processing completes successfully */
        public static final LogRecord USER_PROCESSING_COMPLETED = LogRecordModel.builder()
            .template("User processing completed for user %s")
            .prefix(PREFIX)
            .identifier(2)
            .build();

        /** Logged when data synchronization begins */
        public static final LogRecord DATA_SYNC_STARTED = LogRecordModel.builder()
            .template("Data synchronization started for %s records")
            .prefix(PREFIX)
            .identifier(3)
            .build();
    }

    /**
     * WARN level log messages (identifiers 100-199).
     */
    @UtilityClass
    public static final class WARN {

        /** Logged when an unusual condition is detected */
        public static final LogRecord CONDITION_TRIGGERED = LogRecordModel.builder()
            .template("Unusual condition triggered")
            .prefix(PREFIX)
            .identifier(100)
            .build();

        /** Logged when retry is needed */
        public static final LogRecord RETRY_NEEDED = LogRecordModel.builder()
            .template("Operation failed, retry %d of %d")
            .prefix(PREFIX)
            .identifier(101)
            .build();
    }

    /**
     * ERROR level log messages (identifiers 200-299).
     */
    @UtilityClass
    public static final class ERROR {

        /** Logged when user processing fails */
        public static final LogRecord USER_PROCESSING_FAILED = LogRecordModel.builder()
            .template("User processing failed for user %s: %s")
            .prefix(PREFIX)
            .identifier(200)
            .build();

        /** Logged when database connection fails */
        public static final LogRecord DATABASE_CONNECTION_FAILED = LogRecordModel.builder()
            .template("Database connection failed: %s")
            .prefix(PREFIX)
            .identifier(201)
            .build();
    }

    /**
     * FATAL level log messages (identifiers 300-399).
     */
    @UtilityClass
    public static final class FATAL {

        /** Logged when system cannot start */
        public static final LogRecord SYSTEM_STARTUP_FAILED = LogRecordModel.builder()
            .template("System startup failed: %s")
            .prefix(PREFIX)
            .identifier(300)
            .build();
    }
}
