package probe.producer;

/**
 * Test-source class the producer publishes through both of its test-jars: the default
 * "tests" test-jar (resolved by a type-only test-jar dependency) and the "generators"
 * test-jar (resolved by a classifier-qualified dependency).
 */
public class SharedFixture {

    public static String value() {
        return "shared";
    }
}
