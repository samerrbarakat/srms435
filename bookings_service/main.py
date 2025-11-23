
"""
In this module, we create and configure the Flask application for the bookings service.
Here's the list for all the needed API routes: 

"""
from flask import Flask, jsonify, request
from flask_cors import CORS

from datetime import datetime as now
from bookings_service.auth import degenerate_jwt
from bookings_service.models import (
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
)
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
    @app.route('/api/v1/bookings', methods=['POST'])
    def create_booking():
        """
        Create a new booking for a room and time-slot.
        """
        claims = authenticate_request(request)
        if not claims:
            return jsonify({"message": "Unauthorized"}), 401
        user_id= claims.get("user_id")
        role = claims.get("role")
        
        if role!="user" and role!="facility_manager" : 
            return jsonify ( {"message" : "Must be a user or a facity manager" } ) , 403
        if not request.json: 
            return jsonify({"message": "No input data provided"}), 400
        
        room_id = request.json.get("room_id")
        start_time = request.json.get("start_time")
        end_time = request.json.get("end_time")
        if not room_id or not start_time or not end_time : 
            return jsonify({"message" : "missing some required fields"}), 400
        room_exists =  db_check_room_exists(room_id)
        if not room_exists: 
            return jsonify({"message":"The id deos not belong to an existing room"}), 400
        room_available = db_check_room_availability(room_id, start_time,end_time)
        if not room_available:
            return jsonify({"message" : "Room is not available at the suggested time"}) , 409
        booking_create = db_create_booking(user_id)
        if not booking_create:
            return jsonify({"message" : "Create booking failed"}), 500
        
        return   jsonify({"message" : "Booking creation suucceeeded! "}), 201
    
    @app.route('/api/v1/bookings/myhistory', methods=['GET'])
    def get_booking_history():
        """
        Return only the bookings of the authenticated user (satisfies “user’s booking history”).
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        
        bookings = db_get_booking_history(user_id)
        
        return jsonify(bookings), 200

    @app.route('/api/v1/bookings/user/<int:user_id>', methods=['GET'])
    def get_user_bookings():
        """
        View bookings for a given user id (for admin, facility manager, auditor; user themself can also use it).
        
        input : 
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        role = claims.get("role")
        user_id_claims = claims.get("user_id")
        
        user_id = request.view_args['user_id']
        if user_id !=user_id_claims  and role== "user" : 
            return jsonify({"message": "you can only see your won bookings unless previledged roles"}) , 403
        
        bookings = db_get_bookings_by_user(user_id)
        if bookings is None : 
            return jsonify({"message" : "No bookings found"}), 404 
        
        return jsonify(bookings), 200
    
    @app.route('/api/v1/bookings' ,methods =['GET'])
    def get_all_bookings():
        
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        
        if role =="user" :
            return jsonify({"message": "Users are not previleged to view all bookings"}), 403
          
        
        all_bookings = db_get_all_bookings()
        return jsonify(all_bookings), 200
    
    
    @app.route('/api/v1/bookings/<int:booking_id>', methods=['GET'])
    def get_booking():
        """
        get a booking by id
        """
        
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        booking_id = request.view_args['booking_id']

        booking = db_get_booking_by_id(booking_id)
        if booking["user_id"] != user_id and role=="user" : 
            return jsonify({"message": "You can only see your own books unless you are previlegd"}),403
        
        if not booking : 
            return jsonify({"message":"Booking not found"}),404
        
        
        
        return jsonify(booking), 200
    
    @app.route('/api/v1/bookings/<int:booking_id>', methods=['PATCH'])
    def update_booking(booking_id):
        """
        update a booking by id
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        
        booking_id  =request.view_args['booking_id']
        
        if not request.json: 
            return jsonify({"messsage": "provide data"}), 400
        
        room_id = request.json.get("room_id")
        start_time = request.json.get("start_time")
        end_time  = request.json.get("end_time")
        
        
        booking_id_exists = db_get_booking_by_id(booking_id)
        if not booking_id_exists:
            return jsonify({"message":" Booking doesnt exist! "}), 404 
        if booking_id_exists.status == "cancelled":
            return jsonify({"message" : "Cannot update a cancelled booking"}), 400
        if booking_id_exists.user_id!= claims.get("user_id") and claims.get("role") =="user":
            return jsonify({"message" : "You can only update your own booking"}),403
        if booking_id_exists.start_time <= now():
             return jsonify({"message" : "cbooking already started or finished "}), 400
        room_exists =  db_check_room_exists(room_id)
        if not room_exists: 
            return jsonify({"message":"The id deos not belong to an existing room"}), 400
        room_available = db_check_room_availability(room_id, start_time,end_time)
        if not room_available:
            return jsonify({"message" : "Room is not available at the suggested time"}) , 409   
        
        update = db_update_booking(booking_id, room_id, start_time, end_time)
        
        if not update: 
            return jsonify({"message" : "Update failed"}), 400
        
        return jsonify(update), 200
        
    @app.route('/api/v1/bookings/<int:booking_id>/cancel', methods=['POST'])
    def soft_cancel_booking(booking_id):
        """
        Set status = 'cancelled'.
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        
        booking_id = request.view_args["booking_id"]
        booking = db_get_booking_by_id(booking_id)
        if not booking :
            return jsonify({"message" : "This booking does not exist"}),404 
        if booking["user_id"] !=user_id and role=="user":
            return jsonify({"message" : "you can cancel only ur own booking"}),403
        if booking["status"] =="cancelled":
            return jsonify({"message" : "Booking already was canceled"}), 400
        if booking["start_time"] <= now(): 
            return jsonify({"message" : "session alreasy started or finished"}), 400
        
        cancel = db_soft_cancel_booking(booking_id)
        if not cancel: 
            return jsonify({"message" : "cancellation failedd"}), 500
        
        return jsonify({"message": f"Booking {booking_id} cancelled"}), 200
    
    @app.route('/api/v1/bookings/<int:booking_id>/hard', methods=['DELETE'])
    def hard_cancel_booking(booking_id):
        """
        Permanently delete a booking by its ID.
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        
        if role!="admin" :
            return jsonify({"message" : "This action can only be done by a admin !"}), 403 
        
        booking_id = request.view_args["booking_id"]
        booking = db_get_booking_by_id(booking_id)
        if not booking : 
            return jsonify({"message" : "Bookinf doesnt exist"}), 404 
        delete = db_hard_delete_booking(booking_id) 
        if not delete : 
            return jsonify({"message" : "it wasnt succesfully deleted "}), 500
        
        return jsonify({"message": f"Booking {booking_id} permanently deleted"}), 200
    
    @app.route('/api/v1/bookings/availability', methods=['GET'])
    def check_availablity():
        """
        Check whether a room is free in a given timeslot (satisfies “Checking room availability (based on time and date)” requirement).   
        
        example : /api/v1/bookings/availability?room_id=2&start_time=2025-11-23T14:00:00&end_time=2025-11-23T15:00:00
             
        """
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")

        room_id  = request.args.get("room_id")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        
        room_exists = db_check_room_exists(room_id)
        if not room_exists: 
            return jsonify({"message" : " The id does nto belong to an existing room"}), 400
        
        room_available = db_check_room_availability(room_id, start_time,end_time)
        return jsonify({"room_available": room_available}), 200

    @app.route('/api/v1/bookings/room/<int:int:room_id>', methods=['GET'])
    def get_bookings_for_room(room_id):
        """
        View all bookings for a given room id.
        """
        
        claims = authenticate_request(request)
        if not claims : 
            return jsonify({"message" : "Seems to be unautharized"}), 401 
        user_id= claims.get("user_id")
        role = claims.get("role")
        if role =="user":
            return jsonify({"message" : "Users are not allowed to view this"}), 403
        
        bookings = db_get_bookings_by_room(room_id)
        if bookings is None : 
            return jsonify({"message" : "No bookings found"}), 404 
        
        return jsonify({"bookings": bookings}), 200 
    return app
