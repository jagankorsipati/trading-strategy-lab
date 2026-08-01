from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from trading_lab.api.dependencies import get_catalog
from trading_lab.api.models.responses import PaginatedTrades, TradeResponse
from trading_lab.api.routes.runs import _record, _trades
from trading_lab.api.services.artifact_catalog import ArtifactCatalog

router = APIRouter(prefix="/runs/{run_id}/trades", tags=["trades"])


def _filtered(
    run_id: str,
    catalog: ArtifactCatalog,
    direction: Literal["long", "short"] | None,
    outcome: Literal["winner", "loser", "breakeven"] | None,
    exit_reason: str | None,
    start_date: date | None,
    end_date: date | None,
    min_pnl: float | None,
    max_pnl: float | None,
    min_holding_minutes: float | None,
    max_holding_minutes: float | None,
) -> list[dict]:
    items = _trades(_record(catalog, run_id))
    if direction:
        items = [item for item in items if item["direction"] == direction]
    if outcome == "winner":
        items = [item for item in items if item["realized_pnl"] > 0]
    elif outcome == "loser":
        items = [item for item in items if item["realized_pnl"] < 0]
    elif outcome == "breakeven":
        items = [item for item in items if item["realized_pnl"] == 0]
    if exit_reason:
        items = [item for item in items if item["exit_reason"] == exit_reason]
    if start_date:
        items = [item for item in items if date.fromisoformat(item["entry_timestamp"][:10]) >= start_date]
    if end_date:
        items = [item for item in items if date.fromisoformat(item["entry_timestamp"][:10]) <= end_date]
    if min_pnl is not None:
        items = [item for item in items if item["realized_pnl"] >= min_pnl]
    if max_pnl is not None:
        items = [item for item in items if item["realized_pnl"] <= max_pnl]
    if min_holding_minutes is not None:
        items = [item for item in items if item["holding_minutes"] >= min_holding_minutes]
    if max_holding_minutes is not None:
        items = [item for item in items if item["holding_minutes"] <= max_holding_minutes]
    return items


@router.get("", response_model=PaginatedTrades)
def list_trades(
    run_id: str,
    direction: Literal["long", "short"] | None = None,
    outcome: Literal["winner", "loser", "breakeven"] | None = None,
    exit_reason: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_pnl: float | None = None,
    max_pnl: float | None = None,
    min_holding_minutes: float | None = Query(None, ge=0),
    max_holding_minutes: float | None = Query(None, ge=0),
    sort_by: Literal["entry_timestamp", "exit_timestamp", "realized_pnl", "holding_minutes"] = "entry_timestamp",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=250),
    catalog: ArtifactCatalog = Depends(get_catalog),
) -> PaginatedTrades:
    items = _filtered(
        run_id, catalog, direction, outcome, exit_reason, start_date, end_date,
        min_pnl, max_pnl, min_holding_minutes, max_holding_minutes,
    )
    items.sort(key=lambda item: item[sort_by], reverse=order == "desc")
    total = len(items)
    offset = (page - 1) * page_size
    return PaginatedTrades(
        items=[TradeResponse(**item) for item in items[offset : offset + page_size]],
        page=page, page_size=page_size, total=total,
    )


@router.get("/{trade_id}", response_model=TradeResponse)
def get_trade(run_id: str, trade_id: int, catalog: ArtifactCatalog = Depends(get_catalog)) -> TradeResponse:
    if trade_id <= 0:
        raise HTTPException(404, detail={"code": "unknown_trade", "message": str(trade_id)})
    items = _trades(_record(catalog, run_id))
    if trade_id > len(items):
        raise HTTPException(404, detail={"code": "unknown_trade", "message": str(trade_id)})
    return TradeResponse(**items[trade_id - 1])
