import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/srms",
)

TZ = ZoneInfo("Asia/Beirut")

engine: Engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    room_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(Text)


def _to_dict(review: Review) -> Dict[str, Any]:
    """Convert a Review ORM object to a dictionary suitable for JSON serialization."""
    def _fmt(dt: Optional[datetime]) -> Optional[str]:
        """Format datetime to string in Beirut timezone."""
        if not dt:
            return None
        # Treat naive datetimes as UTC and convert to Beirut time for display
        aware = dt if dt.tzinfo else dt.replace(tzinfo=ZoneInfo("UTC"))
        local = aware.astimezone(TZ)
        # Format as "YYYY-MM-DD T HH:MM" with no offset or seconds
        return local.replace(microsecond=0).strftime("%Y-%m-%d T %H:%M")

    base: Dict[str, Any] = {
        "id": review.id,
        "user_id": review.user_id,
        "room_id": review.room_id,
        "created_at": _fmt(review.created_at),
    }
    if review.updated_at:
        base["updated_at"] = _fmt(review.updated_at)

    if review.is_flagged:
        # When removed/flagged, only expose minimal info
        return {
            "id": review.id,
            "removed": True,
            "message": review.flag_reason or "removed by moderator",
        }

    base["rating"] = review.rating
    base["comment"] = review.comment
    return base


def _validate_rating(rating: Optional[int]) -> None:
    """Validate that the rating is an integer between 1 and 5."""
    if rating is None:
        return
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("rating must be an integer between 1 and 5")


def create_review(user_id: int, room_id: int, rating: int, comment: Optional[str]) -> Dict[str, Any]:
    """Create a new review and return it as a dictionary."""
    _validate_rating(rating)
    with SessionLocal() as session:
        review = Review(
            user_id=user_id,
            room_id=room_id,
            rating=rating,
            comment=comment,
            created_at=datetime.now(TZ),
        )
        session.add(review)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            constraint = getattr(getattr(exc, "orig", None), "diag", None)
            constraint_name = getattr(constraint, "constraint_name", "") if constraint else ""
            if "room_id" in constraint_name:
                raise ValueError("room_id does not exist") from exc
            if "user_id" in constraint_name:
                raise ValueError("user_id does not exist") from exc
            raise ValueError("room_id or user_id does not exist") from exc
        session.refresh(review)
        return _to_dict(review)


def get_review_by_id(review_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a review by its ID and return it as a dictionary, or None if not found."""
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        return _to_dict(review) if review else None


def list_all_reviews() -> List[Dict[str, Any]]:
    """List all reviews in the database."""
    with SessionLocal() as session:
        stmt = select(Review).order_by(Review.created_at.desc())
        reviews = session.execute(stmt).scalars().all()
        return [_to_dict(r) for r in reviews]


def list_reviews_by_room(room_id: int) -> List[Dict[str, Any]]:
    """List reviews for a specific room."""
    with SessionLocal() as session:
        stmt = select(Review).where(Review.room_id == room_id).order_by(Review.created_at.desc())
        reviews = session.execute(stmt).scalars().all()
        return [_to_dict(r) for r in reviews]


def list_reviews_by_user(user_id: int) -> List[Dict[str, Any]]:
    """List reviews for a specific user."""
    with SessionLocal() as session:
        stmt = select(Review).where(Review.user_id == user_id).order_by(Review.created_at.desc())
        reviews = session.execute(stmt).scalars().all()
        return [_to_dict(r) for r in reviews]


def update_review(review_id: int, rating: Optional[int] = None, comment: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update a review's rating and/or comment."""
    _validate_rating(rating)
    if rating is None and comment is None:
        return None
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        if review is None:
            return None
        if rating is not None:
            review.rating = rating
        if comment is not None:
            review.comment = comment
        review.updated_at = datetime.now(TZ)
        session.commit()
        session.refresh(review)
        return _to_dict(review)


def delete_review(review_id: int) -> bool:
    """Delete a review by its ID. Returns True if deleted, False if not found."""
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        if review is None:
            return False
        session.delete(review)
        session.commit()
        return True


def flag_review(review_id: int, flag_reason: Optional[str] = None, is_flagged: bool = True) -> Optional[Dict[str, Any]]:
    """Flag or unflag a review as inappropriate."""
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        if review is None:
            return None
        review.is_flagged = is_flagged
        review.flag_reason = flag_reason
        review.updated_at = datetime.now(TZ)
        session.commit()
        session.refresh(review)
        return _to_dict(review)


def remove_review(review_id: int, reason: Optional[str] = "removed by moderator") -> Optional[Dict[str, Any]]:
    """Soft remove a review by flagging it with a removal reason."""
    # Reuse flagging to represent soft removal
    return flag_review(review_id, flag_reason=reason, is_flagged=True)


def restore_review(review_id: int) -> Optional[Dict[str, Any]]:
    """Restore a previously removed review by unflagging it."""
    return flag_review(review_id, flag_reason=None, is_flagged=False)
