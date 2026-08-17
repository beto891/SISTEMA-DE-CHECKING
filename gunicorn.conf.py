import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv('GUNICORN_WORKERS', '2'))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'eventlet')
threads = int(os.getenv('GUNICORN_THREADS', '1'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))
accesslog = '-' if os.getenv('GUNICORN_ACCESS_LOG', '1') == '1' else None
errorlog = '-' if os.getenv('GUNICORN_ERROR_LOG', '1') == '1' else None
preload_app = False
