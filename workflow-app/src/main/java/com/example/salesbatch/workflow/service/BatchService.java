package com.example.salesbatch.workflow.service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.activiti.engine.HistoryService;
import org.activiti.engine.RuntimeService;
import org.activiti.engine.TaskService;
import org.activiti.engine.history.HistoricProcessInstance;
import org.activiti.engine.history.HistoricVariableInstance;
import org.activiti.engine.runtime.ProcessInstance;
import org.activiti.engine.task.Task;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.salesbatch.common.SalesRepository;
import com.example.salesbatch.workflow.delegate.AuditWrites;
import com.example.salesbatch.workflow.delegate.RunFailure;

@Service
public class BatchService {

    public static final String PROCESS_KEY = "salesBatch";

    private final RuntimeService runtimeService;
    private final TaskService taskService;
    private final SalesRepository repository;
    private final HistoryService historyService;

    @Autowired
    public BatchService(RuntimeService runtimeService, TaskService taskService, SalesRepository repository,
            HistoryService historyService) {
        this.runtimeService = runtimeService;
        this.taskService = taskService;
        this.repository = repository;
        this.historyService = historyService;
    }

    /**
     * Starts a run and returns its id at once. Ingest and the Spark job run in the background (job executor);
     * poll {@link #status(String)} until it is WAITING_APPROVAL or FAILED.
     */
    public String start(String csvPath, String businessDate) {
        if (businessDate == null || !businessDate.matches("\\d{8}")) {
            throw new IllegalArgumentException("businessDate must be yyyyMMdd");
        }
        if (csvPath == null || csvPath.trim().isEmpty()) {
            throw new IllegalArgumentException("csvPath is required");
        }
        Map<String, Object> vars = new HashMap<>();
        vars.put("csvPath", csvPath);
        vars.put("businessDate", businessDate);
        vars.put("failed", false); // read by the gateways after each async step
        ProcessInstance instance = runtimeService.startProcessInstanceByKey(PROCESS_KEY, vars);
        return instance.getId();
    }

    /** Completes the approval task of a run. */
    public void approve(String processInstanceId, boolean approved, String approver) {
        List<Task> tasks = taskService.createTaskQuery().processInstanceId(processInstanceId).taskDefinitionKey("approval").list();
        if (tasks.isEmpty()) {
            throw new IllegalStateException("No pending approval for process instance " + processInstanceId);
        }
        Map<String, Object> vars = new HashMap<>();
        vars.put("approved", approved);
        vars.put("approver", approver == null ? "unknown" : approver);
        taskService.complete(tasks.get(0).getId(), vars);
    }

    /**
     * Audit status (QUEUED, RUNNING, WAITING_APPROVAL, COMPLETED, REJECTED, FAILED) or null if the id is unknown.
     *
     * WAITING_APPROVAL and FAILED are written after the engine commits (card SBJ17-11). If the audit store was down
     * for longer than that write's retries, the audit still says RUNNING while the engine has moved on. The engine is
     * then the record: a RUNNING run with an approval task is written as WAITING_APPROVAL, and a RUNNING run the
     * engine has ended is written as FAILED with its reason (COMPLETED and REJECTED are written inside their step, so
     * an ended run still at RUNNING can only have failed). The repair writes only while the audit still says RUNNING.
     */
    public String status(String processInstanceId) {
        String status = repository.auditStatus(processInstanceId);
        if (!"RUNNING".equals(status)) {
            return status;
        }
        if (taskService.createTaskQuery().processInstanceId(processInstanceId).taskDefinitionKey("approval")
                .count() > 0) {
            AuditWrites.writeIf(repository, processInstanceId, "RUNNING", "WAITING_APPROVAL");
            return repository.auditStatus(processInstanceId);
        }
        if (runtimeService.createProcessInstanceQuery().processInstanceId(processInstanceId).count() == 0) {
            HistoricProcessInstance ended = historyService.createHistoricProcessInstanceQuery()
                    .processInstanceId(processInstanceId).finished().singleResult();
            if (ended != null) {
                AuditWrites.failIf(repository, processInstanceId, "RUNNING", failureReason(processInstanceId));
                return repository.auditStatus(processInstanceId);
            }
        }
        return status;
    }

    private String failureReason(String processInstanceId) {
        HistoricVariableInstance reason = historyService.createHistoricVariableInstanceQuery()
                .processInstanceId(processInstanceId).variableName(RunFailure.FAILURE_REASON).singleResult();
        return reason == null || reason.getValue() == null
                ? "The run failed; its reason was not recorded" : String.valueOf(reason.getValue());
    }

    /** Why a run failed, or null. */
    public String error(String processInstanceId) {
        return repository.auditError(processInstanceId);
    }
}
