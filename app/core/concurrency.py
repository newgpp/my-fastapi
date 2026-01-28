from asyncio import Semaphore
from contextlib import asynccontextmanager
import time
from loguru import logger


@asynccontextmanager
async def limited(sem: Semaphore):
    start = time.perf_counter()
    try:
        async with sem:
            logger.info(f"等待了 {time.perf_counter() - start:.3f} 秒才拿到许可")
            yield
    finally:
        logger.info("任务结束，释放信号量")


