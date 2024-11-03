from datetime import datetime
from flask import jsonify, request, Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import Session
from models.transaction_model import Transaction
from models.account_model import Account
from connectors.db import get_db

transaction_bp = Blueprint('transactions', __name__)
 
@transaction_bp.route('/transaction', methods=['POST'])
@jwt_required()
def create_transaction():
    data = request.json
    current_user_id = get_jwt_identity()

    if 'from_account_id' not in data or 'type' not in data or 'amount' not in data:
        return jsonify({"message": "Missing required fields"}), 400

    db = next(get_db())

    try:
        amount = float(data['amount'])
        transaction_type = data['type']
        
        from_account = db.query(Account).filter_by(id=data['from_account_id'], user_id=current_user_id).first()
        if not from_account:
            return jsonify({"message": "Unauthorized transaction"}), 403

        if transaction_type == 'deposit':
            from_account.balance += amount
        elif transaction_type == 'withdrawal':
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds"}), 400
            from_account.balance -= amount
        elif transaction_type == 'transfer':
            if 'to_account_id' not in data:
                return jsonify({"message": "Missing to_account_id for transfer"}), 400
            to_account = db.query(Account).filter_by(id=data['to_account_id'], user_id=current_user_id).first()
            if not to_account:
                return jsonify({"message": "Invalid transfer"}), 403
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds"}), 400
            from_account.balance -= amount
            to_account.balance += amount
        else:
            return jsonify({"message": "Invalid transaction type"}), 400

        transaction = Transaction(
            from_account_id=data['from_account_id'],
            to_account_id=data.get('to_account_id'),
            amount=amount,
            type=transaction_type,
            description=data.get('description', ''),
            created_at=datetime.utcnow()
        )

        db.add(transaction)
        db.commit()
        return jsonify({"message": "Transaction successful"}), 201

    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

@transaction_bp.route('/', methods=['GET'])
@jwt_required()
def get_transactions():
    current_user_id = get_jwt_identity()
    account_id = request.args.get('account_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    db = next(get_db())
    try:
        # Fetch user's accounts
        user_accounts = db.query(Account).filter_by(user_id=current_user_id).all()
        user_account_ids = [account.id for account in user_accounts]

        # Base query for transactions involving user's accounts
        query = db.query(Transaction).filter(
            (Transaction.from_account_id.in_(user_account_ids)) |
            (Transaction.to_account_id.in_(user_account_ids))
        )

        # Apply account filter if provided
        if account_id:
            query = query.filter(
                (Transaction.from_account_id == account_id) |
                (Transaction.to_account_id == account_id)
            )

        # Apply date range filters if provided
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start_date)
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at <= end_date)

        transactions = query.all()
        result = [t.to_dict() for t in transactions]
        return jsonify(result), 200

    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

@transaction_bp.route('/<int:transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    current_user_id = get_jwt_identity()
    db = next(get_db())

    try:
        transaction = db.query(Transaction).filter_by(id=transaction_id).first()

        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404

        # Verify if the user owns the account related to the transaction
        from_account = db.query(Account).filter_by(id=transaction.from_account_id, user_id=current_user_id).first()
        to_account = db.query(Account).filter_by(id=transaction.to_account_id, user_id=current_user_id).first()

        if not (from_account or to_account):
            return jsonify({"message": "Unauthorized access"}), 403

        return jsonify(transaction.to_dict()), 200

    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()
