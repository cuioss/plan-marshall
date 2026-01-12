package com.example;

import java.util.logging.Logger;

public class ServiceWithMarkers {

    private static final Logger LOGGER = Logger.getLogger(ServiceWithMarkers.class.getName());

    public void methodWithLogRecordMarker() {
        /*~~(TODO: CuiLogRecordPatternRecipe - LOGGER call does not use LogRecord)>*/
        LOGGER.info("Direct string message without LogRecord");
    }

    public void methodWithExceptionMarker() {
        try {
            doSomethingRisky();
        /*~~(TODO: InvalidExceptionUsageRecipe - catch block does not follow pattern)>*/
        } catch (Exception e) {
            LOGGER.severe("Error: " + e.getMessage());
        }
    }

    public void methodWithOtherMarker() {
        /*~~(TODO: SomeOtherRecipe - this requires user review)>*/
        doSomethingElse();
    }

    private void doSomethingRisky() throws Exception {
        // Risky operation
    }

    private void doSomethingElse() {
        // Other operation
    }
}
