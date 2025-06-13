
import streamlit as st

def mostrar_previsualizacao(df_visivel, nome_log):
    n_linhas = st.slider(
        "🔍 Número de linhas para visualizar",
        min_value=5, max_value=2000, value=20, step=5,
        key=f"slider_{nome_log}"
    )
    st.dataframe(df_visivel.head(n_linhas), use_container_width=True)