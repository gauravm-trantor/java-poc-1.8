package com.example.salesbatch.workflow.delegate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.concurrent.atomic.AtomicInteger;

import org.activiti.engine.impl.cfg.TransactionContext;
import org.activiti.engine.impl.cfg.TransactionListener;
import org.activiti.engine.impl.cfg.TransactionState;
import org.activiti.engine.impl.context.Context;
import org.activiti.engine.impl.interceptor.CommandContext;
import org.junit.After;
import org.junit.Test;
import org.mockito.ArgumentCaptor;

import com.example.salesbatch.common.SalesRepository;

/** Writes after the engine commits, and does not lose a failing audit store silently (card SBJ17-11). */
public class AfterCommitTest {

    private static final long[] NO_PAUSES = {0L, 0L};

    private final SalesRepository repository = mock(SalesRepository.class);
    private final CommandContext commandContext = mock(CommandContext.class);
    private final TransactionContext transactionContext = mock(TransactionContext.class);

    @After
    public void leaveTheCommand() {
        if (Context.getCommandContext() == commandContext) {
            Context.removeCommandContext();
        }
    }

    /** Puts the test inside an engine command and returns what runs on COMMITTED. */
    private TransactionListener onCommit(Runnable insideTheCommand) {
        when(commandContext.getTransactionContext()).thenReturn(transactionContext);
        Context.setCommandContext(commandContext);
        insideTheCommand.run();
        ArgumentCaptor<TransactionListener> listener = ArgumentCaptor.forClass(TransactionListener.class);
        verify(transactionContext).addTransactionListener(eq(TransactionState.COMMITTED), listener.capture());
        return listener.getValue();
    }

    @Test
    public void writesAtOnceOutsideAnEngineCommand() {
        AtomicInteger writes = new AtomicInteger();

        AfterCommit.run(repository, "no-process", writes::incrementAndGet);

        assertEquals(1, writes.get());
    }

    @Test
    public void insideAnEngineCommandTheWriteWaitsForTheCommit() {
        AtomicInteger writes = new AtomicInteger();

        TransactionListener listener = onCommit(() -> AfterCommit.run(repository, "p1", writes::incrementAndGet));

        assertEquals("nothing is written before the commit", 0, writes.get());
        listener.execute(commandContext);
        assertEquals(1, writes.get());
    }

    @Test
    public void anAuditStoreThatDoesNotAnswerFailsTheStepBeforeTheCommit() {
        when(repository.auditStatus("p1")).thenThrow(new IllegalStateException("Cannot read audit"));
        when(commandContext.getTransactionContext()).thenReturn(transactionContext);
        Context.setCommandContext(commandContext);

        try {
            AfterCommit.run(repository, "p1", () -> fail("must not write"));
            fail("the step must throw, so the engine rolls it back and retries it");
        } catch (IllegalStateException expected) {
            assertEquals("Cannot read audit", expected.getMessage());
        }
        verify(transactionContext, org.mockito.Mockito.never()).addTransactionListener(any(), any());
    }

    @Test
    public void aWriteThatFailsAfterTheCommitIsTriedAgain() {
        AtomicInteger calls = new AtomicInteger();
        TransactionListener listener = onCommit(() -> AfterCommit.run(repository, "p1", () -> {
            if (calls.incrementAndGet() == 1) {
                throw new IllegalStateException("Cannot write to audit");
            }
        }));

        listener.execute(commandContext);

        assertEquals("one failure, then one write that worked", 2, calls.get());
    }

    @Test
    public void aWriteThatFailsOnceIsWrittenOnTheSecondAttempt() {
        AtomicInteger calls = new AtomicInteger();

        boolean written = AfterCommit.attempt("p1", () -> {
            if (calls.incrementAndGet() == 1) {
                throw new IllegalStateException("blip");
            }
        }, NO_PAUSES);

        assertTrue(written);
        assertEquals(2, calls.get());
    }

    @Test
    public void aWriteThatKeepsFailingIsTriedThreeTimesAndDoesNotThrow() {
        AtomicInteger calls = new AtomicInteger();

        boolean written = AfterCommit.attempt("p1", () -> {
            calls.incrementAndGet();
            throw new IllegalStateException("down");
        }, NO_PAUSES);

        assertFalse(written);
        assertEquals(3, calls.get());
    }
}
