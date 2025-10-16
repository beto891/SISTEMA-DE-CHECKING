import pandas as pd
from flask import (
    Blueprint, render_template, request,
    jsonify, redirect, url_for,
    current_app
)
from geopy.distance import geodesic
from datetime import datetime
import logging
import sys

# Importações ajustadas para o sistema de login e socketio
from flask_login import login_required
from app import socketio

from app.utils.database import get_db_connection
from app.routes.upload import slug

# Configuração do Blueprint
campaign_bp = Blueprint('campaign', __name__, url_prefix='/api/campaign')

# Configuração do logger
logging.basicConfig(stream=sys.stdout, encoding='utf-8', level=logging.INFO)
logger = logging.getLogger(__name__)

def to_float(valor):
    """Converte um valor para float, tratando vírgulas como pontos decimais."""
    try:
        return float(str(valor).replace(',', '.'))
    except (ValueError, TypeError):
        return None

# --- ROTA UNIFICADA PARA AÇÕES POR ID (GET, PUT, DELETE) ---
# Esta função única resolve o conflito de rotas e o bug de edição.

# Em app/routes/campaign.py

@campaign_bp.route('/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def handle_campaign_item(item_id):
    """
    Gerencia uma campanha/espaço por ID.
    """
    
    if request.method == 'PUT':
        # (Remova os prints de 'espião' agora que encontramos o problema)
        data = request.get_json()
        if not data or 'novo_nome' not in data:
            return jsonify(success=False, mensagem="Dados de entrada inválidos."), 400
        
        novo_nome = data['novo_nome']
        try:
            with get_db_connection() as conn:
                # --- LÓGICA DE ATUALIZAÇÃO CORRIGIDA ---

                # 1. Primeiro, usamos o ID para encontrar o NOME ANTIGO da campanha.
                row = conn.execute("SELECT nome FROM campanhas WHERE id = ?", (item_id,)).fetchone()
                if not row:
                    return jsonify(success=False, mensagem="Campanha original não encontrada."), 404
                
                nome_antigo = row['nome']

                # 2. Agora, atualizamos TODAS as linhas que têm o nome antigo.
                cursor = conn.execute(
                    "UPDATE campanhas SET nome = ? WHERE nome = ?", 
                    (novo_nome, nome_antigo)
                )

                if cursor.rowcount == 0:
                    return jsonify(success=False, mensagem="Nenhuma campanha encontrada para atualização."), 404
                
                conn.commit()
            return jsonify(success=True, mensagem=f"{cursor.rowcount} espaços da campanha foram atualizados com sucesso!")
        except Exception as e:
            current_app.logger.error(f"Erro ao atualizar campanha: {e}")
            return jsonify(success=False, mensagem="Erro ao processar a atualização."), 500

   
    # --- LÓGICA PARA EXCLUIR (DELETE) ---
    if request.method == 'DELETE':
        try:
            with get_db_connection() as conn:
                # PASSO 1: Encontrar o nome da campanha a partir do ID do espaço
                row = conn.execute("SELECT nome FROM campanhas WHERE id = ?", (item_id,)).fetchone()
                if not row:
                    return jsonify(success=False, mensagem="Espaço da campanha não encontrado."), 404
                
                nome_da_campanha = row['nome']

                # PASSO 2: Encontrar todos os IDs dos espaços dessa campanha
                ids_cursor = conn.execute("SELECT id FROM campanhas WHERE nome = ?", (nome_da_campanha,))
                ids_para_excluir = [r['id'] for r in ids_cursor.fetchall()]

                if not ids_para_excluir:
                    return jsonify(success=False, mensagem="Nenhum espaço encontrado para esta campanha."), 404

                # PASSO 3 & 4: Excluir imagens e depois os espaços
                placeholders = ','.join(['?'] * len(ids_para_excluir))
                conn.execute(f"DELETE FROM campanhas_imagens WHERE campanha_id IN ({placeholders})", ids_para_excluir)
                cursor_campanha = conn.execute("DELETE FROM campanhas WHERE nome = ?", (nome_da_campanha,))
                
                conn.commit()
                return jsonify(
                    success=True, 
                    mensagem=f"Campanha '{nome_da_campanha}' ({cursor_campanha.rowcount} espaços) foi excluída."
                )
        except Exception as e:
            current_app.logger.error(f"Erro ao excluir campanha por nome: {e}")
            return jsonify(success=False, mensagem="Erro ao processar a exclusão."), 500
            
    # --- LÓGICA PARA BUSCAR (GET) ---
    # (Default: if request.method == 'GET')
    with get_db_connection() as conn:
        campanha = conn.execute("SELECT id, nome FROM campanhas WHERE id = ?", (item_id,)).fetchone()
    if not campanha:
        return jsonify(success=False, mensagem="Campanha não encontrada."), 404
    return jsonify(dict(campanha))


# --- SUAS OUTRAS ROTAS DESTE ARQUIVO ---

@campaign_bp.route('/ponto-proximo', methods=['POST'])
@login_required
def ponto_proximo():
    user_lat = float(request.form['lat'])
    user_lon = float(request.form['lon'])

    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    conn.close()

    if not campanhas:
        return "Nenhuma campanha cadastrada", 404

    ponto = min(
        campanhas,
        key=lambda c: geodesic((user_lat, user_lon), (c['latitude'], c['longitude'])).km
    )
    return render_template('ponto.html', campanha=ponto)


# ✅ ROTA RESTAURADA: Esta rota renderiza a página de check-in fotográfico
@campaign_bp.route('/campanhas')
@login_required
def listar_campanhas():
    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    campanhas_data = []
    for c in campanhas:
        camp = dict(c)
        img_row = conn.execute(
            "SELECT imagem_path FROM campanhas_imagens WHERE campanha_id = ? LIMIT 1",
            (c['id'],)
        ).fetchone()
        if img_row:
            camp['imagem_url'] = url_for(
                'static',
                filename=img_row['imagem_path'],
                _external=False
            )
        else:
            camp['imagem_url'] = None
        campanhas_data.append(camp)
    conn.close()
    return render_template('campanhas.html', campanhas=campanhas_data)


@campaign_bp.route('/importar-campanhas', methods=['POST'])
@login_required
def importar_campanhas():
    # ESPİÃO DO POSSÍVEL CULPADO
    print("\n❌❌❌ ALERTA: ROTA DE IMPORTAR CAMPANHAS FOI ACIONADA PELA EDIÇÃO! --- ERRO DE ROTEAMENTO --- ❌❌❌\n") 
    logger.info("🔄 Iniciando importação de campanhas")
    arquivo = request.files.get('arquivo')
    if not arquivo:
        return jsonify({"success": False, "mensagem": "Nenhum arquivo enviado"}), 400

    try:
        if arquivo.filename.lower().endswith('.csv'):
            df = pd.read_csv(arquivo)
        elif arquivo.filename.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(arquivo)
        else:
            return jsonify({"success": False, "mensagem": "Formato de arquivo não suportado"}), 400
    except Exception as e:
        return jsonify({"success": False, "mensagem": "Erro ao processar o arquivo"}), 500

    df.columns = [col.strip().lower() for col in df.columns]
    conn = get_db_connection()
    cursor = conn.cursor()
    ignoradas = 0
    criadas = 0
    novas = []

    for i, row in df.iterrows():
        linha_num = i + 2
        cod = str(row.get('cod', '')).strip()
        nome = str(row.get('nome', '')).strip()
        if not cod or not nome:
            ignoradas += 1
            continue
        
        lat = to_float(row.get('latitude'))
        lon = to_float(row.get('longitude'))
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT id FROM campanhas WHERE LOWER(cod) = ? AND LOWER(nome) = ?", (cod.lower(), nome.lower()))
        if cursor.fetchone():
            ignoradas += 1
            continue

        try:
            cursor.execute(
                "INSERT INTO campanhas (cod, nome, latitude, longitude, data_criacao) VALUES (?, ?, ?, ?, ?)",
                (cod, nome, lat, lon, ts)
            )
            criadas += 1
            novas.append({"cod": cod, "nome": nome, "latitude": lat, "longitude": lon})
        except Exception as e:
            logger.error(f"❌ Erro ao inserir campanha {cod} - {nome}: {e}")
            ignoradas += 1
            continue

    conn.commit()
    conn.close()
    logger.info(f"📦 Importação finalizada: {criadas} criadas, {ignoradas} ignoradas")

    if novas:
        socketio.emit('nova_campanha', {'tipo': 'nova_campanha', 'dados': novas})
        logger.debug("📡 WebSocket emitido com novas campanhas")

    return jsonify({
        "success": True,
        "mensagem": f"✅ {criadas} campanha(s) importada(s), {ignoradas} ignorada(s)",
        "criadas": criadas,
        "ignoradas": ignoradas
    }), 200

@campaign_bp.route('/mapa-dados')
@login_required
def mapa_dados():
    conn = get_db_connection()
    pontos = conn.execute("""
        SELECT id, cod, nome, latitude, longitude
        FROM campanhas
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchall()
    conn.close()
    dados_mapa = [dict(p) for p in pontos]
    return jsonify(dados_mapa)
