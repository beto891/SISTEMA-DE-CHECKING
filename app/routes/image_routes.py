# Em app/routes/image_routes.py

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import text
from dropbox.exceptions import ApiError
import os
from ..helpers import get_dropbox_service, slug, get_campaign_from_image_path

# Importe as funções auxiliares que você vai precisar
from ..utils.database import get_db_connection
from ..services.dropbox_service import DropboxService
from .upload import get_campaign_from_image_path, slug # Importando do seu outro arquivo de rotas

# --- Configuração do Blueprint ---
image_bp = Blueprint('image', __name__, url_prefix='/api/image')

def get_dropbox_service():
    """Inicializa e retorna uma instância do serviço do Dropbox."""
    # (Pode copiar esta função de upload.py ou centralizá-la em outro lugar)
    try:
        return DropboxService(
            refresh_token=current_app.config['DROPBOX_REFRESH_TOKEN'],
            app_key=current_app.config['DROPBOX_APP_KEY'],
            app_secret=current_app.config['DROPBOX_APP_SECRET']
        )
    except KeyError as e:
        current_app.logger.error(f"❌ Configuração do Dropbox ausente: {e}")
        raise RuntimeError(f"Credencial do Dropbox não encontrada: {e}")

#
#  >>> É AQUI QUE VAMOS COLAR AS FUNÇÕES DE RESTAURAR E EXCLUIR <<<
#

# Em app/routes/image_routes.py

@image_bp.route('/restore', methods=['POST'])
@login_required
def restaurar_imagem():
    data = request.get_json()
    image_id = data.get('image_id')
    if not image_id:
        return jsonify(success=False, mensagem="ID da imagem não informado."), 400

    try:
        with get_db_connection() as conn:
            # Busca o caminho da imagem na lixeira usando o ID
            imagem_row = conn.execute(text("SELECT imagem_path FROM campanhas_imagens WHERE id = :id AND apagada = 1"), {"id": image_id}).fetchone()
            if not imagem_row:
                return jsonify(success=False, mensagem="Imagem não encontrada na lixeira do banco."), 404
            
            imagem_path_lixeira = imagem_row[0]
            
            # Recria o path original (esta lógica precisa ser igual à sua)
            campanha = get_campaign_from_image_path(conn, imagem_path_lixeira)
            if not campanha:
                return jsonify(success=False, mensagem="Campanha associada não encontrada."), 404
            
            nome_arquivo = os.path.basename(imagem_path_lixeira)
            path_original = f"/{slug(campanha['nome'])}/{nome_arquivo}"
            
            # Lógica de banco de dados primeiro
            cursor = conn.execute(
                text("UPDATE campanhas_imagens SET apagada = 0, imagem_path = :path_original WHERE id = :id"),
                {"path_original": path_original, "id": image_id}
            )
            
            if cursor.rowcount == 0:
                return jsonify(success=False, mensagem="Falha ao atualizar o registro no banco de dados."), 500

            # Move o arquivo no Dropbox
            dropbox = get_dropbox_service()
            dropbox.move_file(imagem_path_lixeira, path_original)
            
            conn.commit()
            return jsonify(success=True, mensagem="Imagem restaurada com sucesso.")

    except Exception as e:
        current_app.logger.error(f"Falha ao restaurar imagem: {e}")
        return jsonify(success=False, mensagem="Erro ao restaurar imagem."), 500

# (Certifique-se de que 'dropbox' está importado ou acessível)
from dropbox.exceptions import ApiError

@image_bp.route('/delete-permanent', methods=['POST']) # <<< NOME DA ROTA CORRIGIDO
@login_required
def excluir_definitivo():
    data = request.get_json()
    image_id = data.get('image_id')
    if not image_id:
        return jsonify(success=False, mensagem="ID da imagem não informado."), 400

    try:
        with get_db_connection() as conn:
            # Busca o caminho do arquivo ANTES de deletar do banco
            imagem_row = conn.execute(text("SELECT imagem_path FROM campanhas_imagens WHERE id = :id"), {"id": image_id}).fetchone()
            if not imagem_row:
                 return jsonify(success=False, mensagem="Imagem não encontrada no banco de dados."), 404

            imagem_path = imagem_row[0]

            # Deleta do banco primeiro
            cursor = conn.execute(text("DELETE FROM campanhas_imagens WHERE id = :id"), {"id": image_id})
            
            # Deleta do Dropbox
            try:
                dropbox = get_dropbox_service()
                dropbox.delete_file(imagem_path)
            except ApiError as e:
                if 'path/not_found' not in str(e):
                    raise e 
            
            conn.commit()
            return jsonify(success=True, mensagem="Imagem excluída permanentemente.")

    except Exception as e:
        current_app.logger.error(f"Falha na exclusão definitiva: {e}")
        return jsonify(success=False, mensagem="Erro na exclusão definitiva da imagem."), 500