# Sistema de gestão de campanhas e check-in

Aplicação web em Flask para gestão de campanhas, upload de imagens, acompanhamento de entregas, relatórios e controle administrativo.

## Stack principal
- Python 3.12+
- Flask 3
- Flask-SQLAlchemy
- Flask-Login
- SQLite em desenvolvimento / PostgreSQL em produção
- Dropbox para armazenamento de mídias
- ReportLab para geração de PDFs

## Requisitos de produção
Antes de subir em ambiente real, configure as variáveis abaixo em um arquivo `.env` baseado em [.env.example](.env.example):

- `SECRET_KEY`: string forte e aleatória
- `DATABASE_URL`: conexão do banco
- `ADMIN_USERNAME`: usuário administrativo
- `ADMIN_PASSWORD`: senha administrativa
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`: caso use Dropbox

## Setup local
1. Crie um ambiente virtual:
   python -m venv .venv
2. Ative o ambiente:
   source .venv/bin/activate
3. Instale as dependências:
   pip install -r requirements.txt
4. Copie o arquivo de exemplo:
   cp .env.example .env
5. Ajuste os valores sensíveis no `.env`.
6. Inicie a aplicação:
   python main.py

## Execução em produção
Use o entrypoint oficial:

python main.py

Ou via Gunicorn com configurações profissionais:

gunicorn --config gunicorn.conf.py main:app

O arquivo [gunicorn.conf.py](gunicorn.conf.py) centraliza bind, workers, timeout e logs para facilitar deploy em Render, Railway, Heroku e servidores Linux.

## Deploy profissional
O projeto já está preparado para deploy em serviços como Render, Railway e Docker.

### Render
1. Conecte o repositório ao Render.
2. Use o arquivo [render.yaml](render.yaml) como configuração base.
3. Defina manualmente as variáveis sensíveis no painel se necessário:
   - `SECRET_KEY`
   - `ADMIN_PASSWORD`
   - `DROPBOX_APP_KEY`
   - `DROPBOX_APP_SECRET`
   - `DROPBOX_REFRESH_TOKEN`
4. O serviço usará Gunicorn com [gunicorn.conf.py](gunicorn.conf.py) e aplicação principal em [main.py](main.py).

### Docker
Use o [Dockerfile](Dockerfile) para subir o sistema em qualquer ambiente Docker-compatible:

```bash
docker build -t sistema-checking .
docker run --rm -p 8000:8000 --env-file .env sistema-checking
```

## Segurança e boas práticas
- Nunca comite `.env`.
- Nunca use senha padrão em produção.
- Mantenha `SECRET_KEY` e credenciais do Dropbox em variáveis de ambiente.
- Configure backups regulares do banco e dos arquivos armazenados.
- Atualize dependências e revise logs de autenticação e uploads.

## Migrações de banco
O projeto utiliza Alembic para versionar a estrutura do banco e evitar alterações manuais em produção.

Para gerar novas migrações:

flask db migrate -m "descricao da alteracao"

Para aplicar no ambiente atual:

flask db upgrade

## Testes e CI
Para validar o comportamento principal da aplicação:

pytest

O repositório também inclui pipeline do GitHub Actions em [.github/workflows/ci.yml](.github/workflows/ci.yml) para executar os testes automaticamente em push e pull request.

## Checklist de release
- [x] `SECRET_KEY` configurada
- [x] `ADMIN_PASSWORD` definida
- [x] `DATABASE_URL` apontando para banco de produção
- [x] Backup do banco habilitado
- [x] Credenciais do Dropbox validadas
- [x] Testes automatizados executando em CI

## Observações
O sistema passou por uma consolidação de bootstrap, autenticação, upload e documentação de produção. A camada de migrações e CI foi integrada para aproximar a base da operação profissional em ambientes reais.
