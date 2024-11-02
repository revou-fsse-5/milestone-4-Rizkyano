from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models.user_model import User
from connectors.db import get_db
from sqlalchemy.orm import Session

user_bp = Blueprint('users', __name__)

@user_bp.route('/register', methods=['POST'])
def create_user():
    db: Session = next(get_db())
    data = request.json
    hashed_password = generate_password_hash(data['password'])
    user = User(username=data['username'], email=data['email'], password_hash=hashed_password)
    db.add(user)
    db.commit()
    return jsonify({"message": "User created successfully"}), 201

@user_bp.route('/login', methods=['POST'])
def login():
    db: Session = next(get_db())
    data = request.json

    if not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    user = db.query(User).filter_by(email=data['email']).first()

    if user and check_password_hash(user.password_hash, data['password']):

        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401
@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    db: Session = next(get_db())
    current_user_id = get_jwt_identity()
    user = db.query(User).filter_by(id=current_user_id).first()
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    }
    return jsonify(user_data), 200

@user_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_user_profile():
    db: Session = next(get_db())
    current_user_id = get_jwt_identity()
    user = db.query(User).filter_by(id=current_user_id).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'password' in data:
        user.password_hash = generate_password_hash(data['password'])
    
    db.commit()
    return jsonify({"message": "User profile updated successfully"}), 200
