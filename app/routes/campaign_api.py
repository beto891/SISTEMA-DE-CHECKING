# # app/routes/campaign_api.py (Versão Refatorada)

# from flask import Blueprint, jsonify
# from app.utils.database import get_db_connection

# # <<< IMPORTAÇÃO CORRETA >>>
# # Importe o decorador de login oficial do Flask-Login
# from flask_login import login_required

# campaign_api_bp = Blueprint('campaign_api', __name__, url_prefix='/api/campaign')


# # --- REMOÇÃO ---
# # O decorador 'api_login_required' foi removido. Usaremos o @login_required oficial.
# # As rotas '/login' e '/logout' também foram removidas. A autenticação
# # deve ser centralizada em um único lugar (no seu 'auth.py').


# # 📋 Lista de campanhas (protegida com o decorador correto)
# @campaign_api_bp.route('/json', methods=['GET'])
# @login_required
# def api_campanhas():
#     conn = get_db_connection()
#     campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
#     conn.close()
#     return jsonify([dict(c) for c in campanhas])

# # 🔍 Nomes por código (protegido com o decorador correto)
# @campaign_api_bp.route('/nomes/<cod>', methods=['GET'])
# @login_required
# def api_nomes_por_cod(cod):
#     conn = get_db_connection()
#     nomes = conn.execute("SELECT DISTINCT nome FROM campanhas WHERE cod = ?", (cod,)).fetchall()
#     conn.close()
#     return jsonify([n["nome"] for n in nomes]) if nomes else jsonify([])

# # 
# @campaign_api_bp.route('/public', methods=['GET'])
# def api_campanhas_public():
#     """Esta rota é pública e não precisa de login."""
#     conn = get_db_connection()
#     campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
#     # conn.commit() # Desnecessário para uma consulta SELECT
#     conn.close()
#     return jsonify([dict(c) for c in campanhas])