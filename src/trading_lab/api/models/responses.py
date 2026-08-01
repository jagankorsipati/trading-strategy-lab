from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(ApiModel):
    status: str
    version: str
    read_only: bool


class StrategyResponse(ApiModel):
    id: str
    name: str
    status: str
    frozen: bool
    baseline_release: str
    source_file: str
    specification: str
    starting_capital: float
    sizing: str
    default_assumptions: dict[str, Any]
    key_results: dict[str, float]
    conclusion: str


class ArtifactIssue(ApiModel):
    source: str
    code: str
    message: str


class Provenance(ApiModel):
    source_file: str
    strategy_version: str | None = None
    baseline_status: str | None = None
    data_period: str | None = None
    execution_model: str | None = None
    slippage_bps: float | None = None
    generated_time: str | None = None
    project_version: str = "0.1.0"
    commit_hash: str | None = None


class RunSummary(ApiModel):
    id: str
    strategy: str
    run_type: str
    start_date: str | None = None
    end_date: str | None = None
    execution_model: str | None = None
    slippage_bps: float | None = None
    profitable: bool | None = None
    starting_equity: float | None = None
    total_return: float | None = None
    source_path: str
    provenance: Provenance
    issues: list[ArtifactIssue] = Field(default_factory=list)


class PaginatedRuns(ApiModel):
    items: list[RunSummary]
    page: int
    page_size: int
    total: int


class MetricsResponse(ApiModel):
    run_id: str
    metrics: dict[str, Any]
    provenance: Provenance


class SeriesPoint(ApiModel):
    timestamp: str
    value: float


class SeriesResponse(ApiModel):
    run_id: str
    name: str
    unit: str
    available: bool
    methodology: str | None = None
    points: list[SeriesPoint] = Field(default_factory=list)


class TradeResponse(ApiModel):
    id: int
    symbol: str
    direction: str
    entry_timestamp: str
    entry_price: float
    exit_timestamp: str
    exit_price: float
    quantity: int
    stop_price: float
    take_profit_price: float
    fees: float
    slippage: float
    realized_pnl: float
    return_pct: float
    exit_reason: str
    holding_minutes: float
    modeled_execution_cost: float


class PaginatedTrades(ApiModel):
    items: list[TradeResponse]
    page: int
    page_size: int
    total: int


class StudySummary(ApiModel):
    id: str
    strategy: str
    run_id: str
    source_path: str


class WalkForwardDetail(StudySummary):
    config: dict[str, Any]
    summary: dict[str, Any]
    windows: list[dict[str, Any]]
    periods: list[dict[str, Any]]
    issues: list[ArtifactIssue] = Field(default_factory=list)


class ExecutionStudyDetail(StudySummary):
    config: dict[str, Any]
    scenarios: list[dict[str, Any]]
    issues: list[ArtifactIssue] = Field(default_factory=list)


class ReportSummary(ApiModel):
    id: str
    title: str
    category: str
    source_path: str


class ReportDetail(ReportSummary):
    markdown: str
    raw_html_enabled: bool = False
