package com.example.salesbatch.workflow.delegate;

import org.activiti.engine.impl.cfg.TransactionListener;
import org.activiti.engine.impl.cfg.TransactionState;
import org.activiti.engine.impl.context.Context;
import org.activiti.engine.impl.interceptor.CommandContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.example.salesbatch.common.SalesRepository;

/**
 * Runs an audit write once the engine's transaction has committed.
 *
 * The audit store (HBase) is not part of the engine's transaction. A status written while a step's transaction is
 * still open can be seen by a client before the engine has created the approval task or ended the run, and the
 * client then acts too early. Written after the commit, a status a client sees is already true in the engine
 * (card SBJ17-11).
 *
 * Two guards keep a failing audit store from going unnoticed. Before the commit, {@link #run} reads the run's
 * status: if the store is down, that read throws, the step rolls back and the job executor retries it, as it did
 * when the write itself was inside the transaction. After the commit, a write that fails is tried again a few
 * times; only if every attempt fails is it logged, because the step has committed and cannot be rolled back.
 */
final class AfterCommit {

    private static final Logger LOG = LoggerFactory.getLogger(AfterCommit.class);

    /** Pauses before the second and third attempt of a write that failed. */
    static final long[] RETRY_PAUSES_MILLIS = {200L, 1000L};

    private AfterCommit() {}

    /**
     * Checks that the audit store answers, then runs {@code write} after the current engine command commits, or at
     * once when no command is running.
     *
     * @throws RuntimeException from the check, so the step rolls back and is retried while the store is down
     */
    static void run(final SalesRepository repository, final String processInstanceId, final Runnable write) {
        repository.auditStatus(processInstanceId);
        CommandContext commandContext = Context.getCommandContext();
        if (commandContext == null) {
            attempt(processInstanceId, write, RETRY_PAUSES_MILLIS);
            return;
        }
        commandContext.getTransactionContext().addTransactionListener(TransactionState.COMMITTED,
                new TransactionListener() {
                    @Override
                    public void execute(CommandContext committed) {
                        attempt(processInstanceId, write, RETRY_PAUSES_MILLIS);
                    }
                });
    }

    /**
     * Runs {@code write}, and again after each pause while it throws. Returns whether it succeeded; it never throws,
     * because after the commit there is no step left to roll back.
     */
    static boolean attempt(String processInstanceId, Runnable write, long[] pausesMillis) {
        for (int i = 0; ; i++) {
            try {
                write.run();
                return true;
            } catch (RuntimeException e) {
                if (i >= pausesMillis.length) {
                    LOG.error("Process {}: audit write after commit failed {} times; the run's audit status was not"
                            + " updated", processInstanceId, i + 1, e);
                    return false;
                }
                LOG.warn("Process {}: audit write after commit failed, trying again: {}", processInstanceId,
                        e.getMessage());
                try {
                    Thread.sleep(pausesMillis[i]);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    LOG.error("Process {}: interrupted while retrying an audit write; the run's audit status was not"
                            + " updated", processInstanceId, e);
                    return false;
                }
            }
        }
    }
}
