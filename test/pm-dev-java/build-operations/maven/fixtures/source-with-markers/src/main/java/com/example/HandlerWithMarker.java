package com.example;

import java.util.logging.Logger;

public class HandlerWithMarker {

    private static final Logger LOGGER = Logger.getLogger(HandlerWithMarker.class.getName());

    public void handleRequest() {
        /*~~(TODO: CuiLogRecordPatternRecipe - LOGGER.debug uses direct string)>*/
        LOGGER.fine("Processing request");
    }
}
