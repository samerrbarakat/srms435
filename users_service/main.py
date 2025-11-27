from unittest import result
from flask import Flask, jsonify, request 
from flask_cors import CORS
from users_service.models import (
    delete_user, get_all_users, get_bookings_by_user_id,
    get_user_by_id, get_user_by_username_or_email,
    insert_user, update_user,
)
from users_service.auth import generate_jwt, hasher, degenerate_jwt
from users_service.rate_limiter import rate_limit

"""
This is the main entry point for the Users Service.
It provides endpoints for user registration, login, and fetching user data.
The routes we will implement are:
- POST /api/v1/users/register : Register a new user.
- POST /api/v1/users/login : Login a user and return a JWT token.
- GET /api/v1/users : Get all users (admin only).   
- GET /api/v1/users/<int:user_id> : Get user by ID (admin or self).
- PUT /api/v1/users/<int:user_id> : Update user by ID (admin or self).
- DELETE /api/v1/users/<int:user_id> : Delete user by ID (admin only).
- GET /api/v1/users/<int:user_id>/bookings : Get bookings for a user (admin or self).

"""
def authenticate_request(request):
    """Extract user info from JWT if present."""
    # You can improve by using flask_jwt_extended or manual verification
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header[len('Bearer '):]
    try:
        payload = degenerate_jwt(token, secret="your_secret_key")
        return payload
    except Exception:
        return None
    
    
