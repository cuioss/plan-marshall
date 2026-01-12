package com.example;

import java.util.logging.Logger;

/**
 * A clean service with no OpenRewrite markers.
 */
public class CleanService {

    private static final Logger LOGGER = Logger.getLogger(CleanService.class.getName());

    public void doWork() {
        LOGGER.info("Working...");
    }
}
