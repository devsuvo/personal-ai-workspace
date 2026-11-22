from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.security import (
    EncryptionOperationError,
    EncryptionService,
    MasterKeyError,
    SecurityError,
    get_encryption_service,
    mask_api_key,
    validate_base_url,
)
from app.models.provider import Provider, ProviderCredential, ProviderModel
from app.providers.base import ProviderAdapterError
from app.providers.registry import (
    get_provider_adapter,
    get_provider_descriptor,
    list_planned_providers,
)
from app.schemas.provider import (
    CredentialCreateRequest,
    CredentialResponse,
    CredentialUpdateRequest,
    ProviderCapabilitiesSchema,
    ProviderCatalogItem,
    ProviderCreateRequest,
    ProviderDetailResponse,
    ProviderModelCreateRequest,
    ProviderModelResponse,
    ProviderModelsListResponse,
    ProviderModelUpdateRequest,
    ProviderSummaryResponse,
    ProviderTestResponse,
    ProviderUpdateRequest,
)

logger = logging.getLogger("workspace.providers")


def _build_encryption_service(db: Session) -> EncryptionService:
    def _has_credentials() -> bool:
        count = db.execute(select(func.count(ProviderCredential.id))).scalar_one()
        return count > 0

    return get_encryption_service(has_encrypted_data_check=_has_credentials)


def _to_credential_response(cred: ProviderCredential) -> CredentialResponse:
    return CredentialResponse(
        id=cred.id,
        provider_id=cred.provider_id,
        credential_name=cred.credential_name,
        masked_api_key=cred.key_fingerprint,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )


