# --- Monkey-patching (DEVE SER A PRIMEIRA COISA NO FICHEIRO) ---
import gevent.monkey
gevent.monkey.patch_all()

# --- Importações ---
import os
from dotenv import load_dotenv
from flask import request  # <<< CORREÇÃO 1: Importa o 'request' que estava a faltar
from app import create_app
from app import socketio     # <<< CORREÇÃO 2: Importa o 'socketio' a partir do pacote 'app'

# 🔄 Carrega variáveis do .env
load_dotenv()

# 🌍 Ambiente
ENV = os.getenv("FLASK_ENV", "development").lower()
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

print(f"🚀 Iniciando servidor em modo: {ENV.upper()}")

# Cria app
app = create_app()
app.config['DEBUG'] = DEBUG

# (Opcional: Pode remover o loop que imprime as rotas em produção)
# for rule in app.url_map.iter_rules():
#     print(f"🔗 Rota ativa: {rule}")


# (O comando 'create-db' pode ser mantido ou removido, já que não o podemos usar no Render)
@app.cli.command("create-db")
def create_db():
    """Cria as tabelas da base de dados."""
    from app.models import db
    with app.app_context():
        db.create_all()
    print("✅ Tabelas da base de dados criadas com sucesso.")


from werkzeug.security import generate_password_hash
from app.models import db, User
import os

@app.cli.command("create-admin")
def create_admin():
    """Cria o utilizador administrador a partir das variáveis do ambiente."""
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD')

    if not admin_password:
        print("⚠️ ADMIN_PASSWORD não configurado. Defina a variável de ambiente antes de criar o admin.")
        return

    existing_user = User.query.filter_by(username=admin_username).first()
    if existing_user:
        existing_user.senha = generate_password_hash(admin_password, method='pbkdf2:sha256')
        existing_user.is_admin = 1
        db.session.commit()
        print(f"✅ Utilizador '{admin_username}' atualizado com a senha do ambiente.")
        return

    admin_user = User(
        username=admin_username,
        senha=generate_password_hash(admin_password, method='pbkdf2:sha256'),
        is_admin=1
    )
    db.session.add(admin_user)
    db.session.commit()
    print(f"✅ Utilizador '{admin_username}' criado com sucesso.")

# --- Execução ---
if __name__ == "__main__":
    if ENV == "development":
        print("✅ Servidor Flask com SocketIO escutando em http://127.0.0.1:5000")
        socketio.run(app, host="0.0.0.0", port=5000, debug=DEBUG, use_reloader=False)
    else:
        # Em produção (como no Render), o Gunicorn irá gerir a aplicação,
        # então o código de produção que você tinha aqui não é necessário
        # quando se usa o 'Start Command' do Render.
        print("Aplicação pronta para ser servida pelo Gunicorn.")