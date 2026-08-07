import streamlit as st
import pandas as pd
import requests
import base64
import os
from PIL import Image, ImageOps
import io

# Importação para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
        border: 2px solid #ef4444 !important;
        border-left: 8px solid #ef4444 !important;
        padding: 18px !important;
        border-radius: 10px !important;
        margin-bottom: 14px !important;
    }
    
    .card-seguro {
        background-color: var(--secondary-background-color) !important;
        border: 2px solid #22c55e !important;
        border-left: 8px solid #22c55e !important;
        padding: 18px !important;
        border-radius: 10px !important;
        margin-bottom: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Escola Segura")
st.caption("Sistema Tático de Mapeamento de Riscos e Zonas de Abrigo Escolar — Defesa Civil")
st.markdown("---")

# 3. Leitura da Chave API
def obter_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and hasattr(st, "secrets"):
        api_key = st.secrets.get("GROQ_API_KEY", None)
    return api_key

API_KEY_GROQ = obter_groq_api_key()

# 4. TRATAMENTO DE IMAGEM: OTIMIZAÇÃO + CORREÇÃO DE ROTAÇÃO EXIF
def otimizar_e_corrigir_orientacao(file_bytes, max_dim=1024, qualidade=75):
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

# 5. LOCALIZAÇÃO DE PRECISÃO: COORDENADAS, ENDEREÇO EXACTO & ALTITUDE NO RELEVO
@st.cache_data(ttl=300)
def obter_localizacao_ip():
    try:
        res = requests.get('https://ipapi.co/json/', timeout=4)
        if res.status_code == 200:
            data = res.json()
            return {
                "cidade": data.get("city", "Não identificada"),
                "estado": data.get("region_code", "RS"),
                "lat": float(data.get("latitude", -29.88)),
                "lon": float(data.get("longitude", -50.26))
            }
    except Exception:
        pass
    return {"cidade": "Osório", "estado": "RS", "lat": -29.88, "lon": -50.26}

@st.cache_data(ttl=3600)
def obter_detalhes_geograficos_exatos(lat, lon):
    detalhes = {
        "endereco_completo": "Coordenadas informadas diretamente no mapa",
        "altitude_m": "N/D"
    }
    headers = {"User-Agent": "EscolaSegura_DefesaCivilApp"}
    
    # 1. Geocodificação Reversa para pegar o Bairro/Rua exatos (Nominatim OSM)
    try:
        url_geo = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        res_geo = requests.get(url_geo, headers=headers, timeout=4)
        if res_geo.status_code == 200:
            data_geo = res_geo.json()
            detalhes["endereco_completo"] = data_geo.get("display_name", "Endereço geolocalizado")
    except Exception:
        pass

    # 2. Altitude exata no terreno (Open-Meteo Elevation API - Copernicus DEM 90m)
    try:
        url_alt = f"https://open-meteo.com/en/docs/elevation-api?latitude={lat}&longitude={lon}"
        res_alt = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}", timeout=4)
        if res_alt.status_code == 200:
            data_alt = res_alt.json()
            elev_list = data_alt.get("elevation", [])
            if elev_list:
                detalhes["altitude_m"] = f"{elev_list[0]} metros acima do nível do mar"
    except Exception:
        pass
        
    return detalhes

# 6. GERAÇÃO DE RELATÓRIO PDF (ReportLab)
def gerar_pdf_laudo(nome_escola, municipio, endereco_conf, laudo_texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'DocHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )
    
    story = []
    
    story.append(Paragraph("<b>DEFESA CIVIL — PLANO TÁTICO DE RESILIÊNCIA ESCOLAR</b>", title_style))
    story.append(Spacer(1, 8))
    
    info_tabela = [
        [Paragraph("<b>Estabelecimento:</b>", body_style), Paragraph(nome_escola, body_style)],
        [Paragraph("<b>Município:</b>", body_style), Paragraph(municipio, body_style)],
        [Paragraph("<b>Microlocalização Exata:</b>", body_style), Paragraph(endereco_conf, body_style)],
        [Paragraph("<b>Emissão do Laudo:</b>", body_style), Paragraph("Plataforma de Inteligência Artificial Escola Segura", body_style)]
    ]
    t = Table(info_tabela, colWidths=[130, 400])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))
    
    linhas = laudo_texto.split("\n")
    for linha in linhas:
        l = linha.strip()
        if not l:
            continue
        if l.startswith("###") or l.startswith("##"):
            texto_limpo = l.replace("#", "").strip()
            story.append(Paragraph(f"<b>{texto_limpo}</b>", heading_style))
        elif l.startswith("- ") or l.startswith("* "):
            texto_limpo = l[2:].strip()
            story.append(Paragraph(f"• {texto_limpo}", body_style))
            story.append(Spacer(1, 3))
        else:
            story.append(Paragraph(l, body_style))
            story.append(Spacer(1, 4))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

