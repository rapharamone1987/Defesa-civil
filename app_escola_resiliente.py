import streamlit as st
import pandas as pd
import requests
import base64
import os
import re
import html
from PIL import Image, ImageOps
import io

# ReportLab para geração do PDF Oficial RS sem erros de HTML
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Configuração da Página
st.set_page_config(
    page_title="Escola Segura — Defesa Civil RS",
    page_icon="🛡️",
    layout="wide"
)

# 2. CSS de Alto Contraste
st.markdown("""
    <style>
    h1, h2, h3, h4, h5, h6, 
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
    .stMarkdown p, .stMarkdown li, .stCaption, span, label {
        color: var(--text-color) !important;
        word-wrap: break-word !important;
        white-space: normal !important;
    }

    div[data-testid="stFileUploader"] {
        background-color: var(--secondary-background-color) !important;
        border: 2px dashed var(--text-color) !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    .card-alerta {
        background-color: var(--secondary-background-color) !important;
        border: 2px solid #dc2626 !important;
        border-left: 8px solid #dc2626 !important;
        padding: 18px !important;
        border-radius: 10px !important;
        margin-bottom: 14px !important;
    }
    
    .card-seguro {
        background-color: var(--secondary-background-color) !important;
        border: 2px solid #16a34a !important;
        border-left: 8px solid #16a34a !important;
        padding: 18px !important;
        border-radius: 10px !important;
        margin-bottom: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Escola Segura")
st.caption("Sistema Tático de Mapeamento de Riscos e Zonas de Abrigo Escolar — Defesa Civil RS")
st.markdown("---")

# 3. Chave da API Groq
def obter_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and hasattr(st, "secrets"):
        api_key = st.secrets.get("GROQ_API_KEY", None)
    return api_key

API_KEY_GROQ = obter_groq_api_key()

# 4. Tratamento e Rotação EXIF de Fotos
def otimizar_e_corrigir_orientacao(file_bytes, max_dim=1024, qualidade=80):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((max_dim, max_dim))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=qualidade)
        b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img, b64_str, buffer.getvalue()
    except Exception:
        img_raw = Image.open(io.BytesIO(file_bytes))
        b64_raw = base64.b64encode(file_bytes).decode('utf-8')
        return img_raw, b64_raw, file_bytes

# 5. Geocodificação Exata
@st.cache_data(ttl=300)
def obter_detalhes_geograficos_exatos(lat, lon):
    detalhes = {
        "endereco_completo": f"Latitude {lat:.6f}, Longitude {lon:.6f}",
        "altitude_m": "Informação de terreno obtida via GPS"
    }
    headers = {"User-Agent": "EscolaSegura_DefesaCivilApp"}
    
    try:
        url_geo = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        res_geo = requests.get(url_geo, headers=headers, timeout=4)
        if res_geo.status_code == 200:
            data_geo = res_geo.json()
            detalhes["endereco_completo"] = data_geo.get("display_name", detalhes["endereco_completo"])
    except Exception:
        pass

    try:
        res_alt = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}", timeout=4)
        if res_alt.status_code == 200:
            data_alt = res_alt.json()
            elev_list = data_alt.get("elevation", [])
            if elev_list:
                detalhes["altitude_m"] = f"{elev_list[0]} metros (Nível do Mar)"
    except Exception:
        pass
        
    return detalhes

# Gerador do Mapa Estático para o PDF
def gerar_imagem_mapa(lat, lon):
    try:
        url = f"https://static-maps.yandex.ru/1.x/?lang=pt_BR&ll={lon},{lat}&z=15&l=map&pt={lon},{lat},pm2rdm"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

# FUNÇÃO PURIFICADORA SEGURA (Evita crash no ReportLab)
def purificar_texto_laudo(texto_bruto):
    if not texto_bruto:
        return ""
    
    # 1. Elimina texto de raciocínio prévio em inglês
    match_inicio = re.search(r'(1\.\s*Diagnóstico\s*Geográfico.*)', texto_bruto, re.DOTALL | re.IGNORECASE)
    if match_inicio:
        texto_bruto = match_inicio.group(1)
    else:
        match_alt = re.search(r'(###?\s*1\..*)', texto_bruto, re.DOTALL | re.IGNORECASE)
        if match_alt:
            texto_bruto = match_alt.group(1)

    # 2. Limpa tags ou marcadores indesejados
    texto_bruto = re.sub(r'(?i)(analyze user input|deconstruct|thinking process|draft).*?\n\n', '', texto_bruto, flags=re.DOTALL)
    
    # 3. Escapa HTML perigoso antes de aplicar negrito/itálico do Markdown
    texto_linhas = texto_bruto.split('\n')
    linhas_processadas = []
    
    for l in texto_linhas:
        l_str = l.strip()
        if not l_str:
            continue
            
        # Converte Markdown para tags seguras
        l_str = re.sub(r'\*\*(.*?)\*\*', r'__BOLD_START__\1__BOLD_END__', l_str)
        l_str = re.sub(r'\*(.*?)\*', r'__ITALIC_START__\1__ITALIC_END__', l_str)
        
        # Escapa caracteres como < e >
        l_str = html.escape(l_str)
        
        # Restaura as tags seguras
        l_str = l_str.replace('__BOLD_START__', '<b>').replace('__BOLD_END__', '</b>')
        l_str = l_str.replace('__ITALIC_START__', '<i>').replace('__ITALIC_END__', '</i>')
        
        # Remove marcas brutas
        l_str = re.sub(r'^#+\s*', '', l_str)
        l_str = l_str.replace("■", "").replace("•", "").replace("`", "").strip()
        
        linhas_processadas.append(l_str)
        
    return "\n".join(linhas_processadas)

# 6. GERADOR DE PDF
def gerar_pdf_estilo_oficial_rs(nome_escola, municipio, dados_geo, laudo_texto, fotos_bytes, mapa_bytes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    VERMELHO_RS = colors.HexColor("#b91c1c")
    VERDE_RS = colors.HexColor("#15803d")
    AMARELO_RS = colors.HexColor("#f59e0b")
    CINZA_FUNDO = colors.HexColor("#f8fafc")
    TEXTO_ESCURO = colors.HexColor("#0f172a")
    
    style_header_title = ParagraphStyle(
        'HeaderTitle', parent=styles['Heading1'],
        fontSize=14, leading=18, textColor=colors.HexColor("#ffffff"), fontName="Helvetica-Bold", alignment=1
    )
    style_sec_title = ParagraphStyle(
        'SecTitle', parent=styles['Heading2'],
        fontSize=12, leading=16, textColor=VERMELHO_RS, spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold"
    )
    style_cell_header = ParagraphStyle(
        'CellHeader', parent=styles['Normal'],
        fontSize=10, leading=13, textColor=VERDE_RS, fontName="Helvetica-Bold"
    )
    style_cell_body = ParagraphStyle(
        'CellBody', parent=styles['Normal'],
        fontSize=10.5, leading=14.5, textColor=TEXTO_ESCURO, fontName="Helvetica"
    )

    story = []

    # Banner Superior
    banner_data = [[Paragraph("<b>DEFESA CIVIL — RELATÓRIO TÁTICO ESCOLA SEGURA (RS)</b>", style_header_title)]]
    t_banner = Table(banner_data, colWidths=[540])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), VERMELHO_RS),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_banner)
    
    faixa_data = [["", ""]]
    t_faixa = Table(faixa_data, colWidths=[270, 270], rowHeights=[3])
    t_faixa.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), AMARELO_RS),
        ('BACKGROUND', (1, 0), (1, 0), VERDE_RS),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_faixa)
    story.append(Spacer(1, 10))

    # Identificação Geral
    story.append(Paragraph("<b>1. DADOS DE IDENTIFICAÇÃO E LOCALIZAÇÃO DO PONTO EXATO</b>", style_sec_title))
    
    dados_id = [
        [Paragraph("<b>Nome do Estabelecimento:</b>", style_cell_header), Paragraph(html.escape(nome_escola), style_cell_body)],
        [Paragraph("<b>Município / Estado:</b>", style_cell_header), Paragraph(html.escape(municipio), style_cell_body)],
        [Paragraph("<b>Microlocalização Geocodificada:</b>", style_cell_header), Paragraph(html.escape(dados_geo['endereco']), style_cell_body)],
        [Paragraph("<b>Altitude do Terreno:</b>", style_cell_header), Paragraph(html.escape(dados_geo['altitude']), style_cell_body)],
        [Paragraph("<b>Emissão do Laudo:</b>", style_cell_header), Paragraph("Plataforma Digital Escola Segura (Auditoria Técnica)", style_cell_body)]
    ]
    t_id = Table(dados_id, colWidths=[160, 380])
    t_id.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CINZA_FUNDO),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('BOX', (0, 0), (-1, -1), 1, VERDE_RS),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_id)
    story.append(Spacer(1, 10))

    # Mapa no PDF
    if mapa_bytes:
        story.append(Paragraph("<b>MAPA DE LOCALIZAÇÃO DO TERRENO</b>", style_sec_title))
        img_mapa_io = io.BytesIO(mapa_bytes)
        rl_mapa = RLImage(img_mapa_io, width=540, height=180)
        story.append(rl_mapa)
        story.append(Spacer(1, 10))

    # Diagnóstico Técnico
    story.append(Paragraph("<b>2. DIAGNÓSTICO DE RISCO E RECOMENDAÇÕES TÁTICAS DE ABRIGO</b>", style_sec_title))
    
    texto_purificado = purificar_texto_laudo(laudo_texto)
    linhas = texto_purificado.split("\n")
    
    for l in linhas:
        if not l or "analyze" in l.lower() or "draft" in l.lower():
            continue
            
        try:
            if l.startswith("1.") or l.startswith("2.") or l.startswith("3.") or l.startswith("4."):
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"<b>{l}</b>", style_sec_title))
                story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO_RS, spaceAfter=4))
            elif l.startswith("- ") or l.startswith("* "):
                texto_item = l.lstrip("-* ").strip()
                story.append(Paragraph(f"• {texto_item}", style_cell_body))
                story.append(Spacer(1, 2))
            else:
                story.append(Paragraph(l, style_cell_body))
                story.append(Spacer(1, 3))
        except Exception:
            # Fallback seguro contra erros de parser
            texto_limpo_plano = re.sub(r'<[^>]+>', '', l)
            story.append(Paragraph(texto_limpo_plano, style_cell_body))
            story.append(Spacer(1, 3))

    # Fotos Vistoriadas no PDF
    if fotos_bytes:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>3. REGISTROS FOTOGRÁFICOS DOS AMBIENTES AUDITADOS</b>", style_sec_title))
        
        tabela_fotos_data = []
        linha_atual = []
        
        for i, f_byte in enumerate(fotos_bytes):
            f_io = io.BytesIO(f_byte)
            rl_img = RLImage(f_io, width=250, height=160)
            cap = Paragraph(f"<b>Foto {i+1}</b>", style_cell_body)
            cell_box = [rl_img, Spacer(1, 2), cap]
            linha_atual.append(cell_box)
            
            if len(linha_atual) == 2:
                tabela_fotos_data.append(linha_atual)
                linha_atual = []
                
        if linha_atual:
            if len(linha_atual) == 1:
                linha_atual.append("")
            tabela_fotos_data.append(linha_atual)
            
        t_fotos = Table(tabela_fotos_data, colWidths=[270, 270])
        t_fotos.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_fotos)

    doc.build(story)
    buffer.seek(0)
    return buffer

# 7. MOTOR IA
def analisar_lote_escola(imagens_b64_list, nome_escola, municipio, dados_geo_exatos, obs_gerais):
    if not API_KEY_GROQ:
        return "⚠️ Chave `GROQ_API_KEY` não foi encontrada nos Secrets do Streamlit."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY_GROQ}"
    }

    prompt_sistema = """
    Você é um Engenheiro Sênior da Defesa Civil do Rio Grande do Sul e está emitindo um LAUDO TÉCNICO OFICIAL DE SEGURANÇA ESCOLAR.

    REGRAS INVIOLÁVEIS:
    1. Escreva a resposta DIRETA em Português do Brasil.
    2. NUNCA gere introduções em inglês, rascunhos, análises do prompt ou frases como "Analyze User Input".
    3. Comece a resposta IMEDIATAMENTE pelo título "1. Diagnóstico Geográfico da Microlocalização Exata".

    ESTRUTURA DA RESPOSTA:

    1. Diagnóstico Geográfico da Microlocalização Exata
    Avalie a vulnerabilidade geotécnica e hidrológica das coordenadas ({coords}) e altitude ({altitude}).

    2. Auditoria Detalhada dos Ambientes Anexados
    Para cada uma das {num_fotos} foto(s) enviadas:
    - Foto X: Identifique o cômodo e detalhe fragilidades físicas (forro leve, fiação exposta, móveis instáveis, vidros).

    3. Matriz Tática de Abrigo e Posicionamento Espacial
    Especifique a LOCALIZAÇÃO EXATA no espaço das fotos para proteção:
    - Vendavais / Microexplosões: Posição exata abaixo de peitoris ou cantos opostos às janelas.
    - Enxurradas Rápidas: Rotas de elevação vertical para pavimentos superiores.
    - Granizo Severo: Áreas com proteção sob laje sólida de concreto.

    4. Plano de Ação Imediata (Primeiros 3 Minutos)
    Ações práticas em tópicos para a equipe escolar.
    """

    prompt_detalhado = prompt_sistema.format(
        coords=dados_geo_exatos['endereco'],
        altitude=dados_geo_exatos['altitude'],
        num_fotos=len(imagens_b64_list)
    )

    content_payload = [
        {
            "type": "text", 
            "text": f"Escola: '{nome_escola}' ({municipio}). Observações do Gestor: '{obs_gerais}'."
        }
    ]

    for img_b64 in imagens_b64_list:
        content_payload.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}"
            }
        })

    payload = {
        "messages": [
            {"role": "system", "content": prompt_detalhado},
            {"role": "user", "content": content_payload}
        ],
        "model": "qwen/qwen3.6-27b",
        "temperature": 0.0
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=40)
        if res.status_code == 200:
            conteudo = res.json()['choices'][0]['message']['content']
            return purificar_texto_laudo(conteudo)
        else:
            return f"⚠️ Erro no processamento da IA (Código HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Erro de conexão com a API de Visão: {e}"

# =========================================================
# FLUXO PRINCIPAL DA APLICAÇÃO
# =========================================================

# 1. IDENTIFICAÇÃO DA ESCOLA
st.subheader("📋 1. Identificação do Estabelecimento de Ensino")

col_f1, col_f2 = st.columns(2)
with col_f1:
    nome_escola = st.text_input("Nome Completo da Escola:", "EEEB Marquês de Herval")
with col_f2:
    municipio_input = st.text_input("Município / Estado:", "Osório / RS")

obs_gerais = st.text_area(
    "Observações Gerais da Estrutura ou Histórico de Eventos Extremos na Escola:",
    "."
)

st.markdown("---")

# 2. GEOLOCALIZAÇÃO DINÂMICA
st.subheader("📍 2. Localização Geográfica de Precisão")
st.caption("Ajuste as coordenadas ou utilize o endereço geocodificado automático do local.")

col_c1, col_c2 = st.columns(2)
with col_c1:
    lat_input = st.number_input("Latitude Coletada:", value=-29.887200, format="%.6f")
with col_c2:
    lon_input = st.number_input("Longitude Coletada:", value=-50.264100, format="%.6f")

geo_exata = obter_detalhes_geograficos_exatos(lat_input, lon_input)

st.info(f"📌 **Localização Geocodificada:** {geo_exata['endereco_completo']}")
st.success(f"🏔️ **Altitude Exata no Terreno:** {geo_exata['altitude_m']}")

df_mapa = pd.DataFrame({"lat": [lat_input], "lon": [lon_input]})
st.map(df_mapa, zoom=15)

geo_payload = {
    "endereco": f"Lat {lat_input:.6f}, Lon {lon_input:.6f} ({geo_exata['endereco_completo']})",
    "altitude": geo_exata['altitude_m']
}

st.markdown("---")

# 3. UPLOAD DE FOTOS
st.subheader("📸 3. Registros Fotográficos dos Ambientes da Escola")
st.caption("Selecione fotos das salas de aula, corredores, ginásio, pátio externo e planta baixa.")

arquivos_uploaded = st.file_uploader(
    "Carregue as fotos dos ambientes da escola (Selecione vários arquivos JPG/PNG):", 
    type=["jpg", "png", "jpeg"],
    accept_multiple_files=True
)

lote_b64 = []
fotos_raw_list = []

if arquivos_uploaded:
    st.write(f"📂 **{len(arquivos_uploaded)} foto(s) carregada(s):**")
    cols = st.columns(min(len(arquivos_uploaded), 4))
    
    for i, file in enumerate(arquivos_uploaded):
        img_corrigida, b64_str, raw_bytes = otimizar_e_corrigir_orientacao(file.getvalue())
        lote_b64.append(b64_str)
        fotos_raw_list.append(raw_bytes)
        
        with cols[i % 4]:
            st.image(img_corrigida, caption=f"Foto {i+1}: {file.name}", use_container_width=True)

st.markdown("---")

# 4. AUDITORIA & RELATÓRIO PDF
st.subheader("🛡️ 4. Laudo Técnico Tático & Plano de Contingência Escolar")

if arquivos_uploaded:
    if st.button("🚨 Gerar Plano Tático de Abrigo & Relatório PDF (IA)", type="primary"):
        with st.spinner("Analisando fotos, purificando laudo e compilando PDF oficial..."):
            laudo_completo = analisar_lote_escola(lote_b64, nome_escola, municipio_input, geo_payload, obs_gerais)
            st.session_state["laudo_unificado"] = laudo_completo
            
            # Gera imagem do mapa estático
            mapa_bytes = gerar_imagem_mapa(lat_input, lon_input)
            
            # Gera o PDF oficial do RS com purificação de HTML
            pdf_bytes = gerar_pdf_estilo_oficial_rs(
                nome_escola, municipio_input, geo_payload, laudo_completo, fotos_raw_list, mapa_bytes
            )
            st.session_state["pdf_bytes"] = pdf_bytes

    if "laudo_unificado" in st.session_state and st.session_state["laudo_unificado"]:
        st.markdown(st.session_state["laudo_unificado"])
        
        st.markdown("---")
        if "pdf_bytes" in st.session_state:
            st.download_button(
                label="📄 Baixar Relatório Oficial em PDF (Escola Segura RS)",
                data=st.session_state["pdf_bytes"],
                file_name=f"Relatorio_Escola_Segura_{nome_escola.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )
else:
    st.info("👈 Faça o upload das fotos dos ambientes da escola acima para habilitar o diagnóstico da IA e a emissão do PDF.")

st.markdown("---")

# 5. GUIA RÁPIDO VISUAL
st.subheader("🚨 Guia de Diretrizes Rápidas da Defesa Civil")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="card-alerta">
        <h4>💨 Vendavais & Microexplosões</h4>
        <ul>
            <li><b>Evitar:</b> Ginásios, auditórios e salas com janelas amplas.</li>
            <li><b>Ação:</b> Mover alunos para 
