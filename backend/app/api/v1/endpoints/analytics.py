from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.productivity import (
    AnalyticsOverviewResponse,
    ModelPricingListResponse,
    ModelPricingResponse,
    ModelPricingUpsertRequest,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get local chat, request, token, and optional cost analytics",
)
def read_analytics_overview(
    days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    return analytics_service.get_analytics_overview(db, days=days)


@router.get(
    "/pricing",
    response_model=ModelPricingListResponse,
    summary="List user-configured model pricing rates",
)
def read_model_pricing(db: Session = Depends(get_db)) -> ModelPricingListResponse:
    return analytics_service.list_pricing(db)


@router.put(
    "/pricing",
    response_model=ModelPricingResponse,
    summary="Configure per-1M token pricing for a model locally",
)
def save_model_pricing(
    payload: ModelPricingUpsertRequest,
    db: Session = Depends(get_db),
) -> ModelPricingResponse:
    return analytics_service.upsert_pricing(db, payload)


@router.delete(
    "/pricing/{pricing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a configured pricing entry",
)
def remove_model_pricing(
    pricing_id: str, db: Session = Depends(get_db)
) -> Response:
    analytics_service.delete_pricing(db, pricing_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
