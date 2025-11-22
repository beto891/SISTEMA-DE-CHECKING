from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib.colors import Color
from reportlab.graphics import renderPDF
from datetime import datetime
import os
import requests
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import current_app
from app.utils.database import get_db_connection
from app.services.dropbox_service import DropboxService
from sqlalchemy import text 

# ✅ Definição Global (Acessível por todo o arquivo)
magenta = Color(0.95, 0.2, 0.5)

# ◀️ NOVO: Importar o serviço de cache (necessário para o Redis)
# Certifique-se de ter criado o arquivo app/services/cache_service.py conforme orientado
from app.services.cache_service import cache_service

# 🔐 Instancia única do serviço Dropbox
dropbox_service = DropboxService()

# 🔗 Monta URL pública e direta do Dropbox (AGORA COM CACHE ⚡)
def montar_url_dropbox(imagem_path):
    if not imagem_path:
        return None
        
    # 1. Tenta buscar no cache primeiro
    cache_key = f"dropbox_url:{imagem_path}"
    cached_url = cache_service.get(cache_key)

    if cached_url:
        # print(f"ℹ️ Cache HIT (Dropbox): {imagem_path}") # Debug opcional
        return cached_url
        
    try:
        if imagem_path.startswith("http://") or imagem_path.startswith("https://"):
            return imagem_path

        # Lógica original (chama a API do Dropbox - Lenta)
        url = dropbox_service.create_shared_link(imagem_path)
        if url and "dropbox.com" in url:
            url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
        
        # 2. Se obteve sucesso, salva no cache por 24 horas (86400 segundos)
        if url:
            cache_service.set(cache_key, url, ttl=86400)
            
        return url
    except Exception as e:
        print(f"⚠️ Erro ao montar URL do Dropbox: {e}")
        return None

