import os
import unicodedata
from datetime import datetime
from PIL import Image
from flask_login import login_required
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text # NOVO: Importação para compatibilidade com SQLAlchemy 2.0+

from flask import (
    Blueprint, request, jsonify, 
    current_app, render_template
)
from werkzeug.utils import secure_filename

from app.utils.database import get_db_connection
from app.services.dropbox_service import DropboxService
import dropbox

# --- Configuração do Blueprint ---
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

# --- Constantes ---
EXTENSOES_VALIDAS = {'.png', '.jpg', '.jpeg', '.webp'}
PASTA_LIXEIRA = "/LIXEIRA"

# --- Funções Auxiliares ---

def get_dropbox_service():
    """Inicializa e retorna uma instância do serviço do Dropbox."""
    try:
        return DropboxService(
            refresh_token=current_app.config['DROPBOX_REFRESH_TOKEN'],
            app_key=current_app.config['DROPBOX_APP_KEY'],
            app_secret=current_app.config['DROPBOX_APP_SECRET']
        )
    except KeyError as e:
        current_app.logger.error(f"❌ Configuração do Dropbox ausente: {e}")
        raise RuntimeError(f"Credencial do Dropbox não encontrada: {e}")

def normalizar(texto: str) -> str:
    """Remove acentos e caracteres especiais, convertendo para minúsculas."""
    if not isinstance(texto, str):
        texto = str(texto)
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()

def slug(texto: str) -> str:
    """Converte uma string para um formato 'slug' seguro para nomes de arquivo/pasta."""
    return normalizar(texto).replace(' ', '_').replace('-', '_')

def get_campaign_from_image_path(conn, imagem_path: str) -> dict | None:
    """Encontra os detalhes da campanha associada a um caminho de imagem."""
    # CORREÇÃO 1: Usando text() e marcador nomeado :path
    resultado = conn.execute(
        text("SELECT campanha_id FROM campanhas_imagens WHERE imagem_path = :path"), 
        {"path": imagem_path}
    ).fetchone()

    if not resultado:
        return None
    
    # CORREÇÃO 2: Usando text() e marcador nomeado :campanha_id
    campanha = conn.execute(
        text("SELECT id, cod, nome FROM campanhas WHERE id = :campanha_id"), 
        {"campanha_id": resultado[0]} # Acessa o índice 0 da tupla de resultado
    ).fetchone()
    
    # CORREÇÃO DE TIPAGEM: Converte o objeto Row para dicionário antes de retornar
    return dict(campanha._mapping) if campanha else None


# --- Rotas da API ---

@upload_bp.route('/foto', methods=['POST'])
def upload_foto():
    """Recebe arquivos de imagem e os associa a uma campanha existente."""
    campanha_cod = request.form.get('cod')
    campanha_nome = request.form.get('nome')
    arquivos = request.files.getlist('imagem')

    if not campanha_cod or not campanha_nome or not arquivos or all(not a.filename for a in arquivos):
        return jsonify(success=False, mensagem="O código, o nome da campanha e ao menos uma imagem são obrigatórios."), 400

    with get_db_connection() as conn:
        # CORREÇÃO 3: Usando text() e marcadores nomeados
        campanha_row = conn.execute(
            text("SELECT id, cod, nome FROM campanhas WHERE cod = :cod AND nome = :nome"), 
            {"cod": campanha_cod, "nome": campanha_nome}
        ).fetchone()
        
        if not campanha_row:
            return jsonify(success=False, mensagem="Campanha não encontrada."), 404
        
        # CORREÇÃO DE TIPAGEM: Usa o ._mapping para acessar os campos por nome
        campanha = dict(campanha_row._mapping)

        campanha_id = campanha['id'] # AGORA FUNCIONA
        slug_pasta = slug(campanha['nome'])
        dropbox = get_dropbox_service()
        salvos, erros = [], []

        for arq in arquivos:
            fn_seguro = secure_filename(arq.filename)
            try:
                _, ext = os.path.splitext(fn_seguro.lower())
                if ext not in EXTENSOES_VALIDAS:
                    erros.append(f"{fn_seguro}: Formato de arquivo inválido.")
                    continue

                nome_final = f"{slug(campanha['cod'])}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
                remote_path = f"/{slug_pasta}/{nome_final}"

                # ✅ CORREÇÃO: Lê o conteúdo do arquivo em bytes e o passa para o serviço.
                file_content = arq.read()
                dropbox.upload_file(file_content, remote_path)

                # CORREÇÃO 4: Usando text() e marcadores nomeados
                conn.execute(
                    text("INSERT INTO campanhas_imagens (campanha_id, imagem_path) VALUES (:campanha_id, :path)"),
                    {"campanha_id": campanha_id, "path": remote_path}
                )
                salvos.append(fn_seguro)
            except Exception as e:
                current_app.logger.error(f"Erro no upload do arquivo {fn_seguro}: {e}")
                erros.append(f"{fn_seguro}: Falha no processamento.")
        
        conn.commit()

    return jsonify({
        'success': len(salvos) > 0,
        'mensagem': f"{len(salvos)} de {len(arquivos)} imagem(ns) salvas com sucesso.",
        'arquivos_salvos': salvos,
        'arquivos_com_erro': erros
    })

