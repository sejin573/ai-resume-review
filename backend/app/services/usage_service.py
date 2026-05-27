from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.review import UsageEvent
from app.models.user import User

REVIEW_CREATE = "review_create"
REFINEMENT_CREATE = "refinement_create"
PDF_EXPORT = "pdf_export"


@dataclass(frozen=True)
class UsageLimit:
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def unlimited(self) -> bool:
        return self.limit <= 0

    def as_dict(self) -> dict:
        return {
            "used": self.used,
            "limit": self.limit,
            "remaining": self.remaining if not self.unlimited else None,
            "unlimited": self.unlimited,
        }


def is_admin_user(user: User) -> bool:
    return user.email in settings.admin_emails


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_of_today() -> datetime:
    now = _now()
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def start_of_month() -> datetime:
    now = _now()
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _count_events(db: Session, *, user_id: int, event_type: str, since: datetime) -> int:
    stmt = select(func.count(UsageEvent.id)).where(
        UsageEvent.user_id == user_id,
        UsageEvent.event_type == event_type,
        UsageEvent.created_at >= since,
    )
    return int(db.scalar(stmt) or 0)


def _limits_for_user(user: User) -> dict[str, int]:
    if is_admin_user(user):
        return {"review_daily": 0, "refine_daily": 0, "pdf_monthly": 0}
    if user.plan == "pro":
        return {
            "review_daily": settings.pro_daily_review_limit,
            "refine_daily": settings.pro_daily_refine_limit,
            "pdf_monthly": settings.pro_monthly_pdf_export_limit,
        }
    return {
        "review_daily": settings.free_daily_review_limit,
        "refine_daily": settings.free_daily_refine_limit,
        "pdf_monthly": settings.free_monthly_pdf_export_limit,
    }


def get_usage_summary(db: Session, user: User) -> dict:
    limits = _limits_for_user(user)
    today = start_of_today()
    month = start_of_month()
    review_today = _count_events(db, user_id=user.id, event_type=REVIEW_CREATE, since=today)
    refine_today = _count_events(db, user_id=user.id, event_type=REFINEMENT_CREATE, since=today)
    pdf_this_month = _count_events(db, user_id=user.id, event_type=PDF_EXPORT, since=month)
    return {
        "plan": user.plan,
        "is_admin": is_admin_user(user),
        "review_daily": UsageLimit(review_today, limits["review_daily"]).as_dict(),
        "refine_daily": UsageLimit(refine_today, limits["refine_daily"]).as_dict(),
        "pdf_monthly": UsageLimit(pdf_this_month, limits["pdf_monthly"]).as_dict(),
        "periods": {
            "daily_reset_at": (today + timedelta(days=1)).isoformat(),
            "monthly_reset_at": _next_month(month).isoformat(),
        },
    }


def _next_month(month_start: datetime) -> datetime:
    if month_start.month == 12:
        return datetime(month_start.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(month_start.year, month_start.month + 1, 1, tzinfo=timezone.utc)


def assert_usage_available(db: Session, user: User, event_type: str) -> None:
    if is_admin_user(user):
        return
    summary = get_usage_summary(db, user)
    if event_type == REVIEW_CREATE:
        bucket = summary["review_daily"]
        message = "오늘 무료 첨삭 횟수를 모두 사용했습니다. 내일 다시 시도하거나 Pro 요금제로 전환해 주세요."
    elif event_type == REFINEMENT_CREATE:
        bucket = summary["refine_daily"]
        message = "오늘 문장 다듬기 횟수를 모두 사용했습니다. 내일 다시 시도하거나 Pro 요금제로 전환해 주세요."
    elif event_type == PDF_EXPORT:
        bucket = summary["pdf_monthly"]
        message = "이번 달 PDF 내보내기 횟수를 모두 사용했습니다. 다음 달에 다시 시도하거나 Pro 요금제로 전환해 주세요."
    else:
        return
    if bucket["unlimited"]:
        return
    if bucket["used"] >= bucket["limit"]:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)


def record_usage_event(db: Session, *, user: User, event_type: str, review_request_id: int | None = None) -> UsageEvent:
    event = UsageEvent(user_id=user.id, event_type=event_type, review_request_id=review_request_id)
    db.add(event)
    db.flush()
    return event