# 🔍 Converte coordenadas em bairro e cidade (OpenStreetMap) - AGORA COM CACHE ⚡
def buscar_localizacao(lat, lng):
    if not lat or not lng:
        return None, None
        
    # 1. Cria uma chave de cache baseada nas coordenadas
    # Arredondamos para 5 casas para agrupar consultas muito próximas
    lat_short = round(float(lat), 5)
    lng_short = round(float(lng), 5)
    cache_key = f"location:{lat_short}:{lng_short}"
    
    cached_location = cache_service.get(cache_key)
    
    if cached_location:
        # print(f"ℹ️ Cache HIT (Location): {lat}, {lng}") # Debug opcional
        return cached_location.get('bairro'), cached_location.get('cidade')
        
    url = (
        f"https://nominatim.openstreetmap.org/reverse?"
        f"format=json&lat={lat}&lon={lng}&zoom=14&addressdetails=1"
    )
    headers = {"User-Agent": "bdrops-relatorio"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("address", {})
            bairro = data.get("suburb") or data.get("neighbourhood") or data.get("quarter")
            cidade = data.get("city") or data.get("town") or data.get("county")
            
            # 2. Salva no cache por 7 dias (604800 segundos), pois endereços raramente mudam
            result = {'bairro': bairro, 'cidade': cidade}
            cache_service.set(cache_key, result, ttl=604800)
            
            return bairro, cidade
    except Exception as e:
        print(f"⚠️ Erro ao buscar localização: {e}")
    return None, None

def gerar_registros_dinamicos_por_campanha(nome_campanha: str) -> list[dict]:
    conn = get_db_connection()

    # ✅ Query Otimizada com INNER JOIN e compatível com SQLAlchemy 2.0
    rows = conn.execute(text("""
        SELECT
            c.id, c.cod, c.nome, c.latitude, c.longitude, i.imagem_path
        FROM campanhas AS c
        
        -- Garante que só retornamos campanhas que têm imagens associadas
        INNER JOIN campanhas_imagens AS i 
            ON i.campanha_id = c.id
        
        WHERE 
            c.nome = :nome_campanha  -- Filtra pelo nome exato
            AND i.apagada = 0        -- Garante que a imagem não está na lixeira
            
    """), {"nome_campanha": nome_campanha}).fetchall() 
    
    conn.close()
    
    agrup = {}
    for id_, cod, nome, lat, lng, img in rows:
        key = (id_, cod, nome, lat, lng)
        agrup.setdefault(key, []).append(img)
        
    resultado = []
    for (id_, cod, nome, lat, lng), imgs in agrup.items():
        resultado.append({
            "cod": cod, "nome": nome, "latitude": lat, "longitude": lng,
            "espaco": cod or "Espaço não informado",
            "imagens": [img for img in imgs if img]
        })
        
    print(f"🔍 Registros com imagens para campanha '{nome_campanha}': {len(resultado)}")
    return resultado

# 🔍 Verifica se link remoto está acessível (Auxiliar)
def link_acessivel(url):
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code == 200
    except:
        return False

# --- WORKER THREAD (Usa a função com cache agora) ---
def _fetch_pdf_image_worker(imagem_path, session):
    """
    Função de trabalho (worker) para thread:
    1. Obtém o link do Dropbox (agora verifica o Cache antes).
    2. Baixa os dados da imagem.
    """
    try:
        # 1. Obter link (Cache -> Dropbox API)
        url = montar_url_dropbox(imagem_path)
        if not url:
            print(f"⚠️ Falha ao obter link para: {imagem_path}")
            return (imagem_path, None)
        
        # 2. Baixar dados da imagem
        # Usa a sessão de requests passada para performance (keep-alive)
        resp = session.get(url, timeout=15) 
        
        if resp.status_code == 200:
            image_data_io = io.BytesIO(resp.content)
            img_reader = ImageReader(image_data_io)
            return (imagem_path, img_reader)
        else:
            print(f"⚠️ Imagem com status {resp.status_code}: {url}")
            return (imagem_path, None)
    except Exception as e:
        print(f"❌ Erro no worker ao processar {imagem_path}: {e}")
        return (imagem_path, None)

# --- FUNÇÃO PRINCIPAL ---
def gerar_pdf_por_nome(registros, nome_campanha="campanha", pi_numero=None, data_inicio=None, data_fim=None, imagem_dinamica=None):
    
    registros_com_foto = [r for r in registros if r.get("imagens")]
    if not registros_com_foto:
        print("🚫 Nenhum espaço com imagem. PDF não será gerado.")
        return None

    # ... (Setup do Canvas e Arquivo) ...
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    CAMINHO_STATIC = os.path.join(BASE_DIR, "static", "pdfs")
    os.makedirs(CAMINHO_STATIC, exist_ok=True)
    nome_limpo = "".join(c for c in nome_campanha if c.isalnum() or c in "_-").strip()
    caminho_pdf = os.path.join(CAMINHO_STATIC, f"B.drops - {nome_limpo}_relatorio.pdf")
    
    largura_mm = 254
    altura_mm = 159
    tamanho_personalizado = (largura_mm * mm, altura_mm * mm)
    largura, altura = tamanho_personalizado
    c = canvas.Canvas(caminho_pdf, pagesize=tamanho_personalizado)
    
    def desenhar_faixas_laterais():
        faixa_largura = 1.5 * cm
        faixa_altura = altura * 0.7
        raio = 17
        y_pos = 2 * cm
        x_esq = -0.5 * cm
        x_dir = largura - faixa_largura + 0.5 * cm
        for x in (x_esq, x_dir):
            d = Drawing(largura, altura)
            r = Rect(x, y_pos, faixa_largura, faixa_altura, rx=raio, ry=raio,
                      fillColor=magenta, strokeWidth=0, strokeColor=None)
            d.add(r)
            renderPDF.draw(d, c, 0, 0)

    # === Capa ===
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, largura, altura, fill=True, stroke=False)
    desenhar_faixas_laterais()
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(largura / 2, altura - 6 * cm, nome_campanha)
    
    if pi_numero:
        c.setFont("Helvetica", 14)
        c.drawCentredString(largura / 2, altura - 7.5 * cm, f"PI: {pi_numero}")
        
    if data_inicio and data_fim:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_inicio_formatada = data_inicio_obj.strftime('%d/%m/%Y')
        except ValueError:
            data_inicio_formatada = data_inicio
        try:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim_formatada = data_fim_obj.strftime('%d/%m/%Y')
        except ValueError:
            data_fim_formatada = data_fim
        c.setFont("Helvetica", 12)
        c.drawCentredString(largura / 2, altura - 8.8 * cm, f"Período: {data_inicio_formatada} até {data_fim_formatada}")
        
    hoje = datetime.now().strftime("%d/%m/%Y")
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(largura / 2, altura - 10.2 * cm, f"Gerado em: {hoje}")
    
    logo_path = os.path.join(current_app.root_path, "utils", "static", "imagens", "logo.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        lw, lh = 10 * cm, 10 * cm
        x = (largura - lw) / 2
        y = altura - 8.5 * cm
        c.drawImage(logo, x, y, width=lw, height=lh, preserveAspectRatio=True, mask="auto")
        
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(8.8 * cm, 1.5 * cm, "bdrops.tv - contato@bdrops.tv - (11) 3078-0879")
    c.showPage()

    # === Página dedicada à imagem enviada (após capa) ===
    stream = getattr(imagem_dinamica, "stream", None)
    if stream:
        try:
            stream.seek(0)
            if stream.read(1): # Check se tem conteudo
                stream.seek(0)
                img_reader = ImageReader(stream)
                iw, ih = img_reader.getSize()
                escala = min(largura / iw, altura / ih)
                iw *= escala
                ih *= escala
                x = (largura - iw) / 2
                y = (altura - ih) / 2
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, largura, altura, fill=True, stroke=False)
                c.drawImage(img_reader, x, y, width=iw, height=ih, preserveAspectRatio=True, mask='auto')
                c.showPage()
        except Exception as e:
            print(f"⚠️ Erro ao renderizar imagem da campanha (capa): {e}")

    
    # --- PASSO A: Coletar paths ---
    todos_os_paths = []
    for reg in registros_com_foto:
        todos_os_paths.extend(reg["imagens"])
    
    unique_paths = list(set(todos_os_paths))
    print(f"ℹ️ Gerando PDF: {len(unique_paths)} imagens únicas para baixar.")

    # --- PASSO B: Baixar em Paralelo (Agora usando Cache) ---
    imagens_prontas = {} 
    
    with requests.Session() as session:
        # max_workers=8 para equilibrar carga
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_fetch_pdf_image_worker, path, session): path for path in unique_paths}
            
            for future in as_completed(futures):
                path, img_reader = future.result()
                if img_reader:
                    imagens_prontas[path] = img_reader
                else:
                    print(f"❌ Falha ao baixar: {path}")

    print(f"ℹ️ Imagens prontas: {len(imagens_prontas)}/{len(unique_paths)}")
    
    # --- PASSO C: Desenhar ---
    total_imgs = 0
    imgs_carregadas = 0

    for reg in registros_com_foto:
        espaco = reg.get("espaco", "Espaço não informado")
        nome = reg.get("nome")
        lat, lng = reg.get("latitude"), reg.get("longitude")
        
        # Busca localização (usa cache)
        bairro, cidade = buscar_localizacao(lat, lng) if lat and lng else (None, None)
        local_text = f"{bairro}, {cidade}" if bairro and cidade else cidade or "Localização indisponível"

        for imagem_path in reg["imagens"]:
            total_imgs += 1
            img = imagens_prontas.get(imagem_path)
            
            if not img:
                continue 
            
            imgs_carregadas += 1

            try:
                w, h = img.getSize()
                escala = min((16 * cm) / w, (10 * cm) / h)
                w, h = w * escala, h * escala
                x = (largura - w) / 2
                y = (altura - h) / 2

                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, largura, altura, fill=True, stroke=False)
                desenhar_faixas_laterais()

                c.drawImage(img, x, y, width=w, height=h, preserveAspectRatio=True)

                c.setFont("Helvetica-Bold", 12)
                c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(1.5 * cm, 2.5 * cm, f"Espaço: {espaco}")

                c.setFont("Helvetica", 12)
                c.drawString(1.5 * cm, 1.8 * cm, f"Campanha: {nome}")
                c.drawString(1.5 * cm, 1.1 * cm, local_text)
                
                if data_inicio:
                     c.setFont("Helvetica-Oblique", 10)
                     c.setFillColorRGB(0.4, 0.4, 0.4)
                     c.drawRightString(largura - 1.5 * cm, 1.1 * cm, f"{data_inicio}")

                if os.path.exists(logo_path):
                     c.drawImage(logo, (largura - 5*cm)/2, altura - 4*cm, width=5*cm, height=5*cm, preserveAspectRatio=True, mask="auto")

                c.showPage()
            except Exception as e:
                print(f"❌ Erro desenho: {e}")

    # --- PÁGINA FINAL ---
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, largura, altura, fill=True, stroke=False)
    desenhar_faixas_laterais()
    c.setFont("Helvetica-Bold", 46)
    c.setFillColor(magenta)
    c.drawCentredString(largura / 2, altura / 2 + 1 * cm, "Agradecemos a parceria!")
    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(largura / 2, altura / 2 - 1.5 * cm, "contato@bdrops.tv   |   bdrops.tv   |   (11) 3078-0879")
    c.showPage()
    
    c.save()
    return caminho_pdf