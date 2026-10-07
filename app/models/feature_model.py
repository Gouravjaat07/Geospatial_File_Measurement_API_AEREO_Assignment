from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base

if TYPE_CHECKING:
    from app.models.file_model import FileRecord


class FeatureRecord(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), index=True, nullable=False)
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str | None] = mapped_column(String(50))
    geometry: Mapped[dict | None] = mapped_column(JSON)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    area: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str | None] = mapped_column(String(20))
    length: Mapped[float | None] = mapped_column(Float)
    length_unit: Mapped[str | None] = mapped_column(String(20))
    measurement_crs: Mapped[str | None] = mapped_column(String(255))
    measurement_status: Mapped[str] = mapped_column(String(30), nullable=False)
    measurement_message: Mapped[str | None] = mapped_column(Text)
    file: Mapped["FileRecord"] = relationship(back_populates="features")
