from typing import Any, Dict, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS
from rooms_service.auth import degenerate_jwt
from rooms_service.helperSQL import create_room, update_room, delete_room, list_available_rooms, get_room_status, list_all_rooms

ROOM_MANAGERS = {"admin", "facility_manager"}

def authenticate_request(request):
    """Extract user info from JWT if present."""
    # You can improve by using flask_jwt_extended or manual verification
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):]
    try:
        payload = degenerate_jwt(token)
        return payload
    except Exception:
        return None
    
def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "ok"}), 200


    def _parse_int(value: Optional[str]) -> Optional[int]:
        """Parse an integer from a string, returning None if invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None


    def _parse_equipment_param(value: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse equipment query parameter into a dictionary."""
        if value is None:
            return None
        items = [item.strip() for item in value.split(",") if item.strip()]
        if not items:
            return None
        return {item: 1 for item in items}


    @app.route("/api/v1/rooms", methods=["POST"])
    def create_room_route():
        """Create a new room."""
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROOM_MANAGERS:
            return jsonify({"error": "admin access required"}), 403
        payload = request.get_json(silent=True) or {}
        name = payload.get("name")
        capacity = payload.get("capacity")
        location = payload.get("location")
        equipment = payload.get("equipment")
        status = payload.get("status", "available")

        if not isinstance(name, str) or not isinstance(location, str):
            return jsonify({"error": "name and location are required strings"}), 400
        if not isinstance(capacity, int) or capacity <= 0:
            return jsonify({"error": "capacity must be a positive integer"}), 400
        if equipment is not None and not isinstance(equipment, dict):
            return jsonify({"error": "equipment must be an object"}), 400

        try:
            room = create_room(
                name=name,
                capacity=capacity,
                equipment=equipment,
                location=location,
                status=status,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(room), 201

    @app.route("/api/v1/rooms", methods=["GET"])
    def list_rooms_route():
        """List all rooms."""
        rooms = list_all_rooms()
        return jsonify(rooms), 200

    @app.route("/api/v1/rooms/<int:room_id>", methods=["PATCH"])
    def update_room_route(room_id: int):
        """Update a room's details."""
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROOM_MANAGERS:
            return jsonify({"error": "admin access required"}), 403

        payload = request.get_json(silent=True) or {}
        updates: Dict[str, Any] = {}

        if "name" in payload:
            if not isinstance(payload["name"], str):
                return jsonify({"error": "name must be a string"}), 400
            updates["name"] = payload["name"]
        if "capacity" in payload:
            if not isinstance(payload["capacity"], int) or payload["capacity"] <= 0:
                return jsonify({"error": "capacity must be a positive integer"}), 400
            updates["capacity"] = payload["capacity"]
        if "equipment" in payload:
            if payload["equipment"] is not None and not isinstance(payload["equipment"], dict):
                return jsonify({"error": "equipment must be an object"}), 400
            updates["equipment"] = payload["equipment"]
        if "location" in payload:
            if not isinstance(payload["location"], str):
                return jsonify({"error": "location must be a string"}), 400
            updates["location"] = payload["location"]
        if "status" in payload:
            if not isinstance(payload["status"], str):
                return jsonify({"error": "status must be a string"}), 400
            updates["status"] = payload["status"]

        if not updates:
            room = update_room(room_id)
            if room is None:
                return jsonify({"error": "room not found"}), 404
            return jsonify(room)

        try:
            room = update_room(room_id, **updates)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        if room is None:
            return jsonify({"error": "room not found"}), 404
        return jsonify(room)


    @app.route("/api/v1/rooms/<int:room_id>", methods=["DELETE"])
    def delete_room_route(room_id: int):
        """Delete a room."""
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROOM_MANAGERS:
            return jsonify({"error": "admin access required"}), 403

        deleted = delete_room(room_id)
        if not deleted:
            return jsonify({"error": "room not found"}), 404
        return ("", 204)


    @app.route("/api/v1/rooms/available", methods=["GET"])
    def list_available_rooms_route():
        """List available rooms with optional filters."""
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401
        capacity_param = request.args.get("capacity")
        location = request.args.get("location")
        equipment_param = request.args.get("equipment")

        capacity = _parse_int(capacity_param)
        equipment = _parse_equipment_param(equipment_param)

        rooms = list_available_rooms(capacity=capacity, location=location, equipment=equipment)
        return jsonify(rooms)


    @app.route("/api/v1/rooms/<int:room_id>/status", methods=["GET"])
    def get_room_status_route(room_id: int):
        """Get the current status of a room."""
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401
        status_info = get_room_status(room_id)
        if status_info is None:
            return jsonify({"error": "room not found"}), 404
        return jsonify(status_info)

    return app
