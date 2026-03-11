package com.example;

/**
 * Service with OpenRewrite markers.
 */
public class ServiceWithMarkers {

    /*~~(TODO: CuiLogRecordPatternRecipe: Use LogRecord pattern for logging)>*/
    public void debug(String message) {
        System.out.println("DEBUG: " + message);
    }

    /*~~(TODO: CuiLogRecordPatternRecipe: Consider using LogRecord)>*/
    public void trace(String message) {
        System.out.println("TRACE: " + message);
    }
}
