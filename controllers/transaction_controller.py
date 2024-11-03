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

    # Check for required fields in request
    required_fields = ['from_account_id', 'type', 'amount']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    db = next(get_db())

    # Validate 'from_account_id' format
    try:
        from_account_id = int(data['from_account_id'])
    except ValueError:
        return jsonify({"message": "Invalid from_account_id format"}), 400

    # Query for the from_account to check ownership
    from_account = db.query(Account).filter_by(id=from_account_id, user_id=current_user_id).first()
    if not from_account:
        return jsonify({"message": "Unauthorized transaction: Invalid from_account_id"}), 403

    try:
        # Parse the amount and transaction type
        amount = float(data['amount'])
        transaction_type = data['type']

        # Process transaction based on type
        if transaction_type == 'deposit':
            from_account.balance += amount

        elif transaction_type == 'withdrawal':
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds for withdrawal"}), 400
            from_account.balance -= amount

        elif transaction_type == 'transfer':
            # Validate 'to_account_id' and check ownership
            if 'to_account_id' not in data:
                return jsonify({"message": "Missing to_account_id for transfer"}), 400
            try:
                to_account_id = int(data['to_account_id'])
            except ValueError:
                return jsonify({"message": "Invalid to_account_id format"}), 400

            # Check that to_account exists and belongs to the current user
            to_account = db.query(Account).filter_by(id=to_account_id, user_id=current_user_id).first()
            if not to_account:
                return jsonify({"message": "Unauthorized transaction: Invalid to_account_id"}), 403

            # Ensure sufficient balance for transfer
            if from_account.balance < amount:
                return jsonify({"message": "Insufficient funds for transfer"}), 400

            # Perform the transfer
            from_account.balance -= amount
            to_account.balance += amount

        else:
            return jsonify({"message": "Invalid transaction type"}), 400

        # Record the transaction
        transaction = Transaction(
            from_account_id=from_account_id,
            to_account_id=data.get('to_account_id'),  # to_account_id is optional except for transfers
            amount=amount,
            type=transaction_type,
            description=data.get('description', ''),
            created_at=datetime.utcnow()
        )

        # Save the transaction and commit
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
        user_accounts = db.query(Account).filter_by(user_id=current_user_id).all()
        user_account_ids = [account.id for account in user_accounts]

        query = db.query(Transaction).filter(
            (Transaction.from_account_id.in_(user_account_ids)) |
            (Transaction.to_account_id.in_(user_account_ids))
        )

        if account_id:
            query = query.filter(
                (Transaction.from_account_id == account_id) |
                (Transaction.to_account_id == account_id)
            )
            
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

