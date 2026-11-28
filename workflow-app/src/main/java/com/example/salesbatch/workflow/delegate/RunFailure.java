package com.example.salesbatch.workflow.delegate;

import org.activiti.engine.delegate.DelegateExecution;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.example.salesbatch.common.SalesRepository;

/**
 * Marks a run as failed without throwing. Steps run in the background job executor, which retries a job that
 * throws; a bad CSV or a failed Spark job would just fail again. Instead the step records the reason and sets
 * {@code failed=true}, and the process routes to its failed end event. The one exception is an audit store that does
 * not answer: then the step throws and is retried, so the failure is not lost (see {@link AfterCommit}).
 */
public final class RunFailure {

    /** Process variable that holds why a run failed. */
    public static final String FAILURE_REASON = "failureReason";

    private static final Logger LOG = LoggerFactory.getLogger(RunFailure.class);

    private RunFailure() {}

    static void mark(SalesRepository repository, DelegateExecution execution, String step, Exception e) {
        String pid = execution.getProcessInstanceId();
        String message = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
        LOG.error("Process {}: step {} failed: {}", pid, step, message, e);
        // After the commit, so the run has ended before a client can see FAILED; the reason first, then the status.
        AfterCommit.run(repository, pid, () -> {
            repository.recordError(pid, message);
            repository.updateAudit(pid, "FAILED", null);
        });
        execution.setVariable("failed", true);
        // Kept in the engine's history, so a status read can still record the reason if the write above was lost.
        execution.setVariable(FAILURE_REASON, message);
    }
}
