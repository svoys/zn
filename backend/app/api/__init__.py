"""API routes package."""

from fastapi import APIRouter

from app.api import asset, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(asset.router)
api_router.include_router(search.router)
