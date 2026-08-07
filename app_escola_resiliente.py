import streamlit as st
import pandas as pd
import requests
import base64
import os
from PIL import Image, ImageOps
import io

# ReportLab para geração do PDF com o tema e fontes oficiais
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Configuração da Página
st.set_page_config(
    page_title="Escola Segura — Defesa Civil",
    page_icon="🛡️",
    layout="wide"
)

# 2. Estilização CSS Adaptável (Dark & Light Mode Nativo)
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

# 3. Leitura da Chave API
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
        return img, b64_str
    except Exception:
        img_raw = Image.open(io.BytesIO(file_bytes))
        b64_raw = base64.b64encode(file_bytes).decode('utf-8')
        return img_raw, b64_raw

# 5. Geocodificação Exata com Cache Dinâmico
@st.cache_data(ttl=600)
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

# 6. GERADOR DE PDF COM FORMATADORES E FONTES REFINADAS (Estilo Oficial RS)
def gerar_pdf_estilo_oficial_rs(nome_escola, municipio, dados_geo, laudo_texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    # Cores Institucionais RS
    VERMELHO_RS = colors.HexColor("#b91c1c")
    VERDE_RS = colors.HexColor("#15803d")
    AMARELO_RS = colors.HexColor("#f59e0b")
    CINZA_FUNDO = colors.HexColor("#f8fafc")
    TEXTO_ESCURO = colors.HexColor("#0f172a")
    
    # Estilos de Fontes Refinados
    style_header_title = ParagraphStyle(
        'HeaderTitle', parent=styles['Heading1'],
        fontSize=13, leading=16, textColor=colors.HexColor("#ffffff"), fontName="Helvetica-Bold", alignment=1
    )
    style_sec_title = ParagraphStyle(
        'SecTitle', parent=styles['Heading2'],
        fontSize=10.5, leading=14, textColor=VERMELHO_RS, spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold"
    )
    style_cell_header = ParagraphStyle(
        'CellHeader', parent=styles['Normal'],
        fontSize=8.5, leading=11, textColor=VERDE_RS, fontName="Helvetica-Bold"
    )
    style_cell_body = ParagraphStyle(
        'CellBody', parent=styles['Normal'],
        fontSize=8.5, leading=11.5, textColor=TEXTO_ESCURO, fontName="Helvetica"
    )

    story = []

    # Banner Superior Institucional (Barra Vermelha)
    banner_data = [[Paragraph("<b>DEFESA CIVIL — RELATÓRIO TÁTICO ESCOLA SEGURA (RS)</b>", style_header_title)]]
    t_banner = Table(banner_data, colWidths=[540])
    t_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), VERMELHO_RS),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_banner)
    
    # Faixa Amarela/Verde Decorativa
    faixa_data = [["", ""]]
    t_faixa = Table(faixa_data, colWidths=[270, 270], rowHeights=[3])
    t_faixa.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), AMARELO_RS),
        ('BACKGROUND', (1, 0), (1, 0), VERDE_RS),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t_faixa)
    story.append(Spacer(1, 8))

    # Tabela 1: Identificação Geral do Estabelecimento
    story.append(Paragraph("<b>1. DADOS DE IDENTIFICAÇÃO E LOCALIZAÇÃO DO PONTO EXATO</b>", style_sec_title))
    
    dados_id = [
        [Paragraph("<b>Nome do Estabelecimento:</b>", style_cell_header), Paragraph(nome_escola, style_cell_body)],
        [Paragraph("<b>Município / Estado:</b>", style_cell_header), Paragraph(municipio, style_cell_body)],
        [Paragraph("<b>Microlocalização Geocodificada:</b>", style_cell_header), Paragraph(dados_geo['endereco'], style_cell_body)],
        [Paragraph("<b>Altitude do Terreno no Ponto:</b>", style_cell_header), Paragraph(dados_geo['altitude'], style_cell_body)],
        [Paragraph("<b>Emissão do Laudo:</b>", style_cell_header), Paragraph("Plataforma Digital Escola Segura (Auditoria Técnica)", style_cell_body)]
    ]
    t_id = Table(dados_id, colWidths=[150, 390])
    t_id.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CINZA_FUNDO),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('BOX', (0, 0), (-1, -1), 1, VERDE_RS),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_id)
    story.append(Spacer(1, 8))

    # Tabela 2: Diagnóstico e Matriz Tática de Abrigo
    story.append(Paragraph("<b>2. DIAGNÓSTICO DE RISCO E RECOMENDAÇÕES TÁTICAS DE ABRIGO</b>", style_sec_title))
    
    linhas = laudo_texto.split("\n")
    for linha in linhas:
        l = linha.strip()
        if not l:
            continue
        if l.startswith("###") or l.startswith("##"):
            texto_limpo = l.replace("#", "").strip()
            story.append(Paragraph(f"<b>{texto_limpo}</b>", style_sec_title))
            story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO_RS, spaceAfter=3))
        elif l.startswith("- ") or l.startswith("* "):
            texto_limpo = l[2:].strip()
            story.append(Paragraph(f"• {texto_limpo}", style_cell_body))
            story.append(Spacer(1, 2))
        else:
            story.append(Paragraph(l, style_cell_body))
            story.append(Spacer(1, 2.5))

    doc.build(story)
    buffer.seek(0)
    return buffer

