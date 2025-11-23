import os
import json
import logging

# Configuração de Log
logger = logging.getLogger(__name__)

# Tenta importar a biblioteca específica do Upstash
try:
    from upstash_redis import Redis
except ImportError:
    logger.critical("❌ A biblioteca 'upstash-redis' não está instalada! O cache será desativado.")
    Redis = None

class CacheService:
    """
    Gerencia o cache usando a API REST do Upstash (HTTP).
    Isso evita problemas de conexão TCP/SSL comuns em ambientes serverless.
    """

    def __init__(self):
        if Redis is None:
            self.redis_client = None
            return

        # Busca as credenciais REST (HTTPS)
        url = os.getenv("UPSTASH_REDIS_REST_URL")
        token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        # Fallback: Tenta ler da REDIS_URL antiga se as novas não existirem (apenas se for formato http)
        if not url and os.getenv("REDIS_URL", "").startswith("http"):
             url = os.getenv("REDIS_URL")

        if not url or not token:
            logger.warning("⚠️ Credenciais UPSTASH (URL/TOKEN) não configuradas. Cache desativado.")
            self.redis_client = None
            return

        try:
            # Conexão via HTTP (não precisa de handshake SSL complexo)
            self.redis_client = Redis(url=url, token=token)
            
            # Teste simples (ping retorna "PONG" string no upstash-redis, ou True)
            # O upstash-redis geralmente não lança erro na instanciação, só no uso.
            logger.info("✅ Cliente Redis (HTTP/Upstash) configurado.")
        except Exception as e:
            logger.error(f"❌ Erro ao configurar cliente Redis: {e}")
            self.redis_client = None

    def get(self, key):
        """Busca um valor no cache."""
        if self.redis_client is None:
            return None
        
        try:
            data = self.redis_client.get(key)
            # O upstash-redis já pode retornar dict se foi salvo como JSON, 
            # mas por garantia, tratamos strings JSON.
            if data and isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data # Retorna a string pura se não for JSON
            return data
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar chave {key}: {e}")
            return None

    def set(self, key, value, ttl=3600):
        """Salva valor no cache."""
        if self.redis_client is None:
            return False
            
        try:
            # O upstash-redis serializa dicts automaticamente, mas 
            # usar json.dumps garante controle sobre o formato.
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            # ex=ttl define a expiração em segundos
            self.redis_client.set(key, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar chave {key}: {e}")
            return False

# Cria uma instância para uso nas rotas
cache_service = CacheService()