from typing import Any, Dict, List, Optional, Tuple

from rooms_service.helperSQL import list_available_rooms


def _score_room(
    room: Dict[str, Any],
    desired_capacity: Optional[int],
    desired_location: Optional[str],
    desired_equipment: Optional[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """Return a tuple usable for sorting recommendations (lower is better).

    Ordering:
    - higher equipment match count (negative for ascending sort)
    - smaller capacity delta (closest to requested capacity)
    - location exact match preferred (0 for match, 1 otherwise)
    """
    # equipment match count
    equip_score = 0
    if desired_equipment:
        room_eq = room.get("equipment") or {}
        for key, val in desired_equipment.items():
            try:
                if key in room_eq and int(room_eq[key]) >= int(val):
                    equip_score += 1
            except (TypeError, ValueError):
                continue

    # capacity delta (smaller is better). If no desired, treat as 0
    cap_delta = 0
    if desired_capacity is not None:
        try:
            cap_delta = abs(int(room.get("capacity", 0)) - desired_capacity)
        except (TypeError, ValueError):
            cap_delta = 0

    # location match flag (0 if substring match, 1 otherwise)
    loc_flag = 0
    if desired_location:
        room_loc = str(room.get("location") or "").lower()
        desired_loc = str(desired_location).lower()
        loc_flag = 0 if desired_loc in room_loc else 1

    # Negative equip_score so higher matches come first when sorted ascending
    return (-equip_score, cap_delta, loc_flag)


def recommend_rooms(
    capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return available rooms ordered by how well they match the preferences."""
    # Fetch available rooms; keep capacity/equipment filtering, but allow fuzzy location match in scoring.
    rooms = list_available_rooms(capacity=capacity, location=None, equipment=equipment)
    scored = [
        (_score_room(room, capacity, location, equipment), room)
        for room in rooms
    ]
    scored.sort(key=lambda item: item[0])
    return [room for _, room in scored]
