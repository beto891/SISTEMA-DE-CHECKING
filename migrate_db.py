import sqlite3

SQL_FILE = "migrate_schema.sql"
DB_FILE  = "database.db"

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql_script = f.read()

conn = sqlite3.connect(DB_FILE)
try:
    conn.executescript(sql_script)
    print("✅ Migração aplicada com sucesso!")
finally:
    conn.close()