# 7. MOTOR IA (GROQ QWEN 3.6 27B VISION)
def analisar_lote_escola(imagens_b64_list, nome_escola, municipio, dados_geo_exatos, obs_gerais):
    if not API_KEY_GROQ:
        return "⚠️ Chave `GROQ_API_KEY` não foi encontrada nos Secrets do Streamlit."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY_GROQ}"
    }

    prompt_sistema = """
    Você é um Engenheiro Sênior de Defesa Civil especialista em Vistoria de Riscos Estruturais e Geográficos em Escolas.
    Sua missão é gerar um PLANO DE CONTINGÊNCIA TÁTICO E ULTRA-OBJETIVO com foco em ZONAS DE ABRIGO E SEGURANÇA baseando-se EXATAMENTE na microlocalização do terreno e fotos enviadas.

    Siga rigorosamente esta estrutura Markdown:

    ### 📍 1. Diagnóstico Geográfico da Microlocalização
    Avalie o ponto EXATO da coordenada geográfica fornecida (considerando as características do endereço, a altitude informada e a inclinação/relevo da área). Determine a suscetibilidade do terreno exato a:
    - Enxurradas / Acúmulo de água por baixada ou proximidade de corpos d'água;
    - Exposição a ventos severos e microexplosões por topo de coxilha/área descampada.

    ### 🔍 2. Análise Detalhada dos Ambientes Anexados
    Vincule DIRETAMENTE cada foto enviada (ex: Foto 1, Foto 2, Foto 3) ao seu ambiente físico e enumere suas fragilidades estruturais (ex: janelas de vidro sem película, telhamento leve, estrutura de alvenaria sem laje).

    ### 🛡️ 3. Matriz Objetiva de Abrigo por Tipo de Emergência
    Especifique EXATAMENTE para onde mover os alunos e professores em cada situação, considerando o plano físico da escola:
    - 💨 **Vendaval / Microexplosão (Vento Severo):** [ZONA DE PERIGO A EVITAR] vs [LOCAL EXATO RECOMENDADA PARA ABRIGO]
    - 🌊 **Enxurrada / Inundação Rápida:** [ZONA DE PERIGO A EVITAR] vs [PONTO EXATO DE ELEVAÇÃO/ABRIGO]
    - 🧊 **Granizo Severo:** [ZONA DE PERIGO A EVITAR] vs [SALA/CORREDOR SEGURO]

    ### 🚨 4. Protocolo Prático de Ação (Ações Imediatas nos primeiros 3 minutos)
    Instruções diretas e acionáveis para a direção, brigada escolar e professores.
    """

    content_payload = [
        {
            "type": "text", 
            "text": f"Escola: '{nome_escola}' em '{municipio}'.\nDADOS GEOGRÁFICOS EXATOS DO PONTO:\n- Coordenadas/Endereço: {dados_geo_exatos['endereco']}\n- Altitude no terreno: {dados_geo_exatos['altitude']}\nObservações do Gestor: '{obs_gerais}'.\nAnalise o conjunto de {len(imagens_b64_list)} fotos anexadas e elabore o laudo tático."
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
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": content_payload}
        ],
        "model": "qwen/qwen3.6-27b",
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=35)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ Erro no processamento da IA (Código HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Erro de conexão com a API de Visão: {e}"

# =========================================================
# FLUXO PRINCIPAL DA APLICAÇÃO (TELA PRINCIPAL)
# =========================================================

# 1. FORMULÁRIO PRINCIPAL DE CADASTRO
st.subheader("📋 1. Identificação do Estabelecimento de Ensino")

col_f1, col_f2 = st.columns(2)
with col_f1:
    nome_escola = st.text_input("Nome Completo da Escola:", "EEEB Marquês de Herval")
with col_f2:
    municipio_input = st.text_input("Município / Estado:", "Osório / RS")

obs_gerais = st.text_area(
    "Observações Gerais da Estrutura ou Histórico de Eventos Extremos na Escola:",
    "Escola com ginásio de cobertura metálica leve, salas de aula com janelas de vidro voltadas para o pátio aberto e histórico de ventos fortes na região."
)

st.markdown("---")

# 2. LOCALIZAÇÃO DO DISPOSITIVO & ANÁLISE GEOGRÁFICA DE PRECISÃO
st.subheader("📍 2. Localização Geográfica de Precisão do Terreno")
st.caption("O sistema coleta a coordenada exata para avaliar a altitude no relevo e a vulnerabilidade geomorfológica do local.")

loc_detectada = obter_localizacao_ip()

col_map1, col_map2 = st.columns([1.1, 0.9])

with col_map1:
    lat_input = st.number_input("Latitude Coletada:", value=loc_detectada['lat'], format="%.6f")
    lon_input = st.number_input("Longitude Coletada:", value=loc_detectada['lon'], format="%.6f")
    
    confirmar_loc = st.checkbox("Confirmar estas coordenadas exatas para a análise de riscos de relevo/altitude", value=True)
    
    if confirmar_loc:
        geo_exata = obter_detalhes_geograficos_exatos(lat_input, lon_input)
        st.success(f"📌 **Endereço Geocodificado:** {geo_exata['endereco_completo']}")
        st.info(f"🏔️ **Altitude Exata no Terreno:** {geo_exata['altitude_m']}")
        
        geo_payload = {
            "endereco": f"Lat {lat_input}, Lon {lon_input} ({geo_exata['endereco_completo']})",
            "altitude": geo_exata['altitude_m']
        }
    else:
        geo_payload = {
            "endereco": f"Município de {municipio_input} (Sem coordenadas exatas)",
            "altitude": "Genérica do município"
        }
        st.warning("⚠️ Usando geolocalização geral do município informado.")

with col_map2:
    if confirmar_loc:
        df_mapa = pd.DataFrame({"lat": [lat_input], "lon": [lon_input]})
        st.map(df_mapa, zoom=14)

st.markdown("---")

# 3. UPLOAD DE FOTOS (COM CORREÇÃO DE ROTAÇÃO EXIF)
st.subheader("📸 3. Registros Fotográficos dos Ambientes da Escola")
st.caption("Selecione fotos de salas de aula, corredores, ginásio, pátio externo e planta baixa. O sistema corrige automaticamente a rotação de fotos tiradas no celular.")

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

# 4. AUDITORIA & GERAÇÃO DE LAUDO / PDF
st.subheader("🛡️ 4. Laudo Técnico Tático & Plano de Contingência Escolar")

if arquivos_uploaded:
    if st.button("🚨 Gerar Plano Tático de Abrigo & Relatório PDF (IA)", type="primary"):
        with st.spinner("Analisando altitude, coordenadas exatas, fotos corrigidas e zonas de abrigo..."):
            laudo_completo = analisar_lote_escola(lote_b64, nome_escola, municipio_input, geo_payload, obs_gerais)
            st.session_state["laudo_unificado"] = laudo_completo
            
            # Gera o PDF
            end_pdf = geo_payload['endereco'] + f" | Altitude: {geo_payload['altitude']}"
            pdf_bytes = gerar_pdf_laudo(nome_escola, municipio_input, end_pdf, laudo_completo)
            st.session_state["pdf_bytes"] = pdf_bytes

    if "laudo_unificado" in st.session_state and st.session_state["laudo_unificado"]:
        st.markdown(st.session_state["laudo_unificado"])
        
        st.markdown("---")
        if "pdf_bytes" in st.session_state:
            st.download_button(
                label="📄 Baixar Relatório Oficial em PDF (Escola Segura)",
                data=st.session_state["pdf_bytes"],
                file_name=f"Plano_Escola_Segura_{nome_escola.replace(' ', '_')}.pdf",
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
                
