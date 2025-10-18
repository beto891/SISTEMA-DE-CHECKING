#!/bin/bash
# Este script inicializa o banco de dados e cria o admin antes de iniciar o servidor.

# 1. Executa o script de inicialização do banco de dados (Corrige o SyntaxError)
# A lógica é: cria o app, e usa app.app_context() para executar a inicialização.
python -c 'from app import create_app; app = create_app(); with app.app_context(): from app.utils.database import inicializar_banco; inicializar_banco(app)'

# 2. Inicia o servidor Gunicorn com o worker assíncrono para SocketIO
# (O Start Command do Render deve ser APENAS: ./setup_db.sh)
gunicorn run:app -k gevent -b 0.0.0.0:$PORT