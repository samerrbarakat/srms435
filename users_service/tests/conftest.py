# users_service/tests/conftest.py
import os
import psycopg2
import pytest
import sys

# add users_service/ to import path so "from main import create_app" works
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from main import create_app
from users_service.main import create_app


# 1) One source of truth for tests: your working DB URL on localhost:5433
#    (Change srms_db_test -> srms_db if you are not using a separate test DB.)
TEST_DB_URL = "postgresql://appuser:appsecret@localhost:5433/srms_db_test"

# 2) Tell the app/models to use THIS DB
os.environ["DATABASE_URL"] = TEST_DB_URL

# 3) For truncate() we use the same URL
DB_URL = TEST_DB_URL

# 4) Now import the app (after DATABASE_URL is set)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from users_service.main import create_app  # noqa: E402

@pytest.fixture(scope="session")
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture(scope="function")
def client(app):
    """A test client for the app."""
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def clear_users_table():
    """
    Use this fixture ONLY in integration tests.
    It will wipe the REAL db users table.
    """
    def truncate():
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
        conn.commit()
        cur.close()
        conn.close()

    truncate()
    yield
    truncate()
