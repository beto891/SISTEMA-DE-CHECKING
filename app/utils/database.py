from werkzeug.security import generate_password_hash
from sqlalchemy import text
from flask import current_app
from sqlalchemy.exc import ProgrammingError, OperationalError
import sys
import os

# NOTA: Assumimos que o objeto 'db' do Flask-SQLAlchemy está importado no módulo 'app'
# e que os modelos (User, Campanhas, etc.) foram definidos em outro local.

def get_db_connection():
    """Retorna uma conexão bruta (DBAPI-style) do SQLAlchemy Engine."""
    # O objeto db precisa ser importado aqui para acessar o engine
    from app import db # Importa o objeto db do seu módulo principal
    return db.engine.connect()

def inicializar_banco(app):
    """Cria as tabelas e o usuário admin padrão, adaptado para SQLAlchemy Engine."""
    from app import db # Importa o objeto db
    
    with app.app_context():
        conn = get_db_connection()
        
        # --- PASSO 1: CRIAÇÃO DO ESQUEMA VIA ORM (Tabelas Base) ---
        try:
            db.create_all()
            print("✅ Tabelas definidas nos modelos criadas com sucesso!")
        except Exception as e:
            # Em ambientes de produção (PostgreSQL), create_all pode falhar se já existir.
            print(f"⚠️ Aviso: Falha ao executar db.create_all(). Pode ser que o esquema já exista: {e}")
            pass
        
        # --- PASSO 2: CRIAÇÃO DE TABELAS MANUAIS (localizacoes_usuarios e imagens_excluidas) ---
        # Estas tabelas precisam de comandos CREATE explícitos.
        try:
            # Tabela localizacoes_usuarios (SOLUÇÃO UndefinedTable)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS localizacoes_usuarios (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    timestamp TEXT
                )
            """))
            # Tabela imagens_excluidas
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
            conn.commit() # Comita a criação das tabelas manuais imediatamente
            print("✅ Tabelas manuais 'localizacoes_usuarios' e 'imagens_excluidas' criadas.")
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro ao criar tabelas manuais: {e}")
            pass


        # --- PASSO 3: MIGRAÇÕES DE COLUNA (ALTER TABLE) ---
        # Adiciona colunas que podem ter sido omitidas em migrações anteriores ou no ORM
        
        def safe_alter_table(conn, table_name, column_name, column_definition):
            """Executa ALTER TABLE de forma segura no PostgreSQL, ignorando se a coluna já existir."""
            try:
                # Tenta adicionar a coluna
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"))
                conn.commit()
                print(f"🛠️ Coluna '{column_name}' adicionada em '{table_name}'.")
                return True
            except (ProgrammingError, OperationalError) as e:
                # Se a coluna já existir (erro DuplicateColumn ou similar) ou outro erro de DDL
                conn.rollback() # Roolback para limpar o estado de erro da transação atual
                
                # O psycopg2.errors.DuplicateColumn é o erro mais comum aqui
                if "already exists" in str(e).lower():
                    print(f"🛠️ Coluna '{column_name}' em '{table_name}' já existia (ignorado).")
                    return False
                
                # Se for erro de tabela inexistente, relança o erro (indicando falha no Passo 1 ou 2)
                elif "does not exist" in str(e).lower():
                    print(f"❌ Erro grave: Tabela '{table_name}' não existe.")
                    raise e
                else:
                    # Qualquer outro erro
                    print(f"❌ Falha desconhecida no ALTER TABLE para {column_name}: {e}")
                    return False
            except Exception as e:
                # Outras exceções de conexão ou runtime
                conn.rollback()
                raise e

        # Adiciona latitude/longitude à campanhas (SOLUÇÃO UndefinedColumn)
        safe_alter_table(conn, 'campanhas', 'latitude', 'REAL')
        safe_alter_table(conn, 'campanhas', 'longitude', 'REAL')
        # Adiciona is_admin a usuarios
        safe_alter_table(conn, 'usuarios', 'is_admin', 'INTEGER DEFAULT 0')
        # Adiciona apagada a campanhas_imagens
        safe_alter_table(conn, 'campanhas_imagens', 'apagada', 'INTEGER DEFAULT 0')
        #Adiciona coluna concluida a campanhas
        safe_alter_table(conn, 'campanhas', 'concluida', 'BOOLEAN DEFAULT FALSE')
        # --- PASSO 4: CRIAÇÃO DE USUÁRIO ADMIN PADRÃO ---
        try:
            # Busca o admin
            user_exists = conn.execute(
                text("SELECT id FROM usuarios WHERE username = :username"), 
                {"username": "admin"}
            ).fetchone()

            if not user_exists:
                # Insere o admin
                conn.execute(
                    text("INSERT INTO usuarios (username, senha, is_admin) VALUES (:user, :senha, :admin)"),
                    {"user": "admin", "senha": generate_password_hash("beto891"), "admin": 1}
                )
                print("👤 Usuário admin criado com senha padrão.")
            
            conn.commit() # Comita a criação do admin
        except Exception as e:
            conn.rollback()
            print(f"❌ Erro grave ao criar usuário admin: {e}")
            
        finally:
            conn.close()
        
        print("✅ Banco de dados inicializado com sucesso!")


# Funções utilitárias

def buscar_usuario(username):
    """Busca um usuário pelo nome."""
    conn = get_db_connection()
    try:
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
