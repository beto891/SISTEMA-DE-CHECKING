import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _resolve_database_path():
    """Respeita DATABASE_URL em ambientes de teste e produção."""
    database_url = os.getenv('DATABASE_URL', '').strip()
    if database_url.startswith('sqlite:///'):
        sqlite_path = database_url.replace('sqlite:///', '', 1)
        if not os.path.isabs(sqlite_path):
            sqlite_path = os.path.abspath(os.path.join(BASE_DIR, sqlite_path))
        return sqlite_path
    return os.path.join(BASE_DIR, 'database.db')


db_path = _resolve_database_path()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')


def get_db_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(_resolve_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table_name, column_name, column_sql):
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def inicializar_banco():
    """Cria e ajusta as tabelas essenciais para o sistema em modo profissional."""
    conn = get_db_connection()
    cursor = conn.cursor()

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campanhas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod TEXT,
        nome TEXT,
        latitude REAL,
        longitude REAL,
        data_criacao TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campanhas_imagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campanha_id INTEGER NOT NULL,
        imagem_path TEXT NOT NULL,
        apagada INTEGER DEFAULT 0,
        fileid TEXT,
        folderid TEXT,
        FOREIGN KEY (campanha_id) REFERENCES campanhas(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS localizacoes_usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        timestamp TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imagens_excluidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cod TEXT NOT NULL,
        campanha TEXT NOT NULL,
        imagem_path TEXT NOT NULL,
        excluido_por TEXT NOT NULL,
        data_exclusao TEXT NOT NULL
    )
    """)

    _ensure_column(conn, 'usuarios', 'is_admin', 'INTEGER DEFAULT 0')
    _ensure_column(conn, 'campanhas_imagens', 'apagada', 'INTEGER DEFAULT 0')
    _ensure_column(conn, 'campanhas_imagens', 'fileid', 'TEXT')
    _ensure_column(conn, 'campanhas_imagens', 'folderid', 'TEXT')
    _ensure_column(conn, 'campanhas', 'data_criacao', 'TEXT DEFAULT CURRENT_TIMESTAMP')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_campanhas_nome ON campanhas(nome)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_campanhas_imagens_campanha ON campanhas_imagens(campanha_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_campanhas_imagens_apagada ON campanhas_imagens(apagada)")

    if ADMIN_PASSWORD:
        cursor.execute("SELECT * FROM usuarios WHERE username = ?", (ADMIN_USERNAME,))
        admin_row = cursor.fetchone()
        if admin_row is None:
            cursor.execute(
                "INSERT INTO usuarios (username, senha, is_admin) VALUES (?, ?, ?)",
                (ADMIN_USERNAME, generate_password_hash(ADMIN_PASSWORD), 1)
            )
            print(f"👤 Usuário admin '{ADMIN_USERNAME}' criado com senha proveniente da variável de ambiente ADMIN_PASSWORD.")
        else:
            cursor.execute(
                "UPDATE usuarios SET senha = ?, is_admin = 1 WHERE username = ?",
                (generate_password_hash(ADMIN_PASSWORD), ADMIN_USERNAME)
            )
            print(f"👤 Usuário admin '{ADMIN_USERNAME}' atualizado com a senha configurada na variável de ambiente ADMIN_PASSWORD.")
    else:
        print("⚠️ Nenhum usuário admin foi criado porque ADMIN_PASSWORD não está definido no ambiente.")

    conn.commit()
    conn.close()
    print("✅ Banco de dados e tabelas criadas com sucesso!")


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