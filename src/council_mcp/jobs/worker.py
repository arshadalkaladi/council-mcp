"""Bounded in-process worker pool.

Design (frozen constraints):
  * No work runs inside an MCP request; the pool executes jobs out of band.
  * Bounded concurrency: a fixed number of worker threads.
  * Atomic claim via the store (QUEUED -> CLAIMED); no double execution.
  * Deterministic retries: on failure, attempts++ then requeue, or DEAD when
    attempts are exhausted.
  * Wall-clock budget: a job exceeding the budget is marked failed (and thus
    retried or DEAD) even if its handler keeps running (handlers should be
    cooperative; the budget guarantees the JOB is accounted for in time).
  * Startup recovery: stale CLAIMED/RUNNING jobs (from a crash) are reset to
    QUEUED before workers start.
  * Graceful shutdown: stop() lets in-flight work settle and joins threads.

Each worker thread owns its own SQLite connection (sqlite3 connections are not
shareable across threads). Handlers also receive their own store.
"""

from __future__ import annotations

import threading
from typing import Callable

from ..store import open_store

# handler(job: dict, store) -> None ; raise on failure.
JobHandler = Callable[[dict, object], None]


class WorkerPool:
    def __init__(self, db_path: str, handlers: dict[str, JobHandler], *,
                 concurrency: int = 2, poll_interval: float = 0.02,
                 job_budget_seconds: float = 5.0):
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        self.db_path = db_path
        self.handlers = dict(handlers)
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.job_budget_seconds = job_budget_seconds
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # -- lifecycle -------------------------------------------------------
    def start(self, *, recover: bool = True) -> None:
        if recover:
            s = open_store(self.db_path)
            try:
                s.recover_stale_jobs()
            finally:
                s.close()
        self._stop.clear()
        for i in range(self.concurrency):
            t = threading.Thread(target=self._loop, name=f"worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)


    def stop(self, timeout: float = 5.0) -> None:
        """Signal shutdown and join workers (graceful)."""
        self._stop.set()
        for t in self._threads:
            t.join(timeout)
        self._threads = []

    # -- worker loop -----------------------------------------------------
    def _loop(self) -> None:
        store = open_store(self.db_path)
        try:
            while not self._stop.is_set():
                job = store.claim_next_job()
                if job is None:
                    self._stop.wait(self.poll_interval)
                    continue
                self._execute(job, store)
        finally:
            store.close()

    def _execute(self, job: dict, accounting_store) -> None:
        job_id = job["job_id"]
        accounting_store.mark_job_running(job_id)

        handler = self.handlers.get(job["kind"])
        if handler is None:
            accounting_store.mark_job_failed(job_id, "no_handler_for_kind")
            return

        outcome: dict = {}

        def run():
            hstore = open_store(self.db_path)
            try:
                handler(job, hstore)
                outcome["ok"] = True
            except Exception as exc:  # noqa: BLE001 - record, never leak
                outcome["err"] = type(exc).__name__
            finally:
                hstore.close()

        worker_thread = threading.Thread(target=run, daemon=True)
        worker_thread.start()
        worker_thread.join(self.job_budget_seconds)

        if worker_thread.is_alive():
            accounting_store.mark_job_failed(job_id, "wall_clock_budget_exceeded")
        elif "err" in outcome:
            accounting_store.mark_job_failed(job_id, outcome["err"])
        else:
            accounting_store.mark_job_succeeded(job_id)
