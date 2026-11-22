from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.provider import (
    CredentialCreateRequest,
    CredentialResponse,
    CredentialUpdateRequest,
    DefaultModelUpdateRequest,
    ProviderCatalogResponse,
    ProviderCreateRequest,
    ProviderDetailResponse,
    ProviderListResponse,
    ProviderModelCreateRequest,
    ProviderModelResponse,
    ProviderModelsListResponse,
    ProviderModelUpdateRequest,
    ProviderTestResponse,
    ProviderUpdateRequest,
)
from app.services import provider_service

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get(
    "/registry",
    response_model=ProviderCatalogResponse,
    summary="List all supported AI provider types and their capabilities",
)
def read_provider_registry() -> ProviderCatalogResponse:
    return ProviderCatalogResponse(providers=provider_service.list_provider_catalog())


@router.get(
    "",
    response_model=ProviderListResponse,
    summary="List all configured local AI providers",
)
def list_configured_providers(
    db: Session = Depends(get_db),
) -> ProviderListResponse:
    return ProviderListResponse(providers=provider_service.list_providers(db))


@router.post(
    "",
    response_model=ProviderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and configure a new local AI provider",
)
def create_configured_provider(
    payload: ProviderCreateRequest,
    db: Session = Depends(get_db),
) -> ProviderDetailResponse:
    return provider_service.create_provider(db, payload)


@router.get(
    "/{provider_id}",
    response_model=ProviderDetailResponse,
    summary="Get full configuration, masked credentials, and models for a provider",
)
def read_configured_provider(
    provider_id: str,
    db: Session = Depends(get_db),
) -> ProviderDetailResponse:
    return provider_service.get_provider(db, provider_id)


@router.put(
    "/{provider_id}",
    response_model=ProviderDetailResponse,
    summary="Update provider configuration",
)
def update_configured_provider(
    provider_id: str,
    payload: ProviderUpdateRequest,
    db: Session = Depends(get_db),
) -> ProviderDetailResponse:
    return provider_service.update_provider(db, provider_id, payload)


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a configured AI provider and all its encrypted credentials",
)
def delete_configured_provider(
    provider_id: str,
    db: Session = Depends(get_db),
) -> Response:
    provider_service.delete_provider(db, provider_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{provider_id}/credentials",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an encrypted API credential to a provider",
)
def add_provider_credential(
    provider_id: str,
    payload: CredentialCreateRequest,
    db: Session = Depends(get_db),
) -> CredentialResponse:
    return provider_service.add_credential(db, provider_id, payload)


@router.put(
    "/{provider_id}/credentials/{credential_id}",
    response_model=CredentialResponse,
    summary="Update or rotate an encrypted API credential",
)
def update_provider_credential(
    provider_id: str,
    credential_id: str,
    payload: CredentialUpdateRequest,
    db: Session = Depends(get_db),
) -> CredentialResponse:
    return provider_service.update_credential(db, provider_id, credential_id, payload)


@router.delete(
    "/{provider_id}/credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an encrypted API credential",
)
def delete_provider_credential(
    provider_id: str,
    credential_id: str,
    db: Session = Depends(get_db),
) -> Response:
    provider_service.delete_credential(db, provider_id, credential_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{provider_id}/test",
    response_model=ProviderTestResponse,
    summary="Test connection and API key validity for a provider",
)
def test_provider(
    provider_id: str,
    db: Session = Depends(get_db),
) -> ProviderTestResponse:
    return provider_service.test_provider_connection(db, provider_id)


@router.get(
    "/{provider_id}/models",
    response_model=ProviderModelsListResponse,
    summary="List saved models (optionally refreshing from the provider API)",
)
def read_provider_models(
    provider_id: str,
    refresh: bool = Query(default=False, description="Fetch models live from provider API"),
    db: Session = Depends(get_db),
) -> ProviderModelsListResponse:
    return provider_service.list_provider_models(db, provider_id, refresh=refresh)


@router.post(
    "/{provider_id}/models",
    response_model=ProviderModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually register a model identifier for a provider",
)
def create_provider_model(
    provider_id: str,
    payload: ProviderModelCreateRequest,
    db: Session = Depends(get_db),
) -> ProviderModelResponse:
    return provider_service.add_provider_model(db, provider_id, payload)


@router.put(
    "/{provider_id}/models/{model_record_id}",
    response_model=ProviderModelResponse,
    summary="Enable, disable, or rename a saved provider model",
)
def update_provider_model(
    provider_id: str,
    model_record_id: str,
    payload: ProviderModelUpdateRequest,
    db: Session = Depends(get_db),
) -> ProviderModelResponse:
    return provider_service.update_provider_model(
        db, provider_id, model_record_id, payload
    )


@router.delete(
    "/{provider_id}/models/{model_record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a saved model from a provider",
)
def delete_provider_model(
    provider_id: str,
    model_record_id: str,
    db: Session = Depends(get_db),
) -> Response:
    provider_service.delete_provider_model(db, provider_id, model_record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{provider_id}/default-model",
    response_model=ProviderDetailResponse,
    summary="Set or clear the default model for a provider",
)
def update_provider_default_model(
    provider_id: str,
    payload: DefaultModelUpdateRequest,
    db: Session = Depends(get_db),
) -> ProviderDetailResponse:
    return provider_service.set_default_model(db, provider_id, payload.model_id)
