from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.system import (
    DatabaseStatusResponse,
    SecurityStatusResponse,
    SystemInfoResponse,
)
from app.services.system_service import (
    get_database_status,
    get_security_status,
    get_system_info,
)

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    summary="Retrieve local system and workspace information",
)
def read_system_info(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> SystemInfoResponse:
    """Return local runtime, storage, and AI provider status."""
    return get_system_info(settings, db=db, db_engine=db.get_bind())


@router.get(
    "/database",
    response_model=DatabaseStatusResponse,
    summary="Retrieve real local SQLite database status and migration state",
)
def read_database_status(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> DatabaseStatusResponse:
    """Return connection state, database type, size, and Alembic migration status."""
    return get_database_status(settings, db_engine=db.get_bind())


@router.get(
    "/security",
    response_model=SecurityStatusResponse,
    summary="Retrieve non-sensitive local security and encryption status",
)
def read_security_status(
    settings: Settings = Depends(get_settings),
) -> SecurityStatusResponse:
    """Return encryption algorithm and key initialization status without exposing secrets."""
    return get_security_status(settings)
