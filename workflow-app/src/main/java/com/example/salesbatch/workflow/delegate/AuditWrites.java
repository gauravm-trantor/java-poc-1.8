package com.example.salesbatch.workflow.delegate;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import com.example.salesbatch.common.SalesRepository;

/**
 * Keeps a late status write from replacing a newer one.
 *
 * WAITING_APPROVAL is written after the Spark step commits (see {@link AfterCommit}). From that commit on the approval
 * task exists, so a caller may approve it, and COMPLETED or REJECTED may be written, before WAITING_APPROVAL lands.
 * The late write therefore checks the status and writes under the same lock as the approval's own write: whichever
 * comes second sees the first, and the newer status stays (card SBJ17-11).
 *
 * The lock is one per run (process instance id), so a slow audit store holds back only the run being written, never
 * another run's approval or status read. A run's lock is dropped when no write of that run holds or waits for it.
 *
 * The lock is held by this workflow app, so it covers approvals handled by the same app; the audit store itself has
 * no compare-and-write in {@link SalesRepository}.
 */
public final class AuditWrites {

    /** One lock per run that is being written; {@code users} counts the threads holding or waiting for it. */
    private static final class RunLock {
        int users;
    }

    private static final ConcurrentMap<String, RunLock> LOCKS = new ConcurrentHashMap<>();

    private interface Write {
        boolean run();
    }

    private AuditWrites() {}

    private static boolean underRunLock(String processInstanceId, Write write) {
        RunLock lock = LOCKS.compute(processInstanceId, (pid, held) -> {
            RunLock taken = held == null ? new RunLock() : held;
            taken.users++;
            return taken;
        });
        try {
            synchronized (lock) {
                return write.run();
            }
        } finally {
            LOCKS.computeIfPresent(processInstanceId, (pid, held) -> --held.users == 0 ? null : held);
        }
    }

    /** How many runs have a lock now; for tests. */
    static int runsLocked() {
        return LOCKS.size();
    }

    /** Writes a status that ends a run (COMPLETED, REJECTED). */
    static void write(SalesRepository repository, String processInstanceId, String status, String approver) {
        underRunLock(processInstanceId, () -> {
            repository.updateAudit(processInstanceId, status, approver);
            return true;
        });
    }

    /** Writes {@code status} only if the run's status is still {@code expected}. Returns whether it wrote. */
    public static boolean writeIf(SalesRepository repository, String processInstanceId, String expected,
            String status) {
        return underRunLock(processInstanceId, () -> {
            if (!expected.equals(repository.auditStatus(processInstanceId))) {
                return false;
            }
            repository.updateAudit(processInstanceId, status, null);
            return true;
        });
    }

    /**
     * Records {@code reason} and writes FAILED, only if the run's status is still {@code expected}. Returns whether it
     * wrote.
     */
    public static boolean failIf(SalesRepository repository, String processInstanceId, String expected,
            String reason) {
        return underRunLock(processInstanceId, () -> {
            if (!expected.equals(repository.auditStatus(processInstanceId))) {
                return false;
            }
            repository.recordError(processInstanceId, reason);
            repository.updateAudit(processInstanceId, "FAILED", null);
            return true;
        });
    }
}
