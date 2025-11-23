import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


"""
Database connection and context managers for bookings service.
Imports database operation functions:
    db_check_room_exists,
    db_check_room_availability,
    db_create_booking,
    db_get_all_bookings,
    db_get_booking_history,
    db_get_bookings_by_user,
    db_get_booking_by_id, 
    db_update_booking, 
    db_soft_cancel_booking, 
    db_hard_delete_booking, 
    db_get_bookings_by_room,
    """
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5433/bookings_db")

@contextmanager 
def get_db_connection():
    """
    Context manager for database connection.
    Yields a psycopg2 connection object."""
    ocnn = psycopg2.connect(DATABASE_URL)
    try:
        yield ocnn
    finally:
        ocnn.close()
        
def db_check_room_exists(room_id):
    """
    Yields True if the room exists, False otherwise.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT 1 FROM rooms WHERE id = %s;", (room_id,))
            result = cursor.fetchone()
            yield result is not None

def db_check_room_availability(room_id, start_time, end_time):
    """
    Yields True if the room is available for the given time range, False otherwise.
    """
    if room_id is None or not start_time or not end_time:
        return False

    query = """
        SELECT 1
        FROM bookings
        WHERE room_id = %s
          AND status <> 'cancelled'
          AND NOT (end_time <= %s OR start_time >= %s)
        LIMIT 1;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (room_id, start_time, end_time))
            conflict = cur.fetchone()
            return conflict is None  
        
def db_create_booking(user_id, room_id, start_time, end_time):
    """
    Insert a new booking row and return the created booking as a dict,
    or None if something goes wrong.
    """
    insert_query = """
        INSERT INTO bookings (user_id, room_id, start_time, end_time)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, room_id, start_time, end_time, status, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(insert_query, (user_id, room_id, start_time, end_time))
            booking = cur.fetchone()
            conn.commit()
            return dict(booking) if booking else None
        
def db_get_all_bookings():
    """
    This functions return the list of all bookings ever! 
    """
    
    query = """
        SELECT id, user_id, room_id, start_time, end_time, status, created_at
        FROM bookings
        ORDER BY created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            bookings = cur.fetchall()
            return [dict(booking) for booking in bookings]
        
def db_get_booking_history(user_id: int):
    """
    Return all bookings for a specific user, ordered by start_time DESC.
    """
    query = """
        SELECT id, user_id, room_id, start_time, end_time, status, created_at
        FROM bookings
        WHERE user_id = %s
        ORDER BY start_time DESC;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
def db_get_booking_history(user_id: int):
    """
    Return all bookings for a specific user, ordered by start_time DESC.
    """
    query = """
        SELECT id, user_id, room_id, start_time, end_time, status, created_at
        FROM bookings
        WHERE user_id = %s
        ORDER BY start_time DESC;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        
def db_get_bookings_by_user(user_id):
    """
    This function returns all the booking of a user:
    """
    query = """
    SELECT * FROM bookings 
    WHERE user_id = %s AND status != 'cancelled'
    ORDER BY start_time DESC
    """
    
    with get_db_connection() as conn: 
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_id,))
            bookings = cur.fetchall()
            return [dict(booking) for booking in bookings]
def db_get_booking_by_id(booking_id):
    """
    This function returns a booking by its ID.
    """
    query = """
    SELECT * FROM bookings 
    WHERE id = %s
    """
    
    with get_db_connection() as conn: 
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (booking_id,))
            booking = cur.fetchone()
            return dict(booking) if booking else None
        
def db_update_booking(booking_id, room_id, start_time, end_time):
    """
    This function updates an existing booking.
    """
    update_query = """
        UPDATE bookings
        SET room_id = %s, start_time = %s, end_time = %s
        WHERE id = %s
        RETURNING id, user_id, room_id, start_time, end_time, status, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(update_query, (room_id, start_time, end_time, booking_id))
            updated_booking = cur.fetchone()
            conn.commit()
            return dict(updated_booking) if updated_booking else None

def db_soft_cancel_booking(booking_id):
    """
    This function soft cancels a booking by updating its status to 'cancelled'.
    """
    cancel_query = """
        UPDATE bookings
        SET status = 'cancelled'
        WHERE id = %s
        RETURNING id, user_id, room_id, start_time, end_time, status, created_at;
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(cancel_query, (booking_id,))
            cancelled_booking = cur.fetchone()
            conn.commit()
            return dict(cancelled_booking) if cancelled_booking else None

def db_hard_delete_booking(booking_id):
    """
    This function hard deletes a booking from the database.
    """
    delete_query = """
        DELETE FROM bookings
        WHERE id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(delete_query, (booking_id,))
            conn.commit()
            
def db_get_bookings_by_room(room_id):
    """
    This function returns all bookings for a specific room.
    """
    query = """
    SELECT * FROM bookings 
    WHERE room_id = %s AND status != 'cancelled'
    ORDER BY start_time DESC
    """
    
    with get_db_connection() as conn: 
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (room_id,))
            bookings = cur.fetchall()
            return [dict(booking) for booking in bookings]
        
