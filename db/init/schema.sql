-- note about room availability, the bool room availability in the table shcema, is only used by the administrator 
-- to allow booking the room or not. 
-- At the attempt to book, we have to run a query that checks if the availability room is not (not available) 
-- and there are no existing bpokings at the same requested time. 
-- This keeps things simple for PART I requirements, alater we could add part 2 enhancement that 
-- could add a backgroud job to update occupancy state if needed. 

-- Additionally for room equipment , it will be a json file that lists key value pairs of equipment name and count. 
-- This is the users table
create table IF not exists users ( 
    id SERIAL PRIMARY KEY , 
    name TEXT not NULL, 
    username TEXT NOT NULL UNIQUE , 
    email TEXT UNIQUE, 
    password_hash TEXT not NULL, 
    role TEXT NOT NULL, --admin , user, facility_manager, moderator, auditor m service 
    created_at TIMESTAMP DEFAULT NOW()
); 

-- Rooms table for storing room information 
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    capacity INTEGER NOT NULL,
    equipment TEXT,          -- It will be a a json file. 
    location TEXT,
    status TEXT DEFAULT 'available'  -- available, out_of_service ( read notes above)
);


-- Bookings table
create table IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER  NOT NULL REFERENCES users(id) ON DELETE  CASCADE,
    room_id INTEGER NOT NULL  REFERENCES rooms(id) ON DELETE CASCADE,
    start_time TIMESTAMP not NULL,
    end_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'confirmed', -- pending, confirmed, cancelled
    created_at TIMESTAMP DEFAULT NOW()
);

create table if not exists reviews(
    id SERIAL PRIMARY KEY, 
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, 
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT
);


-- now to speed some operation in our database , we have to do indexing 
-- Fast lookup by username (login, get user by username)
CREATE INDEX IF NOT EXISTS idx_users_username
ON users (username);

-- Fast search of bookings by room + time window
CREATE INDEX IF NOT EXISTS idx_bookings_room_time
ON bookings (room_id, start_time, end_time);

-- to get the reviews associated with a specifix room 
CREATE INDEX IF NOT EXISTS idx_reviews_room_id
ON reviews (room_id);

INSERT INTO users (name, username, email, password_hash, role)
VALUES ('Administrator', 'admin', 'admin@yourdomain.com', 'a72490a7704afc2beddb8f4c114290e4cc62544839fbda00d92d3c0c852e6dd5', 'admin')
ON CONFLICT (username) DO NOTHING;

-- The password hash above corresponds to 'adminpassword' using SHA-256
-- This default admin user can be used to perform administrative tasks upon initial setup.

I want to add a few rooms records for testing purposes.
INSERT INTO rooms (name, capacity, equipment, location, status) VALUES
('Conference Room A', 20, '{"Projector": 1, "Whiteboard": 1, "WiFi": "Available"}', 'IOEC - First Floor', 'available'),
('Meeting Room B', 10, '{"TV": 1, "Conference Phone": 1}', 'IOEC - Second Floor', 'available'),
('Auditorium', 100, '{"Sound System": 1, "Stage Lighting": 1}', 'IOEC - Ground Floor', 'available')