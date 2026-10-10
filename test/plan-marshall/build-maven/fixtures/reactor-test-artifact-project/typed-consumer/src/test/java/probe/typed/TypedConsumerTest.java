package probe.typed;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

import probe.producer.SharedFixture;

class TypedConsumerTest {

    @Test
    void readsSharedFixture() {
        assertEquals("shared", SharedFixture.value());
    }
}
