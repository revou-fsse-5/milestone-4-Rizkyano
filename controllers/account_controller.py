from flask import Blueprint, request, jsonify, abort
from models.account_model import Account
from connectors.db import get_db
from sqlalchemy.orm import Session
from flask_jwt_extended import jwt_required, get_jwt_identity

account_bp = Blueprint('accounts', __name__)

@account_bp.route('/', methods=['GET'])
@jwt_required()
def get_accounts():
    user_id = get_jwt_identity() 
    db: Session = next(get_db())
    accounts = db.query(Account).filter_by(user_id=user_id).all()
    return jsonify([account.to_dict() for account in accounts]), 200

@account_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_account(id):
    user_id = get_jwt_identity()
    db: Session = next(get_db())
    account = db.query(Account).filter_by(id=id, user_id=user_id).first()
    
    if account is None:
        return abort(404, description="Account not found or you do not have permission to access it")
    
    return jsonify(account.to_dict()), 200

@account_bp.route('/accounts', methods=['POST'])
@jwt_required()
def create_account():
    db: Session = next(get_db())
    data = request.json
    account = Account(user_id=data['user_id'], account_type=data['account_type'], account_number=data['account_number'])
    db.add(account)
    db.commit()
    return jsonify({"message": "Account created successfully"}), 201

@account_bp.route('/accounts/<int:id>', methods=['PUT'])
@jwt_required()
def update_account(id):
    user_id = get_jwt_identity()
    db: Session = next(get_db())
    account = db.query(Account).filter_by(id=id, user_id=user_id).first()
    
    if account is None:
        return abort(404, description="Account not found or you do not have permission to update it")
    
    data = request.json
    account.account_type = data.get('account_type', account.account_type)
    account.account_number = data.get('account_number', account.account_number)
    db.commit()
    return jsonify({"message": "Account updated successfully"}), 200

@account_bp.route('/accounts/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_account(id):
    user_id = get_jwt_identity()
    db: Session = next(get_db())
    account = db.query(Account).filter_by(id=id, user_id=user_id).first()
    
    if account is None:
        return abort(404, description="Account not found or you do not have permission to delete it")
    
    db.delete(account)
    db.commit()
    return jsonify({"message": "Account deleted successfully"}), 200
