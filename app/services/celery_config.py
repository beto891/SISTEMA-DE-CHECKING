import os
import re
from celery import Celery

# 1. Limpeza rigorosa da URL (remove espaços ou quebras de linha acidentais)
raw_url = os.environ.get('REDIS_URL', '').strip()

# Fallback para caso a variável esteja vazia ou mal formatada
if not raw_url.startswith('rediss://'):
    raw_url = 'rediss://default:ARepAAImcDI0MjJkODYwYTE2ZDM0MTM3YTIwYjFiZmM4Yzg5YTMyNnAyNjA1Nw@welcome-sheepdog-6057.upstash.io:6379'

REDIS_URL = raw_url

ssl_options = {
    'ssl_cert_reqs': 'none'
}

celery_app = Celery(
    'checking-redis',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['app.utils.pdf_generator']
)

celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_use_ssl=ssl_options,
    redis_backend_use_ssl=ssl_options,
    #CONFIGURAÇÃO ANTIFALHA DE DNS:
    broker_transport_options={
        'max_retries': 10,
        'interval_start': 0.5,
        'interval_step': 1,
        'interval_max': 5,
        'socket_timeout': 30,
        'socket_connect_timeout': 30,
    }
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