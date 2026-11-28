package com.example.salesbatch.workflow.delegate;

import static org.junit.Assert.assertEquals;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.activiti.engine.delegate.DelegateExecution;
import org.activiti.engine.impl.cfg.TransactionContext;
import org.activiti.engine.impl.cfg.TransactionListener;
import org.activiti.engine.impl.cfg.TransactionState;
import org.activiti.engine.impl.context.Context;
import org.activiti.engine.impl.interceptor.CommandContext;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.ArgumentCaptor;

import com.example.salesbatch.common.AggRecord;
import com.example.salesbatch.common.SalesRecord;
import com.example.salesbatch.common.SalesRepository;
import com.example.salesbatch.workflow.spark.SparkJobLauncher;

/**
 * WAITING_APPROVAL lands after the Spark step commits, when the approval task already exists. A caller who approves
 * in between must keep the newer status (card SBJ17-11).
 */
public class LateStatusWriteTest {

    private final Map<String, String> audit = new ConcurrentHashMap<>();
    private final SalesRepository repository = new SalesRepository() {
        @Override public void saveRaw(java.util.Collection<SalesRecord> records) {}
        @Override public java.util.List<SalesRecord> loadRaw(String date) { return null; }
        @Override public java.util.List<AggRecord> loadAgg(String date) { return null; }
        @Override public void updateAudit(String pid, String status, String approver) { audit.put(pid, status); }
        @Override public String auditStatus(String pid) { return audit.get(pid); }
        @Override public void recordError(String pid, String message) {}
        @Override public String auditError(String pid) { return null; }
    };
    private final CommandContext commandContext = mock(CommandContext.class);
    private final TransactionContext transactionContext = mock(TransactionContext.class);
    private final DelegateExecution execution = mock(DelegateExecution.class);

    @Before
    public void insideTheSparkStep() {
        when(commandContext.getTransactionContext()).thenReturn(transactionContext);
        Context.setCommandContext(commandContext);
        when(execution.getProcessInstanceId()).thenReturn("p1");
        when(execution.getVariable("businessDate")).thenReturn("20261113");
        when(execution.getVariable("approver")).thenReturn("alice");
        audit.put("p1", "RUNNING");
    }

    @After
    public void leaveTheCommand() {
        Context.removeCommandContext();
    }

    private TransactionListener sparkStepCommits() {
        new SparkJobDelegate(mock(SparkJobLauncher.class), repository).execute(execution);
        ArgumentCaptor<TransactionListener> listener = ArgumentCaptor.forClass(TransactionListener.class);
        verify(transactionContext).addTransactionListener(eq(TransactionState.COMMITTED), listener.capture());
        return listener.getValue();
    }

    @Test
    public void aRunStillRunningAfterTheCommitSaysItWaitsForApproval() {
        TransactionListener afterCommit = sparkStepCommits();
        assertEquals("not before the commit", "RUNNING", audit.get("p1"));

        afterCommit.execute(commandContext);

        assertEquals("WAITING_APPROVAL", audit.get("p1"));
    }

    @Test
    public void aLateWaitingApprovalDoesNotReplaceCompleted() {
        TransactionListener afterCommit = sparkStepCommits();
        AuditWrites.write(repository, "p1", "COMPLETED", "alice"); // approved before the late write lands

        afterCommit.execute(commandContext);

        assertEquals("COMPLETED", audit.get("p1"));
    }

    /**
     * The approval's COMPLETED arrives while the late write has read RUNNING and not yet written: it must wait, so
     * COMPLETED lands last.
     */
    @Test
    public void anApprovalThatArrivesDuringTheLateWriteLandsLast() throws Exception {
        CountDownLatch lateWriteHasRead = new CountDownLatch(1);
        CountDownLatch approvalStarted = new CountDownLatch(1);
        SalesRepository slowReader = new SalesRepository() {
            @Override public void saveRaw(java.util.Collection<SalesRecord> records) {}
            @Override public java.util.List<SalesRecord> loadRaw(String date) { return null; }
            @Override public java.util.List<AggRecord> loadAgg(String date) { return new java.util.ArrayList<>(); }
            @Override public void updateAudit(String pid, String status, String approver) { audit.put(pid, status); }
            @Override public String auditStatus(String pid) {
                String status = audit.get(pid);
                if (Thread.currentThread().getName().equals("late-write")) {
                    lateWriteHasRead.countDown();
                    await(approvalStarted); // the approval is now trying to write
                    sleep(300);             // and would have written by now, were it not for the lock
                }
                return status;
            }
            @Override public void recordError(String pid, String message) {}
            @Override public String auditError(String pid) { return null; }
        };
        Thread lateWrite = new Thread(() -> SparkJobDelegate.markWaitingForApproval(slowReader, "p1"), "late-write");
        lateWrite.start();
        await(lateWriteHasRead);
        Path reports = Files.createTempDirectory("sbj17-11-reports");
        Thread approval = new Thread(() -> {
            approvalStarted.countDown();
            try {
                new PublishDelegate(slowReader, reports.toString()).execute(execution);
            } catch (java.io.IOException e) {
                throw new IllegalStateException(e);
            }
        }, "approval");
        approval.start();
        lateWrite.join(5000);
        approval.join(5000);

        assertEquals("COMPLETED", audit.get("p1"));
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Test
    public void aLateWaitingApprovalDoesNotReplaceRejected() {
        TransactionListener afterCommit = sparkStepCommits();
        new RejectDelegate(repository).execute(execution); // rejected before the late write lands

        afterCommit.execute(commandContext);

        assertEquals("REJECTED", audit.get("p1"));
    }
}