def create_app():
    app = Flask(__name__)
    CORS(app)
    # ... define all your routes here, or import from a routes module
    # Return the app instance
 
    @app.route('/api/v1/users/register', methods=['POST'])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def register_user():
        """
        This route takes input user data ( name, username, email, password, role)
        It calls an auth util to hash the password.
        It stores the user data in the database.
        Returns a success message upon successful registration.
        If the username or email already exists, it returns an error message.
        
        Expected JSON body (later we'll validate properly):
        {
            "name": "Full Name",
            "username": "samer",
            "email": "samer@example.com",
            "password": "plain-password",
            "role": "user" | "facility_manager" | ...
        }
        The role cannot be "admin" during registration, the admin user will be an enforced user in the database. 
        """
        body = request.get_json()
        
        
        name = body.get("name")
        username = body.get("username") 
        email = body.get("email")
        password = body.get("password")
        role = body.get("role")
        
        if not name or not username or not email or not password or not role :
            return jsonify({"message": "Missing required fields"}), 400
        # if role == "admin":
        #     return jsonify({"message": "Cannot register as admin"}), 400
        hashed_password =  hasher(password)  # Placeholder for actual hashing logic.
        result = insert_user(name, username, email, hashed_password, role)
        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400
        user_id = result
        return jsonify({
            "id": user_id,
            "name": name,
            "username": username,
            "email": email,
            "role": role
        }), 201

    @app.route('/api/v1/users/login', methods=['POST'])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def login_user():
        """
        This route takes input user data ( username, password)
        It verifies the user credentials.
        Expected JSON body:
        {
            "username": "samer",  # or email
            "password": "plain-password"
        }   
        """
        body = request.get_json()
        username = body.get("username")
        email = body.get("email")
        password = body.get("password")
        if not password or (not username and not email):
            return jsonify({"message": "Missing required fields"}), 400
        
         # Fetch user by username or email
        if username:
           result = get_user_by_username_or_email(username=username, email=None)
        elif email:
            result = get_user_by_username_or_email(username=None, email=email)
        else:
            return jsonify({"message": "Username or email is required"}), 400
        if isinstance(result, tuple):
            valid, e = result
            return jsonify(e), 400
            
        valid = result
        # Here we would verify the credentials against the database.
        if not valid:
            return jsonify({"message": "Invalid username/email or password - nv"}), 401
        
        stored_hash = valid.get("password_hash")
        if not stored_hash or not hasher(password) == stored_hash:
            return jsonify({"message": "Invalid username/email or password"}), 401
        
        # If credentials are valid, generate a JWT token (implemented ) 
        token = generate_jwt({"user_id": valid["id"], "role": valid["role"]}, secret="your_secret_key")
        
        return jsonify({"message": "User logged in successfully", "token": token}), 200

    @app.route('/api/v1/users/adminelevate', methods=['POST'])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def elevate_user_to_role():
        """
        This route allows an admin to elevate a user's role.
        Expected JSON body:
        {
            "user_id": 2,
            "new_role": "facility_manager"
        }
        Only admin users can perform this action.
        """
        claims = authenticate_request(request)
        if not claims or claims.get("role") != "admin":
            return jsonify({"message": "Admin access required"}), 403

        body = request.get_json()
        user_id = body.get("user_id")
        new_role = body.get("new_role")

        if not user_id or not new_role:
            return jsonify({"message": "Missing required fields"}), 400

        result = update_user(
            user_id,
            role=new_role,
        )

        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400

        up = result
        if not up:
            return jsonify({"message": "User not found"}), 404

        up.pop("password_hash", None)
        return jsonify(up), 200




    @app.route('/api/v1/users', methods=['GET']) 
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def get_users():
        """
        This route fetches all users from the database.
        Returns a list of users.
        we need to validate the role for admin only access.
        Expected response:
        [
            {
                "id": 1,
                "name": "Full Name",
                "username": "samer",
                "email": "samer@example.com",
                "role": "user"              
        """
        
        # We need to get the role ffrom the JWT token to validate admin access.
        claims = authenticate_request(request)
        if not claims or claims.get("role") != "admin":
            return jsonify({"message": "Admin access required"}), 403
        
        # now we need to get the users from the database.
        
        result = get_all_users()
        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400
        users = result

        return jsonify(users), 200

    @app.route('/api/v1/users/<int:user_id>', methods=["GET"])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP

    def get_user(user_id):
        """
        Get user info by id.
        Only admin or the user themself can access.
        Never return password hash.
        """
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"message": "Authentication is required for this service!"}), 403

        # authorization
        if not (claims.get("role") == "admin" or str(claims.get("user_id")) == str(user_id)):
            return jsonify({"message": "You are not authorized to view this user info!"}), 403

        # model call (models return value OR (None, err))
        result = get_user_by_id(user_id)
        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400

        info = result
        if not info:
            return jsonify({"message": "User not found"}), 404

        info.pop("password_hash", None)  # remove password hash from response
        return jsonify(info), 200


    @app.route('/api/v1/users/<int:user_id>', methods=["PUT", "PATCH"])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def update_user_info(user_id):
        """
        Admin or user can update own info.
        Non-admin cannot change role.
        Hashing is done inside models.update_user(password=...).
        """
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"message": "Authentication is required for this service!"}), 403

        body = request.get_json() or {}

        name = body.get("name")
        username = body.get("username")
        email = body.get("email")
        password = body.get("password")
        role = body.get("role")

        # authorization
        is_admin = claims.get("role") == "admin"
        is_self = str(claims.get("user_id")) == str(user_id)
        if not (is_admin or is_self):
            return jsonify({"message": "You are not authorized to update this user info!"}), 403

        # non-admins can't change role
        if not is_admin:
            role = None

        result = update_user(
            user_id,
            name=name,
            username=username,
            email=email,
            password=password,
            role=role,
        )

        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400

        up = result
        if not up:
            return jsonify({"message": "User not found"}), 404

        up.pop("password_hash", None)
        return jsonify(up), 200


    @app.route('/api/v1/users/<int:user_id>', methods=["DELETE"])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def delete_user_info(user_id):
        """
        Admin can delete any user.
        A user can delete their own account.
        """
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"message": "Authentication is required for this service!"}), 403

        is_admin = claims.get("role") == "admin"
        is_self = str(claims.get("user_id")) == str(user_id)

        if not (is_admin or is_self):
            return jsonify({"message": "You are not authorized to delete this user!"}), 403

        result = delete_user(user_id)
        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400

        deleted = result
        if not deleted:
            return jsonify({"message": "User not found"}), 404

        return jsonify({"message": "User deleted successfully"}), 200


    @app.route('/api/v1/users/<int:user_id>/bookings', methods=["GET"])
    @rate_limit(calls=3, period=30)  # Limit to 5 requests per 30 seconds per IP
    def get_user_bookings(user_id):
        """
        Admin or user can get their own bookings.
        """
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"message": "Authentication is required for this service!"}), 403

        if not (claims.get("role") == "admin" or str(claims.get("user_id")) == str(user_id)):
            return jsonify({"message": "You are not authorized to view these bookings!"}), 403

        result = get_bookings_by_user_id(user_id)
        if isinstance(result, tuple):
            _, e = result
            return jsonify(e), 400

        bookings = result or []
        return jsonify(bookings), 200

    return app