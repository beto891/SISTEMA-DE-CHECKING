import sqlite3
import os
from werkzeug.security import generate_password_hash

# Caminho absoluto para o banco de dados
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
db_path = os.path.join(BASE_DIR, 'database.db')

def get_db_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def inicializar_banco():
    """Cria as tabelas 'tarefas', 'campanhas', 'campanhas_imagens' e 'usuarios' se ainda não existirem."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de tarefas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tarefas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        motivo TEXT,
        estabelecimento TEXT,
        localidade TEXT,
        status TEXT,
        data_inicio TEXT,
        data_fim TEXT,
        descricao TEXT
    )
    """)

    # Tabela de campanhas atualizada
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campanhas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod TEXT,
        nome TEXT,
        latitude REAL,
        longitude REAL,
        data_criacao TEXT
    )
    """)

    # Tabela de imagens vinculadas a campanhas via campanha_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campanhas_imagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campanha_id INTEGER NOT NULL,
        imagem_path TEXT NOT NULL,
        FOREIGN KEY (campanha_id) REFERENCES campanhas(id)
    )
    """)

    # Tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    """)
    #Imagens excluidas
    cursor.execute("""
    CREATE TABLE imagens_excluidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cod TEXT NOT NULL,
    campanha TEXT NOT NULL,
    imagem_path TEXT NOT NULL,
    excluido_por TEXT NOT NULL,
    data_exclusao TEXT NOT NULL
    
    )
    """);
    

    # Adiciona coluna is_admin se não existir (para bancos antigos)
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = [col[1] for col in cursor.fetchall()]
    if 'is_admin' not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER DEFAULT 0")

    # Cria usuário admin padrão se não existir
    cursor.execute("SELECT * FROM usuarios WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (username, senha, is_admin) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("beto891"), 1)
        )
        print("👤 Usuário admin criado com senha padrão.")

    conn.commit()
    conn.close()
    print("✅ Banco de dados e tabelas criadas com sucesso!")

# Funções utilitárias

def buscar_usuario(username):
    """Busca um usuário pelo nome."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def criar_usuario(username, senha, is_admin=0):
    """Cria um novo usuário com senha criptografada."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO usuarios (username, senha, is_admin) VALUES (?, ?, ?)",
            (username, generate_password_hash(senha), is_admin)
        )
        conn.commit()
        return True
    except Exception as e:
        print("❌ Erro ao criar usuário:", e)
        return False
    finally:
        conn.close()