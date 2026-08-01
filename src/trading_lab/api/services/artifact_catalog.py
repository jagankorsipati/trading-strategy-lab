from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_lab.api.config import ApiConfig
from trading_lab.api.models.responses import Provenance, ReportSummary, RunSummary, StudySummary
from trading_lab.api.services.result_loader import ArtifactLoadError, load_csv_rows, load_json


def safe_child(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("artifact path escapes configured root")
    return resolved


@dataclass(frozen=True)
class RunRecord:
    summary: RunSummary
    metrics_path: Path
    trades_path: Path | None = None
    metrics_row: dict[str, Any] | None = None


@dataclass(frozen=True)
class StudyRecord:
    summary: StudySummary
    root: Path


@dataclass(frozen=True)
class ReportRecord:
    summary: ReportSummary
    path: Path


class ArtifactCatalog:
    """Discovers only allowlisted artifact roots; refresh by constructing anew."""

    def __init__(self, config: ApiConfig) -> None:
        self.config = config
        self.runs: dict[str, RunRecord] = {}
        self.walk_forward: dict[str, StudyRecord] = {}
        self.execution_studies: dict[str, StudyRecord] = {}
        self.reports: dict[str, ReportRecord] = {}
        self.issues: list[dict[str, str]] = []
        self._discover()

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.config.project_root.resolve()).as_posix()

    def _standard_run(self, run_id: str, strategy: str, summary: Path, trades: Path) -> None:
        if not summary.exists():
            return
        try:
            metrics = load_json(summary)
            run = RunSummary(
                id=run_id, strategy=strategy, run_type="standard_backtest",
                start_date="2025-01-01", end_date="2025-12-31",
                execution_model="fixed-0bps", slippage_bps=0,
                profitable=float(metrics.get("total_return", 0)) > 0,
                starting_equity=metrics.get("starting_capital"),
                total_return=metrics.get("total_return"), source_path=self.relative(summary),
                provenance=Provenance(
                    source_file=self.relative(summary), strategy_version=strategy,
                    baseline_status="FROZEN", data_period="2025",
                    execution_model="fixed-0bps", slippage_bps=0,
                ),
            )
            self.runs[run_id] = RunRecord(run, summary, trades if trades.exists() else None)
        except (ArtifactLoadError, ValueError) as exc:
            self.issues.append({"source": self.relative(summary), "code": "malformed_artifact", "message": str(exc)})

    def _discover(self) -> None:
        output = safe_child(self.config.project_root, self.config.output_root)
        docs = safe_child(self.config.project_root, self.config.docs_root)
        self._standard_run("orb-v1-2025", "orb-v1", output / "summary.json", output / "trades.csv")
        self._standard_run(
            "reference-orb-v1-2025", "reference-orb-v1",
            output / "reference_orb" / "summary.json",
            output / "reference_orb" / "trades.csv",
        )

        for root in sorted((output / "walk_forward").glob("*/*")):
            if not root.is_dir():
                continue
            strategy, run_id = root.parent.name, root.name
            study_id = f"walk-forward--{strategy}--{run_id}"
            summary = StudySummary(id=study_id, strategy=strategy, run_id=run_id, source_path=self.relative(root))
            self.walk_forward[study_id] = StudyRecord(summary, safe_child(output, root))

        for root in sorted((output / "execution_studies").glob("*/*")):
            if not root.is_dir():
                continue
            strategy, run_id = root.parent.name, root.name
            study_id = f"execution--{strategy}--{run_id}"
            summary = StudySummary(id=study_id, strategy=strategy, run_id=run_id, source_path=self.relative(root))
            self.execution_studies[study_id] = StudyRecord(summary, safe_child(output, root))
            metrics_path = root / "metrics.csv"
            config_path = root / "config.json"
            try:
                config = load_json(config_path)
                period = config.get("assumptions", {}).get("study_period", {})
                for row in load_csv_rows(metrics_path):
                    scenario = row.get("scenario", "unavailable")
                    run_key = f"execution--{strategy}--{scenario}"
                    total_return = float(row["total_return"])
                    slippage = {"fixed-0bps": 0.0, "fixed-2bps": 2.0, "fixed-5bps": 5.0}.get(scenario)
                    summary_run = RunSummary(
                        id=run_key, strategy=strategy, run_type="execution_study",
                        start_date=period.get("start"), end_date=period.get("end"),
                        execution_model=scenario, slippage_bps=slippage,
                        profitable=total_return > 0,
                        starting_equity=float(row["starting_capital"]),
                        total_return=total_return, source_path=self.relative(metrics_path),
                        provenance=Provenance(
                            source_file=self.relative(metrics_path), strategy_version=strategy,
                            baseline_status="FROZEN", data_period=(
                                f"{period.get('start')} to {period.get('end')}" if period else None
                            ), execution_model=scenario, slippage_bps=slippage,
                        ),
                    )
                    self.runs[run_key] = RunRecord(summary_run, metrics_path, metrics_row=row)
            except (ArtifactLoadError, KeyError, TypeError, ValueError) as exc:
                self.issues.append({"source": self.relative(root), "code": "malformed_artifact", "message": str(exc)})

        report_paths = list(docs.glob("*.md"))
        report_paths += list((output / "walk_forward").glob("*/*/report.md"))
        report_paths += list((output / "execution_studies").glob("*/*/report.md"))
        for path in sorted(report_paths):
            safe = safe_child(docs if docs in path.resolve().parents else output, path)
            relative = self.relative(safe)
            report_id = relative.replace("/", "--").removesuffix(".md").lower()
            category = "specification" if relative.startswith("docs/") else "generated_report"
            title = safe.stem.replace("-", " ").title()
            self.reports[report_id] = ReportRecord(
                ReportSummary(id=report_id, title=title, category=category, source_path=relative), safe
            )
