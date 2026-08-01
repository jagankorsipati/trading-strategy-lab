from fastapi import APIRouter

from trading_lab import __version__
from trading_lab.api.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, read_only=True)
