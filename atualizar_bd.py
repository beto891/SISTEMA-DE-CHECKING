from app.utils.database import get_db_connection
from app.routes.upload import slug, BASE_UPLOADS

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("SELECT campanha_id, imagem_path FROM campanhas_imagens")
registros = cursor.fetchall()

for campanha_id, path in registros:
    if not path.startswith('uploads/'):
        cursor.execute("SELECT nome FROM campanhas WHERE id = ?", (campanha_id,))
        nome = cursor.fetchone()[0]
        slug_nome = slug(nome)
        novo_path = f"uploads/{slug_nome}/{path}"
        cursor.execute(
            "UPDATE campanhas_imagens SET imagem_path = ? WHERE campanha_id = ? AND imagem_path = ?",
            (novo_path, campanha_id, path)
        )

conn.commit()
conn.close()