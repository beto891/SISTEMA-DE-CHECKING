from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from sqlalchemy import text, create_engine, event
from flask import current_app
import os
import sys

# Assume que o objeto 'db' do Flask-SQLAlchemy foi inicializado em 'app/__init__.py'
# e importado aqui (embora 'db' não estivesse no escopo, esta é a estrutura padrão).

# IMPORTANTE: Se o seu 'db' não é um objeto ORM (apenas Flask-SQLAlchemy),
# você precisará importá-lo do seu módulo de modelos (ex: 'from .models import db').
# Para esta correção, usarei o db do escopo do Flask-SQLAlchemy.

# Vamos assumir que 'db' é importado globalmente no seu projeto (ex: de app.models)
# e que 'get_db_connection' não é mais usado para conexões cruas, mas sim
# 'db.engine.connect()'.

# Se 'db' for o objeto ORM do Flask-SQLAlchemy, o código abaixo deve funcionar,
# mas se você está usando um modelo de utilitários, precisamos de uma forma de acesso.
# Para manter a função de utilitário, usarei a forma moderna do Flask-SQLAlchemy:

def get_db_connection():
    """Retorna uma conexão bruta (DBAPI-style) do SQLAlchemy Engine."""
    # Como Flask-SQLAlchemy 3.x e SQLAlchemy 2.0+ são usados,
    # usamos db.engine.connect() para obter uma conexão
    from app import db # Importa o objeto db do seu módulo principal
    return db.engine.connect()

def inicializar_banco(app):
    """Cria as tabelas e o usuário admin padrão, adaptado para SQLAlchemy Engine."""
    from app import db # Importa o objeto db
    
    with app.app_context():
        # Usa db.create_all() para o esquema, que é a forma padrão do Flask-SQLAlchemy
        # para criar todas as tabelas definidas nos modelos.
        try:
            db.create_all()
            print("✅ Tabelas definidas nos modelos criadas com sucesso!")
        except Exception as e:
            # Em ambientes de produção (PostgreSQL), create_all pode ser substituído por migrações.
            # Aqui, assume-se que as tabelas são criadas via ORM.
            print(f"⚠️ Aviso: Falha ao executar db.create_all(). Pode ser que o esquema já exista ou que migrações sejam necessárias: {e}")
            pass
        
        # Criação de dados iniciais via SQLAlchemy Engine
        conn = get_db_connection()
        try:
            # Adiciona coluna 'apagada' à campanhas_imagens, se não existir (Migração)
            # Nota: O ORM é preferido, mas para migração manual usamos SQL
            
            # Checa e adiciona coluna 'apagada' (Para campanhas_imagens)
            try:
                conn.execute(text("SELECT apagada FROM campanhas_imagens LIMIT 1"))
            except Exception: # Coluna não existe (PostgreSQL lança erro de coluna não encontrada)
                conn.execute(text("ALTER TABLE campanhas_imagens ADD COLUMN apagada INTEGER DEFAULT 0"))
                print("🛠️ Coluna 'apagada' adicionada em campanhas_imagens.")
            
            # Checa e adiciona coluna 'is_admin' (Para usuarios - SQL BRUTO)
            try:
                conn.execute(text("SELECT is_admin FROM usuarios LIMIT 1"))
            except Exception: # Coluna não existe
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER DEFAULT 0"))
                print("🛠️ Coluna 'is_admin' adicionada em usuarios.")


            # Cria usuário admin padrão se não existir (SQL BRUTO)
            # CORREÇÃO 1: Usando text() e parâmetro nomeado
            user_exists = conn.execute(
                text("SELECT id FROM usuarios WHERE username = :username"), 
                {"username": "admin"}
            ).fetchone()

            if not user_exists:
                # CORREÇÃO 2: Usando text() e parâmetro nomeado
                conn.execute(
                    text("INSERT INTO usuarios (username, senha, is_admin) VALUES (:user, :senha, :admin)"),
                    {"user": "admin", "senha": generate_password_hash("beto891"), "admin": 1}
                )
                print("👤 Usuário admin criado com senha padrão.")
            
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"❌ Erro na inicialização de dados: {e}")
            
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
        current_app.logger.error(f"Erro ao buscar usuário: {e}")
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
