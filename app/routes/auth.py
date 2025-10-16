# app/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from werkzeug.security import check_password_hash
from functools import wraps

# <<< ADICIONAR: Importe as funções do Flask-Login e sua classe User >>>
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User, db # Assumindo que db e User estão em models.py

auth = Blueprint('auth', __name__)


# <<< AJUSTADO: Este decorador agora usa o sistema do Flask-Login >>>
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # A verificação de login já é feita pelo @login_required que usaremos em conjunto
        if not current_user.is_authenticated or not current_user.is_admin:
            # Pode redirecionar ou mostrar uma página de erro 403 (Acesso Negado)
            return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

# NOTA: O seu decorador @login_required manual não é mais necessário.
# Vamos usar o @login_required que importamos do flask_login em todas as rotas.


@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver logado, redireciona para o dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form.get('usuario') or request.form.get('username')
        password = request.form.get('senha') or request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Busca o usuário no banco usando SQLAlchemy (mais limpo)
        user = User.query.filter_by(username=username).first()

        # Verifica se o usuário existe e a senha está correta
        if not user or not check_password_hash(user.senha, password):
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('auth.login'))

        # --- MUDANÇA MAIS IMPORTANTE ---
        # Em vez de 'session['usuario'] = u', usamos a função do Flask-Login
        # Ela vai criar o "cartão de acesso" eletrônico (a sessão segura).
        login_user(user, remember=remember)
        
        # Redireciona para a página 'next' se ela existir, ou para o dashboard
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.dashboard'))

    return render_template('login.html')


@auth.route('/logout')
@login_required # Boa prática: só quem está logado pode fazer logout
def logout():
    # <<< AJUSTADO: Usa a função de logout do Flask-Login >>>
    logout_user()
    return redirect(url_for('auth.login'))