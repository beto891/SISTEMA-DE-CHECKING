import os
from celery import Celery

# 1. REMOVA a linha "from app import create_app" do topo!

raw_url = os.environ.get('REDIS_URL', '').strip()
if not raw_url.startswith('rediss://'):
    raw_url = 'rediss://default:ARepAAImcDI0MjJkODYwYTE2ZDM0MTM3YTIwYjFiZmM4Yzg5YTMyNnAyNjA1Nw@welcome-sheepdog-6057.upstash.io:6379'

REDIS_URL = raw_url
ssl_options = {'ssl_cert_reqs': 'none'}

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
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_transport_options={
        'max_retries': 10,
        'interval_start': 0.5,
        'interval_step': 1,
        'interval_max': 5,
        'socket_timeout': 30,
        'socket_connect_timeout': 30,
    }
)

class ContextTask(celery_app.Task):
    _flask_app = None  # Variável de classe para persistência

    def __call__(self, *args, **kwargs):
        # Usamos a referência da CLASSE (ContextTask) em vez de 'self'
        if ContextTask._flask_app is None:
            from app import create_app
            print("🚀 Worker: Iniciando criação da instância Flask...")
            temp_app = create_app()
            
            if temp_app is None:
                raise RuntimeError("ERRO CRÍTICO: create_app() retornou None!")
            
            ContextTask._flask_app = temp_app

        # Agora garantimos que o contexto é aberto no objeto Flask real
        with ContextTask._flask_app.app_context():
            return self.run(*args, **kwargs)

# Aplica a classe ao app do Celery
celery_app.Task = ContextTask

def init_celery(app):
    """Vincula o app do Flask ao Celery"""
    celery_app.app = app
    celery_app.conf.update(app.config)