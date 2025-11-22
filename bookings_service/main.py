
"""
In this module, we create and configure the Flask application for the bookings service.
Here's the list for all the needed API routes: 

"""
from flask import Flask, jsonify
from flask_cors import CORS
def create_app():
    app = Flask(__name__)
    CORS(app)
    # ... define all your routes here, or import from a routes module
    @app.route('/api/v1/bookings', methods=['POST'])
    def create_booking():
        """
        Create a new booking for a room and time-slot.
        """
        return jsonify({"message": "Booking created"}), 201    
    
    @app.route('/api/v1/bookings/myhistory', methods=['GET'])
    def get_booking_history():
        """
        Return only the bookings of the authenticated user (satisfies “user’s booking history”).
        """
        return jsonify({"message": "Booking history"}), 200
    
    @app.route('/api/v1/bookings/user/<user_id>', methods=['GET'])
    def get_user_bookings(u):
        """
        View bookings for a given user id (for admin, facility manager, auditor; user themself can also use it).
        """
        return jsonify({"message": f"Bookings for user {u}"}), 200
    
    @app.route('/api/v1/bookings' ,methods =['GET'])
    def get_all_bookings():
        return jsonify({"message": "All bookings"}), 200
    
    
    @app.route('/api/v1/bookings/<booking_id>', methods=['GET'])
    def get_booking(booking_id):
        """
        get a booking by id
        """
        return jsonify({"message": f"Booking {booking_id} details"}), 200
    
    @app.route('/api/v1/bookings/<booking_id>', methods=['PATCH'])
    def update_booking(booking_id):
        """
        update a booking by id
        """
        return jsonify({"message": f"Booking {booking_id} updated"}), 200
    
    @app.route('/api/v1/bookings/<booking_id>', methods=['POST'])
    def soft_cancel_booking(booking_id):
        """
        Set status = 'cancelled'.
        """
        return jsonify({"message": f"Booking {booking_id} cancelled"}), 200
    
    @app.route('/api/v1/bookings/<booking_id>/hard', methods=['DELETE'])
    def hard_cancel_booking(booking_id):
        """
        Permanently delete a booking by its ID.
        """
        return jsonify({"message": f"Booking {booking_id} permanently deleted"}), 200
    
    @app.route('/api/v1/bookings/availablity', methods=['GET'])
    def check_availablity():
        """
        Check whether a room is free in a given timeslot (satisfies “Checking room availability (based on time and date)” requirement).        
        """
        return jsonify({"message": "Room availability"}), 200

    @app.route('/api/v1/bookings/room/<int:room_id>', methods=['GET'])
    def get_bookings_for_room(room_id):
        """
        View all bookings for a given room id.
        """
        return jsonify({"message": f"Bookings for room {room_id}"}), 200
    
    return app