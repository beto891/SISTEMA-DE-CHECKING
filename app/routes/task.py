from app.utils.database import get_db_connection
from flask import Blueprint, request, jsonify, abort, session, redirect, url_for, render_template
from app.routes.auth import login_required
from app.routes.auth import admin_required

task_bp = Blueprint('task', __name__)

@task_bp.route('/')
@login_required
@admin_required
def index():
    return redirect(url_for('campaign.listar_campanhas')) 


# Outras rotas relacionadas a tarefas...
@task_bp.route('/tasks', methods=['GET'])
@login_required
@admin_required
def get_tasks():
    if 'usuario' not in session:
        abort(401)
    conn = get_db_connection()
    tarefas = conn.execute("SELECT * FROM tarefas").fetchall()
    conn.close()
    return jsonify([dict(tarefa) for tarefa in tarefas])

@task_bp.route('/tasks', methods=['POST'])
@login_required
@admin_required
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

@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
@admin_required
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

@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_task(task_id):
    if 'usuario' not in session:
        abort(401)
    conn = get_db_connection()
    conn.execute("DELETE FROM tarefas WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return '', 204

@task_bp.route('/relatorio')
@login_required
@admin_required
def relatorio():
    return render_template('relatorio.html')