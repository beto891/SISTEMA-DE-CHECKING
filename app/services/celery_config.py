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
    _flask_app = None

    def __call__(self, *args, **kwargs):
        # Usamos a referência da CLASSE (ContextTask) para garantir o Singleton
        if ContextTask._flask_app is None:
            from app import create_app
            print("🚀 Worker criando instância do Flask...")
            ContextTask._flask_app = create_app()

        # Verificação de segurança: Se create_app() não retornou nada, gera erro explicativo
        if ContextTask._flask_app is None:
            raise RuntimeError(
                "Falha crítica: a função create_app() retornou None. "
                "Verifique se existe 'return app' no final do seu app/__init__.py"
            )
        
        # Agora o contexto funcionará pois garantimos que _flask_app não é None
        with ContextTask._flask_app.app_context():
            return self.run(*args, **kwargs)

# Aplica a classe ao Celery
celery_app.Task = ContextTask

def init_celery(app):
    celery_app.app = app
    celery_app.conf.update(app.config)