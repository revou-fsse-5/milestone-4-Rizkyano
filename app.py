from flask import Flask, redirect
from flask_jwt_extended import JWTManager
from connectors.db import engine, Base
from controllers.user_controller import user_bp
from controllers.account_controller import account_bp
from controllers.transaction_controller import transaction_bp
import os

app = Flask(__name__)
app.config['DEBUG'] = True

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

jwt = JWTManager(app)

app.register_blueprint(user_bp, url_prefix='/users')
app.register_blueprint(account_bp, url_prefix='/accounts')
app.register_blueprint(transaction_bp, url_prefix='/transactions')

@app.route("/")
def home():
    return "Welcome to the Banking API!"
@app.route("/docs")
def docs():
    return "API Documentation will be here."


Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    app.run(debug=True)
