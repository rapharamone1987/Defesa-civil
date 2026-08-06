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

# 2. Estilização CSS de Alto Contraste (Fontes Escuras e Leitura Perfeita)
st.markdown("""
    <style>
    /* Força cores escuras em todos os textos para garantir legibilidade */
    div[data-testid="stMarkdownContainer"] p, 
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] h1,
    div[data-testid="stMarkdownContainer"] h2,
    div[data-testid="stMarkdownContainer"] h3,
    div[data-testid="stMarkdownContainer"] h4 {
        color: #0f172a !important;
        word-wrap: break-word !important;
        white-space: normal !important;
    }
    
    /* Cartões de Alto Contraste */
    .card-alerta {
        background-color: #fef2f2 !important;
        border: 2px solid #dc2626 !important;
        border-left: 8px solid #dc2626 !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
    
    .card-seguro {
        background-color: #f0fdf4 !important;
        border: 2px solid #16a34a !important;
        border-left: 8px solid #16a34a !important;
        padding: 16px !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
    
    .card-alerta h4, .card-seguro h4 {
        color: #0f172a !important;
        margin-top: 0px !important;
        font-weight: 800 !important;
    }
    
    .card-alerta li, .card-seguro li, .card-alerta p, .card-seguro p {
        color: #1e293b !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        line-height: 1.5 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏫 Escola Resiliente IA")
st.caption("Sistema Tático de Mapeamento de Riscos e Zonas de Abrigo Escolar — Defesa Civil")
st.markdown("---")

# 3. Leitura da Chave API
def obter_groq_api_key():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and hasattr(st, "secrets"):
        api_key = st.secrets.get("GROQ_API_KEY", None)
    return api_key

API_KEY_GROQ = obter_groq_api_key()

def encode_image(file_bytes):
    return base64.b64encode(file_bytes).decode('utf-8')

# 4. Motor de Visão Computacional para Múltiplas Imagens (Groq Llama 3.2 Vision)
def analisar_lote_escola(imagens_list, nome_escola, municipio, observacoes_gerais):
    if not API_KEY_GROQ:
        return "⚠️ Chave `GROQ_API_KEY` não foi encontrada nos Secrets do Streamlit."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY_GROQ}"
    }

    prompt_sistema = """
    Você é um Engenheiro Sênior de Defesa Civil especialista em Vistoria de Riscos Estruturais em Escolas.
    Você receberá um conjunto de fotos cobrindo múltiplos ambientes de uma mesma escola (ex: salas de aula, ginásio, corredores, pátio e/ou planta baixa).

    Analise as imagens de forma INTEGRADA e elabore um PLANO DE CONTINGÊNCIA E RESILIÊNCIA ESCOLAR completo em Markdown bem estruturado, com o seguinte padrão:

    ### 🏫 1. Resumo da Auditoria Integrada
    Apresente um panorama geral da infraestrutura observada e nível de resiliência global do estabelecimento.

    ### 🔍 2. Diagnóstico por Ambiente Mapeado
    Para cada imagem fornecida, identifique o ambiente e enumere as vulnerabilidades físicas (ex: fachadas de vidro, coberturas de fibrocimento/zinco, ausência de laje, árvores de grande porte, desníveis de piso).

    ### 🛡️ 3. Matriz Tática de Zonas de Abrigo por Evento Extremo
    Crie uma tabela ou lista clara separando os ambientes da escola em:
    - **Vendavais / Microexplosões:** [ZONA DE PERIGO A EVITAR] vs [ZONA DE ABRIGO RECOMENDADA]
    - **Enxurradas / Inundações:** [ZONA DE PERIGO A EVITAR] vs [ZONA DE ELEVAÇÃO RECOMENDADA]
    - **Granizo Severo:** [ZONA DE PERIGO A EVITAR] vs [ZONA DE PROTEÇÃO RECOMENDADA]

    ### 🚨 4. Plano Prático de Ação e Rota de Evacuação/Abrigo
    Orientações diretas para a direção, professores e brigada escolar sobre como agir nos primeiros 3 minutos de um alerta.
    """

    content_payload = [
        {
            "type": "text", 
            "text": f"Escola: '{nome_escola}' ({municipio}/RS).\nObservações Adicionais do Gestor: '{observacoes_gerais}'.\nAnalise o conjunto de {len(imagens_list)} fotos anexadas e gere o laudo completo de resiliência."
        }
    ]

    # Anexa todas as imagens no payload da API
    for img_b64 in imagens_list:
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
        "model": "llama-3.2-11b-vision-preview",
        "temperature": 0.2
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            return f"⚠️ Erro no processamento do lote de imagens (Código HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"⚠️ Erro de conexão com a API do Groq Vision: {e}"

# 5. Painel Lateral (Inputs do Usuário)
st.sidebar.header("📋 Cadastro do Estabelecimento")

nome_escola = st.sidebar.text_input("Nome da Escola:", "EEEB Marquês de Herval")
municipio = st.sidebar.text_input("Município / RS:", "Osório")
obs_gerais = st.sidebar.text_area("Observações / Histórico de Eventos Locais:", "Escola próxima a encosta/rio. Ginásio com telha leve.")

st.sidebar.markdown("---")
if API_KEY_GROQ:
    st.sidebar.success("🤖 Groq Vision IA: **Conectado**")
else:
    st.sidebar.error("🤖 Groq Vision IA: **Configure a GROQ_API_KEY**")

# 6. Área Principal
st.subheader("📸 Registre Todos os Ambientes da Escola (Upload Simultâneo)")
st.caption("Selecione fotos de salas de aula, corredores, ginásio, pátio externo e planta baixa de uma só vez.")

# Upload Múltiplo
arquivos_uploaded = st.file_uploader(
    "Carregue as fotos dos ambientes da escola (Selecione vários arquivos JPG/PNG):", 
    type=["jpg", "png", "jpeg"],
    accept_multiple_files=True
)

if arquivos_uploaded:
    st.write(f"📂 **{len(arquivos_uploaded)} ambiente(s) selecionado(s) para análise:**")
    cols = st.columns(min(len(arquivos_uploaded), 4))
    for i, file in enumerate(arquivos_uploaded):
        with cols[i % 4]:
            st.image(file, caption=f"Foto {i+1}: {file.name}", use_column_width=True)

st.markdown("---")

st.subheader("🛡️ Laudo Técnico Unificado de Resiliência & Zonas de Abrigo")

if arquivos_uploaded:
    if st.button("🚨 Processar Auditoria Completa da Escola (IA Multimodal)", type="primary"):
        with st.spinner(f"Analisando lote de {len(arquivos_uploaded)} fotos e mapeando zonas de abrigo com IA Vision..."):
            # Converte todas as fotos para Base64
            lote_b64 = [encode_image(f.getvalue()) for f in arquivos_uploaded]
            laudo_completo = analisar_lote_escola(lote_b64, nome_escola, municipio, obs_gerais)
            st.session_state["laudo_unificado"] = laudo_completo

    if "laudo_unificado" in st.session_state and st.session_state["laudo_unificado"]:
        st.markdown(st.session_state["laudo_unificado"])
else:
    st.info("👈 Faça o upload das fotos dos ambientes da escola acima para gerar o laudo integrado.")

st.markdown("---")

# 7. Guia Rápido com Fontes Escuras
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
        <h4>🌊 Enxurradas Rápida</h4>
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
    
