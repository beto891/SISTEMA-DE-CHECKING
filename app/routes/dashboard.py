from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, jsonify
from app.utils.database import get_db_connection
from app.utils.pdf_generator import gerar_pdf_por_nome, gerar_registros_dinamicos_por_campanha
from app.services.dropbox_service import DropboxService
import os

dashboard_bp = Blueprint('dashboard', __name__)
dropbox_service = DropboxService()

def gerar_link_publico(path):
    try:
        if path.startswith("https://") or path.startswith("http://"):
            return path
        return dropbox_service.create_shared_link(path)
    except Exception as e:
        print(f"[Dropbox] Erro ao gerar link público para '{path}': {e}")
        return path  # fallback para o caminho original

@dashboard_bp.route('/')
def inicio():
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/dashboard')
def dashboard():
    conn = get_db_connection()

    # ✅ AJUSTE AQUI: Adiciona a coluna 'data_criacao' na consulta
    resultados = conn.execute("""
        SELECT
            c.nome AS campanha,
            c.data_criacao,
            MIN(c.id) AS id,
            COUNT(DISTINCT c.cod) AS total_espacos,
            COUNT(DISTINCT CASE WHEN i.imagem_path IS NOT NULL THEN c.cod END) AS espacos_com_imagem
        FROM campanhas c
        LEFT JOIN campanhas_imagens i ON i.campanha_id = c.id
        GROUP BY c.nome
        ORDER BY c.nome
    """).fetchall()

    espacos_por_campanha = conn.execute("""
        SELECT c.nome AS campanha, c.cod AS espaco_nome
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
    """).fetchall()

    imagens_por_espaco = conn.execute("""
        SELECT c.nome AS campanha, c.cod AS espaco, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
        ORDER BY c.nome, c.cod, i.id
    """).fetchall()

    conn.close()

    espacos_dict = {}
    for row in espacos_por_campanha:
        espacos_dict.setdefault(row["campanha"], []).append(row["espaco_nome"])

    imagens_dict = {}
    for row in imagens_por_espaco:
        campanha = row["campanha"]
        espaco = row["espaco"]
        imagem = row["imagem_path"]
        imagens_dict.setdefault(campanha, {}).setdefault(espaco, []).append(imagem)

    registros, labels, valores = [], [], []

    for row in resultados:
        campanha = row["campanha"]
        total = row["total_espacos"]
        com_imagem = row["espacos_com_imagem"]
        percentual = round((com_imagem / total) * 100, 2) if total > 0 else 0

        labels.append(campanha)
        valores.append(percentual)

        espaco_destaque = espacos_dict.get(campanha, [None])[0]

        registros.append({
            "id": row["id"],
            "campanha": campanha,
            "data_criacao": row["data_criacao"],  # ✅ AJUSTE AQUI: Adiciona a data de criação
            "espaco_nome": espaco_destaque,
            "espacos": total,
            "imagens": com_imagem,
            "percentual": percentual,
            "meta": percentual >= 10,
            "espacos_com_imagem_lista": espacos_dict.get(campanha, []),
            "imagens_por_espaco": imagens_dict.get(campanha, {})
        })

    return render_template(
        'dashboard.html',
        labels=labels,
        valores=valores,
        registros=registros
    )

@dashboard_bp.route('/api/report-location', methods=['POST'])
def report_location():
    """
    Endpoint para receber e salvar a localização do utilizador.
    """
    if 'usuario' not in session:
        return jsonify(success=False, mensagem="Não autenticado"), 401

    data = request.get_json()
    if not data or 'latitude' not in data or 'longitude' not in data:
        return jsonify(success=False, mensagem="Dados de localização ausentes"), 400

    latitude = data['latitude']
    longitude = data['longitude']
    timestamp = data.get('timestamp')
    user_id = data.get('userId')

    if not user_id:
        return jsonify(success=False, mensagem="ID do utilizador ausente"), 400

    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO localizacoes_usuarios (user_id, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, latitude, longitude, timestamp))
        conn.commit()
        conn.close()
        return jsonify(success=True, mensagem="Localização recebida e salva com sucesso"), 200
    except Exception as e:
        print(f"Erro ao salvar localização: {e}")
        return jsonify(success=False, mensagem=f"Erro interno do servidor: {str(e)}"), 500

@dashboard_bp.route('/api/user-locations', methods=['GET'])
def get_user_locations():
    """
    Endpoint para buscar todas as localizações de utilizadores salvas no banco de dados.
    """
    conn = get_db_connection()
    locations = conn.execute("""
        SELECT user_id, latitude, longitude, timestamp
        FROM localizacoes_usuarios
        ORDER BY timestamp DESC
    """).fetchall()
    conn.close()

    resultados = [dict(row) for row in locations]
    return jsonify(resultados), 200

