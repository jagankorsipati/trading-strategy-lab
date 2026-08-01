from fastapi import APIRouter, HTTPException

from trading_lab.api.models.responses import StrategyResponse
from trading_lab.api.services.strategy_catalog import STRATEGIES

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyResponse])
def list_strategies() -> list[StrategyResponse]:
    return list(STRATEGIES.values())


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: str) -> StrategyResponse:
    if strategy_id not in STRATEGIES:
        raise HTTPException(404, detail={"code": "unknown_strategy", "message": strategy_id})
    return STRATEGIES[strategy_id]
