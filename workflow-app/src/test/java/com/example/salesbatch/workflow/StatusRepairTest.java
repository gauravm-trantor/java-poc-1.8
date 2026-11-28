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
 * A WAITING_APPROVAL or FAILED write lost after the engine committed (audit store down longer than the retries) does
 * not leave the run at RUNNING: the next status read repairs it from the engine (card SBJ17-11, second review).
 *
 * The lost write is simulated by putting the audit back to RUNNING once the run has reached the status.
 * Same Spring context as SalesBatchProcessTest, so no second engine shares the in-memory database.
 */
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(classes = {AppConfig.class, TestInfraConfig.class})
public class StatusRepairTest {

    @BeforeClass
    public static void reportDirectory() throws Exception {
        Path reportDir = Files.createDirectories(Paths.get(System.getProperty("java.io.tmpdir"), "sales-batch-test-reports"));
        System.setProperty("report.dir", reportDir.toString());
    }

    @Autowired BatchService batchService;
    @Autowired InMemorySalesRepository repository;
    @Autowired RuntimeService runtimeService;

    private Path csv;

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
        TestInfraConfig.failSpark = false;
        Files.deleteIfExists(csv);
    }

    @Test
    public void aLostWaitingApprovalIsRepairedFromTheApprovalTask() throws Exception {
        String id = batchService.start(csv.toString(), "20261121");
        Await.status(batchService, id, "WAITING_APPROVAL");
        repository.updateAudit(id, "RUNNING", null); // the write after the commit was lost

        assertEquals("WAITING_APPROVAL", batchService.status(id));
        assertEquals("the repair is written, not only returned", "WAITING_APPROVAL", repository.auditStatus(id));
        batchService.approve(id, true, "alice");
        assertEquals("COMPLETED", batchService.status(id));
    }

    @Test
    public void aLostFailedIsRepairedFromTheEndedRunWithItsReason() throws Exception {
        TestInfraConfig.failSpark = true;
        String id = batchService.start(csv.toString(), "20261122");
        Await.status(batchService, id, "FAILED");
        repository.updateAudit(id, "RUNNING", null); // the write after the commit was lost
        repository.recordError(id, null);

        assertEquals("FAILED", batchService.status(id));
        assertEquals("FAILED", repository.auditStatus(id));
        assertNull(runtimeService.createProcessInstanceQuery().processInstanceId(id).singleResult());
        assertTrue("reason from the engine's history: " + batchService.error(id),
                batchService.error(id).contains("spark-submit"));
    }

    @Test
    public void aStatusOtherThanRunningIsReturnedAsItIs() throws Exception {
        String id = batchService.start(csv.toString(), "20261123");
        Await.status(batchService, id, "WAITING_APPROVAL");
        batchService.approve(id, false, "bob");

        assertEquals("REJECTED", batchService.status(id));
        assertEquals("REJECTED", repository.auditStatus(id));
    }
}
