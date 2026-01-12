package de.cuioss.tools.sample;

import de.cuioss.tools.logging.LogRecord;
import de.cuioss.tools.logging.LogRecordModel;

/**
 * Sample LogMessages holder class for testing documentation generation.
 */
public class SampleLogMessages {

    public static final String PREFIX = "CUI-SAMPLE";

    /**
     * INFO level log records (001-099).
     */
    public static final class INFO {

        /** Logged when an operation starts successfully. */
        public static final LogRecord OPERATION_STARTED = LogRecordModel.builder()
                .template("Operation '{}' started successfully")
                .identifier(1)
                .build();

        /** Logged when data is loaded from cache. */
        public static final LogRecord CACHE_HIT = LogRecordModel.builder()
                .template("Cache hit for key: {}")
                .identifier(2)
                .build();

        /** Logged when configuration is loaded. */
        public static final LogRecord CONFIG_LOADED = LogRecordModel.builder()
                .template("Configuration loaded from: {}")
                .identifier(3)
                .build();
    }

    /**
     * WARN level log records (100-199).
     */
    public static final class WARN {

        /** Logged when validation fails. */
        public static final LogRecord VALIDATION_FAILED = LogRecordModel.builder()
                .template("Validation failed for field: {}")
                .identifier(100)
                .build();

        /** Logged when deprecated API is used. */
        public static final LogRecord DEPRECATED_API = LogRecordModel.builder()
                .template("Deprecated API '{}' used, will be removed in version {}")
                .identifier(101)
                .build();
    }

    /**
     * ERROR level log records (200-299).
     */
    public static final class ERROR {

        /** Logged when processing fails. */
        public static final LogRecord PROCESSING_FAILED = LogRecordModel.builder()
                .template("Processing failed: {}")
                .identifier(200)
                .build();

        /** Logged when database connection fails. */
        public static final LogRecord DATABASE_ERROR = LogRecordModel.builder()
                .template("Database error: {}")
                .identifier(201)
                .build();
    }

    /**
     * FATAL level log records (300-399).
     */
    public static final class FATAL {

        /** Logged when system cannot start. */
        public static final LogRecord STARTUP_FAILED = LogRecordModel.builder()
                .template("System startup failed: {}")
                .identifier(300)
                .build();
    }
}
