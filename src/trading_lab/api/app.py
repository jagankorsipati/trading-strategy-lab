from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from trading_lab import __version__
from trading_lab.api.config import ApiConfig, default_config
from trading_lab.api.routes import health, reports, runs, strategies, studies, trades


def create_app(config: ApiConfig | None = None) -> FastAPI:
    application = FastAPI(
        title="Trading Strategy Lab Research API",
        version=__version__,
        description="Read-only API over generated research artifacts.",
    )
    application.state.config = config or default_config()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[application.state.config.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )
    prefix = "/api/v1"
    application.include_router(health.router, prefix=prefix)
    application.include_router(strategies.router, prefix=prefix)
    application.include_router(runs.router, prefix=prefix)
    application.include_router(trades.router, prefix=prefix)
    application.include_router(studies.router, prefix=prefix)
    application.include_router(reports.router, prefix=prefix)

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "internal_error", "message": "Unable to load the requested research artifact."}},
        )

    return application


app = create_app()
