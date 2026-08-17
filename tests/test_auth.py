import os

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import User, db


def test_create_app_uses_env_configuration(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'SenhaTeste@123')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///test_app.db')

    app = create_app()

    assert app.config['SECRET_KEY'] == 'test-secret-key'
    assert app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///')


def test_login_accepts_valid_credentials(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'SenhaTeste@123')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///test_login.db')

    app = create_app()
    with app.app_context():
        db.session.query(User).delete()
        db.session.add(User(username='admin', senha=generate_password_hash('SenhaTeste@123'), is_admin=1))
        db.session.commit()

    client = app.test_client()
    response = client.post('/login', data={'usuario': 'admin', 'senha': 'SenhaTeste@123'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers.get('Location').endswith('/dashboard')


def test_login_rejects_invalid_credentials(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'SenhaTeste@123')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///test_login_invalid.db')

    app = create_app()
    with app.app_context():
        db.session.query(User).delete()
        db.session.add(User(username='admin', senha=generate_password_hash('SenhaTeste@123'), is_admin=1))
        db.session.commit()

    client = app.test_client()
    response = client.post('/login', data={'usuario': 'admin', 'senha': 'senha-errada'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers.get('Location').endswith('/login')
