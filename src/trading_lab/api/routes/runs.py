from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from trading_lab.api.dependencies import get_catalog
from trading_lab.api.models.responses import (
    MetricsResponse, PaginatedRuns, Provenance, RunSummary, SeriesResponse,
)
from trading_lab.api.services.artifact_catalog import ArtifactCatalog, RunRecord
from trading_lab.api.services.result_loader import (
    ArtifactLoadError, drawdown_series, load_json, load_trades, realized_equity_series,
)

router = APIRouter(prefix="/runs", tags=["runs"])


def _record(catalog: ArtifactCatalog, run_id: str) -> RunRecord:
    if run_id not in catalog.runs:
        raise HTTPException(404, detail={"code": "unknown_run", "message": run_id})
    return catalog.runs[run_id]


def _typed_metrics(row: dict) -> dict:
    result = {}
    for key, value in row.items():
        if isinstance(value, (int, float)) or value is None:
            result[key] = value
            continue
        if value == "":
            result[key] = None
            continue
        try:
            result[key] = float(value)
        except (TypeError, ValueError):
            result[key] = value
    return result


@router.get("", response_model=PaginatedRuns)
def list_runs(
    strategy: str | None = None,
    run_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    execution_model: str | None = None,
    slippage: float | None = None,
    profitability: Literal["profitable", "unprofitable"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    catalog: ArtifactCatalog = Depends(get_catalog),
) -> PaginatedRuns:
    items = list(catalog.runs.values())
    if strategy:
        items = [item for item in items if item.summary.strategy == strategy]
    if run_type:
        items = [item for item in items if item.summary.run_type == run_type]
    if start_date:
        items = [item for item in items if item.summary.start_date and date.fromisoformat(item.summary.start_date) >= start_date]
    if end_date:
        items = [item for item in items if item.summary.end_date and date.fromisoformat(item.summary.end_date) <= end_date]
    if execution_model:
        items = [item for item in items if item.summary.execution_model == execution_model]
    if slippage is not None:
        items = [item for item in items if item.summary.slippage_bps == slippage]
    if profitability:
        desired = profitability == "profitable"
        items = [item for item in items if item.summary.profitable is desired]
    items.sort(key=lambda item: item.summary.id)
    total = len(items)
    offset = (page - 1) * page_size
    return PaginatedRuns(
        items=[item.summary for item in items[offset : offset + page_size]],
        page=page, page_size=page_size, total=total,
    )


@router.get("/{run_id}", response_model=RunSummary)
def get_run(run_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> RunSummary:
    return _record(catalog, run_id).summary


@router.get("/{run_id}/metrics", response_model=MetricsResponse)
def run_metrics(run_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> MetricsResponse:
    record = _record(catalog, run_id)
    try:
        metrics = record.metrics_row or load_json(record.metrics_path)
    except ArtifactLoadError as exc:
        raise HTTPException(422, detail={"code": "malformed_artifact", "message": exc.message}) from exc
    return MetricsResponse(run_id=run_id, metrics=_typed_metrics(metrics), provenance=record.summary.provenance)


def _trades(record: RunRecord) -> list[dict]:
    if record.trades_path is None:
        raise HTTPException(422, detail={"code": "unavailable_metric", "message": "trade-level artifact is unavailable"})
    try:
        return load_trades(record.trades_path)
    except (ArtifactLoadError, ValueError) as exc:
        raise HTTPException(422, detail={"code": "malformed_artifact", "message": str(exc)}) from exc


@router.get("/{run_id}/equity", response_model=SeriesResponse)
def run_equity(run_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> SeriesResponse:
    record = _record(catalog, run_id)
    trades = _trades(record)
    metrics = load_json(record.metrics_path)
    points = realized_equity_series(trades, float(metrics["starting_capital"]))
    return SeriesResponse(
        run_id=run_id, name="Realized equity", unit="USD", available=True,
        methodology="Reconstructed from cumulative realized trade P&L; intratrade mark-to-market equity is unavailable in this artifact.",
        points=points,
    )


@router.get("/{run_id}/drawdown", response_model=SeriesResponse)
def run_drawdown(run_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> SeriesResponse:
    record = _record(catalog, run_id)
    trades = _trades(record)
    metrics = load_json(record.metrics_path)
    start = float(metrics["starting_capital"])
    points = drawdown_series(realized_equity_series(trades, start), start)
    return SeriesResponse(
        run_id=run_id, name="Realized-equity drawdown", unit="percent", available=True,
        methodology="Drawdown from realized-only equity; the summary maximum drawdown uses the full mark-to-market curve.",
        points=points,
    )


@router.get("/{run_id}/monthly", response_model=SeriesResponse)
def run_monthly(run_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> SeriesResponse:
    record = _record(catalog, run_id)
    monthly: dict[str, float] = defaultdict(float)
    for trade in _trades(record):
        monthly[trade["exit_timestamp"][:7]] += trade["realized_pnl"]
    points = [{"timestamp": f"{month}-01", "value": value} for month, value in sorted(monthly.items())]
    return SeriesResponse(
        run_id=run_id, name="Monthly realized P&L", unit="USD", available=True,
        methodology="Grouped by trade exit month.", points=points,
    )
