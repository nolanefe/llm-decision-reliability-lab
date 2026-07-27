from fastapi import FastAPI

from app.api import dataset_items, experiments, health, prompt_versions
from app.api.error_handlers import register_exception_handlers
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(dataset_items.router)
app.include_router(prompt_versions.router)
app.include_router(experiments.router)
