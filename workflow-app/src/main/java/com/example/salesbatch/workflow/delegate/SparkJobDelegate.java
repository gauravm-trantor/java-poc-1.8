package com.example.salesbatch.workflow.delegate;

import org.activiti.engine.delegate.DelegateExecution;
import org.activiti.engine.delegate.JavaDelegate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import com.example.salesbatch.common.SalesRepository;
import com.example.salesbatch.workflow.spark.SparkJobLauncher;

@Component("sparkJobDelegate")
public class SparkJobDelegate implements JavaDelegate {

    private static final Logger LOG = LoggerFactory.getLogger(SparkJobDelegate.class);

    private final SparkJobLauncher launcher;
    private final SalesRepository repository;

    @Autowired
    public SparkJobDelegate(SparkJobLauncher launcher, SalesRepository repository) {
        this.launcher = launcher;
        this.repository = repository;
    }

    @Override
    public void execute(DelegateExecution execution) {
        String pid = execution.getProcessInstanceId();
        try {
            launcher.run((String) execution.getVariable("businessDate"));
        } catch (RuntimeException e) {
            RunFailure.mark(repository, execution, "spark", e);
            return;
        }
        // After the commit, so the approval task exists before a client can see the status.
        AfterCommit.run(repository, pid, () -> markWaitingForApproval(repository, pid));
    }

    /**
     * Writes WAITING_APPROVAL only while the run is still RUNNING. The approval task exists from the commit on, so a
     * caller may approve it before this write lands; COMPLETED or REJECTED is then newer and must stay.
     */
    static void markWaitingForApproval(SalesRepository repository, String pid) {
        if (!AuditWrites.writeIf(repository, pid, "RUNNING", "WAITING_APPROVAL")) {
            LOG.info("Process {}: status already moved past RUNNING; WAITING_APPROVAL not written", pid);
        }
    }
}
