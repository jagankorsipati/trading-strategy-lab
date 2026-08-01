from fastapi import Request

from trading_lab.api.config import ApiConfig
from trading_lab.api.services.artifact_catalog import ArtifactCatalog


def get_config(request: Request) -> ApiConfig:
    return request.app.state.config


def get_catalog(request: Request) -> ArtifactCatalog:
    return ArtifactCatalog(get_config(request))
