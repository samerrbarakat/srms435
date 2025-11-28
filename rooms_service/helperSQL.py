import os
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, Text, and_, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/srms",
)


engine: Engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    equipment = Column(Text)
    location = Column(Text)
    status = Column(Text, default="available")


def _serialize_equipment(equipment: Optional[Dict[str, Any]]) -> Optional[str]:
    if equipment is None:
        return None
    return json.dumps(equipment)


def _deserialize_equipment(equipment: Optional[str]) -> Optional[Dict[str, Any]]:
    if equipment is None:
        return None
    try:
        return json.loads(equipment)
    except json.JSONDecodeError:
        return None


def _room_to_dict(room: Room) -> Dict[str, Any]:
    return {
        "id": room.id,
        "name": room.name,
        "capacity": room.capacity,
        "equipment": _deserialize_equipment(room.equipment),
        "location": room.location,
        "status": room.status,
    }


def _equipment_matches(
    room_equipment: Optional[Dict[str, Any]], required: Optional[Dict[str, Any]]
) -> bool:
    if not required:
        return True
    if not room_equipment:
        return False
    for key, value in required.items():
        if key not in room_equipment:
            return False
        try:
            if int(room_equipment[key]) < int(value):
                return False
        except (TypeError, ValueError):
            return False
    return True


def create_room(
    name: str,
    capacity: int,
    equipment: Optional[Dict[str, Any]],
    location: str,
    status: str = "available",
) -> Dict[str, Any]:
    with SessionLocal() as session:
        room = Room(
            name=name,
            capacity=capacity,
            equipment=_serialize_equipment(equipment),
            location=location,
            status=status,
        )
        session.add(room)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Room with this name already exists") from exc
        session.refresh(room)
        return _room_to_dict(room)


def update_room(
    room_id: int,
    *,
    name: Optional[str] = None,
    capacity: Optional[int] = None,
    equipment: Optional[Dict[str, Any]] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        room: Optional[Room] = session.get(Room, room_id)
        if room is None:
            return None
        if name is not None:
            room.name = name
        if capacity is not None:
            room.capacity = capacity
        if equipment is not None:
            room.equipment = _serialize_equipment(equipment)
        if location is not None:
            room.location = location
        if status is not None:
            room.status = status
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Room with this name already exists") from exc
        session.refresh(room)
        return _room_to_dict(room)


def delete_room(room_id: int) -> bool:
    with SessionLocal() as session:
        room: Optional[Room] = session.get(Room, room_id)
        if room is None:
            return False
        session.delete(room)
        session.commit()
        return True


def list_all_rooms() -> List[Dict[str, Any]]:
    """Return all rooms with full details."""
    with SessionLocal() as session:
        rooms = session.execute(select(Room)).scalars().all()
        return [_room_to_dict(room) for room in rooms]


def list_available_rooms(
    capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        conditions = [Room.status == "available"]
        if capacity is not None:
            conditions.append(Room.capacity >= capacity)
        if location is not None:
            conditions.append(Room.location == location)
        stmt = select(Room)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rooms = session.execute(stmt).scalars().all()
        result = []
        for room in rooms:
            room_dict = _room_to_dict(room)
            if _equipment_matches(room_dict["equipment"], equipment):
                result.append(room_dict)
        return result


def get_room_status(room_id: int) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        room: Optional[Room] = session.get(Room, room_id)
        if room is None:
            return None
        base_status = room.status or "available"
        status_value = "available" if base_status == "available" else "booked"
        return {"id": room.id, "status": status_value}
