from flask import Blueprint, render_template
from app.utils.database import get_db_connection
from app.routes.auth import admin_required
from sqlalchemy import text

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard_admin():
    conn = get_db_connection()
    resultados = conn.execute(text("""
        SELECT
            c.nome AS campanha,
            COUNT(DISTINCT c.id) AS total_espacos,
            COUNT(DISTINCT CASE WHEN i.imagem_path IS NOT NULL AND i.imagem_path != '' THEN c.id END) AS espacos_com_imagem
        FROM campanhas c
        LEFT JOIN campanhas_imagens i ON i.campanha_id = c.id
        GROUP BY c.nome
    """)).fetchall()

    registros = []
    labels = []
    valores = []

    for row in resultados:
        nome = row["campanha"]
        total = row["total_espacos"]
        com_imagem = row["espacos_com_imagem"]
        percentual = round((com_imagem / total) * 100, 2) if total > 0 else 0

        labels.append(nome)
        valores.append(percentual)

        registros.append({
            "campanha": nome,
            "espacos": total,
            "imagens": com_imagem,  # espaço com upload, não número de fotos
            "percentual": percentual,
            "meta": percentual >= 10
        })

    conn.close()
    return render_template(
        "admin_dashboard.html",
        labels=labels,
        valores=valores,
        registros=registros
    )