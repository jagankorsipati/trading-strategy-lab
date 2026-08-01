from fastapi import APIRouter, Depends, HTTPException

from trading_lab.api.dependencies import get_catalog
from trading_lab.api.models.responses import ReportDetail, ReportSummary
from trading_lab.api.services.artifact_catalog import ArtifactCatalog

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
def list_reports(catalog: ArtifactCatalog = Depends(get_catalog)) -> list[ReportSummary]:
    return [record.summary for record in catalog.reports.values()]


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: str, catalog: ArtifactCatalog = Depends(get_catalog)) -> ReportDetail:
    record = catalog.reports.get(report_id)
    if record is None:
        raise HTTPException(404, detail={"code": "unknown_report", "message": report_id})
    try:
        markdown = record.path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(422, detail={"code": "missing_artifact", "message": str(exc)}) from exc
    return ReportDetail(**record.summary.model_dump(), markdown=markdown, raw_html_enabled=False)
