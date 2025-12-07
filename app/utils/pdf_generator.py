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
import gc  # Importante para forçar limpeza de memória

from flask import current_app
from app.utils.database import get_db_connection
from app.services.dropbox_service import DropboxService
from sqlalchemy import text 

from services.celery_config import celery_app

# ✅ Definição Global de Cor
magenta = Color(0.95, 0.2, 0.5)

# Importar o serviço de cache (HTTP/Upstash)
from app.services.cache_service import cache_service

# Instancia única do serviço Dropbox
dropbox_service = DropboxService()

# 🔗 Monta URL pública e direta do Dropbox (COM CACHE)
def montar_url_dropbox(imagem_path):
    if not imagem_path:
        return None
    
    # 1. Tenta buscar no cache
    cache_key = f"dropbox_url:{imagem_path}"
    cached_url = cache_service.get(cache_key)

    if cached_url:
        return cached_url
        
    try:
        if imagem_path.startswith("http://") or imagem_path.startswith("https://"):
            return imagem_path

        # Chama API do Dropbox
        url = dropbox_service.create_shared_link(imagem_path)
        if url and "dropbox.com" in url:
            url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
        
        # 2. Salva no cache por 24h
        if url:
            cache_service.set(cache_key, url, ttl=86400)
            
        return url
    except Exception as e:
        print(f"⚠️ Erro ao montar URL do Dropbox: {e}")
        return None

# 🔍 Converte coordenadas (COM CACHE)
def buscar_localizacao(lat, lng):
    if not lat or not lng:
        return None, None
        
    lat_short = round(float(lat), 5)
    lng_short = round(float(lng), 5)
    cache_key = f"location:{lat_short}:{lng_short}"
    
    cached_location = cache_service.get(cache_key)
    
    if cached_location:
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
            
            result = {'bairro': bairro, 'cidade': cidade}
            cache_service.set(cache_key, result, ttl=604800)
            
            return bairro, cidade
    except Exception as e:
        print(f"⚠️ Erro ao buscar localização: {e}")
    return None, None

def gerar_registros_dinamicos_por_campanha(nome_campanha: str) -> list[dict]:
    conn = get_db_connection()
    # Query otimizada
    rows = conn.execute(text("""
        SELECT
            c.id, c.cod, c.nome, c.latitude, c.longitude, i.imagem_path
        FROM campanhas AS c
        INNER JOIN campanhas_imagens AS i ON i.campanha_id = c.id
        WHERE c.nome = :nome_campanha AND i.apagada = 0
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
    return resultado

# =======================================================
# ✅ FUNÇÃO PRINCIPAL TRANSFORMADA EM TAREFA CELERY
# =======================================================
@celery_app.task(bind=True, name='tasks.gerar_pdf_relatorio')
def gerar_pdf_task(self, nome_campanha, pi_numero=None, data_inicio=None, data_fim=None, imagem_dinamica=None):
    
    # 1. Obtenção de Registros (Chamada dentro da Task!)
    registros = gerar_registros_dinamicos_por_campanha(nome_campanha)
    
    # 2. Chama a função de processamento pesado
    caminho_pdf = gerar_pdf_por_nome(
        registros=registros,
        nome_campanha=nome_campanha,
        pi_numero=pi_numero,
        data_inicio=data_inicio,
        data_fim=data_fim,
        imagem_dinamica=imagem_dinamica # Note: Passar FileStorage aqui pode ser complexo, passe o caminho se for o caso.
    )

    if not caminho_pdf:
        # A tarefa falhou em gerar o PDF
        raise Exception("Nenhum registro válido para gerar PDF.")
        
    # 3. Retorna o caminho do arquivo gerado
    return caminho_pdf

# --- FUNÇÃO PRINCIPAL OTIMIZADA (SEM THREAD POOL / BAIXO CONSUMO DE RAM) ---
def gerar_pdf_por_nome(registros, nome_campanha="campanha", pi_numero=None, data_inicio=None, data_fim=None, imagem_dinamica=None):
    
    registros_com_foto = [r for r in registros if r.get("imagens")]
    if not registros_com_foto:
        print("🚫 Nenhum espaço com imagem. PDF não será gerado.")
        return None

    # Configuração do PDF
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

    # === CAPA ===
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
        # Formatação de datas omitida para brevidade (mantém a lógica original se quiser)
        c.setFont("Helvetica", 12)
        c.drawCentredString(largura / 2, altura - 8.8 * cm, f"Período: {data_inicio} até {data_fim}")
        
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

    if imagem_dinamica:
        caminho_imagem_path = imagem_dinamica # Assumindo que o nome do parâmetro é 'imagem_dinamica'

        try:
            # Verifica se o caminho existe e não é nulo
            if os.path.exists(caminho_imagem_path):
                
                # 1. Abre o arquivo do disco no modo binário de leitura
                with open(caminho_imagem_path, 'rb') as f:
                    # 2. Carrega o conteúdo na memória como um stream
                    stream = io.BytesIO(f.read())
                
                # 3. Processamento ReportLab com o stream na memória
                if stream:
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
                    del img_reader # Libera memória

            else:
                print(f"⚠️ Aviso: Arquivo temporário não encontrado no caminho: {caminho_imagem_path}")

        except Exception as e:
            print(f"⚠️ Erro ao renderizar imagem de capa do disco: {e}")

    # === DESENHO DOS SLIDES (SEQUENCIAL PARA ECONOMIZAR RAM) ===
    print(f"ℹ️ Iniciando geração sequencial de {len(registros_com_foto)} registros para economizar memória.")
    
    # Criamos uma sessão única para reutilizar conexão HTTP (mais rápido)
    with requests.Session() as session:
        for reg in registros_com_foto:
            espaco = reg.get("espaco", "Espaço não informado")
            nome = reg.get("nome")
            lat, lng = reg.get("latitude"), reg.get("longitude")
            
            bairro, cidade = buscar_localizacao(lat, lng) if lat and lng else (None, None)
            local_text = f"{bairro}, {cidade}" if bairro and cidade else cidade or "Localização indisponível"

            # Itera sobre as imagens deste registro
            for imagem_path in reg["imagens"]:
                try:
                    # 1. Obtém URL (Cache ou Dropbox)
                    url = montar_url_dropbox(imagem_path)
                    if not url:
                        continue

                    # 2. Baixa a imagem (apenas esta!)
                    resp = session.get(url, timeout=10)
                    if resp.status_code != 200:
                        print(f"❌ Falha ao baixar imagem: {resp.status_code}")
                        continue
                    
                    # 3. Carrega na memória RAM (temporariamente)
                    image_data_io = io.BytesIO(resp.content)
                    img = ImageReader(image_data_io)

                    # 4. Desenha no PDF
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
                    
                    # 5. LIMPEZA CRÍTICA DE MEMÓRIA 🧹
                    del img
                    del image_data_io
                    # Força o coletor de lixo do Python a liberar a memória agora
                    gc.collect() 

                except Exception as e:
                    print(f"❌ Erro ao processar imagem {imagem_path}: {e}")

    # === PÁGINA FINAL ===
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
    print("✅ PDF gerado com sucesso!")
    return caminho_pdf