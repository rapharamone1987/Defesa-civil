import streamlit as st
import pandas as pd
import requests
import base64
import os

# 1. Configuração da Página
st.set_page_config(
    page_title="Escola Resiliente IA — Gestão de Riscos",
    page_icon="🏫",
    layout="wide"
)

# Estilização CSS para cartões e alertas
st.markdown("""
    <style>
    .card-alerta {
        background-color: #fef2f2 !important;
        border-left: 5px solid #ef4444 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
    .card-seguro {
        background-color: #f0fdf4 !important;
        border-left: 5px solid #22c55e !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏫 Escola Resiliente IA")
st.caption("Sistema Tático de Mapeamento de Riscos e Zonas de Abrigo Escolar — Defesa Civil")
st.markdown("---")

# 2. Leitura da Chave API
def obter_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and hasattr(st, "secrets"):
        api_key = st.secrets.get("GROQ_API_KEY", None)
    return api_key

API_KEY_GROQ = obter_groq_api_key()

# Função para converter a imagem em Base64
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# 3. Motor de Visão Computacional com Groq (Llama 3.2 11B Vision)
def analisar_infraestrutura_escola(image_b64, tipo_ambiente, nome_escola):
    if not API_KEY_GROQ:
        return "⚠️ Chave `GROQ_API_KEY` não foi encontrada nos Secrets do Streamlit."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY_GROQ}"
    }

    prompt_sistema = """
    Você é um Engenheiro de Defesa Civil e Perito em Gestão de Riscos Estruturais em Escolas.
    Analise a imagem enviada (foto de ambiente escolar ou planta baixa) e identifique vulnerabilidades a eventos climáticos extremos.

    Estruture o relatório técnico rigorosamente nestas 3 seções em Markdown:

    ### 🔍 1. Diagnóstico Estrutural & Elementos Identificados
    Liste os elementos visíveis na imagem (ex: janelas de vidro, telhas de fibrocimento/zinco, árvores próximas, lajes de alvenaria, estrutura metálica, corredores).

    ### ⚠️ 2. Vulnerabilidades por Evento Climático
    - **Vendavais / Microexplosões:** Identifique riscos de estilhaçamento de vidro, destelhamento ou queda de estruturas.
    - **Enxurradas / Inundações:** Avalie o nível do solo, fiação e rotas de elevação/evacuação.
    - **Granizo:** Avalie fragilidade do teto e claraboias.

    ### 🛡️ 3. Protocolo de Ação & Classificação do Local
    Classifique o ambiente como: **[ZONA DE PERIGO]** ou **[ABRIGO SEGURO RECOMENDADO]** para cada situação e determine a orientação prática imediata para professores e alunos.
    """

    prompt_usuario = f"Esta é uma imagem da escola '{nome_escola}', do ambiente: '{tipo_ambiente}'. Faça a análise detalhada de risco."

    payload = {
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_usuario},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "model": "llama-3.2-11b-vision-preview",
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=25)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ Erro no processamento da imagem (Código HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Erro de conexão com o serviço de visão computacional: {e}"

# 4. Painel Lateral e Entrada de Dados
st.sidebar.header("📋 Cadastro do Estabelecimento")

nome_escola = st.sidebar.text_input("Nome da Escola:", "EEEB Marquês de Herval")
municipio = st.sidebar.text_input("Município / RS:", "Osório")
tipo_ambiente = st.sidebar.selectbox(
    "Selecione o Ambiente da Foto:",
    [
        "Sala de Aula (Com Janelas)",
        "Corredor Central / Passarela",
        "Ginásio de Esportes / Cobertura Leve",
        "Pátio Externo / Muro / Árvores",
        "Planta Baixa / Mapa do Prédio"
    ]
)

st.sidebar.markdown("---")
if API_KEY_GROQ:
    st.sidebar.success("🤖 Groq Vision IA: **Conectado**")
else:
    st.sidebar.error("🤖 Groq Vision IA: **Configure a GROQ_API_KEY**")

# 5. Interface Principal
col_upload, col_resultado = st.columns([1, 1.2])

with col_upload:
    st.subheader("📸 Registre a Estrutura da Escola")
    st.caption("Envie fotos do ambiente ou da planta baixa para auditoria preditiva de risco.")
    
    foto_uploaded = st.file_uploader(
        "Upload da foto ou planta (JPG/PNG):", 
        type=["jpg", "png", "jpeg"]
    )

    if foto_uploaded:
        st.image(foto_uploaded, caption=f"Ambiente: {tipo_ambiente} — {nome_escola}", use_column_width=True)

with col_resultado:
    st.subheader("🛡️ Laudo Técnico de Resiliência & Abrigo")
    
    if foto_uploaded:
        if st.button("🚨 Processar Análise de Vulnerabilidade (IA)", type="primary"):
            with st.spinner("Analisando elementos estruturais e padrões de risco com Llama Vision..."):
                img_b64 = encode_image(foto_uploaded)
                laudo = analisar_infraestrutura_escola(img_b64, tipo_ambiente, nome_escola)
                st.session_state["laudo_escola"] = laudo

        if "laudo_escola" in st.session_state and st.session_state["laudo_escola"]:
            st.markdown(st.session_state["laudo_escola"])
    else:
        st.info("👈 Faça o upload de uma foto no painel ao lado para gerar a matriz de segurança.")

st.markdown("---")

# 6. Tabela Guia de Protocolos Padronizados (SOP Escolar)
st.subheader("🚨 Guia Rápido de Emergência Escolar (Defesa Civil)")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="card-alerta">
        <h4>💨 Vendavais & Microexplosões</h4>
        <ul>
            <li><b>Evitar:</b> Ginásios, auditórios e salas com fachadas de vidro.</li>
            <li><b>Ação:</b> Mover alunos para corredores internos com laje sólida.</li>
            <li><b>Posição:</b> Agachar, de costas para aberturas, protegendo o pescoço.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="card-alerta">
        <h4>🌊 Enxurradas Rápida</h4>
        <ul>
            <li><b>Evitar:</b> Térreo, pátios rebaixados e subsolos.</li>
            <li><b>Ação:</b> Evacuação vertical imediata para o 2º pavimento.</li>
            <li><b>Energia:</b> Desligar chave geral antes de o nível da água atingir tomadas.</li>
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
            <li><b>Rotas:</b> Manter corredores livres de armários ou obstáculos.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
