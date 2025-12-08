import pandas as pd
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, jsonify
from app.utils.database import get_db_connection # Mantido para funções que o utilizam
from app.utils.pdf_generator import gerar_pdf_por_nome, gerar_registros_dinamicos_por_campanha
from app.services.dropbox_service import DropboxService
from app import db # Importado para acessar o engine do SQLAlchemy
import os
from sqlalchemy import text # Importação obrigatória para SQL puro no SQLAlchemy 2.0+
from flask_login import login_required

from app.utils.pdf_generator import gerar_pdf_task 
from app.services.celery_config import celery_app 
from werkzeug.datastructures import FileStorage 

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

# Em app/routes/dashboard.py

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    conn = db.engine.connect()

    # Query 1 (resultados) - CORRIGIDA PARA AGRUPAR REAIS DUPLICATAS
    resultados = conn.execute(text("""
        SELECT
            c.nome AS campanha,
            MIN(c.data_criacao) AS data_criacao, -- Pega a data mais antiga para exibição
            c.concluida,
            MIN(c.id) AS id, -- Pega um ID qualquer (o primeiro) para usar nos botões
            COUNT(c.cod) AS total_espacos, -- Conta o total de linhas (espaços) com esse nome
            COUNT(CASE WHEN i.imagem_path IS NOT NULL THEN c.cod END)
                AS espacos_com_imagem
        FROM campanhas c
        LEFT JOIN campanhas_imagens i
        ON i.campanha_id = c.id
        GROUP BY
            c.nome,
            c.concluida -- Agrupa apenas por Nome e Status
        ORDER BY c.nome
    """)).fetchall()

    # Query 2 (espacos_por_campanha) - RESTAURADA
    espacos_por_campanha = conn.execute(text("""
        SELECT c.nome AS campanha, c.cod AS espaco_nome
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
    """)).fetchall()

    # Query 3 (imagens_por_espaco) - RESTAURADA
    imagens_por_espaco = conn.execute(text("""
        SELECT c.nome AS campanha, c.cod AS espaco, i.imagem_path
        FROM campanhas c
        JOIN campanhas_imagens i ON i.campanha_id = c.id
        WHERE i.imagem_path IS NOT NULL
        ORDER BY c.nome, c.cod, i.id
    """)).fetchall()

    conn.close()

    # O resto da sua lógica de processamento de dados permanece igual
    resultados_dicts = [dict(row._mapping) for row in resultados]
    espacos_por_campanha_dicts = [dict(row._mapping) for row in espacos_por_campanha]
    imagens_por_espaco_dicts = [dict(row._mapping) for row in imagens_por_espaco]

    espacos_dict = {}
    for row in espacos_por_campanha_dicts:
        espacos_dict.setdefault(row["campanha"], []).append(row["espaco_nome"])

    imagens_dict = {}
    for row in imagens_por_espaco_dicts:
        imagens_dict.setdefault(row["campanha"], {}).setdefault(row["espaco"], []).append(row["imagem_path"])

    registros, labels, valores = [], [], []
    for row in resultados_dicts:
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
            "data_criacao": row["data_criacao"],
            "espaco_nome": espaco_destaque,
            "espacos": total,
            "imagens": com_imagem,
            "percentual": percentual,
            "meta": percentual >= 10,
            "espacos_com_imagem_lista": espacos_dict.get(campanha, []),
            "imagens_por_espaco": imagens_dict.get(campanha, {}),
            "concluida": row["concluida"]
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


# =======================================================
# ✅ 1. ROTA DE DISPARO (POST /gerar-pdf-async)
# Dispara a tarefa e retorna o Task ID Imediatamente.
# =======================================================

