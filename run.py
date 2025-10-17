# --- Monkey-patching (DEVE SER A PRIMEIRA COISA NO FICHEIRO) ---
import gevent.monkey
gevent.monkey.patch_all(socket=False)

# --- Importações ---
import os
from dotenv import load_dotenv
from flask import request
from app import create_app, socketio
from app.models import db, User
from werkzeug.security import generate_password_hash

# 🔄 Carrega variáveis do .env
load_dotenv()

# 🌍 Ambiente
ENV   = os.getenv("FLASK_ENV",   "development").lower()
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

print(f"🚀 Iniciando servidor em modo: {ENV.upper()}")

# --- Cria a app e configurações principais ---
app = create_app()
app.config["DEBUG"] = DEBUG

# --- Configurações de produção (PostgreSQL + Sessões) ---
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SECRET_KEY"]             = os.getenv("SECRET_KEY")
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# --- Comandos de CLI ---
@app.cli.command("create-db")
def create_db():
    """Cria as tabelas da base de dados."""
    with app.app_context():
        db.create_all()
    print("✅ Tabelas da base de dados criadas com sucesso.")

@app.cli.command("create-admin")
def create_admin():
    """Cria o utilizador administrador padrão."""
    with app.app_context():
        if User.query.filter_by(username="admin").first():
            print("Utilizador 'admin' já existe.")
            return
        admin_user = User(
            username="admin",
            senha=generate_password_hash("beto891", method="pbkdf2:sha256"),
            is_admin=1,
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Utilizador 'admin' criado com sucesso.")

# --- Execução via SocketIO / Gunicorn ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))

    if ENV == "development":
        print("✅ Dev server em http://127.0.0.1:5000")
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=DEBUG,
            use_reloader=False,
        )
    else:
        print(f"🚀 Produção escutando em 0.0.0.0:{port}")
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
        )