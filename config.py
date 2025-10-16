import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')

# Token do Dropbox
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN')