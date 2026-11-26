from contextlib import asynccontextmanager
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import settings
from app.database.init import initialize_database


logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    logger.info("KitchenCheck API started.")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
