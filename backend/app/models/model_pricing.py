from uuid import uuid4

from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class ModelPricing(TimestampMixin, Base):
    """Optional user-configured pricing (USD per 1M tokens) for local cost analytics."""

    __tablename__ = "model_pricing"
    __table_args__ = (
        UniqueConstraint(
            "provider_name", "model_name", name="uq_model_pricing_provider_model"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    provider_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    input_cost_per_1m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_cost_per_1m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
