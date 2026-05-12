"""Routes for librarian provider settings and operations."""

from __future__ import annotations

from app.library.application.librarian_service import LibrarianService
from app.library.interface.routers.dependencies import get_librarian_service
from app.library.interface.schemas.provider_schema import (
    LibrarianProviderCreateRequest,
    LibrarianProviderPatchRequest,
    LibrarianProviderResponse,
    LibrarianProviderTestRequest,
    LibrarianProviderTestResponse,
)
from app.shared.exceptions import (
    LibraryProviderUnsupportedError,
    LibraryResourceNotFoundError,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/settings/librarians", tags=["librarians"])


@router.post(
    "",
    response_model=LibrarianProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_librarian_provider(
    request: LibrarianProviderCreateRequest,
    service: LibrarianService = Depends(get_librarian_service),
) -> LibrarianProviderResponse:
    """Create provider settings."""
    try:
        payload = await service.create_provider(
            name=request.name,
            provider_type=request.provider_type,
            auth_type=request.auth_type,
            enabled=request.enabled,
            config=request.config,
            api_key=request.api_key,
            oauth_access_token=request.oauth_access_token,
        )
    except LibraryProviderUnsupportedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return LibrarianProviderResponse.model_validate(payload)


@router.get("", response_model=list[LibrarianProviderResponse])
async def list_librarian_providers(
    service: LibrarianService = Depends(get_librarian_service),
) -> list[LibrarianProviderResponse]:
    """List all configured providers."""
    payloads = await service.list_providers()
    return [LibrarianProviderResponse.model_validate(payload) for payload in payloads]


@router.get("/{provider_id}", response_model=LibrarianProviderResponse)
async def get_librarian_provider(
    provider_id: int,
    service: LibrarianService = Depends(get_librarian_service),
) -> LibrarianProviderResponse:
    """Read one provider by id."""
    try:
        payload = await service.get_provider(provider_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return LibrarianProviderResponse.model_validate(payload)


@router.patch("/{provider_id}", response_model=LibrarianProviderResponse)
async def patch_librarian_provider(
    provider_id: int,
    request: LibrarianProviderPatchRequest,
    service: LibrarianService = Depends(get_librarian_service),
) -> LibrarianProviderResponse:
    """Patch provider settings."""
    payload = request.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided",
        )
    try:
        updated = await service.update_provider(
            provider_id,
            payload=payload,
        )
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except LibraryProviderUnsupportedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return LibrarianProviderResponse.model_validate(updated)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_librarian_provider(
    provider_id: int,
    service: LibrarianService = Depends(get_librarian_service),
) -> None:
    """Delete provider and associated secrets."""
    try:
        await service.delete_provider(provider_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{provider_id}/test", response_model=LibrarianProviderTestResponse)
async def test_librarian_provider(
    provider_id: int,
    request: LibrarianProviderTestRequest,
    service: LibrarianService = Depends(get_librarian_service),
) -> LibrarianProviderTestResponse:
    """Run quick provider validation."""
    result = await service.test_provider(
        provider_id,
        test_query=request.test_query,
    )
    return LibrarianProviderTestResponse.model_validate(result)
