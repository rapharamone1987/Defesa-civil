import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import base64
import os
from PIL import Image, ImageOps
import io

# Importações do ReportLab para o novo PDF
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

# 3. Chave da API
def obter_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and hasattr(st, "secrets"):
        api_key = st.secrets.get("GROQ_API_KEY", None)
    return api_key

API_KEY_GROQ = obter_groq_api_key()

# 4. Trata e Corrigir Orientação de Foto EXIF
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

# 5. Geocodificação Exata e Altitude no Terreno
@st.cache_data(ttl=3600)
def obter_detalhes_geograficos_exatos(lat, lon):
    detalhes = {
        "endereco_completo": "Coordenadas informadas no dispositivo",
        "altitude_m": "N/D"
    }
    headers = {"User-Agent": "EscolaSegura_DefesaCivilApp"}
    
    try:
        url_geo = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        res_geo = requests.get(url_geo, headers=headers, timeout=4)
        if res_geo.status_code == 200:
            data_geo = res_geo.json()
            detalhes["endereco_completo"] = data_geo.get("display_name", "Endereço geolocalizado")
    except Exception:
        pass

    try:
        res_alt = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}", timeout=4)
        if res_alt.status_code == 200:
            data_alt = res_alt.json()
            elev_list = data_alt.get("elevation", [])
            if elev_list:
                detalhes["altitude_m"] = f"{elev_list[0]} metros acima do nível do mar"
    except Exception:
        pass
        
    return detalhes

# 6. DESIGN DO PDF REFORMULADO (Estilo Relatório Executivo Defesa Civil)
def gerar_pdf_laudo(nome_escola, municipio, dados_geo, laudo_texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    
    # Estilos Customizados
    style_header_title = ParagraphStyle(
        'HeaderTitle', parent=styles['Heading1'],
        fontSize=16, leading=20, textColor=colors.HexColor("#1e3a8a"), fontName="Helvetica-Bold"
    )
    style_header_sub = ParagraphStyle(
        'HeaderSub', parent=styles['Normal'],
        fontSize=10, leading=13, textColor=colors.HexColor("#475569"), fontName="Helvetica"
    )
    style_sec_title = ParagraphStyle(
        'SecTitle', parent=styles['Heading2'],
        fontSize=12, leading=16, textColor=colors.HexColor("#1e3a8a"), spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold"
    )
    style_body = ParagraphStyle(
        'BodyDark', parent=styles['Normal'],
        fontSize=9.5, leading=13.5, textColor=colors.HexColor("#1e293b"), fontName="Helvetica"
    )

    story = []

    # Cabeçalho Institucional
    story.append(Paragraph("DEFESA CIVIL — SISTEMA ESCOLA SEGURA", style_header_title))
    story.append(Paragraph("Relatório Técnico de Auditoria Estrutural e Plano Tático de Resiliência", style_header_sub))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e3a8a"), spaceAfter=12))

    # Tabela de Dados Principais
    dados_tabela = [
        [Paragraph("<b>Estabelecimento:</b>", style_body), Paragraph(nome_escola, style_body)],
        [Paragraph("<b>Município / UF:</b>", style_body), Paragraph(municipio, style_body)],
        [Paragraph("<b>Microlocalização:</b>", style_body), Paragraph(dados_geo['endereco'], style_body)],
        [Paragraph("<b>Altitude no Ponto:</b>", style_body), Paragraph(dados_geo['altitude'], style_body)],
        [Paragraph("<b>Emissão do Laudo:</b>", style_body), Paragraph("Auditoria Automatizada via IA Multimodal", style_body)]
    ]
    t = Table(dados_tabela, colWidths=[120, 410])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Conteúdo da Análise
    linhas = laudo_texto.split("\n")
    for linha in linhas:
        l = linha.strip()
        if not l:
            continue
        if l.startswith("###") or l.startswith("##"):
            texto_limpo = l.replace("#", "").strip()
            story.append(Paragraph(texto_limpo, style_sec_title))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        elif l.startswith("- ") or l.startswith("* "):
            texto_limpo = l[2:].strip()
            story.append(Paragraph(f"• {texto_limpo}", style_body))
            story.append(Spacer(1, 2))
        else:
            story.append(Paragraph(l, style_body))
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer

# 7. MOTOR IA APROFUNDADO (GROQ QWEN 3.6 27B VISION)
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
    Elabore uma auditoria EXTREMAMENTE DETALHADA, rigorosa e técnica.

    Siga rigorosamente a seguinte estrutura em Markdown:

    ### 📍 1. Diagnóstico Geográfico de Precisão (Coordenadas e Relevo)
    Avalie o ponto exato das coordenadas ({coords}) e altitude ({altitude}). Relacione com a topografia da região e defina o nível de risco geotécnico para enxurradas, deslizamentos e ventos fortes.

    ### 🔍 2. Auditoria Técnica Detalhada por Foto Anexada
    Para CADA uma das {num_fotos} fotos enviadas, crie uma subseção individualizada:
    - **Foto X:** Identifique o ambiente físico, materiais construtivos visíveis (tipo de telhado, esquadrias, vidros, lajes, estrutura de suporte), pontos fortes e VULNERABILIDADES FÍSICAS CRÍTICAS.

    ### 🛡️ 3. Matriz Objetiva de Abrigo por Tipo de Emergência
    Especifique com precisão de metros onde abrigar os alunos:
    - 💨 **Vendaval / Microexplosão (Vento Severo):** [ZONAS DE ALTO RISCO A EVITAR] vs [LOCAL EXATO MAIS SEGURO DA ESCOLA PARA ABRIGO]
    - 🌊 **Enxurrada / Inundação Rápida:** [ZONAS DE PERIGO A EVITAR] vs [PONTO EXATO DE ELEVAÇÃO/ABRIGO]
    - 🧊 **Granizo Severo:** [ZONAS DE PERIGO A EVITAR] vs [SALAS COM PROTEÇÃO SUPERIOR ADEQUADA]

    ### 🚨 4. Protocolo Tático de Ação Rápida (Primeiros 3 Minutos)
    Recomendações técnicas operacionais para a equipe diretiva e professores.
    """

    prompt_detalhado = prompt_sistema.format(
        coords=dados_geo_exatos['endereco'],
        altitude=dados_geo_exatos['altitude'],
        num_fotos=len(imagens_b64_list)
    )

    content_payload = [
        {
            "type": "text", 
            "text": f"Escola: '{nome_escola}' ({municipio}).\nObservações do Gestor: '{obs_gerais}'.\nAnalise o lote de {len(imagens_b64_list)} fotos e elabore a auditoria completa."
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
# FLUXO PRINCIPAL
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
    "Escola com ginásio de cobertura metálica leve, salas de aula com janelas de vidro voltadas para o pátio aberto e histórico de ventos fortes na região."
)

st.markdown("---")

# 2. LOCALIZAÇÃO VIA GPS DO DISPOSITIVO (HTML5 GEOLOCATION)
st.subheader("📍 2. Localização Geográfica de Precisão (GPS do Dispositivo)")
st.caption("Clique no botão abaixo para autorizar o navegador a capturar as coordenadas exatas do seu celular ou computador.")

# Componente JS para capturar GPS real do celular/dispositivo
js_geo = """
<script>
function getGPS() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                document.getElementById("gps_res").innerHTML = 
                    "<b>✅ Coordenadas Capturadas do GPS:</b> Lat " + lat.toFixed(6) + ", Lon " + lon.toFixed(6);
                window.parent.postMessage({type: 'streamlit:setComponentValue', value: {lat: lat, lon: lon}}, '*');
            },
            function(error) {
                document.getElementById("gps_res").innerHTML = "⚠️ Não foi possível obter o GPS: " + error.message;
            },
            {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
        );
    } else {
        document.getElementById("gps_res").innerHTML = "⚠️ Geolocation não suportada pelo navegador.";
    }
}
</script>
<button onclick="getGPS()" style="background-color: #1e3a8a; color: white; border: none; padding: 10px 18px; border-radius: 6px; font-weight: bold; cursor: pointer;">
    📍 Capturar Minha Localização Atual (GPS)
