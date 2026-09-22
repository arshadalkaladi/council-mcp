"""Background job execution (Phase 1E), standard-library threading only.

A bounded in-process worker pool over the Phase-1D jobs table. No external
queue, no extra process, no third-party dependency.

  * worker — WorkerPool: atomic claim, deterministic retries, wall-clock
    budget, startup recovery of stale jobs, graceful shutdown.
"""

from .worker import WorkerPool, JobHandler

__all__ = ["WorkerPool", "JobHandler"]
