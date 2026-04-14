import asyncio
import time
import logging
from typing import Any, List, Tuple, Dict

logger = logging.getLogger("pulse-scheduler")

class PulseScheduler:
    def __init__(self, max_batch_size: int = 64):
        self.queue = asyncio.Queue()
        self.max_batch_size = max_batch_size
        self._worker_task = None
        logger.info(f"PulseScheduler INITIALIZED (max_batch_size={max_batch_size})")

    def start(self):
        """Explicitly start the worker loop."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("PulseScheduler Worker STARTED")

    async def schedule(self, adapter: Any, client: Any, target_url: str, request: Dict) -> Dict:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        await self.queue.put((adapter, client, target_url, request, future))
        return await future

    async def _worker_loop(self):
        while True:
            batch: List[Tuple] = []
            
            # 1. Wait for the FIRST request of the batch
            item = await self.queue.get()
            batch.append(item)
            
            start_time = time.time()
            queue_size = self.queue.qsize()
            window = self._get_adaptive_window(queue_size)
            deadline = start_time + window
            
            # 2. Fill the batch until max_batch_size or deadline
            while len(batch) < self.max_batch_size:
                timeout = deadline - time.time()
                if timeout <= 0:
                    break
                
                try:
                    # Efficiently wait for the next item
                    item = await asyncio.wait_for(self.queue.get(), timeout=timeout)
                    batch.append(item)
                except (asyncio.TimeoutError, asyncio.exceptions.TimeoutError):
                    break
            
            # 3. Dispatch the pulse
            if batch:
                if len(batch) > 1 or queue_size > 0:
                    logger.info(f"[Scheduler] Dispatching Batch: {len(batch)} | Remaining Queue: {self.queue.qsize()}")
                asyncio.create_task(self._dispatch_batch(batch))
            
            # 4. Loop Refill Boost: If queue is still heavy, don't yield long
            if self.queue.qsize() > self.max_batch_size:
                await asyncio.sleep(0) # Minimal yield
            else:
                await asyncio.sleep(0.001)

    def _get_adaptive_window(self, queue_size: int) -> float:
        if queue_size < 10:
            return 0.005   # 5ms - was 3ms
        elif queue_size < 40:
            return 0.015   # 15ms - was 10ms
        else:
            return 0.030   # 30ms - push for max density

    async def _dispatch_batch(self, batch: List[Tuple]):
        tasks = [self._safe_execute(*item) for item in batch]
        await asyncio.gather(*tasks)

    async def _safe_execute(self, adapter, client, target_url, request, future):
        try:
            # Note: adapter.complete is already async
            result = await adapter.complete(client, target_url, request)
            if not future.done():
                future.set_result(result)
        except Exception as e:
            logger.error(f"Pulse Execution Error: {e}")
            if not future.done():
                future.set_exception(e)
