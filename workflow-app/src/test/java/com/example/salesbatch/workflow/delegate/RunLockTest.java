package com.example.salesbatch.workflow.delegate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import org.junit.Test;

import com.example.salesbatch.common.AggRecord;
import com.example.salesbatch.common.SalesRecord;
import com.example.salesbatch.common.SalesRepository;

/**
 * The status lock in {@link AuditWrites} is one per run: a slow audit store holds back only the run being written
 * (card SBJ17-11, third review).
 */
public class RunLockTest {

    private final Map<String, String> audit = new ConcurrentHashMap<>();
    private final CountDownLatch stalledWriteStarted = new CountDownLatch(1);
    private final CountDownLatch storeAnswers = new CountDownLatch(1);

    /** An audit store that stalls on every write of run "slow" until {@link #storeAnswers} opens. */
    private final SalesRepository repository = new SalesRepository() {
        @Override public void saveRaw(java.util.Collection<SalesRecord> records) {}
        @Override public java.util.List<SalesRecord> loadRaw(String date) { return null; }
        @Override public java.util.List<AggRecord> loadAgg(String date) { return null; }
        @Override public void updateAudit(String pid, String status, String approver) {
            if (pid.equals("slow")) {
                stalledWriteStarted.countDown();
                await(storeAnswers);
            }
            audit.put(pid, status);
        }
        @Override public String auditStatus(String pid) { return audit.get(pid); }
        @Override public void recordError(String pid, String message) {}
        @Override public String auditError(String pid) { return null; }
    };

    @Test
    public void aStalledWriteOfOneRunDoesNotHoldBackAnotherRun() throws Exception {
        audit.put("slow", "RUNNING");
        audit.put("other", "RUNNING");
        Thread stalled = new Thread(() -> AuditWrites.write(repository, "slow", "COMPLETED", "alice"), "stalled");
        stalled.start();
        assertTrue("the stalled write started", stalledWriteStarted.await(5, TimeUnit.SECONDS));

        CountDownLatch otherDone = new CountDownLatch(3);
        Thread other = new Thread(() -> {
            AuditWrites.writeIf(repository, "other", "RUNNING", "WAITING_APPROVAL");
            otherDone.countDown();
            AuditWrites.write(repository, "other", "COMPLETED", "bob");
            otherDone.countDown();
            AuditWrites.failIf(repository, "other", "RUNNING", "not written: the run has completed");
            otherDone.countDown();
        }, "other");
        other.start();
        boolean otherFinished = otherDone.await(5, TimeUnit.SECONDS);

        storeAnswers.countDown();
        stalled.join(5000);
        other.join(5000);
        assertTrue("another run's writes finished while the first run's store stalled", otherFinished);
        assertEquals("COMPLETED", audit.get("other"));
        assertEquals("COMPLETED", audit.get("slow"));
    }

    @Test
    public void aRunsLockIsDroppedOnceItsWritesAreDone() {
        audit.put("p9", "RUNNING");
        storeAnswers.countDown();
        int before = AuditWrites.runsLocked();

        AuditWrites.writeIf(repository, "p9", "RUNNING", "WAITING_APPROVAL");
        AuditWrites.write(repository, "p9", "COMPLETED", "alice");
        AuditWrites.failIf(repository, "p9", "RUNNING", "not written");

        assertEquals(before, AuditWrites.runsLocked());
        assertEquals("COMPLETED", audit.get("p9"));
    }

    private static void await(CountDownLatch latch) {
        try {
            latch.await(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
