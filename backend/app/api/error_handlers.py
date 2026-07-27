import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableEntityError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(UnprocessableEntityError)
    async def handle_unprocessable(
        request: Request, exc: UnprocessableEntityError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "Unhandled database error while processing %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500, content={"detail": "A database error occurred."}
        )
