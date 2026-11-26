from contextlib import asynccontextmanager
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.checklists import router as checklists_router
from app.api.routes.executions import router as executions_router
from app.api.routes.health import router as health_router
from app.api.routes.tasks import router as tasks_router
from app.config import settings
from app.database.init import initialize_database
from app.services.exceptions import ResourceConflictError, ResourceNotFoundError


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
app.include_router(checklists_router)
app.include_router(tasks_router)
app.include_router(executions_router)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(
    _: Request, error: ResourceNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(
    _: Request, error: ResourceConflictError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})
