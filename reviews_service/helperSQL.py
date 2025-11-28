import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/srms",
)

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
    return {
        "id": review.id,
        "user_id": review.user_id,
        "room_id": review.room_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
        "is_flagged": review.is_flagged,
        "flag_reason": review.flag_reason,
    }


def _validate_rating(rating: Optional[int]) -> None:
    if rating is None:
        return
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("rating must be an integer between 1 and 5")


def create_review(user_id: int, room_id: int, rating: int, comment: Optional[str]) -> Dict[str, Any]:
    _validate_rating(rating)
    with SessionLocal() as session:
        review = Review(
            user_id=user_id,
            room_id=room_id,
            rating=rating,
            comment=comment,
            created_at=datetime.utcnow(),
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return _to_dict(review)


def get_review_by_id(review_id: int) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        return _to_dict(review) if review else None


def list_all_reviews() -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        stmt = select(Review).order_by(Review.created_at.desc())
        reviews = session.execute(stmt).scalars().all()
        return [_to_dict(r) for r in reviews]


def list_reviews_by_room(room_id: int) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        stmt = select(Review).where(Review.room_id == room_id).order_by(Review.created_at.desc())
        reviews = session.execute(stmt).scalars().all()
        return [_to_dict(r) for r in reviews]


def update_review(review_id: int, rating: Optional[int] = None, comment: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
        review.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(review)
        return _to_dict(review)


def delete_review(review_id: int) -> bool:
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        if review is None:
            return False
        session.delete(review)
        session.commit()
        return True


def flag_review(review_id: int, flag_reason: Optional[str] = None, is_flagged: bool = True) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        review: Optional[Review] = session.get(Review, review_id)
        if review is None:
            return None
        review.is_flagged = is_flagged
        review.flag_reason = flag_reason
        review.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(review)
        return _to_dict(review)


def remove_review(review_id: int, reason: Optional[str] = "removed by moderator") -> Optional[Dict[str, Any]]:
    # Reuse flagging to represent soft removal
    return flag_review(review_id, flag_reason=reason, is_flagged=True)


def restore_review(review_id: int) -> Optional[Dict[str, Any]]:
    return flag_review(review_id, flag_reason=None, is_flagged=False)
