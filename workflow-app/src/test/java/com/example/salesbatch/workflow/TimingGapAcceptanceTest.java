package com.example.salesbatch.workflow;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;

import org.activiti.engine.RuntimeService;
import org.activiti.engine.delegate.event.ActivitiActivityEvent;
import org.activiti.engine.delegate.event.ActivitiEvent;
import org.activiti.engine.delegate.event.ActivitiEventListener;
import org.activiti.engine.delegate.event.ActivitiEventType;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;

import com.example.salesbatch.workflow.config.AppConfig;
import com.example.salesbatch.workflow.service.BatchService;

/**
 * Acceptance tests for card SBJ17-11: a status a client can see is already true in the engine.
 *
 * The gap between the audit status and the engine's commit is a few milliseconds, so these tests widen it: while a
 * test runs, an engine event listener holds the background job for one second when the run reaches the approval task
 * (AC1) or its failed end (AC2). Both points are inside the job's transaction, after the status has been decided and
 * before the commit. If the status is written before the commit, a client sees it a whole second too early and the
 * test fails every time; if it is written after the commit, the hold changes nothing a client sees.
 *
 * Same Spring context as SalesBatchProcessTest, so no second engine shares the in-memory database.
 * Design: docs/cards/SBJ17-11.md, section Plan.
 */
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(classes = {AppConfig.class, TestInfraConfig.class})
public class TimingGapAcceptanceTest {

    private static final long HOLD_MILLIS = 1000;

    @BeforeClass
    public static void reportDirectory() throws Exception {
        // Same directory as the other test classes: the Spring context is cached and report.dir is read only once.
        Path reportDir = Files.createDirectories(Paths.get(System.getProperty("java.io.tmpdir"), "sales-batch-test-reports"));
        System.setProperty("report.dir", reportDir.toString());
    }

    @Autowired BatchService batchService;
    @Autowired InMemorySalesRepository repository;
    @Autowired RuntimeService runtimeService;

    private Path csv;
    private HoldAt hold;

    @Before
    public void sampleCsv() throws Exception {
        TestInfraConfig.failSpark = false;
        repository.clear();
        csv = Files.createTempFile("sales", ".csv");
        Files.write(csv, Arrays.asList(
                "orderId,productId,region,qty,amount",
                "A1,P1,EU,2,10.50",
                "A2,P1,EU,3,15.75",
                "A3,P2,US,1,4.00"), StandardCharsets.UTF_8);
    }

    @After
    public void clean() throws Exception {
        if (hold != null) {
            runtimeService.removeEventListener(hold);
            hold = null;
        }
        TestInfraConfig.failSpark = false;
        Files.deleteIfExists(csv);
    }

    @Test
    public void AC1_aRunThatSaysItWaitsForApprovalCanBeApprovedAtOnce() throws Exception {
        holdTheJobAt("approval");

        String id = batchService.start(csv.toString(), "20261118");
        Await.status(batchService, id, "WAITING_APPROVAL");
        batchService.approve(id, true, "alice"); // at once: no wait between the status and the approval

        assertEquals("COMPLETED", batchService.status(id));
        assertNull(runtimeService.createProcessInstanceQuery().processInstanceId(id).singleResult());
    }

    @Test
    public void AC2_aRunThatSaysItFailedHasAlreadyEnded() throws Exception {
        TestInfraConfig.failSpark = true;
        holdTheJobAt("endFailed");

        String id = batchService.start(csv.toString(), "20261119");
        Await.status(batchService, id, "FAILED");

        // at once: no wait between the status and these checks
        assertNull("the run says FAILED but has not ended",
                runtimeService.createProcessInstanceQuery().processInstanceId(id).singleResult());
        assertTrue(batchService.error(id).contains("spark-submit"));
    }

    private void holdTheJobAt(String activityId) {
        hold = new HoldAt(activityId);
        runtimeService.addEventListener(hold, ActivitiEventType.ACTIVITY_STARTED);
    }

    /** Holds the engine thread for HOLD_MILLIS when any run starts the given activity. */
    private static final class HoldAt implements ActivitiEventListener {

        private final String activityId;

        HoldAt(String activityId) {
            this.activityId = activityId;
        }

        @Override
        public void onEvent(ActivitiEvent event) {
            if (event instanceof ActivitiActivityEvent
                    && activityId.equals(((ActivitiActivityEvent) event).getActivityId())) {
                try {
                    Thread.sleep(HOLD_MILLIS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }

        @Override
        public boolean isFailOnException() {
            return false;
        }
    }
}
