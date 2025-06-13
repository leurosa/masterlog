import streamlit as st
import pandas as pd
import os
from utils import processar_multiplos_logs, gerar_grafico
from ui import mostrar_previsualizacao

st.set_page_config(
    page_title="Master Log Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
creds = st.secrets.get("credentials", {})
if not creds:
    st.error("❌ Seção [credentials] não encontrada em Secrets")
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

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


st.sidebar.success(f"✔️ Logado como `{st.session_state.username}`")
st.title("📊 Master Log Viewer")


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
                df = log["df"]
                df_visivel = log["df_visivel"]

                mostrar_previsualizacao(df_visivel, nome_log=log["nome"])

                eixo_y = st.multiselect(
                    "📊 Selecione até 4 colunas para o gráfico",
                    df_visivel.columns,
                    max_selections=4,
                    key=log["nome"]
                )
                if eixo_y:
                    gerar_grafico(df, eixo_y)
