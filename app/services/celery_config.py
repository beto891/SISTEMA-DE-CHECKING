from celery import Celery
import os

# 1. Obtém a URL e garante que use 'rediss://' para SSL (essencial para Upstash)
REDIS_URL = os.environ.get('REDIS_URL', 
                           'rediss://default:ARepAAImcDI0MjJkODYwYTE2ZDM0MTM3YTIwYjFiZmM4Yzg5YTMyNnAyNjA1Nw@welcome-sheepdog-6057.upstash.io:6379')

# 2. Configuração de SSL para evitar erros de validação no Render/Upstash
ssl_options = {
    'ssl_cert_reqs': 'none'  # Permite conectar sem validar a cadeia de certificados (padrão p/ Upstash)
}

celery_app = Celery(
    'checking-redis',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# 3. Configurações adicionais robustas
celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    # Chaves para resolver o problema de SSL:
    broker_use_ssl=ssl_options if REDIS_URL.startswith('rediss') else None,
    redis_backend_use_ssl=ssl_options if REDIS_URL.startswith('rediss') else None,
    # Otimização para o Render (evita que o worker fique preso)
    worker_prefetch_multiplier=1,
    worker_concurrency=1
)

# 

class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        # O self.app é injetado pelo init_celery abaixo
        with self.app.app_context():
            return self.run(*args, **kwargs)

def init_celery(app):
    """Vincula a instância do Flask ao Celery sem importação circular"""
    celery_app.app = app
    celery_app.Task = ContextTask
    # Mescla as configurações do Flask (como DB_URL) no Celery
    celery_app.conf.update(app.config)