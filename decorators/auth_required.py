from flask import request, jsonify
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_identity = get_jwt_identity() 
            return fn(*args, **kwargs)
        except NoAuthorizationError:
            return jsonify({"msg": "Missing or invalid token"}), 401
    return wrapper
