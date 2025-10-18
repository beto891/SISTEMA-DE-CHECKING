import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, jsonify
from app.utils.database import get_db_connection # Mantido para funções que o utilizam
from app.utils.pdf_generator import gerar_pdf_por_nome, gerar_registros_dinamicos_por_campanha
from app.services.dropbox_service import DropboxService
from app import db # Importado para acessar o engine do SQLAlchemy
import os
from sqlalchemy import text # Importação obrigatória para SQL puro no SQLAlchemy 2.0+
from flask_login import login_required

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
@login_required
def dashboard():
    # Usando db.engine.connect() para obter a conexão (Melhor prática com Flask-SQLAlchemy)
    conn = db.engine.connect()

    # Query 1 (resultados) - JÁ ESTAVA CORRETO
    resultados = conn.execute(text("""
        SELECT
            c.nome AS campanha,
            c.data_criacao,
            MIN(c.id) AS id,
            COUNT(DISTINCT c.cod) AS total_espacos,
            COUNT(DISTINCT CASE WHEN i.imagem_path IS NOT NULL THEN c.cod END)
                AS espacos_com_imagem
        FROM campanhas c
        LEFT JOIN campanhas_imagens i
        ON i.campanha_id = c.id
        GROUP BY
            c.nome,
            c.data_criacao      -- Correção PostgreSQL: Adicionado ao GROUP BY
        ORDER BY c.nome
    """)).fetchall()

    # Query 2 (espacos_por_campanha) - JÁ ESTAVA CORRETO
    espacos_por_campanha = conn.execute(text("""
        SELECT c.nome AS campanha, c.cod AS espaco_nome
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
    """)).fetchall()

    # Query 3 (imagens_por_espaco) - JÁ ESTAVA CORRETO
    imagens_por_espaco = conn.execute(text("""
        SELECT c.nome AS campanha, c.cod AS espaco, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
        ORDER BY c.nome, c.cod, i.id
    """)).fetchall()

    conn.close()

    # CORREÇÃO DE TIPAGEM: Converte os objetos Row para dicionários Python para uso posterior.
    # Isto resolve o TypeError: tuple indices must be integers or slices, not str
    resultados_dicts = [dict(row._mapping) for row in resultados]
    espacos_por_campanha_dicts = [dict(row._mapping) for row in espacos_por_campanha]
    imagens_por_espaco_dicts = [dict(row._mapping) for row in imagens_por_espaco]

    espacos_dict = {}
    for row in espacos_por_campanha_dicts:
        espacos_dict.setdefault(row["campanha"], []).append(row["espaco_nome"])

    imagens_dict = {}
    for row in imagens_por_espaco_dicts:
        campanha = row["campanha"]
        espaco = row["espaco"]
        imagem = row["imagem_path"]
        imagens_dict.setdefault(campanha, {}).setdefault(espaco, []).append(imagem)

    registros, labels, valores = [], [], []

    for row in resultados_dicts: # Usa a lista de dicionários corrigida
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
@login_required
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
        # CORREÇÃO 4: Usando text() com parâmetros nomeados.
        with db.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO localizacoes_usuarios (user_id, latitude, longitude, timestamp)
                    VALUES (:user_id, :latitude, :longitude, :timestamp)
                """), 
                {
                    "user_id": user_id, 
                    "latitude": latitude, 
                    "longitude": longitude, 
                    "timestamp": timestamp
                }
            )
            # Para DML (INSERT/UPDATE/DELETE) com engine.connect(), é necessário um commit.
            conn.commit()
            return jsonify(success=True, mensagem="Localização recebida e salva com sucesso"), 200
    except Exception as e:
        print(f"Erro ao salvar localização: {e}")
        return jsonify(success=False, mensagem=f"Erro interno do servidor: {str(e)}"), 500

@dashboard_bp.route('/api/user-locations', methods=['GET'])
@login_required
def get_user_locations():
    """
    Endpoint para buscar todas as localizações de utilizadores salvas no banco de dados.
    """
    conn = db.engine.connect() # Padronizando para db.engine.connect()
    # Query 5 (SELECT) - JÁ ESTAVA CORRETO
    locations = conn.execute(text("""
        SELECT user_id, latitude, longitude, timestamp
        FROM localizacoes_usuarios
        ORDER BY timestamp DESC
    """)).fetchall()
    conn.close()

    # CORREÇÃO DE TIPAGEM: Converte o objeto Row para dicionário
    resultados = [dict(row._mapping) for row in locations]
    return jsonify(resultados), 200

@dashboard_bp.route('/api/campanha-imagens')
@login_required
def campanha_imagens():
    nome = request.args.get("nome")
    if not nome:
        return jsonify(success=False, mensagem="Campanha não informada"), 400

    conn = db.engine.connect() # Padronizando para db.engine.connect()
    # CORREÇÃO 6: Usando text() com parâmetro nomeado :nome, corrigindo o erro de parâmetro posicional (?)
    imagens = conn.execute(text("""
        SELECT c.cod AS espaco, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE LOWER(c.nome) = LOWER(:nome)
        ORDER BY c.cod, i.id
    """), {"nome": nome}).fetchall()
    conn.close()

    # CORREÇÃO DE TIPAGEM: Converte o objeto Row para dicionário
    imagens_dicts = [dict(row._mapping) for row in imagens]

    resultado = {}
    for row in imagens_dicts:
        espaco = row["espaco"]
        resultado.setdefault(espaco, []).append(row["imagem_path"])

    return jsonify(success=True, campanha=nome, imagens_por_espaco=resultado)

# O trecho @dashboard_bp.route('/api/upload/imagens') estava comentado e foi mantido assim.

@dashboard_bp.route('/gerar-pdf', methods=["POST"])
@login_required
def gerar_pdf_campanha_post():
    nome    = request.form.get("nome")
    pi      = request.form.get("pi")
    inicio  = request.form.get("inicio")
    fim     = request.form.get("fim")

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
@login_required
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
@login_required
def verificar_imagens(nome):
    conn = db.engine.connect() # Padronizando para db.engine.connect()
    
    # CORREÇÃO 7: Substitui conn.cursor().execute(SQL_bruto) por conn.execute(text())
    registros = conn.execute(text("""
        SELECT c.cod, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE LOWER(c.nome) LIKE :nome_like
    """), {"nome_like": f"%{nome.lower()}%"}).fetchall()

    conn.close()

    # CORREÇÃO DE TIPAGEM: Converte o objeto Row para dicionário
    registros_dicts = [dict(r._mapping) for r in registros]

    resultado = []
    for r in registros_dicts:
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
@login_required
def excluir_campanha_api(id_campanha):
    conn = db.engine.connect() # Padronizando para db.engine.connect()

    try:
        # CORREÇÃO 8: Substitui conn.cursor().execute(SQL_bruto) por conn.execute(text())
        
        # Passo 1: Excluir todos os espaços relacionados a esta campanha
        conn.execute(
            text("DELETE FROM espacos WHERE id_campanha = :id"), 
            {"id": id_campanha}
        )

        # Passo 2: Excluir a própria campanha
        cursor_campanha = conn.execute(
            text("DELETE FROM campanhas WHERE id = :id"), 
            {"id": id_campanha}
        )
        
        conn.commit()
        return jsonify({"success": True, "message": "Campanha e todos os espaços relacionados foram excluídos com sucesso."}), 200
    except Exception as e:
        conn.rollback()
        print(f"Erro ao excluir campanha: {e}")
        return jsonify({"success": False, "message": "Erro ao excluir campanha."}), 500
    finally:
        conn.close()
