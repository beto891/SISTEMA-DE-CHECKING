from app.utils.database import get_db_connection
from flask import Blueprint, request, jsonify, abort, session, redirect, url_for, render_template, current_app # CORREÇÃO: Adicionado current_app
from app.routes.auth import login_required
from app.routes.auth import admin_required
from sqlalchemy import text # Importação necessária para o SQLAlchemy 2.0

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
    try:
        # CORREÇÃO 1: Adicionar text() à query
        tarefas = conn.execute(text("SELECT * FROM tarefas")).fetchall()
        return jsonify([dict(tarefa) for tarefa in tarefas])
    except Exception as e:
        # current_app está agora corretamente importado
        current_app.logger.error(f"Erro ao buscar tarefas: {e}")
        abort(500)
    finally:
        conn.close()

@task_bp.route('/tasks', methods=['POST'])
@login_required
@admin_required
def create_task():
    if 'usuario' not in session:
        abort(401)
    data = request.json
    conn = get_db_connection()
    try:
        # CORREÇÃO 2: Adicionar text() e usar parâmetros nomeados (:nome)
        # O SQLAlchemy 2.0 com db.engine.connect() é a forma preferida.
        result = conn.execute(
            text(
                "INSERT INTO tarefas (titulo, motivo, estabelecimento, localidade, status, data_inicio, data_fim, descricao) "
                "VALUES (:titulo, :motivo, :estabelecimento, :localidade, :status, :data_inicio, :data_fim, :descricao)"
            ),
            {
                "titulo": data.get("titulo", ""),
                "motivo": data.get("motivo", ""),
                "estabelecimento": data.get("estabelecimento", ""),
                "localidade": data.get("localidade", ""),
                "status": data.get("status", ""),
                "data_inicio": data.get("data_inicio", ""),
                "data_fim": data.get("data_fim", ""),
                "descricao": data.get("descricao", "")
            }
        )
        conn.commit()
        # No PostgreSQL, o último ID inserido é geralmente recuperado via result.lastrowid
        task_id = result.lastrowid
        return jsonify({"id": task_id, **data}), 201
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao criar tarefa: {e}")
        abort(500)
    finally:
        conn.close()

@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
@admin_required
def update_task(task_id):
    if 'usuario' not in session:
        abort(401)
    data = request.json
    conn = get_db_connection()
    try:
        # CORREÇÃO 3A: Busca os valores atuais
        # Adicionar text() e usar parâmetros nomeados
        tarefa_atual = conn.execute(
            text("SELECT * FROM tarefas WHERE id=:id"),
            {"id": task_id}
        ).fetchone()

        if not tarefa_atual:
            return jsonify({"erro": "Tarefa não encontrada"}), 404

        # Busca os valores atuais para compatibilidade com SQLAlchemy 2.0 (que retorna Row)
        tarefa_dict = dict(tarefa_atual)
        
        # Usa os valores enviados ou mantém os antigos
        titulo = data.get("titulo", tarefa_dict.get("titulo"))
        motivo = data.get("motivo", tarefa_dict.get("motivo"))
        estabelecimento = data.get("estabelecimento", tarefa_dict.get("estabelecimento"))
        localidade = data.get("localidade", tarefa_dict.get("localidade"))
        status = data.get("status", tarefa_dict.get("status"))
        data_inicio = data.get("data_inicio", tarefa_dict.get("data_inicio"))
        data_fim = data.get("data_fim", tarefa_dict.get("data_fim"))
        descricao = data.get("descricao", tarefa_dict.get("descricao"))

        # CORREÇÃO 3B: Query de UPDATE
        # Adicionar text() e usar parâmetros nomeados
        conn.execute(
            text(
                "UPDATE tarefas SET titulo=:titulo, motivo=:motivo, estabelecimento=:estabelecimento, "
                "localidade=:localidade, status=:status, data_inicio=:data_inicio, data_fim=:data_fim, "
                "descricao=:descricao WHERE id=:id"
            ),
            {
                "titulo": titulo, "motivo": motivo, "estabelecimento": estabelecimento, 
                "localidade": localidade, "status": status, "data_inicio": data_inicio, 
                "data_fim": data_fim, "descricao": descricao, "id": task_id
            }
        )

        conn.commit()
        return jsonify({"id": task_id, **data})
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao atualizar tarefa: {e}")
        abort(500)
    finally:
        conn.close()

@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_task(task_id):
    if 'usuario' not in session:
        abort(401)
    conn = get_db_connection()
    try:
        # CORREÇÃO 4: Query de DELETE
        # Adicionar text() e usar parâmetros nomeados
        conn.execute(text("DELETE FROM tarefas WHERE id=:id"), {"id": task_id})
        conn.commit()
        return '', 204
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"Erro ao excluir tarefa: {e}")
        abort(500)
    finally:
        conn.close()

@task_bp.route('/relatorio')
@login_required
@admin_required
def relatorio():
    return render_template('relatorio.html')
