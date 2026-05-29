import asyncio
import logging
from database import get_db
from pymongo.errors import OperationFailure

logger = logging.getLogger(__name__)


async def watch_reports_collection():
    try:
        db = get_db()
        if db is None:
            logger.warning("Database not connected")
            return

        async with db.reports.watch(full_document="updateLookup", max_await_time_ms=1000) as stream:
            logger.info("Change stream started on reports collection")
            async for change in stream:
                if change["operationType"] == "insert":
                    report = change.get("fullDocument", {})
                    report_id = str(report.get("_id"))
                    logger.info(f"New report detected via change stream: {report_id}")
    except OperationFailure as e:
        if "40573" in str(e) or "replica sets" in str(e).lower():
            logger.warning(
                "MongoDB change streams require a replica set. "
                "Running in standalone mode — alert processing will happen synchronously "
                "during report upload. Change stream disabled."
            )
        else:
            logger.error(f"Change stream operation failure: {e}")
    except Exception as e:
        logger.error(f"Change stream error: {e}")
