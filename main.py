import streamlit as st
from utils import processar_multiplos_logs, gerar_grafico
from ui import mostrar_previsualizacao
import time

# 1) layout centered para o login
st.set_page_config(
    page_title="Master Log Viewer",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2) credenciais via Secrets
creds = st.secrets.get("credentials", {})
if not creds:
    st.error("❌ Seção [credentials] não encontrada em Secrets")
    st.stop()

# 3) estado de login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 4) tela de login com popup temporário
def show_login():
    st.title("🔒 Master Log Viewer — Login")
    user = st.text_input("Usuário", value=st.session_state.username)
    pwd  = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if creds.get(user) == pwd:
            st.session_state.logged_in = True
            st.session_state.username = user
            ph = st.empty()
            ph.success(f"✔️ Logado como {user}")
            time.sleep(2)
            ph.empty()
        else:
            st.error("❌ Usuário ou senha inválidos")
    st.stop()

if not st.session_state.logged_in:
    show_login()

# 5) após login, força layout wide
st.markdown(
    """
    <style>
      .block-container { max-width:100% !important; padding:1rem 2rem !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# 6) app principal
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
                mostrar_previsualizacao(log["df_visivel"], key_prefix=log["key"])
                sel = st.multiselect(
                    "📊 Selecione até 4 colunas",
                    log["df_visivel"].columns,
                    max_selections=4,
                    key=f"ms_{log['key']}"
                )
                if sel:
                    gerar_grafico(log["df"], sel, rpm_col="RPM")
