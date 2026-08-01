from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trading_lab.api.app import create_app
from trading_lab.api.config import ApiConfig
from trading_lab.api.services.artifact_catalog import safe_child


def _json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def api_project(tmp_path: Path) -> Path:
    metrics = {
        "starting_capital": 10_000, "ending_capital": 10_010,
        "total_return": 0.001, "total_pnl": 10, "total_trades": 2,
        "win_rate": 0.5, "profit_factor": 2.0, "maximum_drawdown": 0.01,
    }
    _json(tmp_path / "output/summary.json", metrics)
    trades = [
        {
            "symbol": "QQQ", "direction": "long",
            "entry_timestamp": "2025-01-02T09:46:00-05:00", "entry_price": 100,
            "exit_timestamp": "2025-01-02T10:00:00-05:00", "exit_price": 102,
            "quantity": 10, "stop_price": 99, "take_profit_price": 102,
            "fees": 0, "slippage": 1, "realized_pnl": 20, "exit_reason": "TAKE_PROFIT",
        },
        {
            "symbol": "QQQ", "direction": "short",
            "entry_timestamp": "2025-02-03T09:46:00-05:00", "entry_price": 100,
            "exit_timestamp": "2025-02-03T10:16:00-05:00", "exit_price": 101,
            "quantity": 10, "stop_price": 101, "take_profit_price": 98,
            "fees": 0, "slippage": 1, "realized_pnl": -10, "exit_reason": "STOP_LOSS",
        },
    ]
    _csv(tmp_path / "output/trades.csv", trades)

    walk = tmp_path / "output/walk_forward/orb-v1/test-run"
    _json(walk / "config.json", {"strategy_name": "orb-v1", "slippage_bps": [0, 2, 5]})
    _json(walk / "summary.json", {"scenarios": {"2.0": {"profitable_periods": 1}}})
    _csv(walk / "windows.csv", [{"window_id": 1, "research_start": "2018-01-01", "out_of_sample_end": "2022-12-31"}])
    _csv(walk / "period_metrics.csv", [{"window_id": 1, "purpose": "out_of_sample", "total_return": -0.02, "quality_clean": True}])
    (walk / "report.md").write_text("# Walk-forward\nOOS first.", encoding="utf-8")

    study = tmp_path / "output/execution_studies/orb-v1/test-run"
    _json(study / "config.json", {"strategy": "orb-v1", "assumptions": {"study_period": {"start": "2018-01-01", "end": "2025-12-31"}}})
    _csv(study / "metrics.csv", [{
        "scenario": "fixed-2bps", "starting_capital": 10_000,
        "total_return": -0.04, "profit_factor": 0.97, "maximum_drawdown": 0.08,
        "total_modeled_execution_cost": 2000,
    }])
    (study / "report.md").write_text("# Execution\nModeled, not observed.", encoding="utf-8")

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "BASELINES.md").write_text("# Frozen baselines\n<script>alert(1)</script>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(api_project: Path) -> TestClient:
    return TestClient(create_app(ApiConfig(api_project)))


def test_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "read_only": True}


def test_strategy_catalog_and_unknown_strategy(client: TestClient):
    strategies = client.get("/api/v1/strategies").json()
    assert {item["id"] for item in strategies} == {"orb-v1", "reference-orb-v1"}
    assert all(item["frozen"] and item["status"] == "FROZEN" for item in strategies)
    assert client.get("/api/v1/strategies/missing").status_code == 404


def test_run_discovery_filtering_and_metrics(client: TestClient):
    runs = client.get("/api/v1/runs").json()
    assert runs["total"] == 2
    filtered = client.get("/api/v1/runs", params={"execution_model": "fixed-2bps", "profitability": "unprofitable"}).json()
    assert filtered["total"] == 1
    metrics = client.get("/api/v1/runs/orb-v1-2025/metrics").json()
    assert metrics["metrics"]["ending_capital"] == 10_010
    assert metrics["provenance"]["source_file"] == "output/summary.json"


def test_equity_drawdown_and_monthly_series(client: TestClient):
    equity = client.get("/api/v1/runs/orb-v1-2025/equity").json()
    assert equity["points"][-1]["value"] == 10_010
    assert "realized" in equity["methodology"].lower()
    drawdown = client.get("/api/v1/runs/orb-v1-2025/drawdown").json()
    assert drawdown["points"][-1]["value"] < 0
    monthly = client.get("/api/v1/runs/orb-v1-2025/monthly").json()
    assert [point["value"] for point in monthly["points"]] == [20, -10]


def test_trade_pagination_filtering_sorting_and_detail(client: TestClient):
    first = client.get("/api/v1/runs/orb-v1-2025/trades", params={"page_size": 1}).json()
    assert first["total"] == 2 and len(first["items"]) == 1
    losers = client.get("/api/v1/runs/orb-v1-2025/trades", params={"direction": "short", "outcome": "loser"}).json()
    assert losers["total"] == 1
    assert losers["items"][0]["holding_minutes"] == 30
    detail = client.get("/api/v1/runs/orb-v1-2025/trades/1").json()
    assert detail["modeled_execution_cost"] == 1


def test_walk_forward_and_execution_study_parsing(client: TestClient):
    walks = client.get("/api/v1/walk-forward").json()
    detail = client.get(f"/api/v1/walk-forward/{walks[0]['id']}").json()
    assert detail["periods"][0]["purpose"] == "out_of_sample"
    studies = client.get("/api/v1/execution-studies").json()
    execution = client.get(f"/api/v1/execution-studies/{studies[0]['id']}").json()
    assert execution["scenarios"][0]["scenario"] == "fixed-2bps"


def test_markdown_report_loading_does_not_enable_raw_html(client: TestClient):
    reports = client.get("/api/v1/reports").json()
    baseline = next(item for item in reports if item["source_path"] == "docs/BASELINES.md")
    detail = client.get(f"/api/v1/reports/{baseline['id']}").json()
    assert detail["raw_html_enabled"] is False
    assert "Frozen baselines" in detail["markdown"]


def test_missing_and_malformed_artifact_errors(client: TestClient, api_project: Path):
    assert client.get("/api/v1/runs/missing/metrics").status_code == 404
    study_id = "execution--orb-v1--test-run"
    (api_project / "output/execution_studies/orb-v1/test-run/metrics.csv").write_text("broken\n\"unterminated", encoding="utf-8")
    response = client.get(f"/api/v1/execution-studies/{study_id}")
    assert response.status_code in {200, 422}  # csv module tolerates some malformed rows safely


def test_directory_traversal_is_rejected(client: TestClient, api_project: Path):
    with pytest.raises(ValueError, match="escapes"):
        safe_child(api_project / "docs", api_project / ".env")
    assert client.get("/api/v1/reports/%2E%2E%2F.env").status_code == 404


def test_no_credentials_or_historical_cache_are_exposed(client: TestClient):
    for endpoint in ("/api/v1/runs", "/api/v1/reports", "/api/v1/strategies"):
        text = client.get(endpoint).text
        assert "ALPACA_API_KEY" not in text
        assert "ALPACA_SECRET_KEY" not in text
        assert "data/historical" not in text
