import os
import sqlite3
from flask import abort, Blueprint, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.distance import geodesic
from werkzeug.utils import secure_filename
import pandas as pd
from app.utils.pdf_generator import gerar_pdf_por_nome
from main import socketio
from functools import wraps
from flask import jsonify




main = Blueprint('main', __name__, template_folder='templates')

users = {
    "admin": generate_password_hash("beto891")
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
database_path = os.path.join(BASE_DIR, 'database.db')

UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'static', 'uploads'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn

@main.route('/')
def root():
    return redirect(url_for('main.login'))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'usuario' not in session:
            # Chamada API?
            accept = request.headers.get('Accept', '')
            wants_json = request.is_json or 'application/json' in accept
            if wants_json:
                return jsonify({"erro": "Não autenticado"}), 401
            # Navegador: redireciona com mensagem
            abort(redirect(url_for('main.login')))
        return f(*args, **kwargs)
    return wrapper


@main.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        is_api = request.is_json or 'application/json' in request.headers.get('Accept','')
        data = request.get_json() if is_api else request.form
        u, p = data.get('usuario') or data.get('username'), data.get('senha') or data.get('password')

        if u in users and check_password_hash(users[u], p):
            session['usuario'] = u
            if is_api: return jsonify(mensagem="Login bem-sucedido")
            return redirect(url_for('main.inicio'))
        if is_api: return jsonify(erro="Credenciais inválidas"), 401
        return render_template('login.html', erro='Usuário ou senha inválidos')

    return render_template('login.html')


@main.route('/index')
def inicio():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))
    return render_template('index.html', usuario=session['usuario'])


@main.route('/relatorio')
def relatorio():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))
    return render_template('relatorio.html')

@main.route('/tasks', methods=['GET'])
def get_tasks():
    if 'usuario' not in session:
        abort(401)
    conn = get_db_connection()
    tarefas = conn.execute("SELECT * FROM tarefas").fetchall()
    conn.close()
    return jsonify([dict(tarefa) for tarefa in tarefas])

@main.route('/tasks', methods=['POST'])
def create_task():
    if 'usuario' not in session:
        abort(401)
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tarefas (titulo, motivo, estabelecimento, localidade, status, data_inicio, data_fim, descricao) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data.get("titulo", ""),
            data.get("motivo", ""),
            data.get("estabelecimento", ""),
            data.get("localidade", ""),
            data.get("status", ""),
            data.get("data_inicio", ""),
            data.get("data_fim", ""),
            data.get("descricao", "")
        )
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return jsonify({"id": task_id, **data}), 201

@main.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if 'usuario' not in session:
        abort(401)
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()

    # Busca os valores atuais
    tarefa_atual = cursor.execute("SELECT * FROM tarefas WHERE id=?", (task_id,)).fetchone()
    if not tarefa_atual:
        conn.close()
        return jsonify({"erro": "Tarefa não encontrada"}), 404

    # Usa os valores enviados ou mantém os antigos
    titulo = data.get("titulo", tarefa_atual["titulo"])
    motivo = data.get("motivo", tarefa_atual["motivo"])
    estabelecimento = data.get("estabelecimento", tarefa_atual["estabelecimento"])
    localidade = data.get("localidade", tarefa_atual["localidade"])
    status = data.get("status", tarefa_atual["status"])
    data_inicio = data.get("data_inicio", tarefa_atual["data_inicio"])
    data_fim = data.get("data_fim", tarefa_atual["data_fim"])
    descricao = data.get("descricao", tarefa_atual["descricao"])

    cursor.execute(
        "UPDATE tarefas SET titulo=?, motivo=?, estabelecimento=?, localidade=?, status=?, data_inicio=?, data_fim=?, descricao=? WHERE id=?",
        (titulo, motivo, estabelecimento, localidade, status, data_inicio, data_fim, descricao, task_id)
    )

    conn.commit()
    conn.close()
    return jsonify({"id": task_id, **data})

@main.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'usuario' not in session:
        abort(401)
    conn = get_db_connection()
    conn.execute("DELETE FROM tarefas WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return '', 204

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@main.route('/campanha', methods=['POST'])
def criar_campanha():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))

    nome = request.form['nome']
    campanha_id = request.form['id']
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    imagem = request.files['imagem']

    nome_arquivo = secure_filename(imagem.filename)
    caminho = os.path.join(UPLOAD_FOLDER, nome_arquivo)
    imagem.save(caminho)
    
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO campanhas (id, nome, latitude, longitude, imagem, data_criacao) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        (campanha_id, nome, latitude, longitude, nome_arquivo)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('main.listar_campanhas'))

