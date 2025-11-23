import os
import json
import logging
import redis

# Configuração de Log
logger = logging.getLogger(__name__)

# 1. Tenta importar o Redis de forma segura
# Se a biblioteca não estiver no requirements.txt, o app não quebra, apenas desativa o cache.
try:
    import redis
except ImportError:
    logger.critical("❌ A biblioteca 'redis' não está instalada! O cache será desativado.")
    redis = None

class CacheService:
    """
    Gerencia a conexão e as operações de cache com o Upstash Redis.
    Se a conexão falhar, ele falha silenciosamente para não derrubar a aplicação.
    """

    def __init__(self):
        # Se a biblioteca não foi importada corretamente, aborta a inicialização do cliente
        if redis is None:
            self.redis_client = None
            return

        # Conecta usando a variável de ambiente REDIS_URL do Render/Upstash
        redis_url = os.getenv("REDIS_URL")
        
        if not redis_url:
            logger.warning("⚠️ REDIS_URL não configurada. O cache está desativado.")
            self.redis_client = None
            return

        try:
            # 2. Configuração de conexão robusta para Upstash
            # decode_responses=True: Já recebe strings ao invés de bytes
            # ssl_cert_reqs="none": Essencial para evitar erros de certificado SSL no Upstash
            self.redis_client = redis.from_url(
                redis_url, 
                decode_responses=True, 
            )
            
            # Teste rápido de conexão (Ping)
            if self.redis_client.ping():
                logger.info("✅ Conexão com Redis (Upstash) estabelecida com sucesso.")
        except Exception as e:
            logger.error(f"❌ Falha ao conectar ao Redis: {e}")
            self.redis_client = None

    def get(self, key):
        """Busca um valor no cache e o desserializa."""
        if self.redis_client is None:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            # Em caso de erro de deserialização ou leitura, limpamos a chave e retornamos None
            logger.warning(f"Erro ao buscar/desserializar chave {key} no Redis.")
            try:
                self.redis_client.delete(key)
            except:
                pass
            return None

    def set(self, key, value, ttl=3600):
        """Armazena um valor serializado no cache com tempo de expiração (TTL)."""
        if self.redis_client is None:
            return False
            
        try:
            serialized_value = json.dumps(value)
            # setex define o valor com expiração em segundos
            self.redis_client.set(key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar chave {key} no Redis: {e}")
            return False

# Cria uma instância para uso nas rotas
cache_service = CacheService()