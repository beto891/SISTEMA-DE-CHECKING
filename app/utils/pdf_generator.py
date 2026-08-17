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
from flask import current_app
from app.utils.database import get_db_connection
from app.services.dropbox_service import DropboxService

# 🔗 Monta URL pública e direta do Dropbox
def montar_url_dropbox(imagem_path):
    if not imagem_path:
        return None
    try:
        if imagem_path.startswith("http://") or imagem_path.startswith("https://"):
            return imagem_path

        service = DropboxService()
        url = None if service.dbx is None else service.create_shared_link(imagem_path)
        if url and "dropbox.com" in url:
            url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
        return url
    except Exception as e:
        print(f"⚠️ Erro ao montar URL do Dropbox: {e}")
        return None

# 🔍 Converte coordenadas em bairro e cidade (OpenStreetMap)
def buscar_localizacao(lat, lng):
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
            return bairro, cidade
    except Exception as e:
        print(f"⚠️ Erro ao buscar localização: {e}")
    return None, None
def gerar_registros_dinamicos_por_campanha(nome_campanha: str) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.cod,
            c.nome,
            c.latitude,
            c.longitude,
            i.imagem_path
        FROM campanhas AS c
        LEFT JOIN campanhas_imagens AS i
        ON i.campanha_id = c.id
        WHERE LOWER(c.nome) LIKE ?
    """, (f"%{nome_campanha.lower()}%",))

    rows = cursor.fetchall()
    agrup = {}

    for id_, cod, nome, lat, lng, img in rows:
        key = (id_, cod, nome, lat, lng)
        agrup.setdefault(key, []).append(img)

    resultado = []
    for (id_, cod, nome, lat, lng), imgs in agrup.items():
        resultado.append({
            "cod": cod,
            "nome": nome,
            "latitude": lat,
            "longitude": lng,
            "espaco": cod or "Espaço não informado",
            "imagens": [img for img in imgs if img]
        })

    print(f"🔍 Registros com imagens para campanha '{nome_campanha}': {len(resultado)}")
    return resultado

# 🔍 Verifica se link remoto está acessível
def link_acessivel(url):
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code == 200
    except:
        return False

def gerar_pdf_por_nome(registros, nome_campanha="campanha", pi_numero=None, data_inicio=None, data_fim=None, imagem_dinamica=None):
    def carregar_imagem(path):
        try:
            if path.startswith("http://") or path.startswith("https://"):
                if not link_acessivel(path):
                    print(f"⚠️ Imagem inacessível: {path}")
                    return None
                resp = requests.get(path, stream=True, timeout=5)
                if resp.status_code == 200:
                    return ImageReader(resp.raw)
            else:
                abs_path = os.path.join(current_app.root_path, "static", path)
                if os.path.exists(abs_path):
                    return ImageReader(abs_path)
                else:
                    print(f"⚠️ Imagem local ausente: {abs_path}")
        except Exception as e:
            print(f"❌ Erro ao carregar imagem: {e}")
        return None

    registros_com_foto = [r for r in registros if r.get("imagens")]
    if not registros_com_foto:
        print("🚫 Nenhum espaço com imagem. PDF não será gerado.")
        return None

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
        magenta = Color(0.95, 0.2, 0.5)
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

    # ✅ Página dedicada à imagem enviada (após capa)
    stream = getattr(imagem_dinamica, "stream", None)
    if stream:
        try:
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
            print(f"⚠️ Erro ao renderizar imagem da campanha: {e}")

    total_imgs = 0
    imgs_carregadas = 0

    for reg in registros_com_foto:
        espaco = reg.get("espaco", "Espaço não informado")
        nome = reg.get("nome")
        lat, lng = reg.get("latitude"), reg.get("longitude")
        bairro, cidade = buscar_localizacao(lat, lng) if lat and lng else (None, None)
        local_text = f"{bairro}, {cidade}" if bairro and cidade else cidade or "Localização indisponível"

        for imagem_path in reg["imagens"]:
            total_imgs += 1
            url = montar_url_dropbox(imagem_path)
            img = carregar_imagem(url)
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

                logo2_path = os.path.join(current_app.root_path, "utils", "static", "imagens", "logo2.png")
                if os.path.exists(logo2_path):
                    logo2 = ImageReader(logo2_path)
                    lw2, lh2 = 5 * cm, 5 * cm
                    x2 = (largura - lw2) / 2
                    y2 = altura - 4 * cm
                    c.drawImage(logo2, x2, y2, width=lw2, height=lh2, preserveAspectRatio=True, mask="auto")

                c.showPage()
            except Exception as e:
                print(f"❌ Erro ao renderizar imagem: {e}")

    # === Página de agradecimento ===
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, largura, altura, fill=True, stroke=False)
    desenhar_faixas_laterais()

    magenta = Color(0.95, 0.2, 0.5)
    c.setFont("Helvetica-Bold", 46)
    c.setFillColor(magenta)
    c.drawCentredString(largura / 2, altura / 2 + 1 * cm, "Agradecemos a parceria!")

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(largura / 2, altura / 2 - 1.5 * cm, "contato@bdrops.tv   |   bdrops.tv   |   (11) 3078-0879")

    c.showPage()
    c.save()

    print(f"📸 Imagens processadas: {imgs_carregadas}/{total_imgs}")
    print(f"✅ PDF gerado com sucesso em: {caminho_pdf}")
    return caminho_pdf
