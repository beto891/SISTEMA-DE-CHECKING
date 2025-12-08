import subprocess
import time

# 1. Inicia o Celery Worker
worker_command = "celery -A service.celery_config worker -l INFO --purge -Q celery"
process = subprocess.Popen(worker_command, shell=True)

# 2. Espera um tempo suficiente para esvaziar a fila (ex: 3 minutos)
time.sleep(180) 

# 3. Força o encerramento do processo após o tempo
process.terminate()