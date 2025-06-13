import streamlit as st
import pandas as pd
import os
from utils import processar_multiplos_logs, gerar_grafico
from ui import mostrar_previsualizacao

# 1) CONFIGURAÇÃO DA PÁGINA — deve ser a primeira coisa do app!
st.set_page_config(
    page_title="Master Log Viewer",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2) BUSCA CREDENCIAIS NO SECRETS (Streamlit Cloud)
creds = st.secrets.get("credentials", {})
if not creds:
    st.error("❌ Seção [credentials] não encontrada em Secrets")
    st.stop()

# 3) ESTADO DE LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 4) TELA DE LOGIN
def show_login():
    st.title("🔒 Master Log Viewer — Login")
    user = st.text_input("Usuário", value=st.session_state.username)
    pwd  = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if creds.get(user) == pwd:
            st.session_state.logged_in = True
            st.session_state.username = user
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

if not st.session_state.logged_in:
    show_login()
   
st.markdown(
    """
    <style>
      .block-container {
        max-width: 100% !important;
        padding: 1rem 2rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# 5) APP PRINCIPAL (só roda quando logado)
st.sidebar.success(f"✔️ Logado como `{st.session_state.username}`")
st.title("📊 Master Log Viewer")

# 6) UPLOAD E PROCESSAMENTO DE LOGS
arquivo = st.file_uploader("📂 Envie o arquivo CSV do log", type="csv")
if arquivo:
    logs, erro = processar_multiplos_logs(arquivo)

    if erro:
        st.error(f"❌ Erro ao processar o arquivo: {erro}")
    elif not logs:
        st.warning("⚠️ Nenhum log foi encontrado no arquivo.")
    else:
        abas = st.tabs([log["nome"] for log in logs])
        for aba, log in zip(abas, logs):
            with aba:
                mostrar_previsualizacao(
                    log["df_visivel"],
                    key_prefix=log["key"]
                )
                eixo_y = st.multiselect(
                    "📊 Selecione até 8 colunas",
                    log["df_visivel"].columns,
                    max_selections=8,
                    key=f"multiselect_{log['key']}"
                )
                if eixo_y:
                    gerar_grafico(log["df"], eixo_y, rpm_col="RPM")
