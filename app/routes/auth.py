# app/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, abort
from werkzeug.security import check_password_hash
from functools import wraps

from flask_login import login_user, logout_user, login_required, current_user
from ..models import User

auth = Blueprint('auth', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', 0):
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        payload = request.get_json(silent=True) if request.is_json else None
        form_data = request.form if not payload else payload

        username = (form_data.get('usuario') or form_data.get('username') or '').strip()
        password = (form_data.get('senha') or form_data.get('password') or '').strip()
        remember = bool(form_data.get('remember')) if isinstance(form_data, dict) else False

        if not username or not password:
            flash('Usuário e senha são obrigatórios.')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.senha, password):
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard.dashboard'))

    return render_template('login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))