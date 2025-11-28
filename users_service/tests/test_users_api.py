from users_service.main import create_app  # adjust if your module is named differently

# Create a single app instance for all tests
app = create_app()
app.config["TESTING"] = True


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_user_and_login(client, *, name, username, email, password="pass123", role="user"):
    """Helper: register a user and log in, return (user_id, token)."""

    payload = {
        "name": name,
        "username": username,
        "email": email,
        "password": password,
        "role": role,
    }

    # Register
    reg_resp = client.post("/api/v1/users/register", json=payload)
    assert reg_resp.status_code in (200, 201)
    reg_data = reg_resp.get_json()
    user_id = reg_data["id"]

    # Login
    login_resp = client.post(
        "/api/v1/users/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.get_json()
    token = login_data["token"]

    return user_id, token


def test_api_register_user(clear_users_table):
    """Test that registering a user succeeds with valid input."""
    client = app.test_client()

    to_send = {
        "name": "Test User",
        "username": "simple_register_user",
        "email": "simple_register@example.com",
        "password": "pass123",
        "role": "user",
    }

    response = client.post("/api/v1/users/register", json=to_send)
    data = response.get_json()

    assert response.status_code in (200, 201)
    assert data["email"] == to_send["email"]
    assert data["username"] == to_send["username"]
    assert "id" in data


def test_api_login_user(clear_users_table):
    """Test that logging in a user succeeds with valid credentials."""
    client = app.test_client()

    username = "simple_login_user"
    email = "simple_login@example.com"
    password = "pass123"

    # First register the user
    client.post(
        "/api/v1/users/register",
        json={
            "name": "Login User",
            "username": username,
            "email": email,
            "password": password,
            "role": "user",
        },
    )

    # Then login
    response = client.post(
        "/api/v1/users/login",
        json={"username": username, "password": password},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert "token" in data
    assert isinstance(data["token"], str)


def test_api_get_user_by_id(clear_users_table):
    """Test that fetching a user by ID succeeds for an authenticated user."""
    client = app.test_client()

    to_send = {
        "name": "Get By Id User",
        "username": "get_by_id_user",
        "email": "getbyid@example.com",
        "password": "pass123",
        "role": "user",
    }

    # Register + login to get token and id
    reg_resp = client.post("/api/v1/users/register", json=to_send)
    created = reg_resp.get_json()
    uid = created["id"]

    login_resp = client.post(
        "/api/v1/users/login",
        json={"username": to_send["username"], "password": to_send["password"]},
    )
    token = login_resp.get_json()["token"]

    # Get user by id (authenticated)
    response = client.get(f"/api/v1/users/{uid}", headers=_auth_headers(token))
    returned_data = response.get_json()

    assert response.status_code == 200
    assert returned_data["id"] == uid
    assert returned_data["email"] == to_send["email"]


def test_api_update_user(clear_users_table):
    """Test that updating a user succeeds with valid input."""
    client = app.test_client()

    # Create user and log in
    user_id, token = _create_user_and_login(
        client,
        name="Update Me",
        username="update_me_user",
        email="update_me@example.com",
        password="pass123",
        role="user",
    )

    updated_info = {
        "name": "Updated Name",
        "username": "update_me_user",  # keep same username
        "email": "updated_email@example.com",
        "password": "newpass123",      # if your API supports password update
        "role": "user",
    }

    # If your endpoint uses PUT instead of PATCH, change .patch to .put
    resp = client.patch(
        f"/api/v1/users/{user_id}",
        json=updated_info,
        headers=_auth_headers(token),
    )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["id"] == user_id
    assert data["email"] == updated_info["email"]
    assert data["name"] == updated_info["name"]


def test_api_delete_user(clear_users_table):
    """Test that deleting a user succeeds."""
    client = app.test_client()

    # Create user and log in
    user_id, token = _create_user_and_login(
        client,
        name="To Delete",
        username="delete_me_user",
        email="delete_me@example.com",
        password="pass123",
        role="user",
    )

    # Delete user
    resp = client.delete(
        f"/api/v1/users/{user_id}",
        headers=_auth_headers(token),
    )
    assert resp.status_code in (200, 204)

    # Try to fetch again (should be 404 or empty)
    check_resp = client.get(
        f"/api/v1/users/{user_id}",
        headers=_auth_headers(token),
    )

    assert check_resp.status_code in (404, 410) or check_resp.get_json() in (None, {})


def test_api_get_all_users_as_admin(clear_users_table):
    """Test that an admin can fetch all users."""
    client = app.test_client()

    # Create an admin user
    admin_id, admin_token = _create_user_and_login(
        client,
        name="Admin User",
        username="simple_admin",
        email="simple_admin@example.com",
        password="adminpass",
        role="admin",
    )

    # Create two normal users (no need to log them in)
    client.post(
        "/api/v1/users/register",
        json={
            "name": "User One",
            "username": "user_one_simple",
            "email": "user_one_simple@example.com",
            "password": "pass123",
            "role": "user",
        },
    )

    client.post(
        "/api/v1/users/register",
        json={
            "name": "User Two",
            "username": "user_two_simple",
            "email": "user_two_simple@example.com",
            "password": "pass123",
            "role": "user",
        },
    )

    # Admin lists all users
    response = client.get(
        "/api/v1/users",
        headers=_auth_headers(admin_token),
    )
    results = response.get_json()

    assert response.status_code == 200
    assert isinstance(results, list)

    emails = [u.get("email") for u in results]
    assert "user_one_simple@example.com" in emails
    assert "user_two_simple@example.com" in emails