@upload_bp.route('/deletar', methods=['POST'])
def deletar_imagem():
    """Move uma imagem para a lixeira (identificada apenas pelo path)."""
    imagem_path = request.form.get('imagem')
    if not imagem_path:
        return jsonify(success=False, mensagem="Caminho da imagem não informado."), 400

    try:
        dropbox = get_dropbox_service()
        nome_arquivo = os.path.basename(imagem_path)
        path_lixeira = f"{PASTA_LIXEIRA}/{nome_arquivo}"
        
        # Move no Dropbox primeiro
        dropbox.move_file(imagem_path, path_lixeira)

        # Atualiza o banco de dados
        with get_db_connection() as conn:
            # CORREÇÃO 5: Usando text() e marcadores nomeados
            cursor = conn.execute(
                text("UPDATE campanhas_imagens SET apagada = 1, imagem_path = :path_lixeira WHERE imagem_path = :path_original"),
                {"path_lixeira": path_lixeira, "path_original": imagem_path}
            )
            # Se a atualização falhar no DB, desfaz a ação no Dropbox
            if cursor.rowcount == 0:
                dropbox.move_file(path_lixeira, imagem_path) 
                return jsonify(success=False, mensagem="Erro: Imagem não encontrada no banco de dados."), 404
            conn.commit()
        
        return jsonify(success=True, mensagem="Imagem movida para a lixeira.")
    except Exception as e:
        current_app.logger.error(f"Falha ao mover para lixeira: {e}")
        return jsonify(success=False, mensagem="Erro ao processar a exclusão."), 500

@upload_bp.route('/restaurar', methods=['POST'])
def restaurar_imagem():
    """Restaura uma imagem da lixeira (identificada apenas pelo path)."""
    imagem_path_lixeira = request.form.get('imagem')
    if not imagem_path_lixeira:
        return jsonify(success=False, mensagem="Caminho da imagem não informado."), 400
    
    try:
        with get_db_connection() as conn:
            # Usa a função auxiliar corrigida (get_campaign_from_image_path)
            campanha = get_campaign_from_image_path(conn, imagem_path_lixeira)
            if not campanha:
                return jsonify(success=False, mensagem="Campanha associada à imagem não encontrada."), 404

            dropbox = get_dropbox_service()
            nome_arquivo = os.path.basename(imagem_path_lixeira)
            path_original = f"/{slug(campanha['nome'])}/{nome_arquivo}"
            
            dropbox.move_file(imagem_path_lixeira, path_original)
            
            # CORREÇÃO 6: Usando text() e marcadores nomeados
            cursor = conn.execute(
                text("UPDATE campanhas_imagens SET apagada = 0, imagem_path = :path_original WHERE imagem_path = :path_lixeira"),
                {"path_original": path_original, "path_lixeira": imagem_path_lixeira}
            )
            if cursor.rowcount == 0:
                dropbox.move_file(path_original, imagem_path_lixeira)
                return jsonify(success=False, mensagem="Erro: Imagem não encontrada na lixeira do banco."), 404
            conn.commit()

        return jsonify(success=True, mensagem="Imagem restaurada com sucesso.")
    except Exception as e:
        current_app.logger.error(f"Falha ao restaurar imagem: {e}")
        return jsonify(success=False, mensagem="Erro ao restaurar imagem."), 500

