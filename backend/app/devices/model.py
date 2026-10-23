from sqlalchemy import Column, Integer, String, DateTime

from app.timezone import now_ist_naive
from database.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True
    )

    name = Column(
        String,
        nullable=False,
        index=True
    )

    ip = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    device_type = Column(
        String,
        nullable=False,
        default="Unknown Device",
        index=True
    )

    network_type = Column(
        String,
        nullable=False,
        default="Unknown",
        server_default="Unknown",
    )

    source = Column(
        String(16),
        nullable=False,
        default="manual",
        server_default="manual",
        index=True,
    )

    created_at = Column(
        DateTime,
        default=now_ist_naive,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=now_ist_naive,
        onupdate=now_ist_naive,
        nullable=False
    )