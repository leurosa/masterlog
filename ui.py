
import streamlit as st

def mostrar_previsualizacao(df_visivel, key_prefix):
    n_linhas = st.slider(
        "Linhas para mostrar",
        min_value=0,
        max_value=len(df_visivel),
        value=10,
        key=f"{key_prefix}_slider"
    )
    st.dataframe(df_visivel.head(n_linhas))
