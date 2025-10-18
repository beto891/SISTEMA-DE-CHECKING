# Este arquivo contém a nova rota para ações de imagem, como deletar para a lixeira.

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import text # Importação obrigatória para SQL puro no SQLAlchemy 2.0+

# Funções e serviços que seu projeto já usa
# Substituímos a importação ambígua de get_db_connection
from app import db # Importamos o objeto db do Flask-SQLAlchemy
from ..services.dropbox_service import DropboxService

# --- Constantes ---
PASTA_LIXEIRA_DROPBOX = "/LIXEIRA"

# --- Criação da Blueprint ---
delete_galeria_bp = Blueprint('delete_galeria', __name__, url_prefix='/api/image')

def get_dbx_service():
    """Função auxiliar para obter o serviço do Dropbox a partir da config do app."""
    return DropboxService(
        refresh_token=current_app.config['DROPBOX_REFRESH_TOKEN'],
        app_key=current_app.config['DROPBOX_APP_KEY'],
        app_secret=current_app.config['DROPBOX_APP_SECRET']
    )

# --- A Nova Rota ---
@delete_galeria_bp.route('/delete-to-trash', methods=['POST'])
@login_required
def move_image_to_trash():
    """
    Move uma imagem para a lixeira (exclusão lógica) usando seu ID.
    """
    data = request.get_json()
    if not data or 'image_id' not in data:
        return jsonify(success=False, mensagem="O ID da imagem é obrigatório."), 400
    
    image_id = data['image_id']

    try:
        # Usamos 'with db.engine.connect() as conn:' para gerenciar a conexão e o recurso
        with db.engine.connect() as conn:
            
            # CORREÇÃO 1: Usando text() e marcador nomeado (:id) para o SELECT
            imagem = conn.execute(
                text("SELECT imagem_path FROM campanhas_imagens WHERE id = :id AND apagada = 0"), 
                {"id": image_id}
            ).fetchone()

            if not imagem:
                return jsonify(success=False, mensagem="Imagem não encontrada ou já está na lixeira."), 404
            
            imagem = dict(imagem._mapping)  # Converte o objeto Row do SQLAlchemy em um dicionário Python

            caminho_atual = imagem['imagem_path']
            nome_arquivo = os.path.basename(caminho_atual)
            caminho_lixeira = f"{PASTA_LIXEIRA_DROPBOX}/{nome_arquivo}"

            # CORREÇÃO 2: Usando text() e marcadores nomeados (:caminho, :id) para o UPDATE
            conn.execute(
                text("UPDATE campanhas_imagens SET apagada = 1, imagem_path = :caminho WHERE id = :id"),
                {"caminho": caminho_lixeira, "id": image_id}
            )
            conn.commit() # Commit explícito da transação
            
            # Se o banco foi atualizado, move o arquivo no Dropbox
            try:
                dropbox = get_dbx_service()
                # O caminho no Dropbox deve ser prefixado com '/'
                dropbox_caminho_atual = caminho_atual if caminho_atual.startswith('/') else '/' + caminho_atual
                dropbox_caminho_lixeira = caminho_lixeira if caminho_lixeira.startswith('/') else '/' + caminho_lixeira
                
                dropbox.move_file(dropbox_caminho_atual, dropbox_caminho_lixeira)
            except Exception as dropbox_error:
                current_app.logger.error(f"DB atualizado (ID {image_id}), mas falha ao mover no Dropbox: {dropbox_error}")
                # Retorna sucesso, mas com alerta (o DB é a fonte da verdade)
                return jsonify(success=True, mensagem="Imagem removida da galeria (alerta de sincronização).")

            return jsonify(success=True, mensagem="Imagem movida para a lixeira com sucesso!")

    except Exception as e:
        current_app.logger.error(f"Erro grave ao mover imagem ID {image_id} para lixeira: {e}")
        # Não é necessário rollback, pois `with db.engine.connect()` cuida da transação
        return jsonify(success=False, mensagem="Erro interno no servidor ao processar a solicitação."), 500
    # O `finally` com `conn.close()` é desnecessário pois o bloco `with` o faz automaticamente.
