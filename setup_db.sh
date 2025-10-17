#!/bin/bash
# Este script inicializa o banco de dados e cria o admin.

# 1. Executa o script de inicialização do banco (db.create_all(), etc.)
python -c "from app import create_app; with create_app().app_context(): from app.utils.database import inicializar_banco; inicializar_banco(create_app())"

# 2. Inicia o servidor Gunicorn
gunicorn run:app -k gevent -b 0.0.0.0:$PORT
```

### 2. Alterar o Comando de Start no Render

Você precisa instruir o Render a executar este novo script de inicialização do banco antes de iniciar o servidor.

| Configuração | **Start Command CORRIGIDO** |
| :--- | :--- |
| **Start Command:** | `./setup_db.sh` |

### 3. Verificar o `run.py` (Final)

Como você está usando o worker `gevent`, você **precisa** do `monkey.patch_all()` em seu `run.py`.

**Arquivo:** `run.py` (Certifique-se de que ele está assim, com o patch de socket corrigido):

```python
import gevent.monkey
# MANTENHA ESTA LINHA: Exclui o patch de socket para corrigir o erro de DNS/Lookup timed out
gevent.monkey.patch_all(socket=False) 

from app import create_app

app = create_app()

if __name__ == '__main__':
    # Esta linha é ignorada pelo Gunicorn, mas é bom manter
    app.run()
