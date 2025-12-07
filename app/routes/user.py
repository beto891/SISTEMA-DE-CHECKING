from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.utils.database import get_db_connection, criar_usuario, buscar_usuario
from werkzeug.security import generate_password_hash
from app.routes.auth import admin_required
from sqlalchemy import text # <<-- NOVO: Importação obrigatória
from werkzeug.security import generate_password_hash
from flask import jsonify
from app.models import db

user_bp = Blueprint('user', __name__, url_prefix='/usuarios')

@user_bp.route('/')
@admin_required
def listar_usuarios():
    conn = get_db_connection()
    # CORREÇÃO 1: Usando text()
    usuarios = conn.execute(text("SELECT * FROM usuarios")).fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)

@user_bp.route('/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    if request.method == 'POST':
        username = request.form['usuario']
        senha = request.form['senha']
        
        # NOTE: Assumimos que 'buscar_usuario' e 'criar_usuario' foram corrigidos
        # em 'app/utils/database.py' para serem compatíveis com SQLAlchemy 2.0/PostgreSQL.
        
        if buscar_usuario(username):
            flash("Usuário já existe!", "danger")
        elif criar_usuario(username, senha):
            flash("Usuário criado com sucesso!", "success")
            return redirect(url_for('user.listar_usuarios'))
        else:
            flash("Erro ao criar usuário.", "danger")
    
    return render_template('novo_usuario.html')

@user_bp.route('/excluir/<int:user_id>', methods=['POST'])
@admin_required
def excluir_usuario(user_id):
    conn = get_db_connection()
    # CORREÇÃO 2: Usando text() e parâmetro nomeado :id
    conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": user_id})
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for('user.listar_usuarios'))

@user_bp.route('/api/user/<int:user_id>', methods=['PUT'])
@admin_required
def editar_usuario_api(user_id):
    data = request.json
    
    username = data.get('username')
    password = data.get('password')

    try:
        with db.engine.connect() as conn:
            # 1. Busca o usuário existente
            user_row = conn.execute(
                text("SELECT id FROM users WHERE id = :id"), 
                {"id": user_id}
            ).fetchone()

            if not user_row:
                return jsonify({"success": False, "message": "Usuário não encontrado."}), 404
            
            # 2. Constrói a query de atualização
            updates = []
            params = {"id": user_id}
            
            # Atualiza o username
            if username:
                updates.append("username = :username")
                params['username'] = username
                
            # Atualiza a senha (requer hashing, use a sua biblioteca de hashing)
            if password:
                # 🚨 IMPORTANTE: SUBSTITUA 'hash_password' PELA SUA FUNÇÃO REAL DE HASHING
                from werkzeug.security import generate_password_hash 
                updates.append("password = :password")
                params['password'] = generate_password_hash(password) 

            if not updates:
                return jsonify({"success": False, "message": "Nenhum dado para atualizar."}), 400
                
            # 3. Executa a atualização
            query = text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id")
            conn.execute(query, params)
            conn.commit()

            return jsonify({"success": True, "message": "Usuário atualizado com sucesso."}), 200

    except Exception as e:
        print(f"Erro ao editar usuário: {e}")
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500