@upload_bp.route('/excluir_definitivo', methods=['POST'])
def excluir_definitivo():
    """Exclui permanentemente uma imagem (identificada apenas pelo path)."""
    imagem_path = request.form.get('imagem')
    if not imagem_path:
        return jsonify(success=False, mensagem="Caminho da imagem não informado."), 400

    try:
        dropbox = get_dropbox_service()
        # ✅ CORREÇÃO: Primeiro, tenta excluir o arquivo do Dropbox
        dropbox.delete_file(imagem_path)

        # ✅ AJUSTE: Se a exclusão no Dropbox for bem-sucedida, remove do banco de dados
        with get_db_connection() as conn:
            # CORREÇÃO 7: Usando text() e marcador nomeado
            cursor = conn.execute(text("DELETE FROM campanhas_imagens WHERE imagem_path = :path"), {"path": imagem_path})
            if cursor.rowcount == 0:
                # Se não encontrar no banco, mas já excluiu no Dropbox, isso é uma falha
                # de consistência, mas o arquivo já foi excluído. Retornamos sucesso.
                return jsonify(success=False, mensagem="Imagem não encontrada no banco de dados, mas removida com sucesso do Dropbox."), 404
            conn.commit()

        return jsonify(success=True, mensagem="Imagem excluída permanentemente.")
    except dropbox.exceptions.ApiError as e:
        # Se o arquivo não existe no Dropbox, podemos assumir que já foi excluído.
        if "path/not_found/" in str(e):
             with get_db_connection() as conn:
                 # CORREÇÃO 8: Usando text() e marcador nomeado
                 cursor = conn.execute(text("DELETE FROM campanhas_imagens WHERE imagem_path = :path"), {"path": imagem_path})
                 conn.commit()
             return jsonify(success=True, mensagem="Imagem já havia sido excluída do Dropbox. Registro removido do banco."), 200
        current_app.logger.error(f"Falha na exclusão definitiva do Dropbox: {e}")
        return jsonify(success=False, mensagem="Erro na exclusão do arquivo no Dropbox."), 500
    except Exception as e:
        current_app.logger.error(f"Falha na exclusão definitiva: {e}")
        return jsonify(success=False, mensagem="Erro na exclusão definitiva da imagem."), 500

# --- Rotas de Listagem para o Frontend ---

def get_shared_links_otimizado(paths):
    """
    Busca ou cria links compartilhados de forma otimizada e paralela para uma lista de caminhos.
    """
    if not paths:
        return {}
    
    dropbox = get_dropbox_service()

    def create_or_get_link(path):
        """Tenta criar um link. Se já existir, busca o link existente."""
        try:
            # A função create_shared_link é inteligente: se um link já existe, ela geralmente o retorna.
            return path.lower(), dropbox.create_shared_link(path)
        except dropbox.exceptions.ApiError as e:
            # Se o erro for 'shared_link_already_exists', significa que o link já foi criado.
            # Nesse caso, precisamos buscá-lo.
            if 'shared_link_already_exists' in str(e):
                try:
                    links = dropbox.dbx.sharing_list_shared_links(path=path, direct_only=True).links
                    if links:
                        return path.lower(), links[0].url
                except Exception as e_inner:
                    current_app.logger.error(f"Falha ao buscar link já existente para {path}: {e_inner}")
            
            # Para qualquer outro erro, registramos e retornamos um link de fallback.
            current_app.logger.warning(f"Não foi possível criar/obter link para {path}: {e}")
            return path.lower(), "#"

    # Usa um ThreadPool para executar todas as chamadas 'create_or_get_link' em paralelo
    urls = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Mapeia todas as paths para a função e executa em threads separadas
        results = dict(list(executor.map(create_or_get_link, paths)))
    
    urls.update(results)
    return urls

