from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import dataset_items, experiments, health, prompt_versions, runs
from app.api.error_handlers import register_exception_handlers
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(dataset_items.router)
app.include_router(prompt_versions.router)
app.include_router(experiments.router)
app.include_router(runs.router)
