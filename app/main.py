import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.controllers.file_controller import router
from app.schemas.file_schema import HealthResponse
from app.utils.exceptions import ApplicationError

logging.basicConfig(level=getattr(logging, get_settings().log_level.upper(), logging.INFO))
app = FastAPI(title=get_settings().app_name, version="1.0.0", description="Secure geospatial upload and measurement service.")
app.include_router(router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")

@app.get("/health", response_model=HealthResponse, summary="Check application availability")
def health() -> dict[str, str]:
    return {"status": "ok"}



@app.exception_handler(ApplicationError)
async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    _ = exc
    return JSONResponse(status_code=422, content={"detail": "Request validation failed."})


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled application error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})
