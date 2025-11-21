# users_service/tests/conftest.py
import os
import psycopg2
import pytest
import sys

# add users_service/ to import path so "from main import create_app" works
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# from main import create_app
from users_service.main import create_app

# HARD-CODE REAL DB URL (NO TEST DB)
DB_URL = "postgresql://appuser:appsecret@localhost:5432/srms_db"


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture(scope="function")
def client(app):
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
