"""Routes for MINIO-backed library archive item discovery."""

from __future__ import annotations

from app.archive.application.minio.use_cases.import_archive_items import (
    MinioArchiveImportUseCase,
)
from app.archive.application.minio.use_cases.list_archive_items import (
    ListMinioArchiveItemsUseCase,
)
from app.archive.interface.schemas.minio_archive.minio_archive_schema import (
    MinioArchiveItemResponseList,
    MinioImportCandidateResponseList,
    MinioImportRequest,
    MinioImportResultResponse,
)
from app.container import ApplicationContainer
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/archive/minio", tags=["minio"])


@router.get(
    "/library/items",
    response_model=MinioArchiveItemResponseList,
    status_code=status.HTTP_200_OK,
    summary="List MINIO archive items",
    description="Return enabled MINIO provider objects as normalized library archive items.",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_minio_items(
    limit: int = Query(default=48, ge=1, le=1000),
    use_case: ListMinioArchiveItemsUseCase = Depends(
        Provide[ApplicationContainer.archive.minio_archive_list_use_case]
    ),
) -> MinioArchiveItemResponseList:
    """List MINIO objects normalized into archive item responses.

    Args:
        limit [int]: Value supplied to list_minio_items.
        use_case [ListMinioArchiveItemsUseCase]: Value supplied to list_minio_items.

    Returns:
        MinioArchiveItemResponseList: Value produced by list_minio_items.
    """
    archive_items = await use_case.execute(limit=limit)
    validation = MinioArchiveItemResponseList.from_archive_items(archive_items)
    return validation


@router.get(
    "/import-candidates",
    response_model=MinioImportCandidateResponseList,
    status_code=status.HTTP_200_OK,
    summary="Scan MINIO import candidates",
    description="Return external archive objects inferred as library import candidates.",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def scan_minio_import_candidates(
    limit: int = Query(default=48, ge=1, le=1000),
    use_case: MinioArchiveImportUseCase = Depends(
        Provide[ApplicationContainer.archive.minio_archive_import_use_case]
    ),
) -> MinioImportCandidateResponseList:
    """Scan MINIO objects and return library card candidates.

    Args:
        limit: Maximum candidate count.
        use_case: MINIO import scanner use case.

    Returns:
        Public candidate response list.
    """
    candidates = await use_case.scan(limit=limit)
    validation = MinioImportCandidateResponseList.from_candidates(candidates)
    return validation


@router.post(
    "/import",
    response_model=MinioImportResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import MINIO archive candidates",
    description="Create DB catalog rows linked to external MINIO originals.",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def import_minio_items(
    request: MinioImportRequest,
    use_case: MinioArchiveImportUseCase = Depends(
        Provide[ApplicationContainer.archive.minio_archive_import_use_case]
    ),
) -> MinioImportResultResponse:
    """Import linked MINIO objects as library catalog rows.

    Args:
        request: Import request including candidate limit.
        use_case: MINIO import use case.

    Returns:
        Public import result response.
    """
    result = await use_case.import_linked(limit=request.limit)
    validation = MinioImportResultResponse.from_result(result)
    return validation
