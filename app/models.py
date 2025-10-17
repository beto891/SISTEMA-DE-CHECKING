from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    senha    = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=False)

class Campanha(db.Model):
    __tablename__ = 'campanhas'

    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False)
    cod           = db.Column(db.String(50),  nullable=False, unique=True)
    data_criacao  = db.Column(db.DateTime,    nullable=False,
                              default=datetime.utcnow)

    # Relacionamento com imagens
    imagens       = db.relationship(
        'CampanhaImagem',
        backref='campanha',
        lazy=True,
        cascade='all, delete-orphan'
    )

class CampanhaImagem(db.Model):
    __tablename__ = 'campanhas_imagens'

    id           = db.Column(db.Integer, primary_key=True)
    campanha_id  = db.Column(db.Integer,
                             db.ForeignKey('campanhas.id'),
                             nullable=False)
    imagem_path  = db.Column(db.String(200), nullable=True)