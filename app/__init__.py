print("--- CARREGANDO A VERSÃO FINAL E CORRETA DO __init__.py ---") # MENSAGEM DE TESTE

import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import LoginManager
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# NOVO: Importa a função de inicialização de DB para criar tabelas e admin
from .utils.database import inicializar_banco

# ✅ NOVO: Importa a função de inicialização do Celery
from app.services.celery_config import init_celery

# --- INSTÂNCIAS GLOBAIS ---
from .models import db, User
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")

# Configura o LoginManager
login_manager.login_view = 'auth.login'
login_manager.login_message = "Por favor, faça o login para acessar este recurso."
login_manager.login_message_category = "warning"

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário da sessão para cada requisição."""
    return User.query.get(int(user_id))

# --- FÁBRICA DE APLICAÇÃO ---
def create_app():
    app = Flask(__name__)

    # --- CONFIGURAÇÕES ---
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "uma-chave-secreta-forte")
    
    # <<< LÓGICA DE CONEXÃO AJUSTADA PARA POSTGRESQL E SQLITE >>>
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        # Pequena correção necessária para compatibilidade com Heroku/Render e SQLAlchemy
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Se a variável de ambiente DATABASE_URL existir (na cloud), usa-a.
    # Senão (localmente), usa o ficheiro SQLite.
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or f"sqlite:///{os.path.abspath('database.db')}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DROPBOX_REFRESH_TOKEN'] = os.getenv("DROPBOX_REFRESH_TOKEN")
    app.config['DROPBOX_APP_KEY'] = os.getenv("DROPBOX_APP_KEY")
    app.config['DROPBOX_APP_SECRET'] = os.getenv("DROPBOX_APP_SECRET")

    # --- INICIALIZAÇÃO DAS EXTENSÕES ---
    CORS(app)
    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)


  
    # ✅ INICIALIZAÇÃO DO CELERY COM A APLICAÇÃO FLASK
    from app.services.celery_config import init_celery
    init_celery(app)

    # --- REGISTRO DE BLUEPRINTS, EVENTOS E INICIALIZAÇÃO DO DB ---
    with app.app_context():
        # CHAMADA CRÍTICA ADICIONADA: Inicializa as tabelas no PostgreSQL/SQLite e cria o admin
        inicializar_banco(app)
        
        # Importa as blueprints
        from .routes.auth import auth
        from .routes.task import task_bp
        from .routes.campaign import campaign_bp
        from .routes.dashboard import dashboard_bp
        from .routes.user import user_bp
        from .routes.upload import upload_bp
        from .routes.delete_galeria import delete_galeria_bp
        from .routes.admin_bp import admin_bp
        from .routes.image_routes import image_bp
        
        # Importa o arquivo de eventos do socketio para que os handlers sejam registrados
        from . import socketio_events 

        # Registro das Blueprints
        app.register_blueprint(auth)
        app.register_blueprint(task_bp)
        app.register_blueprint(campaign_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(upload_bp)
        app.register_blueprint(delete_galeria_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(image_bp)

    return app
