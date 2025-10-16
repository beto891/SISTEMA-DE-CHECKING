import os
from dotenv import load_dotenv
from app import create_app
from app.socketio_events import socketio

# 🔄 Carrega variáveis do .env
load_dotenv()

# 🌍 Ambiente
ENV = os.getenv("FLASK_ENV", "development").lower()
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

print(f"🚀 Iniciando servidor em modo: {ENV.upper()}")

# Cria app
app = create_app()
app.config['DEBUG'] = DEBUG

for rule in app.url_map.iter_rules():
    print(f"🔗 Rota ativa: {rule}")

# 🔌 Execução
if __name__ == "__main__":
    if ENV == "development":
        print("✅ Servidor Flask com SocketIO escutando em http://127.0.0.1:5000")
        socketio.run(app, host="0.0.0.0", port=5000, debug=DEBUG, use_reloader=False)

    elif ENV == "production":
        from cert_util import gerar_certificado
        import ssl

        cert_path = "certs/cert.pem"
        key_path = "certs/key.pem"

        # 🔐 Gera certificado se necessário
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            print("🔧 Gerando certificados SSL...")
            gerar_certificado(cert_path, key_path)

        # 🔒 Contexto SSL
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)

        print("✅ Servidor HTTPS escutando em https://127.0.0.1:5000")
        socketio.run(app, host="0.0.0.0", port=5000, ssl_context=ctx, debug=False)

    else:
        print(f"❌ Ambiente desconhecido: {ENV}")
        
