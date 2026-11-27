package com.example.salesbatch.workflow.delegate;

import com.example.salesbatch.common.SalesRepository;

/**
 * Keeps a late status write from replacing a newer one.
 *
 * WAITING_APPROVAL is written after the Spark step commits (see {@link AfterCommit}). From that commit on the approval
 * task exists, so a caller may approve it, and COMPLETED or REJECTED may be written, before WAITING_APPROVAL lands.
 * The late write therefore checks the status and writes under the same lock as the approval's own write: whichever
 * comes second sees the first, and the newer status stays (card SBJ17-11).
 *
 * The lock is held by this workflow app, so it covers approvals handled by the same app; the audit store itself has
 * no compare-and-write in {@link SalesRepository}.
 */
final class AuditWrites {

    private static final Object LOCK = new Object();

    private AuditWrites() {}

    /** Writes a status that ends a run (COMPLETED, REJECTED). */
    static void write(SalesRepository repository, String processInstanceId, String status, String approver) {
        synchronized (LOCK) {
            repository.updateAudit(processInstanceId, status, approver);
        }
    }

    /** Writes {@code status} only if the run's status is still {@code expected}. Returns whether it wrote. */
    static boolean writeIf(SalesRepository repository, String processInstanceId, String expected, String status) {
        synchronized (LOCK) {
            if (!expected.equals(repository.auditStatus(processInstanceId))) {
                return false;
            }
            repository.updateAudit(processInstanceId, status, null);
            return true;
        }
    }
}
