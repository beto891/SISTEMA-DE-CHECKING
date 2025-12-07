from celery import Celery
import os
from app import app as flask_app
# Configuração do Celery

REDIS_URL = os.environ.get('REDIS_URL', 
                           'rediss://default:ARepAAImcDI0MjJkODYwYTE2ZDM0MTM3YTIwYjFiZmM4Yzg5YTMyNnAyNjA1Nw@welcome-sheepdog-6057.upstash.io:6379') 

celery_app = Celery(
    'checking-redis',
    broker=REDIS_URL,
    backend=REDIS_URL  
)

# Configurações adicionais
celery_app.conf.update(
    task_track_started=True,
    broker_connection_retry_on_startup=True
)

class ContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        # AQUI USAMOS A INSTÂNCIA DO FLASK QUE FOI IMPORTADA GLOBALMENTE
        with flask_app.app_context():
            return self.run(*args, **kwargs)

# versão simplificada:
def init_celery(app):
    celery_app.Task = ContextTask
    celery_app.conf.update(app.config)