from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG,
)
app.include_router(api_router)


@app.on_event("startup")
async def startup():

    logger.info("ZN API started")


@app.get("/")
async def root():

    return {
        "project": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "running",
    }
