# Em app/routes/image_routes.py

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import text
from dropbox.exceptions import ApiError
import os

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

@image_bp.route('/image/restore', methods=['POST']) # ROTA CORRIGIDA
@login_required
def restaurar_imagem():
    """Restaura uma imagem da lixeira (identificada apenas pelo path)."""
    # Se o front-end envia JSON, use request.get_json().get('imagem')
    imagem_path_lixeira = request.form.get('imagem') 
    if not imagem_path_lixeira:
        return jsonify(success=False, mensagem="Caminho da imagem não informado."), 400
    
    try:
        with get_db_connection() as conn:
            campanha = get_campaign_from_image_path(conn, imagem_path_lixeira)
            if not campanha:
                return jsonify(success=False, mensagem="Campanha associada não encontrada."), 404

            nome_arquivo = os.path.basename(imagem_path_lixeira)
            path_original = f"/{slug(campanha['nome'])}/{nome_arquivo}"
            
            # --- LÓGICA CORRIGIDA ---
            # 1. ATUALIZE O BANCO DE DADOS PRIMEIRO
            cursor = conn.execute(
                text("UPDATE campanhas_imagens SET apagada = 0, imagem_path = :path_original WHERE imagem_path = :path_lixeira"),
                {"path_original": path_original, "path_lixeira": imagem_path_lixeira}
            )
            
            # 2. VERIFIQUE SE A ATUALIZAÇÃO FOI BEM-SUCEDIDA
            if cursor.rowcount == 0:
                # Se nada mudou, a imagem não estava no banco. Não faça nada no Dropbox.
                return jsonify(success=False, mensagem="Erro: Imagem não encontrada na lixeira do banco."), 404
            
            # 3. SÓ SE O BANCO FOI ATUALIZADO, MOVA O ARQUIVO NO DROPBOX
            dropbox = get_dropbox_service()
            dropbox.move_file(imagem_path_lixeira, path_original)
            
            # 4. FINALIZE A TRANSAÇÃO
            conn.commit()

        return jsonify(success=True, mensagem="Imagem restaurada com sucesso.")

    except Exception as e:
        # Se ocorrer uma exceção, a transação com o banco será revertida automaticamente pelo 'with'
        current_app.logger.error(f"Falha ao restaurar imagem: {e}")
        return jsonify(success=False, mensagem="Erro ao restaurar imagem."), 500

# (Certifique-se de que 'dropbox' está importado ou acessível)
from dropbox.exceptions import ApiError

@image_bp.route('/excluir_definitivo', methods=['POST'])
@login_required
def excluir_definitivo():
    """Exclui permanentemente uma imagem (identificada apenas pelo path)."""
    imagem_path = request.form.get('imagem')
    if not imagem_path:
        return jsonify(success=False, mensagem="Caminho da imagem não informado."), 400

    try:
        # 1. INICIA A TRANSAÇÃO COM O BANCO DE DADOS
        with get_db_connection() as conn:
            # 2. TENTA REMOVER O REGISTRO DO BANCO PRIMEIRO
            cursor = conn.execute(
                text("DELETE FROM campanhas_imagens WHERE imagem_path = :path"), 
                {"path": imagem_path}
            )

            # 3. VERIFICA SE O REGISTRO EXISTIA
            if cursor.rowcount == 0:
                # Se nenhuma linha foi deletada, o registro não existe no banco.
                # Não há necessidade de prosseguir para o Dropbox.
                return jsonify(success=False, mensagem="Imagem não encontrada no banco de dados."), 404

            # 4. SÓ SE O REGISTRO FOI REMOVIDO DO BANCO, EXCLUI O ARQUIVO DO DROPBOX
            try:
                dropbox = get_dropbox_service()
                dropbox.delete_file(imagem_path)
            except ApiError as e:
                # Caso especial: o arquivo não foi encontrado no Dropbox.
                # Como nosso objetivo é que ele seja deletado, consideramos isso um sucesso.
                # O registro do banco já foi marcado para exclusão, então podemos continuar.
                if 'path/not_found' not in str(e):
                    # Se for outro erro de API, reverta a transação do banco e relate o erro.
                    raise e # Isso fará com que a transação seja revertida (rollback)

            # 5. SE TUDO DEU CERTO, CONFIRMA A TRANSAÇÃO NO BANCO (COMMIT)
            conn.commit()
            return jsonify(success=True, mensagem="Imagem excluída permanentemente.")

    except Exception as e:
        # Qualquer exceção aqui (seja do banco ou do Dropbox) fará com que a transação
        # seja revertida automaticamente pelo 'with' block, garantindo a consistência.
        current_app.logger.error(f"Falha na exclusão definitiva: {e}")
        return jsonify(success=False, mensagem="Erro na exclusão definitiva da imagem."), 500