def _to_model_response(model: ProviderModel) -> ProviderModelResponse:
    return ProviderModelResponse(
        id=model.id,
        provider_id=model.provider_id,
        model_id=model.model_id,
        display_name=model.display_name,
        capabilities=model.capabilities or {},
        is_available=model.is_available,
        is_manual=model.is_manual,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_summary_response(provider: Provider) -> ProviderSummaryResponse:
    descriptor = get_provider_descriptor(provider.provider_key)
    return ProviderSummaryResponse(
        id=provider.id,
        provider_key=provider.provider_key,
        display_name=provider.display_name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        enabled=provider.enabled,
        default_model=provider.default_model,
        connection_status=provider.connection_status,
        last_tested_at=provider.last_tested_at,
        last_error=provider.last_error,
        credentials_count=len(provider.credentials),
        models_count=len(provider.models),
        requires_api_key=descriptor.requires_api_key,
        is_local=descriptor.is_local,
        supports_model_listing=descriptor.supports_model_listing,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _to_detail_response(provider: Provider) -> ProviderDetailResponse:
    summary = _to_summary_response(provider)
    adapter = get_provider_adapter(provider.provider_key)
    caps = adapter.get_capabilities()
    return ProviderDetailResponse(
        **summary.model_dump(),
        credentials=[_to_credential_response(c) for c in provider.credentials],
        models=[_to_model_response(m) for m in provider.models],
        capabilities=ProviderCapabilitiesSchema(
            supports_model_listing=caps.supports_model_listing,
            supports_streaming=caps.supports_streaming,
            supports_tools=caps.supports_tools,
            supports_vision=caps.supports_vision,
            requires_api_key=caps.requires_api_key,
            is_local=caps.is_local,
            allows_custom_base_url=caps.allows_custom_base_url,
        ),
    )


def _load_provider_or_404(db: Session, provider_id: str) -> Provider:
    provider = db.execute(
        select(Provider)
        .options(
            selectinload(Provider.credentials),
            selectinload(Provider.models),
        )
        .where(Provider.id == provider_id)
    ).scalar_one_or_none()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI provider not found.",
        )
    return provider


def _get_active_api_key(db: Session, provider: Provider) -> str | None:
    active_creds = [c for c in provider.credentials if c.is_active]
    if not active_creds:
        return None
    encryption = _build_encryption_service(db)
    try:
        return encryption.decrypt(active_creds[0].encrypted_api_key)
    except (MasterKeyError, EncryptionOperationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


def list_provider_catalog() -> list[ProviderCatalogItem]:
    items: list[ProviderCatalogItem] = []
    for desc in list_planned_providers():
        adapter = get_provider_adapter(desc.id)
        caps = adapter.get_capabilities()
        items.append(
            ProviderCatalogItem(
                provider_key=desc.id,
                name=desc.name,
                provider_type=desc.provider_type,
                description=desc.description,
                default_base_url=desc.default_base_url,
                requires_api_key=desc.requires_api_key,
                is_local=desc.is_local,
                allows_custom_base_url=desc.allows_custom_base_url,
                supports_model_listing=desc.supports_model_listing,
                capabilities=ProviderCapabilitiesSchema(
                    supports_model_listing=caps.supports_model_listing,
                    supports_streaming=caps.supports_streaming,
                    supports_tools=caps.supports_tools,
                    supports_vision=caps.supports_vision,
                    requires_api_key=caps.requires_api_key,
                    is_local=caps.is_local,
                    allows_custom_base_url=caps.allows_custom_base_url,
                ),
            )
        )
    return items


def list_providers(db: Session) -> list[ProviderSummaryResponse]:
    rows = db.execute(
        select(Provider)
        .options(
            selectinload(Provider.credentials),
            selectinload(Provider.models),
        )
        .order_by(Provider.created_at.desc())
    ).scalars().all()
    return [_to_summary_response(p) for p in rows]


def get_provider(db: Session, provider_id: str) -> ProviderDetailResponse:
    provider = _load_provider_or_404(db, provider_id)
    return _to_detail_response(provider)


def create_provider(
    db: Session, payload: ProviderCreateRequest
) -> ProviderDetailResponse:
    try:
        descriptor = get_provider_descriptor(payload.provider_key)
    except ProviderAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    resolved_base_url = (payload.base_url or descriptor.default_base_url or "").strip() or None
    if resolved_base_url is not None:
        try:
            resolved_base_url = validate_base_url(resolved_base_url)
        except SecurityError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
    elif descriptor.id == "custom_openai":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Custom OpenAI-Compatible API requires a valid Base URL.",
        )

    provider = Provider(
        provider_key=descriptor.id,
        display_name=payload.display_name.strip(),
        provider_type=descriptor.provider_type,
        base_url=resolved_base_url,
        enabled=payload.enabled,
        default_model=payload.default_model.strip() if payload.default_model else None,
        connection_status="untested",
    )
    db.add(provider)
    db.flush()

    if payload.api_key and payload.api_key.strip():
        encryption = _build_encryption_service(db)
        try:
            encrypted_key = encryption.encrypt(payload.api_key.strip())
        except (MasterKeyError, EncryptionOperationError) as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        cred = ProviderCredential(
            provider_id=provider.id,
            credential_name=payload.credential_name.strip() or "Default Key",
            encrypted_api_key=encrypted_key,
            key_fingerprint=mask_api_key(payload.api_key),
            is_active=True,
        )
        db.add(cred)

    if provider.default_model:
        db.add(
            ProviderModel(
                provider_id=provider.id,
                model_id=provider.default_model,
                display_name=provider.default_model,
                capabilities={},
                is_available=True,
                is_manual=True,
            )
        )

    db.commit()
    db.expire_all()
    return get_provider(db, provider.id)


def update_provider(
    db: Session, provider_id: str, payload: ProviderUpdateRequest
) -> ProviderDetailResponse:
    provider = _load_provider_or_404(db, provider_id)

    if payload.display_name is not None:
        provider.display_name = payload.display_name.strip()

    if payload.base_url is not None:
        cleaned = payload.base_url.strip()
        if cleaned:
            try:
                provider.base_url = validate_base_url(cleaned)
            except SecurityError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
        else:
            provider.base_url = None

    if payload.enabled is not None:
        provider.enabled = payload.enabled

    if payload.default_model is not None:
        cleaned_model = payload.default_model.strip()
        provider.default_model = cleaned_model or None

    db.commit()
    db.expire_all()
    return get_provider(db, provider.id)


def delete_provider(db: Session, provider_id: str) -> None:
    provider = _load_provider_or_404(db, provider_id)
    db.delete(provider)
    db.commit()


def add_credential(
    db: Session, provider_id: str, payload: CredentialCreateRequest
) -> CredentialResponse:
    provider = _load_provider_or_404(db, provider_id)
    encryption = _build_encryption_service(db)

    try:
        encrypted_key = encryption.encrypt(payload.api_key.strip())
    except (MasterKeyError, EncryptionOperationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if payload.is_active:
        for existing in provider.credentials:
            existing.is_active = False

    cred = ProviderCredential(
        provider_id=provider.id,
        credential_name=payload.credential_name.strip(),
        encrypted_api_key=encrypted_key,
        key_fingerprint=mask_api_key(payload.api_key),
        is_active=payload.is_active,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return _to_credential_response(cred)


def update_credential(
    db: Session,
    provider_id: str,
    credential_id: str,
    payload: CredentialUpdateRequest,
) -> CredentialResponse:
    provider = _load_provider_or_404(db, provider_id)
    cred = next((c for c in provider.credentials if c.id == credential_id), None)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found.",
        )

    if payload.credential_name is not None:
        cred.credential_name = payload.credential_name.strip()

    if payload.api_key is not None:
        encryption = _build_encryption_service(db)
        try:
            cred.encrypted_api_key = encryption.encrypt(payload.api_key.strip())
            cred.key_fingerprint = mask_api_key(payload.api_key)
        except (MasterKeyError, EncryptionOperationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    if payload.is_active is not None:
        if payload.is_active:
            for other in provider.credentials:
                other.is_active = other.id == cred.id
        else:
            cred.is_active = False

    db.commit()
    db.refresh(cred)
    return _to_credential_response(cred)


def delete_credential(db: Session, provider_id: str, credential_id: str) -> None:
    provider = _load_provider_or_404(db, provider_id)
    cred = next((c for c in provider.credentials if c.id == credential_id), None)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found.",
        )

    was_active = cred.is_active
    db.delete(cred)
    db.flush()

    # Promote another credential if one remains and the deleted one was active
    if was_active:
        remaining = [c for c in provider.credentials if c.id != credential_id]
        if remaining:
            remaining[0].is_active = True

    db.commit()


def test_provider_connection(db: Session, provider_id: str) -> ProviderTestResponse:
    provider = _load_provider_or_404(db, provider_id)
    adapter = get_provider_adapter(provider.provider_key)
    api_key = _get_active_api_key(db, provider)

    result = adapter.test_connection(base_url=provider.base_url, api_key=api_key)
    tested_at = datetime.now(timezone.utc)

    provider.connection_status = result.status
    provider.last_tested_at = tested_at
    provider.last_error = None if result.success else result.message
    db.commit()

    return ProviderTestResponse(
        provider_id=provider.id,
        success=result.success,
        connection_status=result.status,
        message=result.message,
        error_code=result.error_code,
        latency_ms=result.latency_ms,
        models_found=result.models_found,
        tested_at=tested_at,
    )


def list_provider_models(
    db: Session, provider_id: str, refresh: bool = False
) -> ProviderModelsListResponse:
    provider = _load_provider_or_404(db, provider_id)
    adapter = get_provider_adapter(provider.provider_key)
    caps = adapter.get_capabilities()
    warning: str | None = None

    if refresh:
        if not caps.supports_model_listing:
            warning = "This provider does not support automatic model listing. Add models manually."
        else:
            api_key = _get_active_api_key(db, provider)
            try:
                discovered = adapter.list_models(
                    base_url=provider.base_url, api_key=api_key
                )
                existing_by_id = {m.model_id: m for m in provider.models}
                for item in discovered:
                    existing = existing_by_id.get(item.model_id)
                    if existing is None:
                        db.add(
                            ProviderModel(
                                provider_id=provider.id,
                                model_id=item.model_id,
                                display_name=item.display_name,
                                capabilities=item.capabilities,
                                is_available=True,
                                is_manual=False,
                            )
                        )
                    else:
                        existing.display_name = item.display_name
                        if item.capabilities:
                            existing.capabilities = item.capabilities
                db.commit()
                db.expire_all()
                provider = _load_provider_or_404(db, provider_id)
            except ProviderAdapterError as exc:
                warning = exc.message

    return ProviderModelsListResponse(
        provider_id=provider.id,
        supports_model_listing=caps.supports_model_listing,
        models=[_to_model_response(m) for m in provider.models],
        discovery_warning=warning,
    )


def add_provider_model(
    db: Session, provider_id: str, payload: ProviderModelCreateRequest
) -> ProviderModelResponse:
    provider = _load_provider_or_404(db, provider_id)
    cleaned_id = payload.model_id.strip()

    existing = next((m for m in provider.models if m.model_id == cleaned_id), None)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{cleaned_id}' is already registered for this provider.",
        )

    model = ProviderModel(
        provider_id=provider.id,
        model_id=cleaned_id,
        display_name=(payload.display_name or cleaned_id).strip(),
        capabilities=payload.capabilities or {},
        is_available=payload.is_available,
        is_manual=True,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _to_model_response(model)


def update_provider_model(
    db: Session,
    provider_id: str,
    model_record_id: str,
    payload: ProviderModelUpdateRequest,
) -> ProviderModelResponse:
    provider = _load_provider_or_404(db, provider_id)
    model = next((m for m in provider.models if m.id == model_record_id), None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider model not found.",
        )

    if payload.display_name is not None:
        model.display_name = payload.display_name.strip()
    if payload.is_available is not None:
        model.is_available = payload.is_available

    db.commit()
    db.refresh(model)
    return _to_model_response(model)


def delete_provider_model(
    db: Session, provider_id: str, model_record_id: str
) -> None:
    provider = _load_provider_or_404(db, provider_id)
    model = next((m for m in provider.models if m.id == model_record_id), None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider model not found.",
        )
    if provider.default_model == model.model_id:
        provider.default_model = None
    db.delete(model)
    db.commit()


def set_default_model(
    db: Session, provider_id: str, model_id: str | None
) -> ProviderDetailResponse:
    provider = _load_provider_or_404(db, provider_id)
    cleaned = model_id.strip() if model_id else None

    if cleaned:
        existing = next((m for m in provider.models if m.model_id == cleaned), None)
        if existing is None:
            db.add(
                ProviderModel(
                    provider_id=provider.id,
                    model_id=cleaned,
                    display_name=cleaned,
                    capabilities={},
                    is_available=True,
                    is_manual=True,
                )
            )
    provider.default_model = cleaned
    db.commit()
    db.expire_all()
    return get_provider(db, provider.id)