@dashboard_bp.route('/api/campanha-imagens')
def campanha_imagens():
    nome = request.args.get("nome")
    if not nome:
        return jsonify(success=False, mensagem="Campanha não informada"), 400

    conn = get_db_connection()
    imagens = conn.execute("""
        SELECT c.cod AS espaco, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE LOWER(c.nome) = LOWER(?)
        ORDER BY c.cod, i.id
    """, (nome,)).fetchall()
    conn.close()

    resultado = {}
    for row in imagens:
        espaco = row["espaco"]
        resultado.setdefault(espaco, []).append(row["imagem_path"])

    return jsonify(success=True, campanha=nome, imagens_por_espaco=resultado)

# @dashboard_bp.route('/api/upload/imagens')
# def api_upload_imagens():
#     campanha_id = request.args.get("campanha_id")
#     if not campanha_id:
#         return jsonify(success=False, mensagem="ID da campanha não informado"), 400

#     conn = get_db_connection()
#     campanha_row = conn.execute("SELECT nome FROM campanhas WHERE id = ?", (campanha_id,)).fetchone()
#     if not campanha_row:
#         conn.close()
#         return jsonify(success=False, mensagem="Campanha não encontrada"), 404

#     nome_campanha = campanha_row["nome"]

#     imagens = conn.execute("""
#         SELECT c.cod AS espaco, i.imagem_path
#         FROM campanhas c
#         JOIN campanhas_imagens i ON i.campanha_id = c.id
#         WHERE LOWER(c.nome) = LOWER(?)
#         ORDER BY c.cod, i.id
#     """, (nome_campanha,)).fetchall()
#     conn.close()

#     resultado = []
#     for row in imagens:
#         link_publico = gerar_link_publico(row["imagem_path"])
#         resultado.append({
#             "espaco": row["espaco"],
#             "url": link_publico or row["imagem_path"],
#             "path": row["imagem_path"]
#         })

#     return jsonify(success=True, imagens=resultado)

@dashboard_bp.route('/gerar-pdf', methods=["POST"])
def gerar_pdf_campanha_post():
    nome  = request.form.get("nome")
    pi    = request.form.get("pi")
    inicio = request.form.get("inicio")
    fim    = request.form.get("fim")

    imagem = request.files.get("imagemCampanha")  # ✅ imagem enviada via FormData

    registros = gerar_registros_dinamicos_por_campanha(nome)
    if not registros:
        return {"status": "erro", "mensagem": "Campanha sem registros válidos."}, 404

    caminho_pdf = gerar_pdf_por_nome(registros, nome, pi, inicio, fim, imagem_dinamica=imagem)  # ✅ envia imagem
    if not caminho_pdf:
        return {"status": "erro", "mensagem": "PDF não pôde ser gerado."}, 404

    return send_file(
        caminho_pdf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=os.path.basename(caminho_pdf)
    )

@dashboard_bp.route('/gerar-pdf-campanha/<nome>', methods=['GET'])
def gerar_pdf_campanha_get(nome):
    if 'usuario' not in session:
        return redirect(url_for('auth.login'))

    pi_numero = request.args.get('pi')
    data_inicio = request.args.get('inicio')
    data_fim = request.args.get('fim')

    registros = gerar_registros_dinamicos_por_campanha(nome)
    if not registros:
        return "PDF não pôde ser gerado. Nenhum conteúdo válido encontrado.", 404

    caminho_pdf = gerar_pdf_por_nome(registros, nome, pi_numero, data_inicio, data_fim)
    return send_file(
        caminho_pdf,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=os.path.basename(caminho_pdf)
    )

@dashboard_bp.route('/verificar-imagens-campanha/<nome>')
def verificar_imagens(nome):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.cod, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE LOWER(c.nome) LIKE ?
    """, (f"%{nome.lower()}%",))
    registros = cursor.fetchall()
    conn.close()

    resultado = []
    for r in registros:
        imagem_path = r["imagem_path"]
        cod = r["cod"]
        caminho = imagem_path if imagem_path.startswith("static") else os.path.join("static", imagem_path)
        caminho_absoluto = os.path.abspath(caminho)
        existe = os.path.exists(caminho_absoluto)
        resultado.append({
            "cod": cod,
            "imagem_path": imagem_path,
            "caminho_absoluto": caminho_absoluto,
            "existe": existe
        })

    return {"campanha": nome, "total": len(resultado), "registros": resultado}

@dashboard_bp.route('/api/campanha/<int:id_campanha>', methods=['DELETE'])
def excluir_campanha_api(id_campanha):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Passo 1: Excluir todos os espaços relacionados a esta campanha
        cursor.execute("DELETE FROM espacos WHERE id_campanha = ?", (id_campanha,))

        # Passo 2: Excluir a própria campanha
        cursor.execute("DELETE FROM campanhas WHERE id = ?", (id_campanha,))
        
        conn.commit()
        return jsonify({"success": True, "message": "Campanha e todos os espaços relacionados foram excluídos com sucesso."}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir campanha: {e}")
        return jsonify({"success": False, "message": "Erro ao excluir campanha."}), 500
    finally:
        conn.close()