# 7. MOTOR IA APROFUNDADO EM PORTUGUÊS (GROQ QWEN 3.6 27B VISION)
def analisar_lote_escola(imagens_b64_list, nome_escola, municipio, dados_geo_exatos, obs_gerais):
    if not API_KEY_GROQ:
        return "⚠️ Chave `GROQ_API_KEY` não foi encontrada nos Secrets do Streamlit."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY_GROQ}"
    }

    prompt_sistema = """
    Você é um Engenheiro Sênior da Defesa Civil do Rio Grande do Sul especialista em Gestão de Riscos e Segurança Escolar.
    RESPONDA EXCLUSIVAMENTE EM PORTUGUÊS (DO BRASIL). É PROIBIDO O USO DE TERMOS EM INGLÊS.

    Analise o lote de imagens fornecido e forneça RECOMENDAÇÕES TÁTICAS ULTRA-OBJETIVAS para a proteção dos alunos.

    Siga rigorosamente esta estrutura Markdown:

    ### 📍 1. Diagnóstico Geográfico da Microlocalização Exata
    Avalie rigorosamente o ponto específico das coordenadas ({coords}) e altitude ({altitude}). Considere o bueiro/rua/bairro identificado e avalie o risco específico de acúmulo de água no terreno ou exposição a ventos severos.

    ### 🔍 2. Auditoria Detalhada dos Ambientes Anexados
    Analise cada uma das {num_fotos} foto(s) enviadas individualmente:
    - **Foto X:** Identifique o ambiente físico (ex: salas, ginásio, corredor) e descreva os pontos fortes e as fragilidades estruturais (ex: janelas de vidro, telha leve, ausência de laje).

    ### 🛡️ 3. Matriz Tática de Abrigo por Evento Extremo (Ações Práticas)
    Forneça instruções diretas e claras sobre onde abrigar os alunos:
    - 💨 **Vendavais / Microexplosões:** [Zonas Perigosas a Evitar] vs [Local Exato Recomendado para Abrigo Seguro]
    - 🌊 **Enxurradas / Inundações Rápidas:** [Zonas de Perigo a Evitar] vs [Ponto Exato de Elevação e Resgate]
    - 🧊 **Granizo Severo:** [Zonas de Perigo a Evitar] vs [Salas com Cobertura Segura]

    ### 🚨 4. Plano de Ação Imediata para Professores e Equipe (Primeiros 3 Minutos)
    Instruções operacionais claras em tópicos para a brigada escolar.
    """

    prompt_detalhado = prompt_sistema.format(
        coords=dados_geo_exatos['endereco'],
        altitude=dados_geo_exatos['altitude'],
        num_fotos=len(imagens_b64_list)
    )

    content_payload = [
        {
            "type": "text", 
            "text": f"Escola: '{nome_escola}' ({municipio}).\nObservações Adicionais: '{obs_gerais}'.\nAnalise o lote de {len(imagens_b64_list)} foto(s) e gere o laudo."
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
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=40)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ Erro no processamento da IA (Código HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Erro de conexão com a API de Visão: {e}"

# =========================================================
# FLUXO PRINCIPAL DA TELA
# =========================================================

# 1. IDENTIFICAÇÃO DA ESCOLA
st.subheader("📋 1. Identificação do Estabelecimento de Ensino")

col_f1, col_f2 = st.columns(2)
with col_f1:
    nome_escola = st.text_input("Nome Completo da Escola:", "EEEB Marquês de Herval")
with col_f2:
    municipio_input = st.text_input("Município / Estado:", "Porto Alegre / RS")

obs_gerais = st.text_area(
    "Observações Gerais da Estrutura ou Histórico de Eventos Extremos na Escola:",
    "Escola com ginásio de cobertura metálica leve, salas de aula com janelas de vidro voltadas para o pátio aberto e histórico de tempestades fortes."
)

st.markdown("---")

# 2. GEOLOCALIZAÇÃO DIRETA E DINÂMICA
st.subheader("📍 2. Localização Geográfica de Precisão (GPS do Dispositivo)")

if "lat_gps" not in st.session_state:
    st.session_state["lat_gps"] = -30.059776
if "lon_gps" not in st.session_state:
    st.session_state["lon_gps"] = -51.220223

# Campos de entrada ligados ao estado da sessão
col_coords1, col_coords2 = st.columns(2)
with col_coords1:
    lat_input = st.number_input("Latitude Coletada (GPS):", value=st.session_state["lat_gps"], format="%.6f")
with col_coords2:
    lon_input = st.number_input("Longitude Coletada (GPS):", value=st.session_state["lon_gps"], format="%.6f")

# Busca detalhes geográficos em tempo real para o ponto selecionado
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
st.caption("Selecione fotos das salas de aula, corredores, ginásio, pátio externo e planta baixa. O sistema corrige automaticamente a orientação de fotos tiradas no celular.")

arquivos_uploaded = st.file_uploader(
    "Carregue as fotos dos ambientes da escola (Selecione vários arquivos JPG/PNG):", 
    type=["jpg", "png", "jpeg"],
    accept_multiple_files=True
)

lote_b64 = []

if arquivos_uploaded:
    st.write(f"📂 **{len(arquivos_uploaded)} foto(s) carregada(s):**")
    cols = st.columns(min(len(arquivos_uploaded), 4))
    
    for i, file in enumerate(arquivos_uploaded):
        img_corrigida, b64_str = otimizar_e_corrigir_orientacao(file.getvalue())
        lote_b64.append(b64_str)
        
        with cols[i % 4]:
            st.image(img_corrigida, caption=f"Foto {i+1}: {file.name}", use_container_width=True)

st.markdown("---")

# 4. AUDITORIA & RELATÓRIO PDF
st.subheader("🛡️ 4. Laudo Técnico Tático & Plano de Contingência Escolar")

if arquivos_uploaded:
    if st.button("🚨 Gerar Plano Tático de Abrigo & Relatório PDF (IA)", type="primary"):
        with st.spinner("Analisando fotos, topografia e formulando plano prático de abrigo..."):
            laudo_completo = analisar_lote_escola(lote_b64, nome_escola, municipio_input, geo_payload, obs_gerais)
            st.session_state["laudo_unificado"] = laudo_completo
            
            # Gera o PDF no modelo oficial do RS
            pdf_bytes = gerar_pdf_estilo_oficial_rs(nome_escola, municipio_input, geo_payload, laudo_completo)
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
            <li><b>Ação:</b> Mover alunos para corredores internos com laje sólida.</li>
            <li><b>Posição:</b> Agachar de costas para aberturas, cobrindo a cabeça.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="card-alerta">
        <h4>🌊 Enxurradas Rápidas</h4>
        <ul>
            <li><b>Evitar:</b> Térreo, pátios rebaixados e subsolos.</li>
            <li><b>Ação:</b> Evacuação vertical imediata para o 2º pavimento.</li>
            <li><b>Energia:</b> Desligar chave geral antes que a água atinja tomadas.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="card-seguro">
        <h4>🛡️ Procedimento de Simulado</h4>
        <ul>
            <li><b>Frequência:</b> Realizar simulados a cada semestre.</li>
            <li><b>Alarmes:</b> Definir sons diferentes para Evacuação vs. Abrigo.</li>
            <li><b>Rotas:</b> Manter corredores livres de obstáculos.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
                                                  
