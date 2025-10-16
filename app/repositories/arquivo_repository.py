from app.utils.database import get_db_connection

def buscar_campanha_id_por_nome(nome_campanha):
    """Busca o ID da campanha pelo nome."""
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM campanhas WHERE nome = ?", (nome_campanha,))
            campanha = cursor.fetchone()
        if campanha:
            return campanha["id"]
        else:
            print(f"⚠️ Campanha '{nome_campanha}' não encontrada.")
            return None
    except Exception as e:
        print(f"❌ Erro ao buscar campanha: {e}")
        return None

def salvar_imagem_campanha(nome_campanha, imagem_path):
    """Salva o caminho da imagem vinculada à campanha."""
    campanha_id = buscar_campanha_id_por_nome(nome_campanha)
    if campanha_id is None:
        print(f"❌ Imagem não salva: campanha '{nome_campanha}' não encontrada.")
        return False

    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campanhas_imagens (campanha_id, imagem_path)
                VALUES (?, ?)
            """, (campanha_id, imagem_path))
        print(f"📸 Imagem '{imagem_path}' vinculada à campanha '{nome_campanha}' com sucesso.")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar imagem da campanha: {e}")
        return False

def listar_imagens_por_campanha(nome_campanha):
    """Retorna os caminhos das imagens vinculadas à campanha informada."""
    campanha_id = buscar_campanha_id_por_nome(nome_campanha)
    if campanha_id is None:
        print(f"⚠️ Campanha '{nome_campanha}' não encontrada.")
        return []

    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT imagem_path
                FROM campanhas_imagens
                WHERE campanha_id = ?
                ORDER BY id ASC
            """, (campanha_id,))
            imagens = [row["imagem_path"] for row in cursor.fetchall()]
        print(f"🖼️ {len(imagens)} imagem(ns) encontradas para a campanha '{nome_campanha}'.")
        return imagens

    except Exception as e:
        print(f"❌ Erro ao listar imagens da campanha: {e}")
        return []

def listar_todas_imagens_por_campanha():
    """Retorna todas as campanhas com suas respectivas imagens."""
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.nome AS campanha_nome, ci.imagem_path
                FROM campanhas c
                LEFT JOIN campanhas_imagens ci ON c.id = ci.campanha_id
                ORDER BY c.nome ASC, ci.id ASC
            """)
            rows = cursor.fetchall()

        campanhas = {}
        for row in rows:
            nome = row["campanha_nome"]
            imagem = row["imagem_path"]
            if nome not in campanhas:
                campanhas[nome] = []
            if imagem:
                campanhas[nome].append(imagem)

        print(f"📊 {len(campanhas)} campanha(s) listadas com imagens.")
        return campanhas

    except Exception as e:
        print(f"❌ Erro ao listar todas as imagens por campanha: {e}")
        return {}

def salvar_arquivo_no_banco(dados):
    """
    Salva os metadados de um arquivo na tabela campanhas_imagens.
    Espera um dicionário com as chaves:
    - campanha_id, imagem_path, fileid, folderid
    """
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campanhas_imagens (
                    campanha_id,
                    imagem_path,
                    fileid,
                    folderid
                ) VALUES (?, ?, ?, ?)
            """, (
                dados.get("campanha_id"),
                dados.get("imagem_path"),
                dados.get("fileid"),
                dados.get("folderid")
            ))
        print(f"📁 Arquivo '{dados.get('imagem_path')}' vinculado à campanha ID {dados.get('campanha_id')} com sucesso.")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar arquivo no banco: {e}")
        return False
    
    
def busca_arquivo_por_fileid(fileid):
    """
    Busca um registro na tabela campanhas_imagens pelo fileid.
    Retorna um dicionário com os dados ou None se não encontrar.
    """
    try:
        conn = get_db_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT campanha_id, imagem_path, fileid, folderid
                FROM campanhas_imagens
                WHERE fileid = ?
                LIMIT 1
            """, (fileid,))
            row = cursor.fetchone()
        return row if row else None

    except Exception as e:
        print(f"❌ Erro ao buscar arquivo por fileid: {e}")
        return None