@main.route('/ponto-proximo', methods=['POST'])
def ponto_proximo():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))

    user_lat = float(request.form['lat'])
    user_lon = float(request.form['lon'])

    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    conn.close()

    if not campanhas:
        return "Nenhuma campanha cadastrada", 404

    ponto = min(campanhas, key=lambda c: geodesic((user_lat, user_lon), (c['latitude'], c['longitude'])).km)
    return render_template('ponto.html', campanha=ponto)

@main.route('/campanhas')
def listar_campanhas():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    conn.close()

    campanhas = [dict(c) for c in campanhas]
    return render_template('campanhas.html', campanhas=campanhas)


@main.route('/importar-campanhas', methods=['POST'])
def importar_campanhas():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))

    arquivo = request.files['arquivo']
    if not arquivo:
        return "Nenhum arquivo enviado", 400

    if arquivo.filename.endswith('.csv'):
        df = pd.read_csv(arquivo)
    elif arquivo.filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(arquivo)
    else:
        return "Formato de arquivo não suportado", 400

    conn = get_db_connection()
    for _, row in df.iterrows():
        conn.execute(
            "INSERT INTO campanhas (cod, nome, latitude, longitude, imagem, data_criacao) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (
                row['cod'],
                row['nome'],
                float(row['latitude']),
                float(row['longitude']),
                row.get('imagem', '')
            )
        )
    conn.commit()
    conn.close()
    return redirect(url_for('main.listar_campanhas'))



@main.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    # Dados para o gráfico (agrupado por nome)
    campanhas = conn.execute("""
        SELECT nome, COUNT(*) as total
        FROM campanhas
        WHERE imagem IS NOT NULL AND imagem != ''
        GROUP BY nome
    """).fetchall()

    # Agrupa por cod, concatena nomes e conta quantos nomes distintos tem por cod
    registros = conn.execute("""
        SELECT 
            cod,
            GROUP_CONCAT(DISTINCT nome) as nomes,
            latitude,
            longitude,
            imagem,
            COUNT(DISTINCT nome) as total_campanhas
        FROM campanhas
        GROUP BY cod
        ORDER BY cod
    """).fetchall()
    conn.close()

    campanhas = [dict(c) for c in campanhas]
    registros = [dict(r) for r in registros]
    labels = [c['nome'] for c in campanhas]
    valores = [c['total'] for c in campanhas]
    nomes = [c['nome'] for c in campanhas]

    return render_template(
        'dashboard.html',
        campanhas=campanhas,
        labels=labels,
        valores=valores,
        nomes=nomes,
        registros=registros
    )
    
    # Rotas API para integração com o app Kivy

@main.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('usuario')
    password = data.get('senha')
    if username in users and check_password_hash(users[username], password):
        return jsonify({"success": True, "usuario": username})
    return jsonify({"success": False, "erro": "Usuário ou senha inválidos"}), 401

@main.route('/api/campanhas', methods=['GET'])
def api_campanhas():
    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    conn.close()
    return jsonify([dict(c) for c in campanhas])

@main.route('/api/nomes/<cod>', methods=['GET'])
def api_nomes_por_cod(cod):
    conn = get_db_connection()
    nomes = conn.execute("SELECT DISTINCT nome FROM campanhas WHERE cod = ?", (cod,)).fetchall()
    conn.close()
    return jsonify([n["nome"] for n in nomes]) if nomes else jsonify(["Nenhum nome encontrado"])



@UPLOAD_FOLDER = "imagens_campanha"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@main.route('/api/upload_imagem', methods=['POST'])
def upload_imagem():
    cod = request.form.get("cod")
    imagem = request.files.get("imagem")

    if not cod or not imagem:
        return "Código ou imagem ausente", 400

    filename = f"{cod}_{imagem.filename}"
    caminho = os.path.join(UPLOAD_FOLDER, filename)
    imagem.save(caminho)

    # Aqui você pode salvar o caminho no banco, se quiser
    return "Imagem recebida com sucesso", 200


@main.route('/gerar-pdf', methods=['POST'])
def gerar_pdf():
    if 'usuario' not in session:
        return redirect(url_for('main.login'))

    conn = get_db_connection()
    campanhas = conn.execute("""
        SELECT cod, nome, latitude, longitude, imagem
        FROM campanhas
        WHERE imagem IS NOT NULL AND imagem != ''
    """).fetchall()
    conn.close()

    campanhas = [dict(c) for c in campanhas]
    caminho_pdf = gerar_pdf_por_nome(campanhas)
    return redirect(url_for('main.baixar_pdf'))

@main.route('/api/campanhas')
def api_listar_campanhas():
    if 'usuario' not in session:
        return jsonify({"erro": "Não autenticado"}), 401

    conn = get_db_connection()
    campanhas = conn.execute("SELECT * FROM campanhas").fetchall()
    conn.close()

    campanhas = [dict(c) for c in campanhas]
    return jsonify(campanhas)