</button>
<div id="gps_res" style="margin-top: 8px; font-family: sans-serif; font-size: 14px; color: #334155;"></div>
"""

gps_data = components.html(js_geo, height=80)

col_map1, col_map2 = st.columns([1.1, 0.9])

with col_map1:
    # Caso o GPS não tenha sido clicado, dá a opção manual preenchida com padrão Osório/RS
    lat_manual = st.number_input("Latitude (Ajuste ou Coordenada do GPS):", value=-29.887200, format="%.6f")
    lon_manual = st.number_input("Longitude (Ajuste ou Coordenada do GPS):", value=-50.264100, format="%.6f")
    
    geo_exata = obter_detalhes_geograficos_exatos(lat_manual, lon_manual)
    st.info(f"📌 **Endereço Geocodificado:** {geo_exata['endereco_completo']}")
    st.success(f"🏔️ **Altitude Exata no Terreno:** {geo_exata['altitude_m']}")
    
    geo_payload = {
        "endereco": f"Lat {lat_manual:.6f}, Lon {lon_manual:.6f} ({geo_exata['endereco_completo']})",
        "altitude": geo_exata['altitude_m']
    }

with col_map2:
    df_mapa = pd.DataFrame({"lat": [lat_manual], "lon": [lon_manual]})
    st.map(df_mapa, zoom=15)

st.markdown("---")

# 3. UPLOAD DE FOTOS (COM CORREÇÃO DE ROTAÇÃO EXIF)
st.subheader("📸 3. Registros Fotográficos dos Ambientes da Escola")
st.caption("Selecione fotos de salas de aula, corredores, ginásio, pátio externo e planta baixa. O sistema corrige automaticamente a rotação de fotos do celular.")

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
        with st.spinner("Realizando auditoria individual de cada imagem e calculando zonas de abrigo..."):
            laudo_completo = analisar_lote_escola(lote_b64, nome_escola, municipio_input, geo_payload, obs_gerais)
            st.session_state["laudo_unificado"] = laudo_completo
            
            # Gera o PDF executivo
            pdf_bytes = gerar_pdf_laudo(nome_escola, municipio_input, geo_payload, laudo_completo)
            st.session_state["pdf_bytes"] = pdf_bytes

    if "laudo_unificado" in st.session_state and st.session_state["laudo_unificado"]:
        st.markdown(st.session_state["laudo_unificado"])
        
        st.markdown("---")
        if "pdf_bytes" in st.session_state:
            st.download_button(
                label="📄 Baixar Relatório Oficial em PDF (Estilo Defesa Civil)",
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
    
