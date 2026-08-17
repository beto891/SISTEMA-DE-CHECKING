"""Legacy routes module.

Este arquivo foi mantido apenas como referência histórica para a implementação antiga.
A aplicação em produção utiliza a factory Flask em app/__init__.py e os blueprints em app/routes/.

Qualquer importação deste módulo é intencionalmente bloqueada para evitar rotas duplicadas,
conflitos de sessão e autenticação divergentes em produção.
"""

raise RuntimeError(
    "Legacy route module disabled. Use the current application factory in app/__init__.py instead."
)
