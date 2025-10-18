#!/bin/bash
# Este script inicializa o banco de dados e cria o admin antes de iniciar o servidor.

# 1. Executa o script de inicialização do banco de dados (Corrige o IndexError removendo o pop())
python -c 'from app import create_app; app = create_app(); app.app_context().push(); from app.utils.database import inicializar_banco; inicializar_banco(app)'

# 2. Inicia o servidor Gunicorn com o worker assíncrono para SocketIO
gunicorn run:app -k gevent -b 0.0.0.0:$PORT
