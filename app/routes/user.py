from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.utils.database import get_db_connection, criar_usuario, buscar_usuario
from werkzeug.security import generate_password_hash
from app.routes.auth import admin_required

user_bp = Blueprint('user', __name__, url_prefix='/usuarios')

@user_bp.route('/')
@admin_required
def listar_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute("SELECT * FROM usuarios").fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)

@user_bp.route('/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    if request.method == 'POST':
        username = request.form['usuario']
        senha = request.form['senha']
        if buscar_usuario(username):
            flash("Usuário já existe!", "danger")
        elif criar_usuario(username, senha):
            flash("Usuário criado com sucesso!", "success")
            return redirect(url_for('user.listar_usuarios'))
        else:
            flash("Erro ao criar usuário.", "danger")
    
    # ✅ Renderiza o formulário de cadastro corretamente
    return render_template('novo_usuario.html')

@user_bp.route('/excluir/<int:user_id>', methods=['POST'])
@admin_required
def excluir_usuario(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!", "success")
    return redirect(url_for('user.listar_usuarios'))