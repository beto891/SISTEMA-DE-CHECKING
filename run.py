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


# --- ROTA TEMPORÁRIA PARA CRIAR A BASE DE DADOS ---
@app.route('/create-tables')
def create_tables_route():
    """
    Rota temporária e secreta para criar as tabelas da base de dados.
    """
    secret_key_from_env = os.getenv('SECRET_KEY')
    secret_key_from_query = request.args.get('secret')

    if not secret_key_from_env or secret_key_from_env != secret_key_from_query:
        return "Acesso não autorizado.", 403

    try:
        from app.models import db
        with app.app_context():
            db.create_all()
        return "✅ Tabelas da base de dados criadas com sucesso! PODE E DEVE REMOVER ESTA ROTA AGORA."
    except Exception as e:
        return f"❌ Ocorreu um erro ao criar as tabelas: {e}", 500

# (O comando 'create-db' pode ser mantido ou removido, já que não o podemos usar no Render)
@app.cli.command("create-db")
def create_db():
    """Cria as tabelas da base de dados."""
    from app.models import db
    with app.app_context():
        db.create_all()
    print("✅ Tabelas da base de dados criadas com sucesso.")


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