from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import BigInteger, Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


class SurveyStatus(str, Enum):
    pending = "pending"
    answered = "answered"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Warsaw")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    surveys: Mapped[list[Survey]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Survey(Base):
    __tablename__ = "surveys"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_survey_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[SurveyStatus] = mapped_column(SqlEnum(SurveyStatus), default=SurveyStatus.pending)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="surveys")
    answer: Mapped[Answer | None] = relationship(back_populates="survey", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), unique=True, index=True)
    mood: Mapped[str] = mapped_column(String(16))
    campaigns_count: Mapped[int] = mapped_column(Integer)
    geo_count: Mapped[int] = mapped_column(Integer)
    creatives_count: Mapped[int] = mapped_column(Integer)
    accounts_count: Mapped[int] = mapped_column(Integer)

    survey: Mapped[Survey] = relationship(back_populates="answer")
