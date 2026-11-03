import asyncio
import logging
import signal
import sys
from typing import Set
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.db.session import init_db, AsyncSessionLocal
from backend.app.models.asset import Job
from backend.app.workers.job_runner import job_runner


class StandaloneWorkerRunner:
    """Decoupled background worker daemon that consumes queued jobs from the database."""

    def __init__(self):
        self.is_running = True
        self.active_tasks: Set[asyncio.Task] = set()
        self.stop_event = asyncio.Event()

    def request_stop(self, sig_name: str = "SIGNAL"):
        logger.info(f"Received {sig_name}. Initiating graceful shutdown of standalone worker...")
        self.is_running = False
        self.stop_event.set()

    async def claim_queued_jobs(self, limit: int):
        """Atomically query and claim up to `limit` queued jobs."""
        if limit <= 0:
            return []

        async with AsyncSessionLocal() as session:
            stmt = (
                select(Job)
                .where(Job.status == "queued")
                .order_by(Job.created_at.asc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            jobs = res.scalars().all()
            if not jobs:
                return []

            claimed_ids = []
            for j in jobs:
                j.status = "running"
                j.stage_description = "Job claimed by decoupled worker process"
                claimed_ids.append(j.id)

            await session.commit()
            return claimed_ids

    async def run_forever(self, poll_interval: float = None):
        """Continuous polling and execution loop."""
        interval = poll_interval or settings.WORKER_POLL_INTERVAL_SECONDS
        logger.info(
            f"Standalone worker started (max_concurrent={settings.MAX_CONCURRENT_JOBS}, "
            f"poll_interval={interval}s). Waiting for jobs..."
        )

        while self.is_running:
            # Prune completed or cancelled tasks
            self.active_tasks = {t for t in self.active_tasks if not t.done()}

            slots = settings.MAX_CONCURRENT_JOBS - len(self.active_tasks)
            if slots > 0:
                try:
                    claimed_ids = await self.claim_queued_jobs(slots)
                    for job_id in claimed_ids:
                        logger.info(f"Worker claimed job {job_id}. Spawning execution task.")
                        task = asyncio.create_task(job_runner.execute_job(job_id))
                        self.active_tasks.add(task)
                except Exception as e:
                    logger.error(f"Error querying/claiming queued jobs: {e}")

            try:
                # Sleep with interruption capability
                await asyncio.wait_for(self.stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

        # Graceful drain: wait for active tasks to complete up to timeout
        if self.active_tasks:
            logger.info(f"Draining {len(self.active_tasks)} active worker tasks...")
            done, pending = await asyncio.wait(self.active_tasks, timeout=10.0)
            if pending:
                logger.warning(f"Force cancelling {len(pending)} tasks that did not finish within timeout.")
                for t in pending:
                    t.cancel()

        logger.info("Standalone worker successfully shut down.")


async def main():
    setup_logging()
    logger.info("Starting AI Novel-to-Webtoon Studio Standalone Worker...")
    
    # Initialize DB schema & indexes
    await init_db()
    
    # Recover any orphaned jobs from prior unexpected restarts
    await job_runner.recover_orphaned_jobs()

    runner = StandaloneWorkerRunner()

    # Setup OS signal handlers cross-platform
    def handle_signal(sig, frame):
        sig_name = signal.Signals(sig).name if hasattr(signal, "Signals") else str(sig)
        runner.request_stop(sig_name)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    await runner.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
