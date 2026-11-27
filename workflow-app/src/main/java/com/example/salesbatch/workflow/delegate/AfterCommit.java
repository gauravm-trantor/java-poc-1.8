package com.example.salesbatch.workflow.delegate;

import org.activiti.engine.impl.cfg.TransactionListener;
import org.activiti.engine.impl.cfg.TransactionState;
import org.activiti.engine.impl.context.Context;
import org.activiti.engine.impl.interceptor.CommandContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Runs an audit write once the engine's transaction has committed.
 *
 * The audit store (HBase) is not part of the engine's transaction. A status written while a step's transaction is
 * still open can be seen by a client before the engine has created the approval task or ended the run, and the
 * client then acts too early. Written after the commit, a status a client sees is already true in the engine
 * (card SBJ17-11).
 */
final class AfterCommit {

    private static final Logger LOG = LoggerFactory.getLogger(AfterCommit.class);

    private AfterCommit() {}

    /**
     * Runs {@code write} after the current engine command commits, or at once when no command is running.
     * A write that fails after the commit is logged, not thrown: the step has already committed, so there is
     * nothing left to roll back or retry.
     */
    static void run(final String processInstanceId, final Runnable write) {
        CommandContext commandContext = Context.getCommandContext();
        if (commandContext == null) {
            write.run();
            return;
        }
        commandContext.getTransactionContext().addTransactionListener(TransactionState.COMMITTED,
                new TransactionListener() {
                    @Override
                    public void execute(CommandContext committed) {
                        try {
                            write.run();
                        } catch (RuntimeException e) {
                            LOG.error("Process {}: audit write after commit failed", processInstanceId, e);
                        }
                    }
                });
    }
}
