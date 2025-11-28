"""
In this we provide helpers to wrte to the database. 
We assume that DATABASE_URL is set in the environment variables for database connection of the docker compose
First we provide a way to get a connection to the database using a context manager.
Then we create all the functions that manipulate that database and that we need. 
"""
# admin password is srms435 
import os 
import psycopg2 , psycopg2.extras
from contextlib import contextmanager
from users_service.auth import hasher


# DATABASE_URL = "postgresql://appuser:appsecret@localhost:5433/srms_db_test"  # or srms_db
DATABASE_URL = os.getenv("DATABASE_URL")
@contextmanager
def get_db_connection():
    """
    Context manager to get a database connection.
    Ensures that the connection is properly closed after use.
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    except psycopg2.Error as e:
        print(f"There's a problem connecting to the database: {e}")
        raise e
    finally:
        conn.close()
        
def get_user_by_username_or_email(username, email):
    """
    Fetch a user from the database by username or email.
    Returns None if no user is found.
    """
    query = "SELECT * FROM users WHERE username = %s OR email = %s"
    try : 
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, (username, email))
                user = cursor.fetchone()
                return dict(user) if user else None
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})
    
def insert_user(name, username, email, password_hash, role):
    """
    Insert a new user into the database.
    Returns the inserted user's ID.
    """
    query = """
    INSERT INTO users (name, username, email, password_hash, role)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (name, username, email, password_hash, role))
                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})

def get_all_users():
    """
    Fetch all users from the database.
    Returns a list of user dictionaries.
    """ 
    query = "SELECT id, name, username, email, role FROM users"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
                return [dict(user) for user in users]
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})
        
def get_user_by_id(user_id):
    """
    Fetch a user from the database by user ID.
    Returns None if no user is found.
    """
    query = "SELECT id, name, username, email, role FROM users WHERE id = %s"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})
    
def delete_user(user_id):
    """
    Delete a user from the database by user ID.
    Returns True if deletion was successful, False otherwise.
    """
    query = "DELETE FROM users WHERE id = %s"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        return (False, {"msg": str(e), "type": "database_error"})
    
def get_bookings_by_user_id(user_id):
    """
    Fetch all bookings for a given user ID.
    Returns a list of booking dictionaries.
    """
    query = "SELECT * FROM bookings WHERE user_id = %s"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, (user_id,))
                bookings = cursor.fetchall()
                return [dict(booking) for booking in bookings]
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})
    
    
def update_user(user_id, name=None, username=None, email=None, password=None, role=None):
    """
    This function updates the user info given all the new info , makes sure no username or email conflicts happen and then updates the info. 
    Returns True if update was successful, False otherwise.
    """
    
    if not name and not username and not email and not password and not role:
        return (False, {"msg": "please provide meaninful udates", "type": "validation_error"})

    toupdate =[]
    respective_vals =[]
    if name:
        toupdate.append("name=%s")
        respective_vals.append(name)        
    if username:
        toupdate.append("username=%s")
        respective_vals.append(username)        
    if email:
        toupdate.append("email=%s")
        respective_vals.append(email)
    if password:
        toupdate.append("password_hash=%s")
        respective_vals.append(hasher(password))
    if role:
        if role =="admin":
            return (False, {"msg": "Cannot elevate role to admin", "type": "validation_error"})
        toupdate.append("role=%s")
        respective_vals.append(role)
        
    respective_vals.append(user_id)
    query = f"UPDATE users SET {', '.join(toupdate)} WHERE id = %s RETURNING id, name, username, email, role;"
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, tuple(respective_vals))
                updated_user = cursor.fetchone()
                conn.commit()
                return dict(updated_user) if updated_user else None
    except psycopg2.errors.UniqueViolation as e:
        # UniqueViolation is raised on duplicate username or email
        # You can inspect e.diag.message_detail or code for more info
        msg = str(e)
        if 'username' in msg:
            return (None, {"msg": "Username already exists.", "type": "conflict"})
        elif 'email' in msg:
            return (None, {"msg": "Email already exists.", "type": "conflict"})
        else:
            return (None, {"msg": "Unique constraint violated.", "type": "conflict"})       
        
    except Exception as e:
        return (None, {"msg": str(e), "type": "database_error"})    