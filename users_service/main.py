from flask import Flask, jsonify, request 
from flask_cors import CORS
from users_service.models import delete_user, get_all_users, get_bookings_by_user_id, get_user_by_id, get_user_by_username_or_email, insert_user, update_user 
from auth import generate_jwt , hasher
import jwt
app = Flask(__name__)
CORS(app)

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
        payload = jwt.decode(token, "your_secret_key", algorithms=["HS256"])
        return payload
    except Exception:
        return None
    
    
@app.route('/api/v1/users/register', methods=['POST'])
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
    
    if not name or not username or not email or not password or not role or role =="admin":
        return jsonify({"message": "Missing required fields"}), 400
    
    hashed_password =  hasher(password)  # Placeholder for actual hashing logic.
    i ,e = insert_user(name, username, email, hashed_password, role)
    
    if e:
        return jsonify(e), 400  # Database error
    
    # next task is to: store the user data in the database.
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/v1/users/login', methods=['POST'])
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
    
    if username : 
        valid ,e = get_user_by_username_or_email(username = username, email = None)
    elif email:
        valid ,e = get_user_by_username_or_email(username = None, email = email)
    else:
        return jsonify({"message": "Username or email is required"}), 400
    
    if not password:
        return jsonify({"message": "Password is required"}), 400
    
    # Here we would verify the credentials against the database.

    if e:
        return jsonify(e), 400
    if not valid:
        return jsonify({"message": "Invalid username/email or password"}), 401
    
    stored_hash = valid.get("password")
    if not stored_hash or not hasher(password) == stored_hash:
        return jsonify({"message": "Invalid username/email or password"}), 401
    
    # If credentials are valid, generate a JWT token (implemented ) 
    token = generate_jwt({"user_id": valid["id"], "role": valid["role"]}, secret="your_secret_key")
    
    return jsonify({"message": "User logged in successfully", "token": token}), 200

@app.route('/api/v1/users', methods=['GET']) #
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
    
    users ,e = get_all_users()
    if e:
        return jsonify(e), 400  # Database error
    
    return jsonify(users), 200



@app.route('/api/v1/users/<int:user_id>',methods = ["GET"])
def get_user(user_id):
    """
    This function get the user information given the id as a URL parameter, we will also enforce that only the user or same-selfuser can get them
    Additionally, we want sent the password with us. 
    1. Check claims
    2. check if the self is asking for self or not . 
    3. call the db util . 
    4. then return the info. 
    """
    claims = authenticate_request(request)
    if not claims :
        return jsonify({"message": "Athentication is required for this service! "}), 403
    
    if claims.get("role") =="admin":
        info , e = get_user_by_id(user_id)
    elif str(claims.get("user_id")) == str(user_id):
        info , e = get_user_by_id(user_id)
    else:
        return jsonify({"message": "You are not authorized to view this user info!"}), 403  
    if e:
        return jsonify(e), 400
    if not info:
        return jsonify({"message": "User not found"}), 404
    info.pop("password", None)  # remove password from response
    return jsonify(info), 200


@app.route('/api/v1/users/<int:user_id>',methods =["PUT"])
def update_user_info(user_id):
    """
    this func lets teh admin or a user update their own info like email or password or name. 
    """
    claims = authenticate_request(request)
    if not claims :
        return jsonify({"message": "Athentication is required for this service! "}), 403
    body = request.get_json()
    name = body.get("name") or None
    email = body.get("email") or None
    password = body.get("password") or None
    role = body.get("role") or None    
    
    if claims.get("role") =="admin" or str(claims.get("user_id")) == str(user_id):
        # we need to prepare the update call here.
        up , e = update_user(user_id, name=name, email=email, password=password, role=role)
        # we need to handle possible errors from the db util
        if e:
            return jsonify(e), 400
        if not up:
            return jsonify({"message": "User not found"}), 404
        # and then call the db util.
        up.pop("password", None)  # remove password from response
        return jsonify(up), 200
    else:
        return jsonify({"message": "You are not authorized to update this user info!"}), 403
    
@app.route('/api/v1/users/<int:user_id>',methods =["DELETE"])
def delete_user_info(user_id):          
    """
    this func lets teh admin delete a user by id. 
    """
    claims = authenticate_request(request)
    if not claims :
        return jsonify({"message": "Athentication is required for this service! "}), 403
    
    if claims.get("role") =="admin":
        de , e = delete_user(user_id)
        if e:
            return jsonify(e), 400
        if not de:
            return jsonify({"message": "User not found"}), 404
        return jsonify({"message": "User deleted successfully"}), 200
    else:
        return jsonify({"message": "You are not authorized to delete this user!"}), 403
    
@app.route('/api/v1/users/<int:user_id>/bookings',methods =["GET"])
def get_user_bookings(user_id):
    """
    this func lets teh admin or a user get their bookings by user id. 
    """
    claims = authenticate_request(request)
    if not claims :
        return jsonify({"message": "Athentication is required for this service! "}), 403
    
    if claims.get("role") =="admin" or str(claims.get("user_id")) == str(user_id):
        bookings , e = get_bookings_by_user_id(user_id)
        if e:
            return jsonify(e), 400
        return jsonify(bookings), 200
    else:
        return jsonify({"message": "You are not authorized to view these bookings!"}), 403
    
    
from auth import hasher
print(hasher("helloworld123"))