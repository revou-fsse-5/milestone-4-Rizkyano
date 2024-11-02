from flask import Blueprint, request, jsonify, abort
from models.transaction_model import Transaction
from models.account_model import Account
from connectors.db import get_db
from sqlalchemy.orm import Session
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

transaction_bp = Blueprint('transactions', __name__)

@transaction_bp.route('/', methods=['GET'])
@jwt_required()
def get_transactions():
    with get_db() as db: 
        current_user_id = get_jwt_identity()
        account_id = request.args.get('account_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = db.query(Transaction).join(Transaction.account).filter(Transaction.account.user_id == current_user_id)

        if account_id:
            query = query.filter(Transaction.from_account_id == account_id)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at <= end_date)

        transactions = query.all()
        transaction_list = [
            {
                "id": transaction.id,
                "from_account_id": transaction.from_account_id,
                "to_account_id": transaction.to_account_id,
                "amount": transaction.amount,
                "type": transaction.type,
                "description": transaction.description,
                "created_at": transaction.created_at,
            } for transaction in transactions
        ]
        
        return jsonify(transaction_list), 200

@transaction_bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id: int) -> tuple:
    with get_db() as db:  
        current_user_id = get_jwt_identity()
        transaction = db.query(Transaction).join(Transaction.account).filter(
            Transaction.id == transaction_id,
            Transaction.account.user_id == current_user_id
        ).first()

        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404

        transaction_data = {
            "id": transaction.id,
            "from_account_id": transaction.from_account_id,
            "to_account_id": transaction.to_account_id,
            "amount": transaction.amount,
            "type": transaction.type,
            "description": transaction.description,
            "created_at": transaction.created_at,
        }

        return jsonify(transaction_data), 200

@transaction_bp.route('/transactions', methods=['POST'])
@jwt_required()
def create_transaction() -> tuple:
    with get_db() as db:  # Ensure proper session management
        data = request.json
        current_user_id = get_jwt_identity()

        # Validate required fields
        if 'from_account_id' not in data or 'type' not in data or 'amount' not in data:
            return jsonify({"message": "Missing required fields"}), 400

        # Check if the from_account belongs to the current user
        from_account = db.query(Account).filter_by(id=data['from_account_id'], user_id=current_user_id).first()
        if not from_account:
            return jsonify({"message": "Unauthorized transaction."}), 403

        transaction_type = data['type']
        amount = data['amount']

        if transaction_type == 'deposit':
            from_account.balance += amount
        elif transaction_type == 'withdrawal':
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds for withdrawal."}), 400
            from_account.balance -= amount
        elif transaction_type == 'transfer':
            if 'to_account_id' not in data:
                return jsonify({"message": "Missing to_account_id for transfer."}), 400
            to_account = db.query(Account).filter_by(id=data['to_account_id'], user_id=current_user_id).first()
            if not to_account:
                return jsonify({"message": "Invalid transfer."}), 403
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds for transfer."}), 400
            from_account.balance -= amount
            to_account.balance += amount
        else:
            return jsonify({"message": "Invalid transaction type."}), 400

        # Create the transaction record
        transaction = Transaction(
        from_account_id=data['from_account_id'],
        to_account_id=data.get('to_account_id'),
        amount=data['amount'],
        type=data['type'],
        description=data.get('description', ''),
        created_at=datetime.utcnow()
        )

        db.add(transaction)
        db.commit()
