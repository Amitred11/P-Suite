# psuite/models.py
from . import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    # FIXED: Added email field to match registration form and store user email
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    credits = db.Column(db.Integer, default=10)
    plan = db.Column(db.String(50), default='free')