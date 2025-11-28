from typing import Any, Dict, Optional
from flask import jsonify


class ApiError(Exception):
    """Custom API error with HTTP status and typed message."""

    def __init__(self, status_code: int = 400, message: str = "Bad Request", error_type: str = "error", payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.payload = payload or {}


def register_error_handlers(app):
    """Register global JSON error handlers for the Flask app."""

    def _response(status_code: int, message: str, error_type: str = "error", extra: Optional[Dict[str, Any]] = None):
        body: Dict[str, Any] = {"error": {"type": error_type, "message": message}}
        if extra:
            body["error"].update(extra)
        return jsonify(body), status_code

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return _response(err.status_code, err.message, err.error_type, err.payload)

    @app.errorhandler(400)
    def handle_400(err):
        return _response(400, "Bad Request", "bad_request")

    @app.errorhandler(401)
    def handle_401(err):
        return _response(401, "Unauthorized", "unauthorized")

    @app.errorhandler(403)
    def handle_403(err):
        return _response(403, "Forbidden", "forbidden")

    @app.errorhandler(404)
    def handle_404(err):
        return _response(404, "Not Found", "not_found")

    @app.errorhandler(405)
    def handle_405(err):
        return _response(405, "Method Not Allowed", "method_not_allowed")

    @app.errorhandler(500)
    def handle_500(err):
        return _response(500, "Internal Server Error", "internal_error")

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # Fallback for uncaught exceptions
        return _response(500, "Internal Server Error", "internal_error")
