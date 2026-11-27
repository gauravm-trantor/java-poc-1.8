package com.example.salesbatch.common;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

/** Throwaway, never merged: card SBJ17-2 checks that the maven job goes red on one failed test. */
public class SensitivityProbeTest {

    @Test
    public void failsOnPurpose() {
        assertEquals("the pipeline must fail on this", 1, 2);
    }
}
