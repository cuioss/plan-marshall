import de.cuioss.tools.logging.CuiLogger;

class Test {
    private static final CuiLogger LOGGER = new CuiLogger(Test.class);

    void method() {
        String username = "john";
        /*~~(TODO: INFO needs LogRecord. Suppress: // cui-rewrite:disable CuiLogRecordPatternRecipe)~~>*/LOGGER.info("User %s logged in", username);
    }
}
