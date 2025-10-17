from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from sqlalchemy import text, create_engine, event
from flask import current_app
import os
import sys

# IMPORTANTE: Se 'db' for importado globalmente (ex: de app.models), 
# as referências abaixo a 'db' serão resolvidas.
# Vamos assumir que 'db' é importado no módulo principal (app/__init__.py)

def get_db_connection():
    """Retorna uma conexão bruta (DBAPI-style) do SQLAlchemy Engine."""
    # O objeto db precisa ser importado aqui para acessar o engine
    from app import db # Importa o objeto db do seu módulo principal
    return db.engine.connect()

def executar_migracao_coluna(conn, table_name, column_name, column_definition):
    """Executa um ALTER TABLE de forma segura, ignorando erros se a coluna já existir."""
    try:
        # Tenta verificar se a coluna já existe no PostgreSQL
        conn.execute(text(f"SELECT {column_name} FROM {table_name} LIMIT 1"))
        print(f"🛠️ Coluna '{column_name}' em '{table_name}' já existe.")
        return False
    except Exception as e:
        # Se falhar, tenta executar o ALTER TABLE
        if "undefined column" in str(e).lower() or "column does not exist" in str(e).lower():
            # Cria um novo bloco de transação isolado para o ALTER TABLE
            # Nota: ALTER TABLE é um DDL, e precisa ser feito com cuidado.
            try:
                print(f"🛠️ Tentando adicionar coluna '{column_name}' em '{table_name}'...")
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
                conn.commit()
                print(f"🛠️ Coluna '{column_name}' adicionada com sucesso em '{table_name}'.")
                return True
            except Exception as e_alter:
                # Se o ALTER TABLE falhar por algum motivo (ex: a coluna já existia e o SELECT deu falso positivo)
                conn.rollback() # Limpa o estado da transação
                print(f"❌ Falha ao adicionar coluna '{column_name}' (provavelmente já existe): {e_alter}")
                return False
        else:
            # Outro erro (Ex: tabela inexistente). Lança o erro.
            raise e

def inicializar_banco(app):
    """Cria as tabelas e o usuário admin padrão, adaptado para SQLAlchemy Engine."""
    from app import db # Importa o objeto db
    
    with app.app_context():
        # --- PASSO 1: CRIAÇÃO DO ESQUEMA VIA ORM (Tabelas Base) ---
        try:
            db.create_all()
            print("✅ Tabelas definidas nos modelos criadas com sucesso!")
        except Exception as e:
            print(f"⚠️ Aviso: Falha ao executar db.create_all(). Pode ser que o esquema já exista: {e}")
            pass
        
        # --- PASSO 2: CRIAÇÃO DE TABELAS MANUAIS (Sem ORM) ---
        conn = get_db_connection()
        try:
            # Tabela localizacoes_usuarios (NOVA E MANUAL)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS localizacoes_usuarios (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    timestamp TEXT
                )
            """))
            # Tabela imagens_excluidas (NOVA E MANUAL)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS imagens_excluidas (
                    id SERIAL PRIMARY KEY,
                    cod TEXT NOT NULL,
                    campanha TEXT NOT NULL,
                    imagem_path TEXT NOT NULL,
                    excluido_por TEXT NOT NULL,
                    data_exclusao TEXT NOT NULL
                )
            """))

            # --- PASSO 3: MIGRAÇÕES DE COLUNA (ALTER TABLE) ---
            # O ALTER TABLE é executado dentro de um bloco try/except isolado
            # usando a função auxiliar para evitar o erro InFailedSqlTransaction.
            executar_migracao_coluna(conn, 'campanhas_imagens', 'apagada', 'INTEGER DEFAULT 0')
            executar_migracao_coluna(conn, 'usuarios', 'is_admin', 'INTEGER DEFAULT 0')
            # Também forçamos a criação de latitude/longitude na tabela campanhas, se necessário
            executar_migracao_coluna(conn, 'campanhas', 'latitude', 'REAL')
            executar_migracao_coluna(conn, 'campanhas', 'longitude', 'REAL')

            # --- PASSO 4: CRIAÇÃO DE USUÁRIO ADMIN PADRÃO ---
            # Esta parte deve estar em uma transação limpa
            user_exists = conn.execute(
                text("SELECT id FROM usuarios WHERE username = :username"), 
                {"username": "admin"}
            ).fetchone()

            if not user_exists:
                conn.execute(
                    text("INSERT INTO usuarios (username, senha, is_admin) VALUES (:user, :senha, :admin)"),
                    {"user": "admin", "senha": generate_password_hash("beto891"), "admin": 1}
                )
                print("👤 Usuário admin criado com senha padrão.")
            
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"❌ Erro grave na inicialização de dados: {e}")
            # print(f"❌ Traceback: {sys.exc_info()[2]}") # Descomentar para debug detalhado
            
        finally:
            conn.close()
        
        print("✅ Banco de dados inicializado com sucesso!")


# Funções utilitárias

def buscar_usuario(username):
    """Busca um usuário pelo nome."""
    # NOTA: O ORM do Flask-Login (User.query.get()) é a melhor prática,
    # mas mantendo a lógica de conexão bruta:
    conn = get_db_connection()
    try:
        # CORREÇÃO 3: Usando text() e parâmetro nomeado
        user = conn.execute(
            text("SELECT * FROM usuarios WHERE username = :username"), 
            {"username": username}
        ).fetchone()
        return user
    except Exception as e:
        # Usa current_app.logger.error para registro (se estiver no contexto da aplicação)
        try:
            current_app.logger.error(f"Erro ao buscar usuário: {e}")
        except RuntimeError:
            print(f"Erro ao buscar usuário (fora de contexto): {e}")
        return None
    finally:
        conn.close()

def criar_usuario(username, senha, is_admin=0):
    """Cria um novo usuário com senha criptografada."""
    conn = get_db_connection()
    try:
        # CORREÇÃO 4: Usando text() e parâmetro nomeado
        conn.execute(
            text("INSERT INTO usuarios (username, senha, is_admin) VALUES (:user, :senha, :admin)"),
            {"user": username, "senha": generate_password_hash(senha), "admin": is_admin}
        )
        conn.commit()
        return True
    except Exception as e:
        print("❌ Erro ao criar usuário:", e)
        return False
    finally:
        conn.close()
