import asyncio
import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .generator import ProposalGenerator
from .store import ProposalStore
from .executor import ProposalExecutor
from .config import get_config


logger = logging.getLogger(__name__)


async def is_quiet_hours() -> bool:
    config = get_config()
    tz = pytz.timezone(config.timezone)
    now = datetime.now(tz)

    start = config.quiet_hours_start
    end = config.quiet_hours_end
    current_hour = now.hour

    if start == end:
        return True
    if start < end:
        return start <= current_hour < end
    return current_hour >= start or current_hour < end


async def generation_job():
    config = get_config()

    if await is_quiet_hours():
        logger.info("Generation skipped: quiet hours.")
        return

    store = ProposalStore()
    pending = store.get_pending()
    if len(pending) >= config.max_pending:
        logger.info("Generation skipped: max pending reached (%s/%s).", len(pending), config.max_pending)
        return

    generator = ProposalGenerator()
    results = await generator.generate(3)
    logger.info("Generated proposals: %s", results)


async def auto_execute_job():
    config = get_config()
    if not config.auto_approve_safe:
        return

    executor = ProposalExecutor()
    results = executor.execute_pending_safe()
    logger.info("Auto-executed safe proposals: %s", results)


async def main():
    config = get_config()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(generation_job, "interval", minutes=config.generation_interval_minutes)
    scheduler.add_job(auto_execute_job, "interval", minutes=5)
    scheduler.start()

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())