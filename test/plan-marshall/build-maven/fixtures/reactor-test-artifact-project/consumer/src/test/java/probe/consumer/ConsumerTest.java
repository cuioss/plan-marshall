package probe.consumer;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

import probe.producer.SharedFixture;

class ConsumerTest {

    @Test
    void readsSharedFixture() {
        assertEquals("shared", SharedFixture.value());
    }
}
