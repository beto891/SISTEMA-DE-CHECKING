import os
from dotenv import load_dotenv
from pcloud_sdk import PCloudSDK

# 🔄 Carrega variáveis do .env
load_dotenv()

email        = os.getenv("PCLOUD_EMAIL")
senha        = os.getenv("PCLOUD_SENHA")
location_id  = int(os.getenv("PCLOUD_LOCATION_ID", 1))  # default para US

# ✅ Inicializa SDK
sdk = None

def get_sdk():
    global sdk  # garante acesso à variável fora da função
    if not sdk or not hasattr(sdk, 'file'):
        raise Exception("SDK não está inicializado corretamente.")
    return sdk

try:
    sdk = PCloudSDK()
    login_result = sdk.login(email, senha, location_id=location_id)

    print("[DEBUG] Resultado do login:", login_result)
    
    if not login_result or not login_result.get('access_token'):
        raise Exception("Login falhou: access_token ausente.")

    print(f"✅ Login pCloud bem-sucedido para {email} (location_id={location_id})")

except Exception as e:
    print(f"🚫 Erro ao autenticar no pCloud: {str(e)}")
    sdk = None  # Evita uso posterior se falhar
    
access_token = login_result['access_token']