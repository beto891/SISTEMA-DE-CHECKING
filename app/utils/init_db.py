from app.utils.database import inicializar_banco

if __name__ == "__main__":
    print("🔧 Inicializando banco de dados...")
    inicializar_banco()
    print("✅ Banco de dados pronto para uso.")
    
    
#python -m app.utils.init_db