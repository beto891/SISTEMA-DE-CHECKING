# app/routes/delete_galeria.py
# Este arquivo contém a nova rota para ações de imagem, como deletar para a lixeira.

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

# Funções e serviços que seu projeto já usa
from ..utils.database import get_db_connection
from ..services.dropbox_service import DropboxService

# --- Constantes ---
PASTA_LIXEIRA_DROPBOX = "/LIXEIRA"

# --- Criação da Blueprint ---
# A parte mais importante: o prefixo é '/api/image', que corresponde ao que o JS chama.
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
    Esta rota responde exatamente a 'POST /api/image/delete-to-trash'.
    """
    data = request.get_json()
    if not data or 'image_id' not in data:
        return jsonify(success=False, mensagem="O ID da imagem é obrigatório."), 400
    
    image_id = data['image_id']

    conn = None
    try:
        conn = get_db_connection()
        
        # Busca a imagem no DB para garantir que ela existe e não está na lixeira
        imagem = conn.execute(
            "SELECT imagem_path FROM campanhas_imagens WHERE id = ? AND apagada = 0", (image_id,)
        ).fetchone()

        if not imagem:
            return jsonify(success=False, mensagem="Imagem não encontrada ou já está na lixeira."), 404
        
        caminho_atual = imagem['imagem_path']
        nome_arquivo = os.path.basename(caminho_atual)
        caminho_lixeira = f"{PASTA_LIXEIRA_DROPBOX}/{nome_arquivo}"

        # Atualiza o banco de dados PRIMEIRO
        with conn:
            conn.execute(
                "UPDATE campanhas_imagens SET apagada = 1, imagem_path = ? WHERE id = ?",
                (caminho_lixeira, image_id)
            )

        # Se o banco foi atualizado, move o arquivo no Dropbox
        try:
            dropbox = get_dbx_service()
            dropbox.move_file(caminho_atual, caminho_lixeira)
        except Exception as dropbox_error:
            current_app.logger.error(f"DB atualizado (ID {image_id}), mas falha ao mover no Dropbox: {dropbox_error}")
            return jsonify(success=True, mensagem="Imagem removida da galeria (alerta de sincronização).")

        return jsonify(success=True, mensagem="Imagem movida para a lixeira com sucesso!")

    except Exception as e:
        current_app.logger.error(f"Erro grave ao mover imagem ID {image_id} para lixeira: {e}")
        return jsonify(success=False, mensagem="Erro interno no servidor ao processar a solicitação."), 500
    finally:
        if conn:
            conn.close()