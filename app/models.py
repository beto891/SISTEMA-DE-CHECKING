# app/models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# A instância 'db' é criada aqui
db = SQLAlchemy()

# A classe 'User' é definida aqui
class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=False)