# <<< VERSÃO CORRIGIDA DA ROTA /imagens >>>
# Em app/routes/upload.py

@upload_bp.route('/imagens', methods=['GET'])
@login_required
def imagens_ativas():
    """Retorna a lista de imagens ativas de uma campanha de forma otimizada."""
    nome_campanha = request.args.get('campanha_nome')
    if not nome_campanha:
        return jsonify(success=False, mensagem="Nome da campanha inválido."), 400

    try:
        with get_db_connection() as conn:
            # CORREÇÃO 9: Usando text() e marcador nomeado :nome
            # Subquery aninhada para obter o ID da campanha
            resultados = conn.execute(text("""
                SELECT id, imagem_path FROM campanhas_imagens
                WHERE apagada = 0 
                AND campanha_id IN (SELECT id FROM campanhas WHERE nome = :nome)
            """), {"nome": nome_campanha}).fetchall()

        # Usa a função otimizada para buscar todos os links de uma vez
        paths = [img['imagem_path'] for img in resultados]
        urls_map = get_shared_links_otimizado([p[0] for p in paths]) # Converte para lista de paths
        
        # CORREÇÃO DE TIPAGEM: Usa o ._mapping para construir a lista final
        imagens = [
            {'id': img._mapping['id'], 'path': img._mapping['imagem_path'], 'url': urls_map.get(img._mapping['imagem_path'].lower(), "#")} 
            for img in resultados
        ]
        return jsonify(success=True, imagens=imagens)
    except Exception as e:
        current_app.logger.error(f"Falha ao gerar links para imagens ativas: {e}")
        return jsonify(success=False, mensagem="Erro ao gerar links para as imagens."), 500


# <<< VERSÃO CORRIGIDA DA ROTA /imagens_lixeira >>>
@upload_bp.route('/imagens_lixeira', methods=['GET'])
@login_required
def imagens_lixeira():
    """Retorna a lista de imagens na lixeira de forma otimizada."""
    nome_campanha = request.args.get('campanha_nome')
    if not nome_campanha:
        return jsonify(success=False, mensagem="Nome da campanha inválido."), 400

    try:
        with get_db_connection() as conn:
            # CORREÇÃO 10: Usando text() e marcador nomeado :nome
            resultados = conn.execute(text("""
                SELECT id, imagem_path FROM campanhas_imagens
                WHERE apagada = 1 
                AND campanha_id IN (SELECT id FROM campanhas WHERE nome = :nome)
            """), {"nome": nome_campanha}).fetchall()

        paths = [img['imagem_path'] for img in resultados]
        urls_map = get_shared_links_otimizado([p[0] for p in paths]) # Converte para lista de paths
        
        # CORREÇÃO DE TIPAGEM: Usa o ._mapping para construir a lista final
        imagens = [
            {'id': img._mapping['id'], 'path': img._mapping['imagem_path'], 'url': urls_map.get(img._mapping['imagem_path'].lower(), "#")} 
            for img in resultados
        ]
        return jsonify(success=True, imagens=imagens)
    except Exception as e:
        current_app.logger.error(f"Falha ao gerar links para imagens da lixeira: {e}")
        return jsonify(success=False, mensagem="Erro ao gerar links da lixeira."), 500

# --- Página de Upload Público ---
@upload_bp.route('/<int:campanha_id>', methods=['GET'])
def upload_page(campanha_id):
    # (Sua função original mantida)
    with get_db_connection() as conn:
        # CORREÇÃO 11: Usando text() e marcador nomeado
        campanha_row = conn.execute(text("SELECT id, nome FROM campanhas WHERE id = :id"), {"id": campanha_id}).fetchone()
    if campanha_row:
        # CORREÇÃO DE TIPAGEM: Converte o objeto Row para dicionário
        return render_template('upload_publico.html', campanha=dict(campanha_row._mapping))
    return "Campanha não encontrada", 404
