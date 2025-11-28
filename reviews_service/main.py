import os
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from reviews_service.auth import degenerate_jwt
from reviews_service.errors import ApiError, register_error_handlers
from reviews_service.helperSQL import (
    create_review,
    delete_review,
    flag_review,
    get_review_by_id,
    list_all_reviews,
    list_reviews_by_user,
    list_reviews_by_room,
    remove_review,
    restore_review,
    update_review,
)


JWT_SECRET = "your_secret_key"
ROLE_MODERATION = {"admin", "moderator"}
ROLE_READ_ALL = {"admin", "moderator", "auditor"}


def authenticate_request(req):
    """Extract user info from JWT if present."""
    auth_header = req.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):]
    try:
        payload = degenerate_jwt(token, secret=JWT_SECRET)
        return payload
    except Exception:
        return None


def create_app():
    app = Flask(__name__)
    CORS(app)
    register_error_handlers(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.route("/api/v1/reviews", methods=["POST"])
    def submit_review():
        claims = authenticate_request(request)
        if not claims:
            raise ApiError(401, "authentication required", "unauthorized")
        if claims.get("role")!= "user":
            raise ApiError(403, "user role required to submit reviews", "forbidden")

        payload = request.get_json(silent=True) or {}
        room_id = payload.get("room_id")
        rating = payload.get("rating")
        comment = payload.get("comment")

        if not isinstance(room_id, int):
            raise ApiError(400, "room_id must be an integer", "validation_error")
        if claims.get("user_id") is None:
            raise ApiError(401, "user_id missing from token", "unauthorized")
        try:
            review = create_review(
                user_id=int(claims.get("user_id")),
                room_id=room_id,
                rating=rating,
                comment=comment,
            )
        except ValueError as exc:
            raise ApiError(400, str(exc), "validation_error")

        return jsonify(review), 201

    @app.route("/api/v1/reviews", methods=["GET"])
    def list_all_reviews_route():
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROLE_READ_ALL:
            raise ApiError(403, "admin, moderator, or auditor role required", "forbidden")
        reviews = list_all_reviews()
        return jsonify(reviews), 200

    @app.route("/api/v1/rooms/<int:room_id>/reviews", methods=["GET"])
    def get_reviews_for_room(room_id: int):
        reviews = list_reviews_by_room(room_id)
        return jsonify(reviews), 200

    @app.route("/api/v1/reviews/mine", methods=["GET"])
    def get_my_reviews():
        claims = authenticate_request(request)
        if not claims:
            raise ApiError(401, "authentication required", "unauthorized")
        user_id = claims.get("user_id")
        if user_id is None:
            raise ApiError(401, "user_id missing from token", "unauthorized")
        reviews = list_reviews_by_user(int(user_id))
        return jsonify(reviews), 200

    @app.route("/api/v1/reviews/<int:review_id>", methods=["PATCH"])
    def update_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            raise ApiError(401, "authentication required", "unauthorized")

        existing = get_review_by_id(review_id)
        if not existing:
            raise ApiError(404, "review not found", "not_found")

        is_owner = str(claims.get("user_id")) == str(existing.get("user_id"))
        if not is_owner:
            raise ApiError(403, "only the review owner can update this review", "forbidden")

        payload = request.get_json(silent=True) or {}
        rating = payload.get("rating")
        comment = payload.get("comment")
        if rating is None and comment is None:
            raise ApiError(400, "nothing to update", "validation_error")

        try:
            updated = update_review(review_id, rating=rating, comment=comment)
        except ValueError as exc:
            raise ApiError(400, str(exc), "validation_error")

        if not updated:
            raise ApiError(404, "review not found", "not_found")
        return jsonify(updated), 200

    @app.route("/api/v1/reviews/<int:review_id>", methods=["DELETE"])
    def delete_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            raise ApiError(401, "authentication required", "unauthorized")

        existing = get_review_by_id(review_id)
        if not existing:
            raise ApiError(404, "review not found", "not_found")

        is_admin_or_mod = claims.get("role") in {"admin", "moderator"}
        is_owner = str(claims.get("user_id")) == str(existing.get("user_id"))
        if not (is_owner or is_admin_or_mod):
            raise ApiError(403, "not authorized to delete this review", "forbidden")

        deleted = delete_review(review_id)
        if not deleted:
            raise ApiError(404, "review not found", "not_found")
        return ("", 204)

    @app.route("/api/v1/reviews/<int:review_id>/flag", methods=["POST"])
    def flag_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims:
            raise ApiError(401, "authentication required", "unauthorized")
        if claims.get("role") not in ROLE_MODERATION:
            raise ApiError(403, "admin or moderator role required", "forbidden")

        payload = request.get_json(silent=True) or {}
        flag_reason = payload.get("flag_reason")

        flagged = flag_review(review_id, flag_reason=flag_reason, is_flagged=True)
        if not flagged:
            raise ApiError(404, "review not found", "not_found")
        return jsonify(flagged), 200

    @app.route("/api/v1/reviews/<int:review_id>/flag/clear", methods=["POST"])
    def clear_flag_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROLE_MODERATION:
            raise ApiError(403, "admin or moderator role required", "forbidden")

        cleared = flag_review(review_id, flag_reason=None, is_flagged=False)
        if not cleared:
            raise ApiError(404, "review not found", "not_found")
        return jsonify(cleared), 200

    @app.route("/api/v1/reviews/<int:review_id>/remove", methods=["POST"])
    def remove_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROLE_MODERATION:
            raise ApiError(403, "admin or moderator role required", "forbidden")

        payload = request.get_json(silent=True) or {}
        reason = payload.get("reason") or "removed by moderator"

        removed = remove_review(review_id, reason=reason)
        if not removed:
            raise ApiError(404, "review not found", "not_found")
        return jsonify(removed), 200

    @app.route("/api/v1/reviews/<int:review_id>/restore", methods=["POST"])
    def restore_review_route(review_id: int):
        claims = authenticate_request(request)
        if not claims or claims.get("role") not in ROLE_MODERATION:
            raise ApiError(403, "admin or moderator role required", "forbidden")

        restored = restore_review(review_id)
        if not restored:
            raise ApiError(404, "review not found", "not_found")
        return jsonify(restored), 200

    return app
