# Em app/utils.py (VERSÃO CORRIGIDA)

import unicodedata
from flask import current_app
from sqlalchemy import text
from .services.dropbox_service import DropboxService # Ajuste o caminho se necessário

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
    # A função 'normalizar' já está disponível aqui, não precisa importar.
    return normalizar(texto).replace(' ', '_').replace('-', '_')

def get_campaign_from_image_path(conn, imagem_path: str) -> dict | None:
    """Encontra os detalhes da campanha associada a um caminho de imagem."""
    resultado = conn.execute(
        text("SELECT campanha_id FROM campanhas_imagens WHERE imagem_path = :path"), 
        {"path": imagem_path}
    ).fetchone()

    if not resultado:
        return None
    
    campanha = conn.execute(
        text("SELECT id, cod, nome FROM campanhas WHERE id = :campanha_id"), 
        {"campanha_id": resultado[0]}
    ).fetchone()
    
    return dict(campanha._mapping) if campanha else None