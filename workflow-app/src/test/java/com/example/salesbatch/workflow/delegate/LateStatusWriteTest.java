package com.example.salesbatch.workflow.delegate;

import static org.junit.Assert.assertEquals;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

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

    @Test
    public void aLateWaitingApprovalDoesNotReplaceRejected() {
        TransactionListener afterCommit = sparkStepCommits();
        new RejectDelegate(repository).execute(execution); // rejected before the late write lands

        afterCommit.execute(commandContext);

        assertEquals("REJECTED", audit.get("p1"));
    }
}
