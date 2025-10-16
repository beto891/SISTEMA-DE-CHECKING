import os
import logging
import requests
import dropbox
from dropbox.sharing import RequestedVisibility, SharedLinkSettings

logger = logging.getLogger(__name__)

def renovar_access_token(refresh_token, app_key, app_secret):
    """Renova o access token usando o refresh token."""
    url = "https://api.dropbox.com/oauth2/token"
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": app_key,
        "client_secret": app_secret
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        novo_token = response.json()["access_token"]
        logger.info("🔄 Access token renovado com sucesso.")
        return novo_token
    except requests.RequestException as e:
        logger.error(f"❌ Erro HTTP ao renovar token: {e.response.text if e.response else str(e)}")
        raise RuntimeError("Erro ao renovar token do Dropbox")
    except Exception as e:
        logger.exception("❌ Falha inesperada ao renovar access token.")
        raise RuntimeError("Erro ao renovar token do Dropbox")

class DropboxService:
    def __init__(self, refresh_token=None, app_key=None, app_secret=None):
        refresh_token = refresh_token or os.getenv("DROPBOX_REFRESH_TOKEN")
        app_key = app_key or os.getenv("DROPBOX_APP_KEY")
        app_secret = app_secret or os.getenv("DROPBOX_APP_SECRET")

        if not all([refresh_token, app_key, app_secret]):
            raise RuntimeError("Credenciais do Dropbox ausentes.")

        access_token = renovar_access_token(refresh_token, app_key, app_secret)
        self.dbx = dropbox.Dropbox(access_token)

        try:
            # ✅ AJUSTE: Força a validação da autenticação ao inicializar a classe
            self.dbx.users_get_current_account()
            logger.info("🔐 Conexão com Dropbox estabelecida com sucesso.")
        except dropbox.exceptions.AuthError as e:
            logger.error(f"❌ Erro de autenticação: {e}")
            raise RuntimeError("Erro de autenticação com Dropbox")
        except Exception as e:
            logger.exception("❌ Falha ao validar conexão com Dropbox.")
            raise RuntimeError("Erro de autenticação com Dropbox")

    def upload_file(self, file_content, dropbox_path):
        """Faz upload de um arquivo para o Dropbox a partir de um stream.
        Recebe o conteúdo do arquivo já lido (em bytes)."""
        try:
            # ✅ CORREÇÃO: Passa o conteúdo do arquivo (em bytes) diretamente
            # O método .read() já foi chamado na rota que enviou o arquivo
            self.dbx.files_upload(
                file_content,
                dropbox_path,
                mode=dropbox.files.WriteMode.overwrite
            )
            logger.info(f"✅ Upload concluído: {dropbox_path}")
            return True, self.create_shared_link(dropbox_path)
        except Exception as e:
            logger.exception("❌ Erro durante upload para Dropbox")
            raise RuntimeError("Erro interno ao enviar arquivo para Dropbox")

    def create_shared_link(self, dropbox_path):
        """Gera um link público direto para o arquivo no Dropbox."""
        try:
            links = self.dbx.sharing_list_shared_links(path=dropbox_path, direct_only=True).links
            if links:
                url = links[0].url
            else:
                settings = SharedLinkSettings(requested_visibility=RequestedVisibility.public)
                link_metadata = self.dbx.sharing_create_shared_link_with_settings(dropbox_path, settings)
                url = link_metadata.url

            if "dropbox.com" in url:
                url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
            elif "dl.dropbox.com" in url:
                url = url.split("?")[0]

            return url

        except dropbox.exceptions.ApiError as e:
            logger.error(f"❌ Erro ao gerar ou recuperar link público: {e}")
            return None
        except Exception as e:
            logger.exception("❌ Falha inesperada ao gerar link público.")
            return None

    def download_file(self, dropbox_path, local_path):
        """Faz download de um arquivo do Dropbox para o disco local."""
        try:
            metadata, res = self.dbx.files_download(dropbox_path)
            with open(local_path, 'wb') as f:
                f.write(res.content)
            logger.info(f"📥 Download concluído: {dropbox_path} → {local_path}")
        except Exception as e:
            logger.exception("❌ Erro ao baixar arquivo do Dropbox")
            raise RuntimeError("Erro ao baixar arquivo")

    def delete_file(self, dropbox_path):
        """Exclui um arquivo do Dropbox."""
        try:
            self.dbx.files_delete_v2(dropbox_path)
            logger.info(f"🗑️ Arquivo excluído: {dropbox_path}")
        except dropbox.exceptions.ApiError as e:
            if "path/not_found" in str(e):
                logger.warning(f"O arquivo {dropbox_path} já não existe no Dropbox.")
                return
            logger.exception("❌ Erro ao excluir arquivo do Dropbox")
            raise RuntimeError("Erro ao excluir arquivo")
        except Exception as e:
            logger.exception("❌ Erro ao excluir arquivo do Dropbox")
            raise RuntimeError("Erro ao excluir arquivo")

    def move_file(self, origem, destino):
        """Move um arquivo dentro do Dropbox."""
        try:
            self.dbx.files_move_v2(from_path=origem, to_path=destino, autorename=True)
            logger.info(f"📂 Arquivo movido: {origem} → {destino}")
        except dropbox.exceptions.ApiError as e:
             if "path/not_found" in str(e):
                logger.warning(f"O arquivo {origem} não foi encontrado para ser movido.")
                return
             logger.exception(f"❌ Erro ao mover arquivo de {origem} para {destino}")
             raise RuntimeError("Erro ao mover arquivo no Dropbox")
        except Exception as e:
            logger.exception(f"❌ Erro ao mover arquivo de {origem} para {destino}")
            raise RuntimeError("Erro ao mover arquivo no Dropbox")

    def file_exists(self, dropbox_path):
        """Verifica se um arquivo existe no Dropbox."""
        try:
            self.dbx.files_get_metadata(dropbox_path)
            return True
        except dropbox.exceptions.ApiError as e:
            if isinstance(e.error, dropbox.files.GetMetadataError) and e.error.is_path() and e.error.get_path().is_not_found():
                return False
            raise
        except Exception as e:
            logger.exception("❌ Falha ao verificar existência do arquivo.")
            return False