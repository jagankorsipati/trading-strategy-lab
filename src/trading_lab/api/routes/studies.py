from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from trading_lab.api.dependencies import get_catalog
from trading_lab.api.models.responses import ExecutionStudyDetail, StudySummary, WalkForwardDetail
from trading_lab.api.services.artifact_catalog import ArtifactCatalog
from trading_lab.api.services.result_loader import ArtifactLoadError, load_csv_rows, load_json

router = APIRouter(tags=["studies"])


@router.get("/walk-forward", response_model=list[StudySummary])
def list_walk_forward(catalog: ArtifactCatalog = Depends(get_catalog)) -> list[StudySummary]:
    return [record.summary for record in catalog.walk_forward.values()]


@router.get("/walk-forward/{study_id}", response_model=WalkForwardDetail)
def get_walk_forward(study_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> WalkForwardDetail:
    record = catalog.walk_forward.get(study_id)
    if record is None:
        raise HTTPException(404, detail={"code": "unknown_study", "message": study_id})
    try:
        return WalkForwardDetail(
            **record.summary.model_dump(),
            config=load_json(record.root / "config.json"),
            summary=load_json(record.root / "summary.json"),
            windows=load_csv_rows(record.root / "windows.csv"),
            periods=load_csv_rows(record.root / "period_metrics.csv"),
        )
    except ArtifactLoadError as exc:
        raise HTTPException(422, detail={"code": "malformed_artifact", "message": exc.message}) from exc


@router.get("/execution-studies", response_model=list[StudySummary])
def list_execution_studies(catalog: ArtifactCatalog = Depends(get_catalog)) -> list[StudySummary]:
    return [record.summary for record in catalog.execution_studies.values()]


@router.get("/execution-studies/{study_id}", response_model=ExecutionStudyDetail)
def get_execution_study(study_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> ExecutionStudyDetail:
    record = catalog.execution_studies.get(study_id)
    if record is None:
        raise HTTPException(404, detail={"code": "unknown_study", "message": study_id})
    try:
        return ExecutionStudyDetail(
            **record.summary.model_dump(),
            config=load_json(record.root / "config.json"),
            scenarios=load_csv_rows(record.root / "metrics.csv"),
        )
    except ArtifactLoadError as exc:
        raise HTTPException(422, detail={"code": "malformed_artifact", "message": exc.message}) from exc
