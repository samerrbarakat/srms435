import os
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from reviews_service.auth import degenerate_jwt
from reviews_service.helperSQL import (
    create_review,
    delete_review,
    flag_review,
    get_review_by_id,
    list_all_reviews,
    list_reviews_by_room,
    remove_review,
    restore_review,
    update_review,
)


JWT_SECRET = os.getenv("JWT_SECRET", "your_secret_key")


def authenticate_request(req):
    """Extract user info from JWT if present."""
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer ") :]
    try:
        return degenerate_jwt(token, secret=JWT_SECRET)
    except Exception:
        return None


def create_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/v1/reviews", methods=["POST"])
    def submit_review():
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401

        payload = request.get_json(silent=True) or {}
        room_id = payload.get("room_id")
        rating = payload.get("rating")
        comment = payload.get("comment")

        if not isinstance(room_id, int):
            return jsonify({"error": "room_id must be an integer"}), 400
        if claims.get("user_id") is None:
            return jsonify({"error": "user_id missing from token"}), 401
        try:
            review = create_review(
                user_id=int(claims.get("user_id")),
                room_id=room_id,
                rating=rating,
                comment=comment,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(review), 201

    @app.route("/api/v1/reviews", methods=["GET"])
    def list_all_reviews_route():
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in {"admin", "moderator"}:
            return jsonify({"error": "admin or moderator role required"}), 403
        reviews = list_all_reviews()
        return jsonify(reviews), 200

    @app.route("/api/v1/rooms/<int:room_id>/reviews", methods=["GET"])
    def get_reviews_for_room(room_id: int):
        reviews = list_reviews_by_room(room_id)
        return jsonify(reviews), 200

    @app.route("/api/v1/reviews/<int:review_id>", methods=["PATCH"])
    def update_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401

        existing = get_review_by_id(review_id)
        if not existing:
            return jsonify({"error": "review not found"}), 404

        is_admin_or_mod = claims.get("role") in {"admin", "moderator"}
        is_owner = str(claims.get("user_id")) == str(existing.get("user_id"))
        if not (is_owner or is_admin_or_mod):
            return jsonify({"error": "not authorized to update this review"}), 403

        payload = request.get_json(silent=True) or {}
        rating = payload.get("rating")
        comment = payload.get("comment")
        if rating is None and comment is None:
            return jsonify({"error": "nothing to update"}), 400

        try:
            updated = update_review(review_id, rating=rating, comment=comment)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        if not updated:
            return jsonify({"error": "review not found"}), 404
        return jsonify(updated), 200

    @app.route("/api/v1/reviews/<int:review_id>", methods=["DELETE"])
    def delete_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401

        existing = get_review_by_id(review_id)
        if not existing:
            return jsonify({"error": "review not found"}), 404

        is_admin_or_mod = claims.get("role") in {"admin", "moderator"}
        is_owner = str(claims.get("user_id")) == str(existing.get("user_id"))
        if not (is_owner or is_admin_or_mod):
            return jsonify({"error": "not authorized to delete this review"}), 403

        deleted = delete_review(review_id)
        if not deleted:
            return jsonify({"error": "review not found"}), 404
        return ("", 204)

    @app.route("/api/v1/reviews/<int:review_id>/flag", methods=["POST"])
    def flag_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"error": "authentication required"}), 401
        if claims.get("role") not in {"admin", "moderator"}:
            return jsonify({"error": "admin or moderator role required"}), 403

        payload = request.get_json(silent=True) or {}
        flag_reason = payload.get("flag_reason")

        flagged = flag_review(review_id, flag_reason=flag_reason, is_flagged=True)
        if not flagged:
            return jsonify({"error": "review not found"}), 404
        return jsonify(flagged), 200

    @app.route("/api/v1/reviews/<int:review_id>/flag/clear", methods=["POST"])
    def clear_flag_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in {"admin", "moderator"}:
            return jsonify({"error": "admin or moderator role required"}), 403

        cleared = flag_review(review_id, flag_reason=None, is_flagged=False)
        if not cleared:
            return jsonify({"error": "review not found"}), 404
        return jsonify(cleared), 200

    @app.route("/api/v1/reviews/<int:review_id>/remove", methods=["POST"])
    def remove_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in {"admin", "moderator"}:
            return jsonify({"error": "admin or moderator role required"}), 403

        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason") or "removed by moderator"

        removed = remove_review(review_id, reason=reason)
        if not removed:
            return jsonify({"error": "review not found"}), 404
        return jsonify(removed), 200

    @app.route("/api/v1/reviews/<int:review_id>/restore", methods=["POST"])
    def restore_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in {"admin", "moderator"}:
            return jsonify({"error": "admin or moderator role required"}), 403

        restored = restore_review(review_id)
        if not restored:
            return jsonify({"error": "review not found"}), 404
        return jsonify(restored), 200

    return app