@dashboard_bp.route('/gerar-pdf-async', methods=['POST'])
@login_required
def gerar_pdf_async():
    # Nota: O frontend deve ser alterado para enviar PI, inicio, fim, etc., como JSON.
    # A imagem (FileStorage) será tratada separadamente, conforme explicado abaixo.

    # 1. Obter dados: Usamos request.form (para FileStorage) e tratamos os demais dados.
    nome = request.form.get("nome")
    pi = request.form.get("pi")
    inicio = request.form.get("inicio")
    fim = request.form.get("fim")
    imagem_file = request.files.get("imagemCampanha")

    if not nome:
        return jsonify({"success": False, "message": "Nome da campanha é obrigatório."}), 400

    # 2. Tratamento do Arquivo (FileStorage):
    # SALVAR o FileStorage ANTES de disparar a tarefa e passar o caminho.
    caminho_imagem_temporario = None
    if imagem_file and isinstance(imagem_file, FileStorage):
        temp_dir = os.path.join(os.getcwd(), 'tmp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        caminho_imagem_temporario = os.path.join(temp_dir, imagem_file.filename)
        imagem_file.save(caminho_imagem_temporario)
        # Atenção: Você deve implementar uma rotina para limpar arquivos antigos em 'tmp_uploads'.

    # 3. Disparar a Tarefa Celery
    task = gerar_pdf_task.delay(
        nome_campanha=nome,
        pi_numero=pi,
        data_inicio=inicio,
        data_fim=fim,
        # Passamos o caminho do arquivo no disco
        imagem_dinamica_path=caminho_imagem_temporario 
    )

    # 4. Retorna Task ID imediatamente
    return jsonify({
        'success': True,
        'status': 'processing',
        'task_id': task.id,
        'message': 'Geração de PDF iniciada em segundo plano.'
    }), 202

# =======================================================
# ✅ 2. ROTA DE STATUS (GET /pdf-status/<task_id>)
# Verifica o progresso da tarefa Celery.
# =======================================================

@dashboard_bp.route('/pdf-status/<task_id>', methods=['GET'])
@login_required
def get_pdf_status(task_id):
    task = celery_app.AsyncResult(task_id)

    response = {
        'status': task.status,
    }

    if task.state == 'SUCCESS':
        # O resultado contém o caminho do PDF retornado pela tarefa
        caminho_pdf = task.result 
        
        # O Celery guarda o caminho, mas vamos retornar apenas o nome do arquivo para o download final
        response['result'] = os.path.basename(caminho_pdf)
        response['file_path'] = caminho_pdf # Retorna o caminho completo para o próximo endpoint
        
        # Limpa o resultado da tarefa do Redis após o sucesso para economizar memória
        task.forget() 
        
    elif task.state == 'FAILURE':
        response['error'] = str(task.result)
        # Limpa o resultado da tarefa do Redis
        task.forget() 

    return jsonify(response)


# =======================================================
# ✅ 3. ROTA DE DOWNLOAD FINAL (GET /download-file)
# Envia o arquivo gerado ao usuário.
# =======================================================

@dashboard_bp.route('/download-file', methods=['GET'])
@login_required
def download_pdf_final():
    # O frontend envia o caminho completo do arquivo temporário
    file_path = request.args.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'message': 'Arquivo não encontrado ou expirado.'}), 404

    try:
        # Envia o arquivo
        return send_file(
            file_path,
            as_attachment=True,
            mimetype='application/pdf',
            download_name=os.path.basename(file_path)
        )
    finally:
        # Importante: Limpa o arquivo temporário após o envio
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Aviso: Não foi possível remover o arquivo temporário {file_path}: {e}")

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
    conn = db.engine.connect()

    try:
        # 1. Descobrir o NOME da campanha baseada no ID que foi clicado
        row = conn.execute(
            text("SELECT nome FROM campanhas WHERE id = :id"), 
            {"id": id_campanha}
        ).fetchone()

        if not row:
            return jsonify({"success": False, "message": "Campanha não encontrada."}), 404
        
        nome_campanha = row.nome

        print(f"🗑️ Excluindo TODAS as campanhas com o nome: '{nome_campanha}'")

        # 2. Apagar imagens relacionadas a QUALQUER campanha com esse nome
        # (Precisamos sub-selecionar os IDs baseados no nome)
        conn.execute(text("""
            DELETE FROM campanhas_imagens 
            WHERE campanha_id IN (SELECT id FROM campanhas WHERE nome = :nome)
        """), {"nome": nome_campanha})

        # 3. Apagar as campanhas em si pelo NOME
        result = conn.execute(
            text("DELETE FROM campanhas WHERE nome = :nome"), 
            {"nome": nome_campanha}
        )
        
        conn.commit()
        
        msg = f"Sucesso! {result.rowcount} registros da campanha '{nome_campanha}' foram excluídos."
        return jsonify({"success": True, "message": msg}), 200

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao excluir campanha: {e}")
        return jsonify({"success": False, "message": "Erro interno ao excluir campanha."}), 500
    finally:
        conn.close()

# Em app/routes/dashboard.py

@dashboard_bp.route('/api/dashboard/chart-data')
@login_required
def get_chart_data():
    """Retorna apenas os dados de labels e valores para o gráfico do dashboard."""
    try:
        with db.engine.connect() as conn:
            # A mesma query da sua rota dashboard, MAS filtrando as concluídas
            resultados = conn.execute(text("""
                SELECT
                    c.nome AS campanha,
                    COUNT(DISTINCT c.cod) AS total_espacos,
                    COUNT(DISTINCT CASE WHEN i.imagem_path IS NOT NULL THEN c.cod END)
                        AS espacos_com_imagem
                FROM campanhas c
                LEFT JOIN campanhas_imagens i ON i.campanha_id = c.id
                WHERE c.concluida = FALSE  -- <<< FILTRO PRINCIPAL AQUI
                GROUP BY c.nome
                ORDER BY c.nome
            """)).fetchall()

        labels, valores = [], []
        for row in resultados:
            total = row.total_espacos
            com_imagem = row.espacos_com_imagem
            percentual = round((com_imagem / total) * 100, 2) if total > 0 else 0
            labels.append(row.campanha)
            valores.append(percentual)
            
        return jsonify(labels=labels, valores=valores)

    except Exception as e:
        print(f"Erro ao buscar dados do gráfico: {e}")
        return jsonify(error="Erro ao buscar dados do gráfico"), 500