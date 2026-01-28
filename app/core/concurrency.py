from asyncio import Semaphore
import time
from contextlib import asynccontextmanager
from loguru import logger

@asynccontextmanager
async def limited(sem: Semaphore):
    start_time = time.time()
    try:
        async with sem:
            logger.info(f"等待了 {time.time() - start_time} 秒才拿到许可")
            yield
    finally:
        logger.info("任务结束，释放信号量")

