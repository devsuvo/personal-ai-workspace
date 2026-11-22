from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.model_pricing import ModelPricing
from app.models.usage_log import UsageLog
from app.schemas.productivity import (
    AnalyticsOverviewResponse,
    ModelPricingListResponse,
    ModelPricingResponse,
    ModelPricingUpsertRequest,
    ModelUsageBreakdown,
    PeriodUsagePoint,
)


def list_pricing(db: Session) -> ModelPricingListResponse:
    rows = (
        db.execute(
            select(ModelPricing).order_by(
                ModelPricing.provider_name.asc(), ModelPricing.model_name.asc()
            )
        )
        .scalars()
        .all()
    )
    return ModelPricingListResponse(
        pricing=[
            ModelPricingResponse(
                id=r.id,
                provider_name=r.provider_name,
                model_name=r.model_name,
                input_cost_per_1m=r.input_cost_per_1m,
                output_cost_per_1m=r.output_cost_per_1m,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
    )


def upsert_pricing(
    db: Session, payload: ModelPricingUpsertRequest
) -> ModelPricingResponse:
    prov = payload.provider_name.strip()
    model = payload.model_name.strip()
    existing = db.execute(
        select(ModelPricing).where(
            ModelPricing.provider_name == prov,
            ModelPricing.model_name == model,
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = ModelPricing(
            provider_name=prov,
            model_name=model,
            input_cost_per_1m=payload.input_cost_per_1m,
            output_cost_per_1m=payload.output_cost_per_1m,
        )
        db.add(existing)
    else:
        existing.input_cost_per_1m = payload.input_cost_per_1m
        existing.output_cost_per_1m = payload.output_cost_per_1m

    db.commit()
    db.refresh(existing)
    return ModelPricingResponse(
        id=existing.id,
        provider_name=existing.provider_name,
        model_name=existing.model_name,
        input_cost_per_1m=existing.input_cost_per_1m,
        output_cost_per_1m=existing.output_cost_per_1m,
        updated_at=existing.updated_at,
    )


def delete_pricing(db: Session, pricing_id: str) -> None:
    row = db.get(ModelPricing, pricing_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pricing entry not found."
        )
    db.delete(row)
    db.commit()


def get_analytics_overview(db: Session, days: int = 30) -> AnalyticsOverviewResponse:
    total_conversations = int(
        db.execute(select(func.count(Conversation.id))).scalar_one()
    )
    total_messages = int(db.execute(select(func.count(Message.id))).scalar_one())

    logs = db.execute(select(UsageLog).order_by(UsageLog.created_at.asc())).scalars().all()
    pricing_rows = db.execute(select(ModelPricing)).scalars().all()
    pricing_map = {
        (p.provider_name.lower(), p.model_name.lower()): (
            p.input_cost_per_1m,
            p.output_cost_per_1m,
        )
        for p in pricing_rows
    }

    total_requests = len(logs)
    successful_requests = sum(1 for l in logs if l.request_status == "success")
    failed_requests = sum(1 for l in logs if l.request_status == "error")
    total_in = sum(l.input_tokens for l in logs)
    total_out = sum(l.output_tokens for l in logs)

    # Breakdown by (provider_name, model_name)
    model_buckets: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"requests": 0, "in": 0, "out": 0}
    )
    daily_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"requests": 0, "in": 0, "out": 0}
    )
    monthly_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"requests": 0, "in": 0, "out": 0}
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for log in logs:
        key = (log.provider_name, log.model_name)
        model_buckets[key]["requests"] += 1
        model_buckets[key]["in"] += log.input_tokens
        model_buckets[key]["out"] += log.output_tokens

        created = log.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        if created >= cutoff:
            day_key = created.strftime("%Y-%m-%d")
            daily_buckets[day_key]["requests"] += 1
            daily_buckets[day_key]["in"] += log.input_tokens
            daily_buckets[day_key]["out"] += log.output_tokens

        month_key = created.strftime("%Y-%m")
        monthly_buckets[month_key]["requests"] += 1
        monthly_buckets[month_key]["in"] += log.input_tokens
        monthly_buckets[month_key]["out"] += log.output_tokens

    has_pricing = len(pricing_map) > 0
    total_estimated_cost = 0.0
    any_model_priced = False

    top_models: list[ModelUsageBreakdown] = []
    for (prov, model), stats in sorted(
        model_buckets.items(), key=lambda kv: kv[1]["requests"], reverse=True
    ):
        rate = pricing_map.get((prov.lower(), model.lower()))
        est_cost: float | None = None
        if rate is not None:
            in_rate, out_rate = rate
            est_cost = round(
                (stats["in"] / 1_000_000.0) * in_rate
                + (stats["out"] / 1_000_000.0) * out_rate,
                6,
            )
            total_estimated_cost += est_cost
            any_model_priced = True

        top_models.append(
            ModelUsageBreakdown(
                provider_name=prov,
                model_name=model,
                requests=stats["requests"],
                input_tokens=stats["in"],
                output_tokens=stats["out"],
                total_tokens=stats["in"] + stats["out"],
                estimated_cost=est_cost,
            )
        )

    daily_usage = [
        PeriodUsagePoint(
            period=day,
            requests=s["requests"],
            input_tokens=s["in"],
            output_tokens=s["out"],
            total_tokens=s["in"] + s["out"],
        )
        for day, s in sorted(daily_buckets.items())
    ]

    monthly_usage = [
        PeriodUsagePoint(
            period=month,
            requests=s["requests"],
            input_tokens=s["in"],
            output_tokens=s["out"],
            total_tokens=s["in"] + s["out"],
        )
        for month, s in sorted(monthly_buckets.items())
    ]

    return AnalyticsOverviewResponse(
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_tokens=total_in + total_out,
        estimated_total_cost=round(total_estimated_cost, 6)
        if any_model_priced
        else None,
        has_configured_pricing=has_pricing,
        top_models=top_models[:12],
        daily_usage=daily_usage,
        monthly_usage=monthly_usage,
    )
