from flask import Flask

def create_app():
    app = Flask(__name__)
    # … registra blueprints aqui …
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.methods} -> {rule.rule}")
    return app