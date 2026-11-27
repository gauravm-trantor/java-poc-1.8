package com.example.salesbatch.workflow.delegate;

import static org.junit.Assert.assertTrue;

import java.util.concurrent.atomic.AtomicBoolean;

import org.junit.Test;

/** Outside an engine command there is no transaction to wait for, so the write runs at once (card SBJ17-11). */
public class AfterCommitTest {

    @Test
    public void writesAtOnceOutsideAnEngineCommand() {
        AtomicBoolean written = new AtomicBoolean();

        AfterCommit.run("no-process", () -> written.set(true));

        assertTrue(written.get());
    }
}
